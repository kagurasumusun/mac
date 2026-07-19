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

    pub fn _clean_alpha(&self, bgra: &mut [u8]) {
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

    pub fn _try_ultra_quant(&self, bgra: &[u8], levels: usize) -> Vec<u8> {
        let step = (256 / std::cmp::max(1, levels)) as u8;
        let mut out = bgra.to_vec();
        for px in out.chunks_exact_mut(4) {
            px[0] = ((px[0] as usize + step as usize / 2) / step as usize * step as usize) as u8;
            px[1] = ((px[1] as usize + step as usize / 2) / step as usize * step as usize) as u8;
            px[2] = ((px[2] as usize + step as usize / 2) / step as usize * step as usize) as u8;
        }
        lzfse::compress(&out)
    }

    pub fn _try_block_mean(&self, bgra: &[u8], _block_size: usize) -> Vec<u8> {
        lzfse::compress(bgra)
    }

    pub fn _try_gradient_predict(&self, bgra: &[u8], width: usize, height: usize) -> Vec<u8> {
        crate::nexus_compression::compress_predictive_dpcm(bgra, width, height)
    }

    pub fn _try_edge_preserve(&self, bgra: &[u8], width: usize, height: usize) -> Vec<u8> {
        if let Some(res) = crate::omega_compression::OMEGACompressor::default()._try_edge_preserving_quant(bgra, width, height) {
            res
        } else {
            lzfse::compress(bgra)
        }
    }

    pub fn _try_ycocg_aggressive(&self, bgra: &[u8]) -> Vec<u8> {
        crate::nexus_compression::compress_ycocg_perceptual(bgra)
    }

    pub fn _try_median_filter(&self, bgra: &[u8]) -> Vec<u8> {
        lzfse::compress(bgra)
    }

    pub fn compress_chunk(&self, chunk_bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
        let mut data = chunk_bgra.to_vec();
        self._clean_alpha(&mut data);

        let w = width as usize;
        let h = height as usize;

        let c1 = lzfse::compress(&data);
        let c2 = self._try_ultra_quant(&data, 16);
        let c3 = self._try_gradient_predict(&data, w, h);
        let c4 = self._try_ycocg_aggressive(&data);

        let candidates = vec![c1, c2, c3, c4];
        candidates.into_iter().min_by_key(|c| c.len()).unwrap_or_else(|| lzfse::compress(&data))
    }

    pub fn compress_image(&self, bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
        crate::cbck::encode_cbck(bgra, width, height, 4, self.clean_alpha)
    }
}

pub fn omniv2_compress(bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
    let comp = OMNIv2Compressor::default();
    comp.compress_image(bgra, width, height)
}
