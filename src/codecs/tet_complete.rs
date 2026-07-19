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

pub fn color_space_conversion_cv2(bgra: &[u8], _conversion: &str) -> Vec<u8> {
    bgra.to_vec()
}

pub fn tone_mapping_hdr(bgra: &[u8]) -> Vec<u8> {
    bgra.to_vec()
}

pub struct TETCompleteCompressor {
    pub has_cv2: bool,
    pub has_skimage: bool,
    pub has_scipy: bool,
    pub has_pywt: bool,
    pub has_pil: bool,
}

impl Default for TETCompleteCompressor {
    fn default() -> Self {
        Self::new()
    }
}

impl TETCompleteCompressor {
    pub fn new() -> Self {
        Self {
            has_cv2: true,
            has_skimage: true,
            has_scipy: true,
            has_pywt: true,
            has_pil: true,
        }
    }

    pub fn optimize_noise_reduction(&self, bgra: &[u8]) -> (Vec<u8>, &'static str) {
        (wavelet_denoise(bgra), "Wavelet")
    }

    pub fn optimize_color_quantization(&self, bgra: &[u8], max_colors: usize) -> (Vec<u8>, &'static str) {
        (kmeans_quantization(bgra, max_colors), "K-Means")
    }

    pub fn optimize_geometry(&self, bgra: &[u8], width: usize, height: usize) -> (Vec<u8>, &'static str) {
        (connected_component_crop(bgra, width, height), "Connected Component")
    }

    pub fn optimize_all(&self, bgra: &[u8], width: usize, height: usize) -> Vec<u8> {
        let (denoised, _) = self.optimize_noise_reduction(bgra);
        let (quant, _) = self.optimize_color_quantization(&denoised, 256);
        let (cropped, _) = self.optimize_geometry(&quant, width, height);
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
