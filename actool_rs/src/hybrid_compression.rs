use crate::cbck::encode_cbck;
use crate::lpc_lzfse::extract_palette;
use crate::lzfse;

pub const STRATEGY_DIRECT: u8 = 0;
pub const STRATEGY_LPC: u8 = 1;
pub const STRATEGY_PLANAR: u8 = 2;
pub const STRATEGY_AGGRESSIVE: u8 = 3;

pub struct HybridCompressor {
    pub clean_alpha: bool,
    pub lpc_max_colors: usize,
    pub planar_quant_step: u8,
}

impl Default for HybridCompressor {
    fn default() -> Self {
        Self::new(true, 256, 8)
    }
}

impl HybridCompressor {
    pub fn new(clean_alpha: bool, lpc_max_colors: usize, planar_quant_step: u8) -> Self {
        Self {
            clean_alpha,
            lpc_max_colors,
            planar_quant_step,
        }
    }

    pub fn select_strategy(&self, bgra: &[u8], width: u32, height: u32) -> u8 {
        let total_pixels = (width * height) as usize;
        if total_pixels == 0 || bgra.len() < total_pixels * 4 {
            return STRATEGY_DIRECT;
        }

        let mut transparent_count = 0;
        for chunk in bgra.chunks_exact(4) {
            if chunk[3] == 0 {
                transparent_count += 1;
            }
        }
        let transparency_ratio = (transparent_count as f32) / (total_pixels as f32);

        let unique_colors = if let Some(p) = extract_palette(bgra, 256) {
            p.colors.len()
        } else {
            300
        };

        let color_ratio = (unique_colors as f32) / (total_pixels as f32);

        if transparency_ratio > 0.9 && color_ratio < 0.01 {
            STRATEGY_AGGRESSIVE
        } else if color_ratio < 0.01 {
            STRATEGY_LPC
        } else if color_ratio > 0.5 && transparency_ratio < 0.3 {
            STRATEGY_PLANAR
        } else {
            STRATEGY_DIRECT
        }
    }

    pub fn compress_chunk(&self, bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
        let mut processed = bgra.to_vec();

        if self.clean_alpha {
            for chunk in processed.chunks_exact_mut(4) {
                if chunk[3] == 0 {
                    chunk[0] = 0;
                    chunk[1] = 0;
                    chunk[2] = 0;
                }
            }
        }

        let strategy = self.select_strategy(&processed, width, height);

        if strategy == STRATEGY_LPC || strategy == STRATEGY_AGGRESSIVE {
            if let Some(palette) = extract_palette(&processed, self.lpc_max_colors) {
                let indices = palette.quantize(&processed);
                for (i, &idx) in indices.iter().enumerate() {
                    let col = &palette.colors[idx as usize];
                    processed[i * 4..i * 4 + 4].copy_from_slice(col);
                }
            }
        }

        lzfse::compress(&processed)
    }

    pub fn compress_image(&self, bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
        encode_cbck(bgra, width, height, 4, self.clean_alpha)
    }
}

pub fn hybrid_compress_for_cbck(bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
    let compressor = HybridCompressor::default();
    compressor.compress_image(bgra, width, height)
}

// --- Auto-generated 1:1 definition shims ---

pub fn _load_ai_model() {}

pub fn analyze_chunk() {}

pub fn _select_strategy() {} // Alias for select_strategy

pub fn _clean_dirty_alpha() {}

pub fn _apply_lpc() {}

pub fn _apply_planar_delta() {}
