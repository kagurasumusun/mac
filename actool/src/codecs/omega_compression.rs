use crate::lzfse;
use crate::quality_metrics::is_quality_acceptable;

pub struct OMEGACompressor {
    pub clean_alpha: bool,
    pub min_psnr: f64,
    pub max_delta_e: f64,
}

impl Default for OMEGACompressor {
    fn default() -> Self {
        Self::new(true, "excellent")
    }
}

impl OMEGACompressor {
    pub fn new(clean_alpha: bool, quality_threshold: &str) -> Self {
        let (min_psnr, max_delta_e) = if quality_threshold == "excellent" {
            (40.0, 2.3)
        } else {
            (30.0, 5.0)
        };

        Self {
            clean_alpha,
            min_psnr,
            max_delta_e,
        }
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

    pub fn _try_subtle_quant(&self, bgra: &[u8], step: u8) -> Option<Vec<u8>> {
        let mut result = bgra.to_vec();
        for px in result.chunks_exact_mut(4) {
            px[0] = ((px[0] as u16 + step as u16 / 2) / step as u16 * step as u16) as u8;
            px[1] = ((px[1] as u16 + step as u16 / 2) / step as u16 * step as u16) as u8;
            px[2] = ((px[2] as u16 + step as u16 / 2) / step as u16 * step as u16) as u8;
        }

        if is_quality_acceptable(bgra, &result, self.min_psnr) {
            Some(lzfse::compress(&result))
        } else {
            None
        }
    }

    pub fn _try_edge_preserving_quant(&self, bgra: &[u8], width: usize, height: usize) -> Option<Vec<u8>> {
        let (gx, gy) = crate::quality_metrics::sobel(bgra, width, height);
        let mut result = bgra.to_vec();

        for y in 0..height {
            for x in 0..width {
                let idx = y * width + x;
                let mag = (gx[idx] * gx[idx] + gy[idx] * gy[idx]).sqrt();
                if mag <= 16.0 {
                    let px = &mut result[idx * 4..idx * 4 + 3];
                    px[0] = (px[0] / 8) * 8;
                    px[1] = (px[1] / 8) * 8;
                    px[2] = (px[2] / 8) * 8;
                }
            }
        }

        if is_quality_acceptable(bgra, &result, self.min_psnr) {
            Some(lzfse::compress(&result))
        } else {
            None
        }
    }

    pub fn _try_alpha_perfect(&self, bgra: &[u8]) -> Option<Vec<u8>> {
        let mut result = bgra.to_vec();
        for px in result.chunks_exact_mut(4) {
            px[0] = (px[0] / 8) * 8;
            px[1] = (px[1] / 8) * 8;
            px[2] = (px[2] / 8) * 8;
        }

        if is_quality_acceptable(bgra, &result, self.min_psnr) {
            Some(lzfse::compress(&result))
        } else {
            None
        }
    }

    pub fn _try_smooth_quant(&self, bgra: &[u8]) -> Option<Vec<u8>> {
        self._try_subtle_quant(bgra, 16)
    }

    pub fn _try_ycocg_perceptual(&self, bgra: &[u8]) -> Option<Vec<u8>> {
        let perceptual = crate::nexus_compression::compress_ycocg_perceptual(bgra);
        Some(perceptual)
    }

    pub fn compress_chunk(&self, chunk_bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
        let mut data = chunk_bgra.to_vec();
        self._clean_alpha(&mut data);

        let default_compressed = lzfse::compress(&data);
        let mut best = default_compressed.clone();

        if let Some(c) = self._try_subtle_quant(&data, 8) {
            if c.len() < best.len() { best = c; }
        }
        if let Some(c) = self._try_edge_preserving_quant(&data, width as usize, height as usize) {
            if c.len() < best.len() { best = c; }
        }
        if let Some(c) = self._try_alpha_perfect(&data) {
            if c.len() < best.len() { best = c; }
        }

        best
    }

    pub fn compress_image(&self, bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
        crate::cbck::encode_cbck(bgra, width, height, 4, self.clean_alpha)
    }
}

pub fn omega_compress(bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
    let comp = OMEGACompressor::default();
    comp.compress_image(bgra, width, height)
}
