"""Hybrid LPC-Planar-Delta Compression — 新世代の適応的圧縮エンジン.

このモジュールはLPC-LZFSEとPlanar-Delta LZFSEの長所を融合した
適応的ハイブリッド圧縮アルゴリズムを実装します。

## アルゴリズム概要

各チャンクに対して以下の分析を行い、最適な前処理を自動選択：

1. **特徴量抽出**:
   - 色数（unique colors）
   - エッジ密度（隣接ピクセルの差分）
   - 透過率（alpha=0の割合）
   - エントロピー（情報量）

2. **戦略選択（AI or ヒューリスティック）**:
   - **低色数 + 高エッジ**（UI要素、テキスト）
     → LPC色数削減 + BGRA再構築 → LZFSE
   - **高透過 + 低エントロピー**（背景、単色領域）
     → Planar-Delta量子化 → LZFSE
   - **グラデーション + 低差分**（滑らかな変化）
     → Planar-Delta量子化 → LZFSE
   - **高エントロピー**（写真、ノイズ）
     → そのままLZFSE

3. **共通前処理**:
   - ダーティアルファのクリーニング（RGB=0 where alpha=0）
   - これは常に適用（Appleの標準動作と同じ）

## Apple互換性

全ての出力は**有効なBGRAピクセルをLZFSE圧縮**したもの。
AppleのCBCKパーサー（stable/cbck.py parse_cbck()）で
正常にデコード可能。

ただし、LPC色数削減とPlanar-Delta量子化は**不可逆**なので、
元画像と完全に同一にはならない（視覚的にほぼ同等）。
"""
from __future__ import annotations

import struct
import json
import numpy as np
from pathlib import Path

try:
    from . import lzfse_compat as lzfse
except ImportError:
    try:
        import lzfse  # type: ignore
    except ImportError:
        lzfse = None  # type: ignore


# 戦略定数
STRATEGY_DIRECT = 0       # そのままLZFSE（高エントロピー）
STRATEGY_LPC = 1          # LPC色数削減（低色数、高エッジ）
STRATEGY_PLANAR = 2       # Planar-Delta量子化（グラデーション）
STRATEGY_AGGRESSIVE = 3   # LPC + Planar両方（超低エントロピー）


