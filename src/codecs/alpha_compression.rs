use crate::hybrid_compression::hybrid_compress_for_cbck;
use crate::lzfse;
use rayon::prelude::*;

pub fn _fusion_planar_then_lpc(bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
    let delta = crate::planar_delta_lzfse::planar_delta_encode(bgra, width, height);
    lzfse::compress(&delta)
}

pub fn _fusion_ycocg_then_block(bgra: &[u8], _block_size: usize) -> Vec<u8> {
    crate::nexus_compression::compress_ycocg_perceptual(bgra)
}

pub fn _fusion_edge_aware_multi(bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
    hybrid_compress_for_cbck(bgra, width, height)
}

pub fn _fusion_alpha_perfect_ycocg(bgra: &[u8]) -> Vec<u8> {
    crate::nexus_compression::compress_ycocg_perceptual(bgra)
}

pub fn _compress_single_chunk(bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
    let c1 = lzfse::compress(bgra);
    let c2 = _fusion_planar_then_lpc(bgra, width, height);
    let c3 = _fusion_ycocg_then_block(bgra, 8);
    let c4 = _fusion_edge_aware_multi(bgra, width, height);
    let c5 = _fusion_alpha_perfect_ycocg(bgra);

    let candidates = vec![c1, c2, c3, c4, c5];
    candidates.into_par_iter().min_by_key(|c| c.len()).unwrap_or_else(|| lzfse::compress(bgra))
}

pub struct ALPHACompressor {
    pub clean_alpha: bool,
    pub parallel: bool,
    pub max_workers: usize,
}

impl Default for ALPHACompressor {
    fn default() -> Self {
        Self::new(true, true, 4)
    }
}

impl ALPHACompressor {
    pub fn new(clean_alpha: bool, parallel: bool, max_workers: usize) -> Self {
        Self { clean_alpha, parallel, max_workers }
    }

    pub fn _clean_alpha(&self, bgra: &mut [u8]) {
        if self.clean_alpha {
            bgra.par_chunks_exact_mut(4).for_each(|px| {
                if px[3] == 0 {
                    px[0] = 0;
                    px[1] = 0;
                    px[2] = 0;
                }
            });
        }
    }

    pub fn compress_image(&self, bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
        let mut data = bgra.to_vec();
        self._clean_alpha(&mut data);
        crate::cbck::encode_cbck(&data, width, height, 4, self.clean_alpha)
    }
}

pub fn alpha_compress(bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
    let comp = ALPHACompressor::default();
    comp.compress_image(bgra, width, height)
}
