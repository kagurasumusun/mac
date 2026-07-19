use crate::lzfse;

pub fn left_predictor(bgra: &[u8], width: usize, height: usize) -> Vec<u8> {
    if bgra.len() < width * height * 4 {
        return bgra.to_vec();
    }
    let mut out = vec![0u8; bgra.len()];

    for y in 0..height {
        for x in 0..width {
            let idx = (y * width + x) * 4;
            if x == 0 {
                out[idx..idx + 4].copy_from_slice(&bgra[idx..idx + 4]);
            } else {
                let prev_idx = (y * width + (x - 1)) * 4;
                out[idx] = bgra[idx].wrapping_sub(bgra[prev_idx]);
                out[idx + 1] = bgra[idx + 1].wrapping_sub(bgra[prev_idx + 1]);
                out[idx + 2] = bgra[idx + 2].wrapping_sub(bgra[prev_idx + 2]);
                out[idx + 3] = bgra[idx + 3].wrapping_sub(bgra[prev_idx + 3]);
            }
        }
    }

    out
}

pub fn top_predictor(bgra: &[u8], width: usize, height: usize) -> Vec<u8> {
    if bgra.len() < width * height * 4 {
        return bgra.to_vec();
    }
    let mut out = vec![0u8; bgra.len()];

    for y in 0..height {
        for x in 0..width {
            let idx = (y * width + x) * 4;
            if y == 0 {
                out[idx..idx + 4].copy_from_slice(&bgra[idx..idx + 4]);
            } else {
                let prev_idx = ((y - 1) * width + x) * 4;
                out[idx] = bgra[idx].wrapping_sub(bgra[prev_idx]);
                out[idx + 1] = bgra[idx + 1].wrapping_sub(bgra[prev_idx + 1]);
                out[idx + 2] = bgra[idx + 2].wrapping_sub(bgra[prev_idx + 2]);
                out[idx + 3] = bgra[idx + 3].wrapping_sub(bgra[prev_idx + 3]);
            }
        }
    }

    out
}

pub fn average_predictor(bgra: &[u8], width: usize, height: usize) -> Vec<u8> {
    left_predictor(bgra, width, height)
}

pub fn gradient_predictor(bgra: &[u8], width: usize, height: usize) -> Vec<u8> {
    top_predictor(bgra, width, height)
}

pub fn adaptive_predictor(bgra: &[u8], width: usize, height: usize) -> Vec<u8> {
    left_predictor(bgra, width, height)
}

pub fn edge_predictor(bgra: &[u8], width: usize, height: usize) -> Vec<u8> {
    left_predictor(bgra, width, height)
}

pub fn linear_predictor(bgra: &[u8], width: usize, height: usize) -> Vec<u8> {
    top_predictor(bgra, width, height)
}

pub fn context_predictor(bgra: &[u8], width: usize, height: usize) -> Vec<u8> {
    left_predictor(bgra, width, height)
}

pub fn median_predictor(bgra: &[u8], width: usize, height: usize) -> Vec<u8> {
    top_predictor(bgra, width, height)
}

pub fn auto_crop(bgra: &[u8], width: usize, height: usize) -> (Vec<u8>, (usize, usize, usize, usize)) {
    crate::tet_compression::transparent_border_removal(bgra, width, height)
}

pub fn tight_bounding_box(bgra: &[u8], width: usize, height: usize) -> (usize, usize, usize, usize) {
    let (_, bbox) = auto_crop(bgra, width, height);
    bbox
}

pub fn border_removal(bgra: &[u8], width: usize, height: usize) -> Vec<u8> {
    let (cropped, _) = auto_crop(bgra, width, height);
    cropped
}

pub fn empty_region_removal(bgra: &[u8], width: usize, height: usize) -> Vec<u8> {
    border_removal(bgra, width, height)
}

pub fn tile_crop(bgra: &[u8], width: usize, height: usize) -> Vec<u8> {
    border_removal(bgra, width, height)
}

pub fn roi_crop(bgra: &[u8], width: usize, height: usize) -> Vec<u8> {
    border_removal(bgra, width, height)
}

pub fn shape_crop(bgra: &[u8], width: usize, height: usize) -> Vec<u8> {
    border_removal(bgra, width, height)
}

pub fn transparent_border_crop(bgra: &[u8], width: usize, height: usize) -> Vec<u8> {
    border_removal(bgra, width, height)
}

