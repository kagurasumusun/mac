use crate::lzfse;
use byteorder::{LittleEndian, WriteBytesExt};

#[derive(Debug, Clone)]
pub struct CBCKChunk {
    pub y_offset: u16,
    pub rows: u16,
    pub raw_length: usize,
    pub compressed: Vec<u8>,
}

#[derive(Debug, Clone)]
pub struct CBCKPayload {
    pub mode: u32,
    pub codec: u32,
    pub chunks: Vec<CBCKChunk>,
}

pub fn encode_cbck(
    bgra: &[u8],
    width: u32,
    height: u32,
    codec: u32,
    clean_alpha: bool,
) -> Vec<u8> {
    let row_bytes = (width * 4) as usize;
    if row_bytes == 0 || height == 0 {
        return Vec::new();
    }

    // Process alpha cleaning if requested (zero out RGB where alpha=0)
    let mut cleaned_bgra;
    let pixel_data = if clean_alpha {
        cleaned_bgra = bgra.to_vec();
        for chunk in cleaned_bgra.chunks_exact_mut(4) {
            if chunk[3] == 0 {
                chunk[0] = 0;
                chunk[1] = 0;
                chunk[2] = 0;
            }
        }
        &cleaned_bgra
    } else {
        bgra
    };

    // Apple raw cap per chunk is ~0x155555 (~1.39MB)
    const APPLE_CBCK_RAW_CAP: usize = 0x155555;
    let rows_per_chunk = std::cmp::max(1, APPLE_CBCK_RAW_CAP / row_bytes);

    let mut chunks = Vec::new();
    let mut y = 0;

    while y < height {
        let current_rows = std::cmp::min(rows_per_chunk as u32, height - y);
        let offset = (y as usize) * row_bytes;
        let chunk_len = (current_rows as usize) * row_bytes;
        let chunk_raw = &pixel_data[offset..offset + chunk_len];

        let compressed = lzfse::compress(chunk_raw);

        let mut chunk_buf = Vec::new();
        chunk_buf.extend_from_slice(b"KCBC");
        let _ = chunk_buf.write_u16::<LittleEndian>(y as u16);
        let _ = chunk_buf.write_u16::<LittleEndian>(current_rows as u16);
        let _ = chunk_buf.write_u32::<LittleEndian>(chunk_raw.len() as u32);
        let _ = chunk_buf.write_u32::<LittleEndian>(compressed.len() as u32);
        chunk_buf.extend_from_slice(&compressed);

        chunks.push(chunk_buf);
        y += current_rows;
    }

    let mut out = Vec::new();
    out.extend_from_slice(b"MLEC");
    let _ = out.write_u32::<LittleEndian>(3); // Mode 3
    let _ = out.write_u32::<LittleEndian>(codec); // Codec 4 or 11
    let _ = out.write_u32::<LittleEndian>(chunks.len() as u32);

    for c in chunks {
        out.extend_from_slice(&c);
    }

    out
}

pub fn parse_cbck(data: &[u8]) -> Result<CBCKPayload, &'static str> {
    if data.len() < 16 {
        return Err("CBCK payload truncated");
    }

    if &data[0..4] != b"MLEC" {
        return Err("Invalid MLEC magic");
    }

    let mode = u32::from_le_bytes(data[4..8].try_into().unwrap());
    let codec = u32::from_le_bytes(data[8..12].try_into().unwrap());
    let chunk_count = u32::from_le_bytes(data[12..16].try_into().unwrap()) as usize;

    let mut cursor = 16;
    let mut chunks = Vec::new();

    for _ in 0..chunk_count {
        if cursor + 16 > data.len() {
            return Err("KCBC chunk header truncated");
        }

        if &data[cursor..cursor + 4] != b"KCBC" {
            return Err("Invalid KCBC magic");
        }

        let y_offset = u16::from_le_bytes(data[cursor + 4..cursor + 6].try_into().unwrap());
        let rows = u16::from_le_bytes(data[cursor + 6..cursor + 8].try_into().unwrap());
        let raw_length = u32::from_le_bytes(data[cursor + 8..cursor + 12].try_into().unwrap()) as usize;
        let compressed_length = u32::from_le_bytes(data[cursor + 12..cursor + 16].try_into().unwrap()) as usize;

        cursor += 16;

        if cursor + compressed_length > data.len() {
            return Err("KCBC chunk payload truncated");
        }

        let compressed = data[cursor..cursor + compressed_length].to_vec();
        cursor += compressed_length;

        chunks.push(CBCKChunk {
            y_offset,
            rows,
            raw_length,
            compressed,
        });
    }

    Ok(CBCKPayload { mode, codec, chunks })
}
