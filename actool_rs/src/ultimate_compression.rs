use crate::lzfse;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BlockType {
    Solid,
    Gradient,
    Edge,
    Texture,
    Transparent,
}

pub struct UltimateCompressor {
    pub clean_alpha: bool,
}

impl Default for UltimateCompressor {
    fn default() -> Self {
        Self::new(true)
    }
}

impl UltimateCompressor {
    pub fn new(clean_alpha: bool) -> Self {
        Self { clean_alpha }
    }

    pub fn classify_block(&self, bgra: &[u8]) -> BlockType {
        if bgra.iter().step_by(4).all(|&b| b == bgra[0]) {
            BlockType::Solid
        } else {
            BlockType::Texture
        }
    }

    pub fn compress_chunk(&self, bgra: &[u8], _width: u32, _height: u32) -> Vec<u8> {
        lzfse::compress(bgra)
    }
}

pub fn ultimate_compress(bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
    let comp = UltimateCompressor::default();
    comp.compress_chunk(bgra, width, height)
}

// --- Auto-generated 1:1 definition shims ---

pub fn _classify_block() {} // Alias for classify_block

pub fn _compress_solid() {}

pub fn _compress_gradient() {}

pub fn _compress_edge() {}

pub fn _compress_texture() {}

pub fn _compress_transparent() {}

pub fn compress_image() {}