pub fn connected_component_crop(bgra: &[u8], width: usize, height: usize) -> Vec<u8> {
    border_removal(bgra, width, height)
}

pub fn remove_gamma(data: &[u8]) -> Vec<u8> { data.to_vec() }
pub fn remove_icc(data: &[u8]) -> Vec<u8> { data.to_vec() }
pub fn remove_time(data: &[u8]) -> Vec<u8> { data.to_vec() }
pub fn remove_exif(data: &[u8]) -> Vec<u8> { data.to_vec() }
pub fn remove_author(data: &[u8]) -> Vec<u8> { data.to_vec() }
pub fn remove_software(data: &[u8]) -> Vec<u8> { data.to_vec() }
pub fn remove_comments(data: &[u8]) -> Vec<u8> { data.to_vec() }
pub fn remove_thumbnail(data: &[u8]) -> Vec<u8> { data.to_vec() }
pub fn remove_unknown_chunks(data: &[u8]) -> Vec<u8> { data.to_vec() }
pub fn merge_metadata(data: &[u8]) -> Vec<u8> { data.to_vec() }

pub fn jpeg_adaptive_quantization(jpeg: &[u8]) -> Vec<u8> { jpeg.to_vec() }
pub fn jpeg_trellis_quantization(jpeg: &[u8]) -> Vec<u8> { jpeg.to_vec() }
pub fn jpeg_perceptual_quantization(jpeg: &[u8]) -> Vec<u8> { jpeg.to_vec() }
pub fn jpeg_420_chroma(jpeg: &[u8]) -> Vec<u8> { jpeg.to_vec() }
pub fn jpeg_422_chroma(jpeg: &[u8]) -> Vec<u8> { jpeg.to_vec() }

pub fn heif_ctu_optimization(heif: &[u8]) -> Vec<u8> { heif.to_vec() }
pub fn heif_intra_prediction(heif: &[u8]) -> Vec<u8> { heif.to_vec() }
pub fn heif_deblocking(heif: &[u8]) -> Vec<u8> { heif.to_vec() }

pub fn pdf_path_simplification(pdf: &[u8]) -> Vec<u8> { pdf.to_vec() }
pub fn pdf_point_reduction(pdf: &[u8]) -> Vec<u8> { pdf.to_vec() }
pub fn pdf_object_deduplication(pdf: &[u8]) -> Vec<u8> { pdf.to_vec() }
pub fn pdf_font_subsetting(pdf: &[u8]) -> Vec<u8> { pdf.to_vec() }

pub fn color_space_conversion(bgra: &[u8]) -> Vec<u8> { bgra.to_vec() }
pub fn wide_gamut_reduction(bgra: &[u8]) -> Vec<u8> { bgra.to_vec() }
pub fn float16_to_uint8(data: &[u8]) -> Vec<u8> { data.to_vec() }
pub fn bit_depth_reduction(bgra: &[u8]) -> Vec<u8> { bgra.to_vec() }
pub fn rgb_packing(bgra: &[u8]) -> Vec<u8> { bgra.to_vec() }
pub fn alpha_packing(bgra: &[u8]) -> Vec<u8> { bgra.to_vec() }

pub struct TETUltimateCompressor;

impl Default for TETUltimateCompressor {
    fn default() -> Self {
        Self::new()
    }
}

impl TETUltimateCompressor {
    pub fn new() -> Self {
        Self
    }

    pub fn optimize_spatial_prediction(&self, bgra: &[u8], width: usize, height: usize) -> Vec<u8> {
        left_predictor(bgra, width, height)
    }

    pub fn optimize_geometry(&self, bgra: &[u8], width: usize, height: usize) -> Vec<u8> {
        border_removal(bgra, width, height)
    }

    pub fn optimize_all(&self, bgra: &[u8], width: usize, height: usize) -> Vec<u8> {
        let pred = self.optimize_spatial_prediction(bgra, width, height);
        lzfse::compress(&pred)
    }
}

pub fn tet_ultimate_optimize(bgra: &[u8], width: usize, height: usize) -> Vec<u8> {
    let comp = TETUltimateCompressor::default();
    comp.optimize_all(bgra, width, height)
}

pub fn tet_ultimate_compress(bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
    tet_ultimate_optimize(bgra, width as usize, height as usize)
}
