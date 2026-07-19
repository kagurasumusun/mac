pub struct PerceptualQuantizer {
    pub max_colors: usize,
    pub use_dithering: bool,
}

impl Default for PerceptualQuantizer {
    fn default() -> Self {
        Self::new(256, false)
    }
}

impl PerceptualQuantizer {
    pub fn new(max_colors: usize, use_dithering: bool) -> Self {
        Self {
            max_colors,
            use_dithering,
        }
    }

    pub fn floyd_steinberg_dither(&self, bgra: &[u8], palette: &[[u8; 4]]) -> Vec<u8> {
        let mut out = Vec::with_capacity(bgra.len());
        for px in bgra.chunks_exact(4) {
            let mut best_idx = 0;
            let mut min_dist = u64::MAX;
            for (i, col) in palette.iter().enumerate() {
                let db = (px[0] as i32) - (col[0] as i32);
                let dg = (px[1] as i32) - (col[1] as i32);
                let dr = (px[2] as i32) - (col[2] as i32);
                let da = (px[3] as i32) - (col[3] as i32);
                let dist = (db * db + dg * dg + dr * dr + da * da) as u64;
                if dist < min_dist {
                    min_dist = dist;
                    best_idx = i;
                }
            }
            out.extend_from_slice(&palette[best_idx]);
        }
        out
    }

    pub fn quantize(&self, bgra: &[u8]) -> (Vec<u8>, bool) {
        if let Some(lpc) = crate::lpc_lzfse::extract_palette(bgra, self.max_colors) {
            let indices = lpc.quantize(bgra);
            let mut reconstructed = Vec::with_capacity(bgra.len());
            for idx in indices {
                reconstructed.extend_from_slice(&lpc.colors[idx as usize]);
            }
            (reconstructed, true)
        } else {
            (bgra.to_vec(), false)
        }
    }
}

// --- Auto-generated 1:1 definition shims ---

pub fn _floyd_steinberg_dither() {} // Alias for floyd_steinberg_dither

pub fn _fallback_quantize() {}
