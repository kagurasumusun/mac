from __future__ import annotations
import numpy as np
try:
    from sklearn.cluster import KMeans
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

class PerceptualQuantizer:
    """
    【進化B】知覚的ロスレス（AIパレット強制減色）エンジン
    K-Means法を用いて、人間の目には劣化が分からないレベルで画像の色数を
    強制的に16色や256色に削減（減色）します。
    これにより、後段の LPC (Local-Palette Chunking) が100%発動し、
    ファイルサイズが劇的に減少します。
    """
    def __init__(self, max_colors: int = 256, use_dithering: bool = False):
        self.max_colors = max_colors
        self.use_dithering = use_dithering
        
    def _floyd_steinberg_dither(self, img_np: np.ndarray, palette: np.ndarray) -> np.ndarray:
        """
        Floyd-Steinberg ディザリングを適用し、バンディングを抑える。
        Python/NumPyでのプロトタイプ実装 (処理が重いためC/Cython推奨)。
        """
        # プロトタイプのため、現状は最も近い色に割り当てるのみ（ディザなし）をフォールバックとして返す
        # ※ 完全なディザリングはループ処理が必要なため
        pixels = img_np.reshape(-1, img_np.shape[2])
        distances = np.sum((pixels[:, None] - palette) ** 2, axis=2)
        labels = np.argmin(distances, axis=1)
        return palette[labels].reshape(img_np.shape)

    def quantize(self, img_np: np.ndarray) -> tuple[np.ndarray, bool]:
        """
        画像をK-Meansで減色する。
        戻り値: (減色された画像配列, パレット化に成功したか)
        """
        if not HAS_SKLEARN:
            print("Warning: scikit-learn is not installed. Using basic quantization fallback.")
            return self._fallback_quantize(img_np)
            
        h, w, c = img_np.shape
        if c not in (3, 4):
            return img_np, False
            
        # 1. 画像を2次元のピクセル配列に変形
        pixels = img_np.reshape(-1, c).astype(np.float32)
        
        # 2. 既に色数が少ない場合はスキップ
        unique_colors = np.unique(pixels, axis=0)
        if len(unique_colors) <= self.max_colors:
            return img_np, True
            
        # 3. K-Means クラスタリングで最適な代表色(パレット)を見つける
        sample_size = min(10000, len(pixels))
        sample_pixels = pixels[np.random.choice(len(pixels), sample_size, replace=False)]
        
        kmeans = KMeans(n_clusters=self.max_colors, n_init=1, random_state=42)
        kmeans.fit(sample_pixels)
        
        # 4. 全ピクセルを最も近いパレット色に置き換える
        palette = kmeans.cluster_centers_.astype(np.uint8)
        
        if self.use_dithering:
            quantized_img = self._floyd_steinberg_dither(img_np, palette)
        else:
            labels = kmeans.predict(pixels)
            quantized_pixels = palette[labels]
            quantized_img = quantized_pixels.reshape((h, w, c))
            
        return quantized_img, True

    def _fallback_quantize(self, img_np: np.ndarray) -> tuple[np.ndarray, bool]:
        """
        scikit-learnがない環境用の超高速な減色(ポスタリゼーション)。
        上位ビットだけを残すことで色数を減らす。
        """
        # 例: 256色(各RGB3ビット程度)にするために下位5ビットを切り捨てる
        # 0b11100000 (224) とANDをとる
        quantized = (img_np & 224)
        return quantized, True
