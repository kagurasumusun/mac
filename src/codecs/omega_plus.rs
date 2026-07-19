use crate::lzfse;

pub fn dmp2_rle_optimize(raw: &[u8], _bpp: u8) -> Vec<u8> {
    if raw.is_empty() {
        return Vec::new();
    }
    lzfse::compress(raw)
}

pub fn dmp2_delta_encode(raw: &[u8]) -> Vec<u8> {
    if raw.is_empty() {
        return Vec::new();
    }
    let mut delta = vec![0u8; raw.len()];
    delta[0] = raw[0];
    for i in 1..raw.len() {
        delta[i] = raw[i].wrapping_sub(raw[i - 1]);
    }
    lzfse::compress(&delta)
}

pub fn adaptive_palette_optimize(bgra: &[u8]) -> Vec<u8> {
    if let Some(palette) = crate::lpc_lzfse::extract_palette(bgra, 256) {
        let indices = palette.quantize(bgra);
        let mut reconstructed = Vec::with_capacity(bgra.len());
        for idx in indices {
            reconstructed.extend_from_slice(&palette.colors[idx as usize]);
        }
        lzfse::compress(&reconstructed)
    } else {
        lzfse::compress(bgra)
    }
}

pub fn ga_optimize(ga_data: &[u8]) -> Vec<u8> {
    lzfse::compress(ga_data)
}

pub fn detect_similar_renditions(renditions: Vec<crate::carwriter::AssetRendition>) -> Vec<crate::carwriter::AssetRendition> {
    let mut unique = Vec::new();
    for r in renditions {
        if !unique.iter().any(|u: &crate::carwriter::AssetRendition| u.csi_bytes == r.csi_bytes) {
            unique.push(r);
        }
    }
    unique
}

pub fn predictive_encode(raw: &[u8]) -> Vec<u8> {
    if raw.len() < 4 {
        return lzfse::compress(raw);
    }
    let mut predicted = vec![0u8; raw.len()];
    predicted[..4].copy_from_slice(&raw[..4]);

    for i in 4..raw.len() {
        predicted[i] = (raw[i] as i16 - raw[i - 4] as i16 + 128).clamp(0, 255) as u8;
    }

    lzfse::compress(&predicted)
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
        let c1 = lzfse::compress(raw);
        let c2 = dmp2_rle_optimize(raw, bpp);
        let c3 = dmp2_delta_encode(raw);
        let c4 = adaptive_palette_optimize(raw);
        let c5 = predictive_encode(raw);

        let candidates = vec![c1, c2, c3, c4, c5];
        candidates.into_iter().min_by_key(|c| c.len()).unwrap_or_else(|| lzfse::compress(raw))
    }

    pub fn optimize_ga(&self, ga_data: &[u8]) -> Vec<u8> {
        ga_optimize(ga_data)
    }

    pub fn optimize_renditions(&self, renditions: Vec<crate::carwriter::AssetRendition>) -> Vec<crate::carwriter::AssetRendition> {
        detect_similar_renditions(renditions)
    }
}

pub fn optimize_dmp2_payload(raw: &[u8], bpp: u8) -> Vec<u8> {
    let comp = OMEGAPlusCompressor::default();
    comp.optimize_dmp2(raw, bpp)
}

pub fn optimize_ga_data(ga_data: &[u8]) -> Vec<u8> {
    ga_optimize(ga_data)
}

pub fn optimize_rendition_list(renditions: Vec<crate::carwriter::AssetRendition>) -> Vec<crate::carwriter::AssetRendition> {
    detect_similar_renditions(renditions)
}
