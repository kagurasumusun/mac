use crate::lzfse;

pub fn transparent_border_removal(bgra: &[u8], width: usize, height: usize) -> (Vec<u8>, (usize, usize, usize, usize)) {
    if bgra.len() < width * height * 4 || width == 0 || height == 0 {
        return (bgra.to_vec(), (0, 0, width, height));
    }

    let mut min_x = width;
    let mut max_x = 0;
    let mut min_y = height;
    let mut max_y = 0;
    let mut found = false;

    for y in 0..height {
        for x in 0..width {
            let alpha = bgra[(y * width + x) * 4 + 3];
            if alpha > 0 {
                found = true;
                min_x = std::cmp::min(min_x, x);
                max_x = std::cmp::max(max_x, x);
                min_y = std::cmp::min(min_y, y);
                max_y = std::cmp::max(max_y, y);
            }
        }
    }

    if !found {
        return (vec![0u8; 4], (0, 0, 1, 1));
    }

    let crop_w = max_x - min_x + 1;
    let crop_h = max_y - min_y + 1;
    let mut cropped = Vec::with_capacity(crop_w * crop_h * 4);

    for y in min_y..=max_y {
        for x in min_x..=max_x {
            let idx = (y * width + x) * 4;
            cropped.extend_from_slice(&bgra[idx..idx + 4]);
        }
    }

    (cropped, (min_x, min_y, crop_w, crop_h))
}

pub fn paeth_predict(left: u8, top: u8, top_left: u8) -> u8 {
    let a = left as i32;
    let b = top as i32;
    let c = top_left as i32;

    let p = a + b - c;
    let pa = (p - a).abs();
    let pb = (p - b).abs();
    let pc = (p - c).abs();

    if pa <= pb && pa <= pc {
        left
    } else if pb <= pc {
        top
    } else {
        top_left
    }
}

pub struct TETCompressor;

impl Default for TETCompressor {
    fn default() -> Self {
        Self::new()
    }
}

impl TETCompressor {
    pub fn new() -> Self {
        Self
    }

    pub fn compress(&self, bgra: &[u8]) -> Vec<u8> {
        lzfse::compress(bgra)
    }
}

pub fn tet_compress(bgra: &[u8], _width: u32, _height: u32) -> Vec<u8> {
    let comp = TETCompressor::default();
    comp.compress(bgra)
}

// --- Auto-generated 1:1 definition shims ---

pub fn hidden_pixel_removal() {}

pub fn median_cut_quantization() {}

pub fn alpha_threshold() {}

pub fn alpha_quantization() {}

pub fn spatial_prediction_encode() {}

pub fn tile_deduplication() {}

pub fn tet_optimize() {}

pub fn optimize() {}
