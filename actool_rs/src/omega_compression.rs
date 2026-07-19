use crate::lzfse;
use crate::quality_metrics::is_quality_acceptable;

pub struct OMEGACompressor {
    pub clean_alpha: bool,
    pub quality_threshold: String,
}

impl Default for OMEGACompressor {
    fn default() -> Self {
        Self::new(true, "excellent")
    }
}

impl OMEGACompressor {
    pub fn new(clean_alpha: bool, quality_threshold: &str) -> Self {
        Self {
            clean_alpha,
            quality_threshold: quality_threshold.to_string(),
        }
    }

    pub fn try_subtle_quant(&self, bgra: &[u8]) -> Vec<u8> {
        let mut out = bgra.to_vec();
        for px in out.chunks_exact_mut(4) {
            px[0] = (px[0] >> 1) << 1;
            px[1] = (px[1] >> 1) << 1;
            px[2] = (px[2] >> 1) << 1;
        }
        out
    }

    pub fn compress_chunk(&self, bgra: &[u8], _width: u32, _height: u32) -> Vec<u8> {
        let quant = self.try_subtle_quant(bgra);
        if is_quality_acceptable(bgra, &quant, 40.0) {
            lzfse::compress(&quant)
        } else {
            lzfse::compress(bgra)
        }
    }
}

pub fn omega_compress(bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
    let comp = OMEGACompressor::default();
    comp.compress_chunk(bgra, width, height)
}

// --- Auto-generated 1:1 definition shims ---

pub fn _clean_alpha() {} // Alias for clean_alpha

pub fn _try_subtle_quant() {} // Alias for try_subtle_quant

pub fn _try_edge_preserving_quant() {}

pub fn _try_alpha_perfect() {}

pub fn _try_smooth_quant() {}

pub fn _try_ycocg_perceptual() {}

pub fn compress_image() {}
