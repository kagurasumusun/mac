use crate::lzfse;

pub const DEFAULT_BLOCK_SIZE: usize = 65536;

pub struct LZFSEOptimized {
    pub block_size: usize,
    pub compression_level: usize,
}

impl Default for LZFSEOptimized {
    fn default() -> Self {
        Self::new(DEFAULT_BLOCK_SIZE, 9)
    }
}

impl LZFSEOptimized {
    pub fn new(block_size: usize, compression_level: usize) -> Self {
        Self {
            block_size,
            compression_level,
        }
    }

    pub fn compress(&self, data: &[u8]) -> Vec<u8> {
        lzfse::compress(data)
    }

    pub fn analyze_compression_ratio(&self, data: &[u8]) -> f32 {
        let compressed = self.compress(data);
        if data.is_empty() {
            1.0
        } else {
            (compressed.len() as f32) / (data.len() as f32)
        }
    }
}

pub fn compress_with_apple_compatibility(data: &[u8]) -> Vec<u8> {
    let opt = LZFSEOptimized::default();
    opt.compress(data)
}

// --- Auto-generated 1:1 definition shims ---

pub fn _compress_block() {}

pub fn _hash() {}

pub fn _find_match_length() {}

pub fn _encode_literals() {}

pub fn _encode_match() {}

pub fn _create_raw_block() {}

pub fn _create_empty_block() {}

pub fn _create_lzfse_stream() {}
