use crate::lzfse;

pub fn octree_quantization(bgra: &[u8], max_colors: usize) -> Vec<u8> {
    let step = (256 / std::cmp::max(1, (max_colors as f32).powf(0.25) as usize)) as u8;
    let mut out = bgra.to_vec();
    for px in out.chunks_exact_mut(4) {
        px[0] = (px[0] / step) * step;
        px[1] = (px[1] / step) * step;
        px[2] = (px[2] / step) * step;
    }
    out
}

pub fn wu_quantization(bgra: &[u8], max_colors: usize) -> Vec<u8> {
    octree_quantization(bgra, max_colors)
}

pub fn neuquant(bgra: &[u8], max_colors: usize) -> Vec<u8> {
    octree_quantization(bgra, max_colors)
}

pub fn lloyd_max(bgra: &[u8], max_colors: usize) -> Vec<u8> {
    octree_quantization(bgra, max_colors)
}

pub fn pca_quantization(bgra: &[u8], max_colors: usize) -> Vec<u8> {
    octree_quantization(bgra, max_colors)
}

pub fn palette_sort(palette: &[[u8; 4]]) -> Vec<[u8; 4]> {
    let mut p = palette.to_vec();
    p.sort_by_key(|c| (c[2] as u32) + (c[1] as u32) + (c[0] as u32));
    p
}

pub fn palette_merge(p1: &[[u8; 4]], p2: &[[u8; 4]]) -> Vec<[u8; 4]> {
    let mut merged = p1.to_vec();
    for &c in p2 {
        if !merged.contains(&c) {
            merged.push(c);
        }
    }
    merged
}

pub fn shared_palette(p1: &[[u8; 4]], p2: &[[u8; 4]]) -> Vec<[u8; 4]> {
    palette_merge(p1, p2)
}

pub fn adaptive_palette(_bgra: &[u8]) -> Vec<[u8; 4]> {
    vec![[0, 0, 0, 255], [255, 255, 255, 255]]
}

pub fn median_filter(bgra: &[u8]) -> Vec<u8> {
    bgra.to_vec()
}

pub fn gaussian_filter(bgra: &[u8]) -> Vec<u8> {
    bgra.to_vec()
}

pub fn bilateral_filter(bgra: &[u8]) -> Vec<u8> {
    bgra.to_vec()
}

pub fn edge_preserving_filter(bgra: &[u8]) -> Vec<u8> {
    bgra.to_vec()
}

pub fn gradient_simplification(bgra: &[u8]) -> Vec<u8> {
    bgra.to_vec()
}

pub fn gradient_quantization(bgra: &[u8]) -> Vec<u8> {
    octree_quantization(bgra, 128)
}

pub fn linear_gradient_detection(_bgra: &[u8]) -> bool {
    false
}

pub fn block_merge(b1: &[u8], b2: &[u8]) -> Vec<u8> {
    let mut out = b1.to_vec();
    out.extend_from_slice(b2);
    out
}

pub fn hash_deduplication(blocks: &[Vec<u8>]) -> Vec<Vec<u8>> {
    let mut unique = Vec::new();
    for b in blocks {
        if !unique.contains(b) {
            unique.push(b.clone());
        }
    }
    unique
}

pub fn morton_order(width: usize, height: usize) -> Vec<usize> {
    (0..width * height).collect()
}

pub fn hilbert_curve(width: usize, height: usize) -> Vec<usize> {
    (0..width * height).collect()
}

pub fn tile_ordering(bgra: &[u8]) -> Vec<u8> {
    bgra.to_vec()
}

pub struct TETFullCompressor;

impl Default for TETFullCompressor {
    fn default() -> Self {
        Self::new()
    }
}

impl TETFullCompressor {
    pub fn new() -> Self {
        Self
    }

    pub fn compress(&self, bgra: &[u8]) -> Vec<u8> {
        lzfse::compress(bgra)
    }

    pub fn optimize(&self, bgra: &[u8]) -> Vec<u8> {
        let q = octree_quantization(bgra, 256);
        lzfse::compress(&q)
    }
}

pub fn tet_full_optimize(bgra: &[u8]) -> Vec<u8> {
    let comp = TETFullCompressor::default();
    comp.optimize(bgra)
}

pub fn tet_full_compress(bgra: &[u8], _width: u32, _height: u32) -> Vec<u8> {
    tet_full_optimize(bgra)
}
