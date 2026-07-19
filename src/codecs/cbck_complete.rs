use crate::cbck::encode_cbck;
use crate::lzfse;
use byteorder::{LittleEndian, WriteBytesExt};

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
    pub chunk_width: u32,
    pub chunk_height: u32,
}

impl Default for CBCKEncoder {
    fn default() -> Self {
        Self::new(64, 64)
    }
}

impl CBCKEncoder {
    pub fn new(chunk_width: u32, chunk_height: u32) -> Self {
        Self { chunk_width, chunk_height }
    }

    pub fn _align_to_power_of_2(value: u32) -> u32 {
        if value <= 16 { 16 }
        else if value <= 32 { 32 }
        else if value <= 64 { 64 }
        else if value <= 128 { 128 }
        else { 256 }
    }

    pub fn determine_optimal_chunk_size(&self, width: u32, height: u32) -> (u32, u32) {
        let mut cw = self.chunk_width;
        let mut ch = self.chunk_height;

        if width < 128 && height < 128 {
            cw = std::cmp::min(32, width);
            ch = std::cmp::min(32, height);
        } else if width > 1024 || height > 1024 {
            cw = std::cmp::min(128, width);
            ch = std::cmp::min(128, height);
        }

        cw = Self::_align_to_power_of_2(cw);
        ch = Self::_align_to_power_of_2(ch);

        (cw, ch)
    }

    pub fn _extract_chunk(pixels: &[u8], img_w: u32, _img_h: u32, x: u32, y: u32, w: u32, h: u32) -> Vec<u8> {
        let mut chunk_data = Vec::with_capacity((w * h * 4) as usize);

        for row in 0..h {
            for col in 0..w {
                let px = x + col;
                let py = y + row;

                let offset = ((py * img_w + px) * 4) as usize;
                if offset + 4 <= pixels.len() {
                    chunk_data.extend_from_slice(&pixels[offset..offset + 4]);
                } else {
                    chunk_data.extend_from_slice(&[0, 0, 0, 0]);
                }
            }
        }

        chunk_data
    }

    pub fn encode(&self, width: u32, height: u32, pixels: &[u8]) -> (Vec<CBCKChunk>, usize, usize) {
        let (cw, ch) = self.determine_optimal_chunk_size(width, height);
        let chunks_per_row = ((width + cw - 1) / cw) as usize;
        let chunks_per_col = ((height + ch - 1) / ch) as usize;

        let mut chunks = Vec::new();

        for row in 0..chunks_per_col {
            for col in 0..chunks_per_row {
                let x = (col as u32) * cw;
                let y = (row as u32) * ch;
                let w = std::cmp::min(cw, width.saturating_sub(x));
                let h = std::cmp::min(ch, height.saturating_sub(y));

                let chunk_pixels = Self::_extract_chunk(pixels, width, height, x, y, w, h);
                chunks.push(CBCKChunk::from_raw(w, h, &chunk_pixels));
            }
        }

        (chunks, chunks_per_row, chunks_per_col)
    }

    pub fn calculate_compression_ratio(&self, chunks: &[CBCKChunk]) -> f32 {
        let total_comp: usize = chunks.iter().map(|c| c.compressed_size).sum();
        let total_uncomp: usize = chunks.iter().map(|c| c.uncompressed_size).sum();
        if total_uncomp == 0 {
            0.0
        } else {
            (total_comp as f32) / (total_uncomp as f32)
        }
    }
}

pub struct CBCKDecoder;

impl CBCKDecoder {
    pub fn decode(chunks: &[CBCKChunk], chunks_per_row: usize, chunks_per_col: usize, width: u32, height: u32) -> Result<Vec<u8>, &'static str> {
        if chunks.is_empty() {
            return Ok(Vec::new());
        }

        let mut output = vec![0u8; (width * height * 4) as usize];
        let cw = chunks[0].width;
        let ch = chunks[0].height;

        for row in 0..chunks_per_col {
            for col in 0..chunks_per_row {
                let idx = row * chunks_per_row + col;
                if idx >= chunks.len() {
                    break;
                }

                let chunk = &chunks[idx];
                let pixels = chunk.decompress()?;

                let x = (col as u32) * cw;
                let y = (row as u32) * ch;

                for py in 0..chunk.height {
                    for px in 0..chunk.width {
                        if x + px < width && y + py < height {
                            let src_off = ((py * chunk.width + px) * 4) as usize;
                            let dst_off = (((y + py) * width + (x + px)) * 4) as usize;
                            if src_off + 4 <= pixels.len() && dst_off + 4 <= output.len() {
                                output[dst_off..dst_off + 4].copy_from_slice(&pixels[src_off..src_off + 4]);
                            }
                        }
                    }
                }
            }
        }

        Ok(output)
    }
}

pub fn _serialize_chunks(chunks: &[CBCKChunk], chunks_per_row: u32, chunks_per_col: u32) -> Vec<u8> {
    let mut out = Vec::new();
    let _ = out.write_u32::<LittleEndian>(chunks.len() as u32);
    let _ = out.write_u32::<LittleEndian>(chunks_per_row);
    let _ = out.write_u32::<LittleEndian>(chunks_per_col);

    for chunk in chunks {
        let _ = out.write_u32::<LittleEndian>(chunk.width);
        let _ = out.write_u32::<LittleEndian>(chunk.height);
        let _ = out.write_u32::<LittleEndian>(chunk.compressed_size as u32);
    }

    for chunk in chunks {
        out.extend_from_slice(&chunk.data);
    }

    out
}

pub fn optimize_cbck_for_apple_compatibility(width: u32, height: u32, pixels: &[u8]) -> Vec<u8> {
    encode_cbck(pixels, width, height, 4, true)
}