class HybridCompressor:
    """LPC + Planar-Delta 融合型適応圧縮エンジン."""

    def __init__(self, clean_alpha: bool = True, lpc_max_colors: int = 256,
                 planar_quant_step: int = 8, use_ai: bool = False):
        """
        Args:
            clean_alpha: ダーティアルファをクリーニングするか
            lpc_max_colors: LPCの最大パレット色数
            planar_quant_step: Planar量子化のステップサイズ（8 = 3ビット精度）
            use_ai: マイクロAIモデルで戦略選択するか（デフォルトFalse=ヒューリスティック）
        """
        self.clean_alpha = clean_alpha
        self.lpc_max_colors = lpc_max_colors
        self.planar_quant_step = planar_quant_step
        self.use_ai = use_ai
        self._load_ai_model()

    def _load_ai_model(self) -> None:
        """マイクロAIモデルを読み込む（存在しない場合はヒューリスティック）."""
        try:
            weights_path = Path(__file__).resolve().parent.parent / "data" / "micro_ai_weights.json"
            with open(weights_path, "r") as f:
                w = json.load(f)
            self._W1 = np.array(w["W1"], dtype=np.float32)
            self._b1 = np.array(w["b1"], dtype=np.float32)
            self._W2 = np.array(w["W2"], dtype=np.float32)
            self._b2 = np.array(w["b2"], dtype=np.float32)
            self.ai_ready = True
        except Exception:
            self.ai_ready = False

    def analyze_chunk(self, bgra: np.ndarray) -> dict:
        """チャンクの特徴量を分析.

        Returns:
            {
                'unique_colors': int,
                'edge_density': float (0-1),
                'transparency_ratio': float (0-1),
                'entropy_estimate': float (0-1),
                'recommended_strategy': int
            }
        """
        h, w = bgra.shape[:2]
        total_pixels = h * w
        flat = bgra.reshape(-1, 4)

        # 1. ユニーク色数
        unique_colors = len(np.unique(flat.view(np.uint32).flatten()))
        color_ratio = unique_colors / total_pixels

        # 2. エッジ密度（水平方向の差分）
        if w > 1:
            gray = bgra[:, :, :3].mean(axis=2).astype(np.float32)
            edge_density = float(np.sum(np.abs(np.diff(gray, axis=1)))) / (total_pixels * 255)
        else:
            edge_density = 0.0

        # 3. 透過率
        transparency_ratio = float(np.sum(flat[:, 3] == 0)) / total_pixels

        # 4. エントロピー推定（色の分散）
        entropy_estimate = float(np.std(flat[:, :3].astype(np.float32))) / 128.0

        # 5. 推奨戦略
        recommended = self._select_strategy(
            color_ratio, edge_density, transparency_ratio, entropy_estimate
        )

        return {
            'unique_colors': unique_colors,
            'color_ratio': color_ratio,
            'edge_density': edge_density,
            'transparency_ratio': transparency_ratio,
            'entropy_estimate': entropy_estimate,
            'recommended_strategy': recommended,
        }

    def _select_strategy(self, color_ratio: float, edge_density: float,
                         transparency_ratio: float, entropy_estimate: float) -> int:
        """特徴量から最適な戦略を選択."""
        if self.use_ai and self.ai_ready:
            # AI推論（モデルが4クラス対応の場合のみ）
            if self._W2.shape[1] >= 4:
                X = np.array([color_ratio, edge_density, transparency_ratio], dtype=np.float32)
                z1 = X @ self._W1 + self._b1
                a1 = np.maximum(0, z1)
                z2 = a1 @ self._W2 + self._b2
                return int(np.argmax(z2))
            # AIモデルが3クラスのみ→ヒューリスティックにフォールバック

        # ヒューリスティック戦略選択
        # 1. 超低エントロピー（単色 + 透過）→ Aggressive (LPC+Planar両方)
        if transparency_ratio > 0.9 and color_ratio < 0.01:
            return STRATEGY_AGGRESSIVE

        # 2. 低色数 + 高エッジ（UI要素、テキスト）→ LPC
        if color_ratio < 0.01 and edge_density > 0.01:
            return STRATEGY_LPC

        # 3. 低色数（フラットカラー）→ LPC
        if color_ratio < 0.01:
            return STRATEGY_LPC

        # 4. 高色数 + 低エッジ + 低透過（グラデーション）→ Planar-Delta
        if color_ratio > 0.5 and edge_density < 0.05 and transparency_ratio < 0.3:
            return STRATEGY_PLANAR

        # 5. 中エントロピー + 低エッジ → Planar-Delta
        if entropy_estimate > 0.3 and edge_density < 0.05:
            return STRATEGY_PLANAR

        # 6. デフォルト → Direct（写真、ノイズ、複雑な画像）
        return STRATEGY_DIRECT

    def _clean_dirty_alpha(self, bgra: np.ndarray) -> np.ndarray:
        """ダーティアルファをクリーニング（alpha=0のピクセルのRGBを0に）."""
        result = bgra.copy()
        mask = result[:, :, 3] == 0
        result[mask, :3] = 0
        return result

    def _apply_lpc(self, bgra: np.ndarray) -> np.ndarray:
        """LPC色数削減を適用.

        パレットを構築し、各ピクセルを最近傍色に量子化。
        結果はBGRAとして返す（Apple互換）。
        """
        from .lpc_lzfse import extract_palette, extract_palette_kmeans

        palette = extract_palette(bgra, self.lpc_max_colors)
        if palette is None:
            palette = extract_palette_kmeans(bgra, self.lpc_max_colors)

        # 各ピクセルをパレットの最近傍色に置き換え
        indices = palette.quantize(bgra)
        return palette.colors[indices]

    def _apply_planar_delta(self, bgra: np.ndarray) -> np.ndarray:
        """Planar-Delta量子化を適用.

        各チャネルで隣接ピクセルとの差分を分析し、
        差分が小さい領域を量子化（ステップ量化）する。
        """
        flat = bgra.reshape(-1, 4).astype(np.int16)
        result = flat.copy()

        # 各チャネル独立に処理
        for ch in range(4):
            channel = flat[:, ch]
            # 差分を計算
            deltas = np.zeros(len(channel), dtype=np.int16)
            deltas[1:] = channel[1:] - channel[:-1]

            # 小さな差分が多い場合、量子化を適用
            small_delta_ratio = np.sum(np.abs(deltas[1:]) <= 4) / max(1, len(deltas) - 1)

            if small_delta_ratio > 0.7:
                # ステップ量化（planar_quant_step刻み）
                step = self.planar_quant_step
                result[:, ch] = ((channel + step // 2) // step) * step

        return result.clip(0, 255).astype(np.uint8).reshape(bgra.shape)

    def compress_chunk(self, bgra: np.ndarray) -> bytes:
        """1チャンクを圧縮（Apple互換のLZFSEストリームを返す）.

        Args:
            bgra: BGRA配列 (H, W, 4), dtype uint8

        Returns:
            LZFSE圧縮されたBGRAデータ
        """
        if lzfse is None:
            return bgra.tobytes()

        # 1. ダーティアルファクリーニング
        if self.clean_alpha:
            bgra = self._clean_dirty_alpha(bgra)

        # 2. 特徴量分析
        analysis = self.analyze_chunk(bgra)
        strategy = analysis['recommended_strategy']

        # 3. 戦略適用
        if strategy == STRATEGY_LPC:
            bgra = self._apply_lpc(bgra)
        elif strategy == STRATEGY_PLANAR:
            bgra = self._apply_planar_delta(bgra)
        elif strategy == STRATEGY_AGGRESSIVE:
            # 両方適用
            bgra = self._apply_lpc(bgra)
            bgra = self._apply_planar_delta(bgra)
        # STRATEGY_DIRECT: 前処理なし

        # 4. LZFSE圧縮
        return lzfse.compress(bgra.tobytes())

    def compress_image(self, bgra: np.ndarray, chunk_rows: int = 256) -> bytes:
        """全画像をチャンク分割して圧縮（Apple CBCK形式）.

        Args:
            bgra: BGRA配列 (H, W, 4), dtype uint8
            chunk_rows: 1チャンクの行数

        Returns:
            MLEC payload (mode=3, codec=4) with KCBC chunks
        """
        if lzfse is None:
            raise RuntimeError("lzfse is required")

        h, w = bgra.shape[:2]
        chunks = []

        for y in range(0, h, chunk_rows):
            rows = min(chunk_rows, h - y)
            chunk_bgra = bgra[y:y+rows, :, :]

            # 各チャンクを圧縮
            compressed = self.compress_chunk(chunk_bgra)

            # KCBCチャンクを構築
            kcbc = (
                b"KCBC"
                + struct.pack("<4I", 0, 0, rows, len(compressed))
                + compressed
            )
            chunks.append(kcbc)

        # MLECペイロードを構築
        payload = b"MLEC" + struct.pack("<3I", 3, 4, len(chunks)) + b"".join(chunks)
        return payload


def hybrid_compress_for_cbck(bgra: np.ndarray, width: int, height: int,
                             filename: str, *, scale: int = 1) -> bytes:
    """ハイブリッド圧縮を適用したCSIレンディションを生成.

    carwriter._csi_png_cbck()のドロップイン代替として使用可能。
    """
    compressor = HybridCompressor(clean_alpha=True)
    bgra_arr = np.frombuffer(bgra, dtype=np.uint8).reshape(height, width, 4) if isinstance(bgra, bytes) else bgra.reshape(height, width, 4)
    payload = compressor.compress_image(bgra_arr)

    # ISTCヘッダー + TLVを構築
    tlvs = b"".join((
        struct.pack("<2I5I", 1001, 20, 1, 0, 0, width, height),
        struct.pack("<2I7I", 1003, 28, 1, 0, 0, 0, 0, width, height),
        struct.pack("<2I8s", 1004, 8, b"\0\0\0\0\0\0\x80?"),
        struct.pack("<2II", 1006, 4, 1),
        struct.pack("<2II", 1007, 4, width * 4),
    ))

    header = bytearray(184)
    header[:4] = b"ISTC"
    struct.pack_into("<5I", header, 4, 1, 0, width, height, scale * 100)
    header[24:28] = b"BGRA"
    struct.pack_into("<I", header, 28, 1)
    struct.pack_into("<I2H", header, 32, 0, 12, 0)

    # ファイル名フィールド（128バイト、nullパディング）
    fname_bytes = filename.encode("utf-8")[:127]
    header[40:40 + len(fname_bytes)] = fname_bytes

    struct.pack_into("<4I", header, 168, len(tlvs), 1, 0, len(payload))
    return bytes(header) + tlvs + payload
