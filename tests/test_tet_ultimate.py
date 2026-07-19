#!/usr/bin/env python3
"""TET Ultimate Test — All remaining tet.txt categories."""

import sys
import numpy as np

sys.path.insert(0, "/home/user/repo-cleanup")

from actool_linux.tet_ultimate import (
    left_predictor, top_predictor, auto_crop, remove_gamma,
    jpeg_adaptive_quantization, heif_ctu_optimization,
    pdf_path_simplification, color_space_conversion,
    tet_ultimate_optimize
)

def test_all_categories():
    """Test all TET Ultimate categories."""
    gradient = np.zeros((64, 64, 4), dtype=np.uint8)
    for y in range(64):
        gradient[y, :] = [y * 4, y * 2, 0, 255]
    
    transparent = np.zeros((64, 64, 4), dtype=np.uint8)
    transparent[20:40, 15:50] = [255, 0, 0, 255]
    
    # Test spatial prediction
    assert left_predictor(gradient).shape == gradient.shape
    assert top_predictor(gradient).shape == gradient.shape
    
    # Test geometry
    cropped, bbox = auto_crop(transparent)
    assert cropped.shape[0] < transparent.shape[0]
    
    # Test metadata
    assert remove_gamma(b'test') == b'test'
    
    # Test JPEG
    assert jpeg_adaptive_quantization(85)['quality'] == 85
    
    # Test HEIF
    assert heif_ctu_optimization()['type'] == 'ctu'
    
    # Test PDF
    assert len(pdf_path_simplification([{'path': 'test'}])) == 1
    
    # Test Named Color
    assert color_space_conversion(gradient, 'sRGB', 'AdobeRGB').shape == gradient.shape
    
    # Test Ultimate optimizer
    result, meta = tet_ultimate_optimize(transparent)
    assert meta['geometry']['reduction'] > 0.8
    
    print("✅ All TET Ultimate tests passed")

if __name__ == "__main__":
    test_all_categories()
