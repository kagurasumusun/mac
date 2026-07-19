use crate::lzfse;

pub fn analyze_block_complexity(block_bgra: &[u8]) -> (f32, f32, f32) {
    if block_bgra.is_empty() {
        return (0.0, 0.0, 0.0);
    }
    let pixels = block_bgra.len() / 4;
    let mut trans_count = 0;
    let mut diff_sum = 0u64;

    for px in block_bgra.chunks_exact(4) {
        if px[3] == 0 {
            trans_count += 1;
        }
        let diff = (px[0] as i32 - px[1] as i32).abs() + (px[1] as i32 - px[2] as i32).abs();
        diff_sum += diff as u64;
    }

    let edge_density = (diff_sum as f32) / (block_bgra.len() as f32 * 255.0);
    let trans_ratio = (trans_count as f32) / (pixels as f32);
    let color_var = edge_density * 0.5;

    (edge_density, color_var, trans_ratio)
}

pub fn select_astc_block_size(edge_density: f32, _color_var: f32, trans_ratio: f32) -> u32 {
    if edge_density > 0.15 {
        4
    } else if edge_density > 0.08 {
        6
    } else if trans_ratio > 0.8 {
        12
    } else {
        8
    }
}

pub fn astc_optimal_endpoints(block_bgra: &[u8], block_size: u32) -> ([u8; 4], [u8; 4]) {
    if block_bgra.len() < 4 {
        return ([0, 0, 0, 255], [255, 255, 255, 255]);
    }
    let step = match block_size {
        4 => 4,
        6 => 8,
        8 => 16,
        10 => 32,
        _ => 64,
    };

    let mut min_col = [255u8; 4];
    let mut max_col = [0u8; 4];

    for px in block_bgra.chunks_exact(4) {
        min_col[0] = std::cmp::min(min_col[0], px[0]);
        min_col[1] = std::cmp::min(min_col[1], px[1]);
        min_col[2] = std::cmp::min(min_col[2], px[2]);
        min_col[3] = std::cmp::min(min_col[3], px[3]);

        max_col[0] = std::cmp::max(max_col[0], px[0]);
        max_col[1] = std::cmp::max(max_col[1], px[1]);
        max_col[2] = std::cmp::max(max_col[2], px[2]);
        max_col[3] = std::cmp::max(max_col[3], px[3]);
    }

    min_col[0] = (min_col[0] / step) * step;
    min_col[1] = (min_col[1] / step) * step;
    min_col[2] = (min_col[2] / step) * step;

    max_col[0] = (max_col[0] / step) * step;
    max_col[1] = (max_col[1] / step) * step;
    max_col[2] = (max_col[2] / step) * step;

    (min_col, max_col)
}

pub fn astc_interpolate_weights(block_bgra: &[u8], endpoints: ([u8; 4], [u8; 4])) -> Vec<u8> {
    let mut out = Vec::with_capacity(block_bgra.len());
    let (ep0, ep1) = endpoints;

    for px in block_bgra.chunks_exact(4) {
        let b = (ep0[0] as u16 + ep1[0] as u16) / 2;
        let g = (ep0[1] as u16 + ep1[1] as u16) / 2;
        let r = (ep0[2] as u16 + ep1[2] as u16) / 2;
        out.push(b as u8);
        out.push(g as u8);
        out.push(r as u8);
        out.push(px[3]);
    }

    out
}

pub fn astc_ultra_compress_block(block_bgra: &[u8]) -> Vec<u8> {
    let (edge, var, trans) = analyze_block_complexity(block_bgra);
    let bs = select_astc_block_size(edge, var, trans);
    let eps = astc_optimal_endpoints(block_bgra, bs);
    let interpolated = astc_interpolate_weights(block_bgra, eps);
    lzfse::compress(&interpolated)
}

pub fn astc_ultra_compress_chunk(bgra: &[u8], _sub_block_size: usize) -> Vec<u8> {
    astc_ultra_compress_block(bgra)
}

pub fn astc_ultra_compress(bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
    crate::cbck::encode_cbck(bgra, width, height, 4, true)
}
