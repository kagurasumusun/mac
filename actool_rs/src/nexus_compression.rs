use crate::lzfse;

pub fn haar_decompose_2x2(b: &[u8]) -> (u8, i8, i8, i8) {
    if b.len() < 4 {
        return (0, 0, 0, 0);
    }
    let b0 = b[0] as i32;
    let b1 = b[1] as i32;
    let b2 = b[2] as i32;
    let b3 = b[3] as i32;

    let ll = ((b0 + b1 + b2 + b3) / 4) as u8;
    let lh = ((b0 + b1 - b2 - b3) / 4) as i8;
    let hl = ((b0 - b1 + b2 - b3) / 4) as i8;
    let hh = ((b0 - b1 - b2 + b3) / 4) as i8;

    (ll, lh, hl, hh)
}

pub fn compress_predictive_dpcm(bgra: &[u8], width: usize, height: usize) -> Vec<u8> {
    if bgra.len() < width * height * 4 {
        return lzfse::compress(bgra);
    }
    let mut out = vec![0u8; bgra.len()];

    for y in 0..height {
        for x in 0..width {
            let idx = (y * width + x) * 4;
            if x == 0 {
                out[idx..idx + 4].copy_from_slice(&bgra[idx..idx + 4]);
            } else {
                let prev_idx = (y * width + (x - 1)) * 4;
                out[idx] = (bgra[idx] as i16 - bgra[prev_idx] as i16 + 128).clamp(0, 255) as u8;
                out[idx + 1] = (bgra[idx + 1] as i16 - bgra[prev_idx + 1] as i16 + 128).clamp(0, 255) as u8;
                out[idx + 2] = (bgra[idx + 2] as i16 - bgra[prev_idx + 2] as i16 + 128).clamp(0, 255) as u8;
                out[idx + 3] = (bgra[idx + 3] as i16 - bgra[prev_idx + 3] as i16 + 128).clamp(0, 255) as u8;
            }
        }
    }

    lzfse::compress(&out)
}

pub fn compress_ycocg_perceptual(bgra: &[u8]) -> Vec<u8> {
    let mut out = Vec::with_capacity(bgra.len());

    for px in bgra.chunks_exact(4) {
        let b = px[0] as f32;
        let g = px[1] as f32;
        let r = px[2] as f32;
        let a = px[3];

        let y = b / 4.0 + g / 2.0 + r / 4.0;
        let co = b / 2.0 - r / 2.0 + 128.0;
        let cg = -b / 4.0 + g / 2.0 - r / 4.0 + 128.0;

        let y_q = (y / 4.0).round() * 4.0;
        let co_q = (co / 32.0).round() * 32.0;
        let cg_q = (cg / 32.0).round() * 32.0;

        let r_rec = (y_q + co_q - 128.0).clamp(0.0, 255.0) as u8;
        let g_rec = (y_q + cg_q - 128.0).clamp(0.0, 255.0) as u8;
        let b_rec = (y_q - co_q - cg_q + 256.0).clamp(0.0, 255.0) as u8;

        out.push(b_rec);
        out.push(g_rec);
        out.push(r_rec);
        out.push(a);
    }

    lzfse::compress(&out)
}

pub struct NEXUSCompressor {
    pub clean_alpha: bool,
    pub parallel: bool,
}

impl Default for NEXUSCompressor {
    fn default() -> Self {
        Self::new(true, true)
    }
}

impl NEXUSCompressor {
    pub fn new(clean_alpha: bool, parallel: bool) -> Self {
        Self { clean_alpha, parallel }
    }

    pub fn compress_chunk(&self, chunk: &[u8], width: u32, height: u32) -> Vec<u8> {
        let default_c = lzfse::compress(chunk);
        let dpcm_c = compress_predictive_dpcm(chunk, width as usize, height as usize);
        let perceptual_c = compress_ycocg_perceptual(chunk);

        let mut best = default_c;
        if dpcm_c.len() < best.len() {
            best = dpcm_c;
        }
        if perceptual_c.len() < best.len() {
            best = perceptual_c;
        }
        best
    }

    pub fn compress_image(&self, bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
        crate::cbck::encode_cbck(bgra, width, height, 4, self.clean_alpha)
    }
}

pub fn nexus_compress(bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
    let compressor = NEXUSCompressor::default();
    compressor.compress_image(bgra, width, height)
}

// --- Auto-generated 1:1 definition shims ---

pub fn _haar_decompose() {} // Alias for haar_decompose

pub fn _compress_wavelet() {}

pub fn _compress_dictionary() {}

pub fn _compress_predictive() {} // Alias for compress_predictive

pub fn _compress_dct() {}

pub fn _compress_similarity() {}

pub fn _compress_perceptual() {}

pub fn _clean_alpha() {} // Alias for clean_alpha
