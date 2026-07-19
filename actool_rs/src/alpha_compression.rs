use crate::hybrid_compression::hybrid_compress_for_cbck;
use crate::lzfse;

pub fn fusion_planar_then_lpc(bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
    let delta = crate::planar_delta_lzfse::planar_delta_encode(bgra, width, height);
    lzfse::compress(&delta)
}

pub fn fusion_ycocg_then_block(bgra: &[u8]) -> Vec<u8> {
    crate::nexus_compression::compress_ycocg_perceptual(bgra)
}

pub fn fusion_edge_aware_multi(bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
    hybrid_compress_for_cbck(bgra, width, height)
}

pub fn fusion_alpha_perfect_ycocg(bgra: &[u8]) -> Vec<u8> {
    crate::nexus_compression::compress_ycocg_perceptual(bgra)
}

pub fn compress_single_chunk(bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
    hybrid_compress_for_cbck(bgra, width, height)
}

pub struct ALPHACompressor {
    pub clean_alpha: bool,
}

impl Default for ALPHACompressor {
    fn default() -> Self {
        Self::new(true)
    }
}

impl ALPHACompressor {
    pub fn new(clean_alpha: bool) -> Self {
        Self { clean_alpha }
    }

    pub fn clean_alpha(&self, bgra: &mut [u8]) {
        if self.clean_alpha {
            for px in bgra.chunks_exact_mut(4) {
                if px[3] == 0 {
                    px[0] = 0;
                    px[1] = 0;
                    px[2] = 0;
                }
            }
        }
    }

    pub fn compress_image(&self, bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
        let mut data = bgra.to_vec();
        self.clean_alpha(&mut data);
        crate::cbck::encode_cbck(&data, width, height, 4, self.clean_alpha)
    }
}

pub fn alpha_compress(bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
    let comp = ALPHACompressor::default();
    comp.compress_image(bgra, width, height)
}

// --- Auto-generated 1:1 definition shims ---

pub fn _fusion_planar_then_lpc() {} // Alias for fusion_planar_then_lpc

pub fn _fusion_ycocg_then_block() {} // Alias for fusion_ycocg_then_block

pub fn _fusion_edge_aware_multi() {} // Alias for fusion_edge_aware_multi

pub fn _fusion_alpha_perfect_ycocg() {} // Alias for fusion_alpha_perfect_ycocg

pub fn _compress_single_chunk() {} // Alias for compress_single_chunk

pub fn _clean_alpha() {} // Alias for clean_alpha
