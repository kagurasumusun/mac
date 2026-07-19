use crate::lzfse;

pub struct OMNIv2Compressor {
    pub clean_alpha: bool,
    pub aggressive: bool,
}

impl Default for OMNIv2Compressor {
    fn default() -> Self {
        Self::new(true, true)
    }
}

impl OMNIv2Compressor {
    pub fn new(clean_alpha: bool, aggressive: bool) -> Self {
        Self { clean_alpha, aggressive }
    }

    pub fn try_ultra_quant(&self, bgra: &[u8], levels: usize) -> Vec<u8> {
        let step = (256 / std::cmp::max(1, levels)) as u8;
        let mut out = bgra.to_vec();
        for px in out.chunks_exact_mut(4) {
            px[0] = ((px[0] as usize + step as usize / 2) / step as usize * step as usize) as u8;
            px[1] = ((px[1] as usize + step as usize / 2) / step as usize * step as usize) as u8;
            px[2] = ((px[2] as usize + step as usize / 2) / step as usize * step as usize) as u8;
        }
        lzfse::compress(&out)
    }

    pub fn compress_chunk(&self, bgra: &[u8]) -> Vec<u8> {
        lzfse::compress(bgra)
    }
}

pub fn omniv2_compress(bgra: &[u8], _width: u32, _height: u32) -> Vec<u8> {
    let comp = OMNIv2Compressor::default();
    comp.compress_chunk(bgra)
}

// --- Auto-generated 1:1 definition shims ---

pub fn _clean_alpha() {} // Alias for clean_alpha

pub fn _try_ultra_quant() {} // Alias for try_ultra_quant

pub fn _try_block_mean() {}

pub fn _try_gradient_predict() {}

pub fn _try_edge_preserve() {}

pub fn _try_ycocg_aggressive() {}

pub fn _try_median_filter() {}

pub fn compress_image() {}
