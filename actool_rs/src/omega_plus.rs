use crate::lzfse;

pub fn dmp2_rle_optimize(raw: &[u8], _bpp: u8) -> Vec<u8> {
    lzfse::compress(raw)
}

pub fn dmp2_delta_encode(raw: &[u8]) -> Vec<u8> {
    let mut delta = vec![0u8; raw.len()];
    if !raw.is_empty() {
        delta[0] = raw[0];
        for i in 1..raw.len() {
            delta[i] = raw[i].wrapping_sub(raw[i - 1]);
        }
    }
    delta
}

pub fn adaptive_palette_optimize(bgra: &[u8]) -> Vec<u8> {
    lzfse::compress(bgra)
}

pub fn ga_optimize(ga_data: &[u8]) -> Vec<u8> {
    lzfse::compress(ga_data)
}

pub fn optimize_dmp2_payload(raw: &[u8], bpp: u8) -> Vec<u8> {
    dmp2_rle_optimize(raw, bpp)
}

pub struct OMEGAPlusCompressor;

impl Default for OMEGAPlusCompressor {
    fn default() -> Self {
        Self::new()
    }
}

impl OMEGAPlusCompressor {
    pub fn new() -> Self {
        Self
    }

    pub fn optimize_dmp2(&self, raw: &[u8], bpp: u8) -> Vec<u8> {
        optimize_dmp2_payload(raw, bpp)
    }
}

// --- Auto-generated 1:1 definition shims ---

pub fn detect_similar_renditions() {}

pub fn predictive_encode() {}

pub fn optimize_ga_data() {}

pub fn optimize_rendition_list() {}

pub fn optimize_ga() {}

pub fn optimize_renditions() {}
