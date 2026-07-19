use crate::lzfse;

pub fn shared_pixels(a: &[u8], b: &[u8]) -> usize {
    a.iter().zip(b.iter()).filter(|(&x, &y)| x == y).count()
}

pub fn binary_difference(a: &[u8], b: &[u8]) -> Vec<u8> {
    a.iter().zip(b.iter()).map(|(&x, &y)| x.wrapping_sub(y)).collect()
}

pub fn variant_deduplication(a: &[u8], b: &[u8]) -> Vec<u8> {
    if a == b {
        a.to_vec()
    } else {
        binary_difference(a, b)
    }
}

pub fn shared_rgb(bgra: &[u8]) -> Vec<u8> {
    let mut out = Vec::with_capacity(bgra.len() * 3 / 4);
    for px in bgra.chunks_exact(4) {
        out.push(px[0]);
        out.push(px[1]);
        out.push(px[2]);
    }
    out
}

pub fn appearance_prediction(light: &[u8]) -> Vec<u8> {
    light.iter().map(|&b| 255 - b).collect()
}

pub fn contrast_delta(bgra: &[u8], factor: f32) -> Vec<u8> {
    bgra.iter().map(|&b| ((b as f32) * factor).clamp(0.0, 255.0) as u8).collect()
}

pub fn shared_background(a: &[u8], b: &[u8]) -> Vec<u8> {
    variant_deduplication(a, b)
}

pub fn accessibility_optimize(bgra: &[u8]) -> Vec<u8> {
    contrast_delta(bgra, 1.2)
}

pub fn relative_luminance(r: u8, g: u8, b: u8) -> f32 {
    0.2126 * (r as f32) + 0.7152 * (g as f32) + 0.0722 * (b as f32)
}

pub fn compute_variant_delta(light: &[u8], dark: &[u8]) -> (Vec<i16>, f64) {
    let min_len = std::cmp::min(light.len(), dark.len());
    let mut delta = Vec::with_capacity(min_len);
    let mut identical_count = 0;

    for i in 0..min_len {
        let diff = (dark[i] as i16) - (light[i] as i16);
        if diff == 0 {
            identical_count += 1;
        }
        delta.push(diff);
    }

    let ratio = (identical_count as f64) / (min_len.max(1) as f64);
    (delta, ratio)
}

pub struct TETVariantsOptimizer;

impl Default for TETVariantsOptimizer {
    fn default() -> Self {
        Self::new()
    }
}

impl TETVariantsOptimizer {
    pub fn new() -> Self {
        Self
    }

    pub fn optimize_light_dark(&self, light: &[u8], dark: &[u8]) -> Vec<u8> {
        let diff = binary_difference(light, dark);
        lzfse::compress(&diff)
    }

    pub fn optimize_color_variants(&self, bgra: &[u8]) -> Vec<u8> {
        let rgb = shared_rgb(bgra);
        lzfse::compress(&rgb)
    }

    pub fn optimize_high_contrast(&self, bgra: &[u8]) -> Vec<u8> {
        let hc = accessibility_optimize(bgra);
        lzfse::compress(&hc)
    }

    pub fn optimize_variants(&self, bgra: &[u8]) -> Vec<u8> {
        lzfse::compress(bgra)
    }

    pub fn optimize_colors(&self, bgra: &[u8]) -> Vec<u8> {
        lzfse::compress(bgra)
    }

    pub fn optimize_contrast(&self, bgra: &[u8]) -> Vec<u8> {
        lzfse::compress(bgra)
    }
}

pub fn tet_variant_compress(bgra: &[u8], _width: u32, _height: u32) -> Vec<u8> {
    let opt = TETVariantsOptimizer::default();
    opt.optimize_variants(bgra)
}
