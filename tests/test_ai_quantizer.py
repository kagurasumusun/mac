from actool_linux.ai_quantizer import PerceptualQuantizer
import numpy as np
import time

def run_test():
    # 1. 1024x1024のグラデーション画像 (数万色) を生成
    print("Generating 1024x1024 image with thousands of colors...")
    img_data = np.zeros((1024, 1024, 4), dtype=np.uint8)
    for y in range(1024):
        for x in range(1024):
            img_data[y, x, 0] = int(255 * (x / 1024))
            img_data[y, x, 1] = int(255 * (y / 1024))
            img_data[y, x, 2] = 128
            img_data[y, x, 3] = 255
            
    # 色数カウント
    pixels = img_data.reshape(-1, 4)
    unique_colors = len(np.unique(pixels, axis=0))
    print(f"Original unique colors: {unique_colors}")
    
    # 2. 減色エンジン初期化
    quantizer = PerceptualQuantizer(max_colors=16, use_dithering=False)
    
    print("\\n=== Running AI Quantizer (Fallback Mode) ===")
    start = time.time()
    q_img, success = quantizer.quantize(img_data)
    elapsed = (time.time() - start) * 1000
    
    q_pixels = q_img.reshape(-1, 4)
    q_unique = len(np.unique(q_pixels, axis=0))
    
    print(f"Quantization Success: {success}")
    print(f"Quantized unique colors: {q_unique}")
    print(f"Time taken: {elapsed:.2f} ms")

if __name__ == "__main__":
    run_test()
