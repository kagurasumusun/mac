use byteorder::{LittleEndian, WriteBytesExt};
use std::collections::HashMap;

pub const DEFAULT_BLOCK_SIZE: usize = 65536;
pub const MAX_MATCH_LENGTH: usize = 273;
pub const MIN_MATCH_LENGTH: usize = 3;
pub const HASH_BITS: usize = 14;

pub struct LZFSEOptimized {
    pub block_size: usize,
    pub compression_level: usize,
    pub max_match_length: usize,
    pub hash_bits: usize,
}

impl Default for LZFSEOptimized {
    fn default() -> Self {
        Self::new(DEFAULT_BLOCK_SIZE, 9)
    }
}

impl LZFSEOptimized {
    pub fn new(block_size: usize, compression_level: usize) -> Self {
        let (max_match_length, hash_bits) = if compression_level >= 9 {
            (MAX_MATCH_LENGTH, HASH_BITS)
        } else if compression_level >= 6 {
            (128, 12)
        } else {
            (64, 10)
        };

        Self {
            block_size,
            compression_level,
            max_match_length,
            hash_bits,
        }
    }

    pub fn _hash(&self, data: &[u8]) -> usize {
        if data.len() < 3 {
            return 0;
        }
        let h = ((data[0] as u32) << 16) | ((data[1] as u32) << 8) | (data[2] as u32);
        let val = (h.wrapping_mul(0x1e35a7bd)) >> (24 - self.hash_bits);
        (val as usize) & ((1 << self.hash_bits) - 1)
    }

    pub fn _find_match_length(&self, data: &[u8], pos1: usize, pos2: usize) -> usize {
        let mut len = 0;
        let max_len = std::cmp::min(self.max_match_length, data.len() - pos2);
        while len < max_len && data[pos1 + len] == data[pos2 + len] {
            len += 1;
        }
        len
    }

    pub fn _encode_literals(&self, literals: &[u8]) -> Vec<u8> {
        let mut out = Vec::with_capacity(3 + literals.len());
        out.push(0x00);
        let _ = out.write_u16::<LittleEndian>(literals.len() as u16);
        out.extend_from_slice(literals);
        out
    }

    pub fn _encode_match(&self, length: usize, distance: usize) -> Vec<u8> {
        let mut out = Vec::new();
        out.push(0x01);

        if length < 16 {
            out.push(length as u8);
        } else if length < 256 {
            out.push(0x10);
            out.push(length as u8);
        } else {
            out.push(0x11);
            let _ = out.write_u16::<LittleEndian>(length as u16);
        }

        if distance < 256 {
            out.push(distance as u8);
        } else if distance < 65536 {
            let _ = out.write_u16::<LittleEndian>(distance as u16);
        } else {
            out.push(0xFF);
            let _ = out.write_u32::<LittleEndian>(distance as u32);
        }

        out
    }

    pub fn _create_raw_block(&self, data: &[u8]) -> Vec<u8> {
        let mut out = Vec::with_capacity(5 + data.len());
        out.push(0xFF);
        let _ = out.write_u32::<LittleEndian>(data.len() as u32);
        out.extend_from_slice(data);
        out
    }

    pub fn _create_empty_block(&self) -> Vec<u8> {
        vec![0, 0, 0, 0]
    }

    pub fn _compress_block(&self, data: &[u8]) -> Vec<u8> {
        if data.len() < 16 {
            return self._create_raw_block(data);
        }

        let mut hash_table: HashMap<usize, usize> = HashMap::new();
        let mut output = Vec::new();
        let mut i = 0;
        let mut literals = Vec::new();

        while i < data.len() {
            if i + MIN_MATCH_LENGTH <= data.len() {
                let hash_val = self._hash(&data[i..i + MIN_MATCH_LENGTH]);

                if let Some(&match_pos) = hash_table.get(&hash_val) {
                    let match_len = self._find_match_length(data, match_pos, i);

                    if match_len >= MIN_MATCH_LENGTH {
                        if !literals.is_empty() {
                            output.extend_from_slice(&self._encode_literals(&literals));
                            literals.clear();
                        }

                        let distance = i - match_pos;
                        output.extend_from_slice(&self._encode_match(match_len, distance));

                        for j in 0..match_len {
                            if i + j + MIN_MATCH_LENGTH <= data.len() {
                                let h = self._hash(&data[i + j..i + j + MIN_MATCH_LENGTH]);
                                hash_table.insert(h, i + j);
                            }
                        }

                        i += match_len;
                        continue;
                    }
                }

                hash_table.insert(hash_val, i);
            }

            literals.push(data[i]);
            i += 1;
        }

        if !literals.is_empty() {
            output.extend_from_slice(&self._encode_literals(&literals));
        }

        output
    }

    pub fn _create_lzfse_stream(&self, blocks: &[Vec<u8>], original_size: usize) -> Vec<u8> {
        let mut output = Vec::new();
        output.extend_from_slice(b"bvx2");
        let _ = output.write_u32::<LittleEndian>(original_size as u32);
        let _ = output.write_u32::<LittleEndian>(blocks.len() as u32);

        let mut block_offset = 0u32;
        for block in blocks {
            let _ = output.write_u32::<LittleEndian>(block_offset);
            let _ = output.write_u32::<LittleEndian>(block.len() as u32);
            block_offset += block.len() as u32;
        }

        for block in blocks {
            output.extend_from_slice(block);
        }

        output.extend_from_slice(b"bvx-");
        output
    }

    pub fn compress(&self, data: &[u8]) -> Vec<u8> {
        if data.is_empty() {
            return self._create_empty_block();
        }

        let mut blocks = Vec::new();
        let mut offset = 0;
        while offset < data.len() {
            let block_len = std::cmp::min(data.len() - offset, self.block_size);
            let block_data = &data[offset..offset + block_len];
            let compressed_block = self._compress_block(block_data);
            blocks.push(compressed_block);
            offset += self.block_size;
        }

        self._create_lzfse_stream(&blocks, data.len())
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
