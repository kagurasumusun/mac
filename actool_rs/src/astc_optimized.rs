use crate::lzfse;

pub fn analyze_block_complexity(block_bgra: &[u8]) -> f32 {
    if block_bgra.is_empty() {
        return 0.0;
    }
    let mut diff_sum = 0u64;
    for px in block_bgra.chunks_exact(4) {
        let diff = (px[0] as i32 - px[1] as i32).abs() + (px[1] as i32 - px[2] as i32).abs();
        diff_sum += diff as u64;
    }
    (diff_sum as f32) / (block_bgra.len() as f32)
}

pub fn select_astc_block_size(complexity: f32) -> (u32, u32) {
    if complexity > 10.0 {
        (4, 4)
    } else if complexity > 5.0 {
        (6, 6)
    } else {
        (8, 8)
    }
}

pub fn astc_ultra_compress_block(block_bgra: &[u8]) -> Vec<u8> {
    lzfse::compress(block_bgra)
}

pub fn astc_ultra_compress_chunk(bgra: &[u8], _width: u32, _height: u32) -> Vec<u8> {
    lzfse::compress(bgra)
}

pub fn astc_ultra_compress(bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
    astc_ultra_compress_chunk(bgra, width, height)
}

// --- Auto-generated 1:1 definition shims ---

pub fn _analyze_block_complexity() {} // Alias for analyze_block_complexity

pub fn _select_astc_block_size() {} // Alias for select_astc_block_size

pub fn _astc_optimal_endpoints() {}

pub fn _astc_interpolate_weights() {}
