from actool_linux.semantic_fusion import SemanticFusionAtlas
import numpy as np

def run_test():
    # 1. 256x256のダミー画像を生成 (16MBの代わり)
    img_data = np.zeros((256, 256, 4), dtype=np.uint8)
    
    # 2. グラデーション領域を作る (上半分: エッジ少)
    for y in range(128):
        img_data[y, :, 0] = int(255 * (y / 128))
        img_data[y, :, 3] = 255
        
    # 3. テキスト/アイコン領域を作る (下半分: エッジ多)
    # ランダムなノイズを配置してエッジ密度を上げる
    img_data[128:256, :, 1] = np.random.choice([0, 255], (128, 256))
    img_data[128:256, :, 3] = 255
    
    # 4. Semantic Fusion Atlas エンジンの初期化
    fusion = SemanticFusionAtlas(block_size=64)
    
    print("=== Semantic Fusion Engine Test ===")
    
    # 手動で解析テスト
    chunk_grad = img_data[0:64, 0:64]
    chunk_edge = img_data[128:192, 0:64]
    chunk_solid = np.zeros((64, 64, 4), dtype=np.uint8)
    
    print(f"Gradient Chunk Edge Score : {fusion.analyze_edge_density(chunk_grad):.2f}")
    print(f"Text/Icon Chunk Edge Score: {fusion.analyze_edge_density(chunk_edge):.2f}")
    print(f"Solid Chunk Edge Score    : {fusion.analyze_edge_density(chunk_solid):.2f}\\n")
    
    # 全体をエンコード
    print("Encoding full image...")
    fused_payload = fusion.fuse_and_encode(img_data)
    print("Success! Encoding logic passed without crashing.")

if __name__ == "__main__":
    run_test()
