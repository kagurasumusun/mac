use crate::lzfse;

pub fn bm3d_denoise(bgra: &[u8]) -> Vec<u8> {
    bgra.to_vec()
}

pub fn wavelet_denoise(bgra: &[u8]) -> Vec<u8> {
    bgra.to_vec()
}

pub fn non_local_means_denoise(bgra: &[u8]) -> Vec<u8> {
    bgra.to_vec()
}

pub fn bilateral_filter_cv2(bgra: &[u8]) -> Vec<u8> {
    bgra.to_vec()
}

pub fn connected_component_crop(bgra: &[u8], width: usize, height: usize) -> Vec<u8> {
    let (cropped, _) = crate::tet_compression::transparent_border_removal(bgra, width, height);
    cropped
}

pub fn kmeans_quantization(bgra: &[u8], max_colors: usize) -> Vec<u8> {
    crate::tet_full::octree_quantization(bgra, max_colors)
}

pub fn median_cut_pil(bgra: &[u8], max_colors: usize) -> Vec<u8> {
    crate::tet_full::octree_quantization(bgra, max_colors)
}

pub fn color_space_conversion_cv2(bgra: &[u8]) -> Vec<u8> {
    bgra.to_vec()
}

pub fn tone_mapping_hdr(bgra: &[u8]) -> Vec<u8> {
    bgra.to_vec()
}

pub struct TETCompleteCompressor;

impl Default for TETCompleteCompressor {
    fn default() -> Self {
        Self::new()
    }
}

impl TETCompleteCompressor {
    pub fn new() -> Self {
        Self
    }

    pub fn optimize_noise_reduction(&self, bgra: &[u8]) -> Vec<u8> {
        wavelet_denoise(bgra)
    }

    pub fn optimize_color_quantization(&self, bgra: &[u8], max_colors: usize) -> Vec<u8> {
        kmeans_quantization(bgra, max_colors)
    }

    pub fn optimize_geometry(&self, bgra: &[u8], width: usize, height: usize) -> Vec<u8> {
        connected_component_crop(bgra, width, height)
    }

    pub fn optimize_all(&self, bgra: &[u8], width: usize, height: usize) -> Vec<u8> {
        let denoised = self.optimize_noise_reduction(bgra);
        let quant = self.optimize_color_quantization(&denoised, 256);
        let cropped = self.optimize_geometry(&quant, width, height);
        lzfse::compress(&cropped)
    }
}

pub fn tet_complete_optimize(bgra: &[u8], width: usize, height: usize) -> Vec<u8> {
    let comp = TETCompleteCompressor::default();
    comp.optimize_all(bgra, width, height)
}

pub fn tet_complete_compress(bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
    tet_complete_optimize(bgra, width as usize, height as usize)
}
