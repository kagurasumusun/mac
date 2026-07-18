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
        
    def quantize(self, img_np: np.ndarray) -> tuple[np.ndarray, bool]:
        """
        画像をK-Meansで減色する。
        戻り値: (減色された画像配列, パレット化に成功したか)
        """
        if not HAS_SKLEARN:
            print("Warning: scikit-learn is not installed. AI Quantization skipped.")
            return img_np, False
            
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
        # 処理速度を考慮し、サンプルサイズを制限する等の工夫が必要(現在はプロトタイプ)
        sample_size = min(10000, len(pixels))
        sample_pixels = pixels[np.random.choice(len(pixels), sample_size, replace=False)]
        
        kmeans = KMeans(n_clusters=self.max_colors, n_init=1, random_state=42)
        kmeans.fit(sample_pixels)
        
        # 4. 全ピクセルを最も近いパレット色に置き換える
        labels = kmeans.predict(pixels)
        palette = kmeans.cluster_centers_.astype(np.uint8)
        
        quantized_pixels = palette[labels]
        
        # TODO: self.use_dithering == True の場合、Floyd-Steinbergディザリングを適用して
        # バンディング(グラデーションの縞模様)を打ち消す処理をここに実装する
        
        # 5. 元の画像形状に戻す
        quantized_img = quantized_pixels.reshape((h, w, c))
        
        return quantized_img, True
