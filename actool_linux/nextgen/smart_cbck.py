from __future__ import annotations
import struct
import json
import numpy as np
from pathlib import Path

try:
    from actool_linux.stable import lzfse_compat as lzfse
except ImportError:
    lzfse = None

# AppleのDMP2/CBCKフォーマットの定数
DMP2_CBCK_CHUNK_RAW_CAP = 16384 # 16KB

class SmartCBCKEncoder:
    def __init__(self, clean_alpha: bool = True, max_chunk_size: int = 128):
        self.clean_alpha = clean_alpha
        self.max_chunk_size = max_chunk_size
        self._load_ai_model()
        
    def _load_ai_model(self):
        try:
            weights_path = Path(__file__).resolve().parent.parent / "data" / "micro_ai_weights.json"
            with open(weights_path, "r") as f:
                w = json.load(f)
            self.W1 = np.array(w["W1"])
            self.b1 = np.array(w["b1"])
            self.W2 = np.array(w["W2"])
            self.b2 = np.array(w["b2"])
            self.ai_ready = True
        except Exception:
            self.ai_ready = False

    def _ai_predict_strategy(self, chunk_np: np.ndarray) -> int:
        """AIモデルでチャンクの最適な圧縮戦略を推論する"""
        if not self.ai_ready:
            return 1 # Fallback to LZFSE
            
        h, w, _ = chunk_np.shape
        total_pixels = w * h
        if total_pixels == 0: return 0
        
        # 特徴量抽出
        alpha_zero_ratio = np.sum(chunk_np[:, :, 3] == 0) / total_pixels
        # 高速化のため色数カウントはサンプリング
        sample = chunk_np.view(np.uint32).flatten()[::max(1, total_pixels//100)]
        unique_color_ratio = len(np.unique(sample)) / len(sample)
        # 簡易エッジ密度
        gray = np.mean(chunk_np[:, :, :3], axis=2)
        edge_density = np.sum(np.abs(np.diff(gray, axis=1))) / (total_pixels * 255)
        
        X = np.array([alpha_zero_ratio, unique_color_ratio, edge_density])
        
        # 推論 (Inference)
        z1 = np.dot(X, self.W1) + self.b1
        a1 = np.maximum(0, z1)
        z2 = np.dot(a1, self.W2) + self.b2
        return int(np.argmax(z2))

    def _clean_dirty_transparency(self, img_np: np.ndarray) -> np.ndarray:
        mask = img_np[:, :, 3] == 0
        img_np[mask, 0:3] = 0
        return img_np

    def _quadtree_chunk(self, data_mv: memoryview, w: int, h: int, x: int, y: int, cw: int, ch: int, min_size: int = 32) -> list[tuple[int, int, int, bytes]]:
        chunk_data = bytearray(cw * ch * 4)
        row_bytes = w * 4
        offset = 0
        for cy in range(ch):
            start = (y + cy) * row_bytes + x * 4
            chunk_data[offset:offset+cw*4] = data_mv[start:start+cw*4]
            offset += cw * 4
            
        is_solid = (chunk_data == chunk_data[:4] * (len(chunk_data) // 4))
        if is_solid or (cw <= min_size and ch <= min_size):
            return [(x, y, ch, bytes(chunk_data))]
            
        hw, hh = cw // 2, ch // 2
        chunks = []
        chunks.extend(self._quadtree_chunk(data_mv, w, h, x, y, hw, hh, min_size))
        chunks.extend(self._quadtree_chunk(data_mv, w, h, x + hw, y, hw, hh, min_size))
        chunks.extend(self._quadtree_chunk(data_mv, w, h, x, y + hh, hw, hh, min_size))
        chunks.extend(self._quadtree_chunk(data_mv, w, h, x + hw, y + hh, hw, hh, min_size))
        return chunks

    def _compress_chunk_apple_format(self, chunk_data: bytes, width: int, height: int) -> bytes:
        if lzfse is None:
            return b"dmp2" + struct.pack("<4BHHHH", 4, 1, 10, 4, width, height, 1, 4) + chunk_data[:4] + struct.pack("<I", len(chunk_data)) + chunk_data
            
        chunk_np = np.frombuffer(chunk_data, dtype=np.uint8).reshape((height, width, 4))
        strategy = self._ai_predict_strategy(chunk_np)
        
        # AIがRLEと判断した場合
        if strategy == 0 and chunk_data == chunk_data[:4] * (len(chunk_data) // 4):
            indices = b"\x00" * (width * height)
            stream = lzfse.compress(indices)
            return (b"dmp2" + bytes((4, 1, 10, 4)) + struct.pack("<HHHH", width, height, 1, 4)
                    + chunk_data[:4] + struct.pack("<I", len(stream)) + stream)
        
        comp = lzfse.compress(chunk_data)
        
        # AIがRawと判断、または圧縮負けした場合
        if strategy == 2 or len(comp) >= len(chunk_data):
            from actool_linux.stable.lzfse_compat import _UNCOMPRESSED_MAGIC, _END_OF_STREAM_MAGIC
            raw_stream = _UNCOMPRESSED_MAGIC + struct.pack("<2I", len(chunk_data), len(chunk_data)) + chunk_data + _END_OF_STREAM_MAGIC
            return b"dmp2" + struct.pack("<4BHHHH", 4, 1, 10, 4, width, height, 1, 4) + b"\x00\x00\x00\x00" + struct.pack("<I", len(raw_stream)) + raw_stream
            
        return b"dmp2" + struct.pack("<4BHHHH", 4, 1, 10, 4, width, height, 1, 4) + b"\x00\x00\x00\x00" + struct.pack("<I", len(comp)) + comp

    def encode(self, data: bytes, w: int, h: int) -> bytes:
        img_np = np.frombuffer(data, dtype=np.uint8).reshape((h, w, 4)).copy()
        if self.clean_alpha: img_np = self._clean_dirty_transparency(img_np)
            
        mv = memoryview(img_np.tobytes())
        raw_chunks = self._quadtree_chunk(mv, w, h, 0, 0, w, h, min_size=64)
        
        encoded_chunks = []
        for x, y, rows, c_data in raw_chunks:
            dmp2_payload = self._compress_chunk_apple_format(c_data, w, rows)
            blob = struct.pack("<4I", 1, 4, len(dmp2_payload), 0) + dmp2_payload
            encoded_chunks.append(b"KCBC" + struct.pack("<4I", x, y, rows, len(blob)) + blob)
            
        payload = b"MLEC" + struct.pack("<3I", 3, 11, len(encoded_chunks)) + b"".join(encoded_chunks)
        return payload

