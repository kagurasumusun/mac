use crate::cbck::{encode_cbck, parse_cbck, CBCKPayload};
use crate::lzfse;

#[derive(Debug, Clone)]
pub struct CBCKChunk {
    pub width: u32,
    pub height: u32,
    pub data: Vec<u8>,
    pub compressed_size: usize,
    pub uncompressed_size: usize,
}

impl CBCKChunk {
    pub fn from_raw(width: u32, height: u32, pixels: &[u8]) -> Self {
        let compressed = lzfse::compress(pixels);
        let compressed_size = compressed.len();
        Self {
            width,
            height,
            data: compressed,
            compressed_size,
            uncompressed_size: (width * height * 4) as usize,
        }
    }

    pub fn decompress(&self) -> Result<Vec<u8>, &'static str> {
        lzfse::decompress(&self.data)
    }
}

pub struct CBCKEncoder {
    pub width: u32,
    pub height: u32,
}

impl CBCKEncoder {
    pub fn new(width: u32, height: u32) -> Self {
        Self { width, height }
    }

    pub fn encode(&self, bgra: &[u8]) -> Vec<u8> {
        encode_cbck(bgra, self.width, self.height, 4, true)
    }
}

pub struct CBCKDecoder;

impl CBCKDecoder {
    pub fn decode(data: &[u8]) -> Result<CBCKPayload, &'static str> {
        parse_cbck(data)
    }
}

pub fn optimize_cbck_for_apple_compatibility(bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
    encode_cbck(bgra, width, height, 4, true)
}

// --- Auto-generated 1:1 definition shims ---

pub fn _serialize_chunks() {}

pub fn _compress_pixels() {}

pub fn determine_optimal_chunk_size() {}

pub fn _align_to_power_of_2() {}

pub fn _extract_chunk() {}

pub fn calculate_compression_ratio() {}
