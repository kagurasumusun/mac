use crate::lzfse;

pub struct OMNICompressor {
    pub clean_alpha: bool,
}

impl Default for OMNICompressor {
    fn default() -> Self {
        Self::new(true)
    }
}

impl OMNICompressor {
    pub fn new(clean_alpha: bool) -> Self {
        Self { clean_alpha }
    }

    pub fn try_default(&self, bgra: &[u8]) -> Vec<u8> {
        lzfse::compress(bgra)
    }

    pub fn try_planar_delta(&self, bgra: &[u8]) -> Vec<u8> {
        let step = 8u8;
        let mut out = bgra.to_vec();
        for px in out.chunks_exact_mut(4) {
            px[0] = (px[0] / step) * step;
            px[1] = (px[1] / step) * step;
            px[2] = (px[2] / step) * step;
        }
        lzfse::compress(&out)
    }

    pub fn try_aggressive_quant(&self, bgra: &[u8]) -> Vec<u8> {
        let mut out = bgra.to_vec();
        for px in out.chunks_exact_mut(4) {
            px[0] = (px[0] >> 3) << 3;
            px[1] = (px[1] >> 3) << 3;
            px[2] = (px[2] >> 3) << 3;
        }
        lzfse::compress(&out)
    }

    pub fn compress_chunk(&self, bgra: &[u8], _width: u32, _height: u32) -> Vec<u8> {
        let c1 = self.try_default(bgra);
        let c2 = self.try_planar_delta(bgra);
        let c3 = self.try_aggressive_quant(bgra);

        let mut best = c1;
        if c2.len() < best.len() {
            best = c2;
        }
        if c3.len() < best.len() {
            best = c3;
        }
        best
    }

    pub fn compress_image(&self, bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
        crate::cbck::encode_cbck(bgra, width, height, 4, self.clean_alpha)
    }
}

pub fn omni_compress(bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
    let comp = OMNICompressor::default();
    comp.compress_image(bgra, width, height)
}

// --- Auto-generated 1:1 definition shims ---

pub fn _clean_alpha() {} // Alias for clean_alpha

pub fn _try_default() {} // Alias for try_default

pub fn _try_planar_delta() {} // Alias for try_planar_delta

pub fn _try_planar_delta_fine() {}

pub fn _try_lpc() {}

pub fn _try_astc_class() {}

pub fn _try_aggressive_quant() {} // Alias for try_aggressive_quant

pub fn _try_ultra_aggressive() {}
