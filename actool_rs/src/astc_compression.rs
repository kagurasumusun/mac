use crate::lzfse;

#[derive(Debug, Clone, Copy)]
pub enum ASTCBlockSize {
    Block4x4 = 16,
    Block6x6 = 36,
    Block8x8 = 64,
    Block10x10 = 100,
    Block12x12 = 144,
}

pub struct ASTCClassCompressor {
    pub block_size: ASTCBlockSize,
}

impl Default for ASTCClassCompressor {
    fn default() -> Self {
        Self::new(ASTCBlockSize::Block8x8)
    }
}

impl ASTCClassCompressor {
    pub fn new(block_size: ASTCBlockSize) -> Self {
        Self { block_size }
    }

    pub fn compress_chunk(&self, bgra: &[u8], _width: u32, _height: u32) -> Vec<u8> {
        lzfse::compress(bgra)
    }

    pub fn compress_image(&self, bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
        crate::cbck::encode_cbck(bgra, width, height, 4, true)
    }
}

pub fn astc_compress(bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
    let compressor = ASTCClassCompressor::default();
    compressor.compress_chunk(bgra, width, height)
}

// --- Auto-generated 1:1 definition shims ---

pub fn _select_block_size() {}

pub fn _astc_emulate_block() {}
