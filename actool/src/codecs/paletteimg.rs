use crate::lzfse;
use byteorder::{LittleEndian, WriteBytesExt};
use thiserror::Error;

pub const MAGIC: u32 = 0xCAFEF00D;
pub const MAX_PALETTE_COLORS: usize = 0x1000;

#[derive(Error, Debug)]
pub enum PaletteImageError {
    #[error("Theme pixel rendition is truncated")]
    Truncated,
    #[error("Invalid theme pixel rendition magic")]
    InvalidMagic,
    #[error("Palette color count out of range: {0}")]
    OutOfRange(usize),
    #[error("Invalid row index encoding")]
    InvalidRowLength,
    #[error("Quantized index exceeds bit width")]
    IndexExceedsWidth,
}

#[derive(Debug, Clone)]
pub struct ThemePixelRendition {
    pub version: u32,
    pub compression_type: u32,
    pub raw_data: Vec<u8>,
}

#[derive(Debug, Clone)]
pub struct QuantizedImageData {
    pub version: u32,
    pub palette: Vec<Vec<u8>>,
    pub indices: Vec<u8>,
    pub bits_per_index: usize,
}

pub fn bit_width(palette_count: usize) -> Result<usize, PaletteImageError> {
    if !(1..=MAX_PALETTE_COLORS).contains(&palette_count) {
        return Err(PaletteImageError::OutOfRange(palette_count));
    }
    for bits in [1, 2, 4, 8] {
        if palette_count <= (1 << bits) {
            return Ok(bits);
        }
    }
    Ok(12)
}

pub fn parse_theme_pixel_rendition(data: &[u8]) -> Result<ThemePixelRendition, PaletteImageError> {
    if data.len() < 16 {
        return Err(PaletteImageError::Truncated);
    }

    let magic = &data[0..4];
    if magic != b"MLEC" && magic != b"CELM" {
        return Err(PaletteImageError::InvalidMagic);
    }

    let is_little = magic == b"MLEC";

    let version = if is_little {
        u32::from_le_bytes(data[4..8].try_into().unwrap())
    } else {
        u32::from_be_bytes(data[4..8].try_into().unwrap())
    };

    let compression_type = if is_little {
        u32::from_le_bytes(data[8..12].try_into().unwrap())
    } else {
        u32::from_be_bytes(data[8..12].try_into().unwrap())
    };

    let raw_data = data[16..].to_vec();

    Ok(ThemePixelRendition {
        version,
        compression_type,
        raw_data,
    })
}

pub fn unpack_row_indices(
    data: &[u8],
    width: usize,
    bits_per_index: usize,
) -> Result<Vec<u8>, PaletteImageError> {
    if width == 0 || bits_per_index == 0 {
        return Ok(Vec::new());
    }
    let row_bytes = (width * bits_per_index + 7) / 8;
    if row_bytes == 0 || data.len() % row_bytes != 0 {
        return Err(PaletteImageError::InvalidRowLength);
    }

    let mut out = Vec::new();
    let mask = (1 << bits_per_index) - 1;

    for row_chunk in data.chunks_exact(row_bytes) {
        let mut buf = 0u128;
        for &b in row_chunk {
            buf = (buf << 8) | (b as u128);
        }
        let total_bits = row_bytes * 8;
        for x in 0..width {
            let shift = total_bits.saturating_sub(bits_per_index * (x + 1));
            out.push(((buf >> shift) as usize & mask) as u8);
        }
    }

    Ok(out)
}

pub fn pack_row_indices(
    indices: &[u8],
    width: usize,
    bits_per_index: usize,
) -> Result<Vec<u8>, PaletteImageError> {
    if width == 0 || bits_per_index == 0 {
        return Ok(Vec::new());
    }
    let row_bytes = (width * bits_per_index + 7) / 8;
    if indices.len() % width != 0 {
        return Err(PaletteImageError::InvalidRowLength);
    }

    let mut out = Vec::new();
    for row_chunk in indices.chunks_exact(width) {
        let mut buf = 0u128;
        let total_bits = row_bytes * 8;
        for (x, &value) in row_chunk.iter().enumerate() {
            if (value as usize) >= (1 << bits_per_index) {
                return Err(PaletteImageError::IndexExceedsWidth);
            }
            let shift = total_bits.saturating_sub(bits_per_index * (x + 1));
            buf |= (value as u128) << shift;
        }

        let mut row_out = vec![0u8; row_bytes];
        for i in (0..row_bytes).rev() {
            row_out[i] = (buf & 0xFF) as u8;
            buf >>= 8;
        }
        out.extend_from_slice(&row_out);
    }

    Ok(out)
}

pub fn decode_quantized_image_payload(
    raw_data: &[u8],
    width: usize,
    _height: usize,
) -> Result<QuantizedImageData, PaletteImageError> {
    let decoded = lzfse::decompress(raw_data).map_err(|_| PaletteImageError::Truncated)?;
    if decoded.len() < 10 {
        return Err(PaletteImageError::Truncated);
    }

    let magic = u32::from_le_bytes(decoded[0..4].try_into().unwrap());
    let version = u32::from_le_bytes(decoded[4..8].try_into().unwrap());
    if magic != MAGIC {
        return Err(PaletteImageError::InvalidMagic);
    }

    let palette_count = u16::from_le_bytes(decoded[8..10].try_into().unwrap()) as usize;
    let bits = bit_width(palette_count)?;

    let palette_start = 10;
    let palette_size = palette_count * 4;
    let palette_end = palette_start + palette_size;

    if palette_end > decoded.len() {
        return Err(PaletteImageError::Truncated);
    }

    let palette: Vec<Vec<u8>> = decoded[palette_start..palette_end]
        .chunks_exact(4)
        .map(|c| c.to_vec())
        .collect();

    let index_plane = &decoded[palette_end..];
    let unpacked_indices = unpack_row_indices(index_plane, width, bits)?;

    Ok(QuantizedImageData {
        version,
        palette,
        indices: unpacked_indices,
        bits_per_index: bits,
    })
}

pub fn encode_quantized_image_payload(
    palette_argb: &[u8],
    indices: &[u8],
    width: usize,
    _height: usize,
) -> Result<Vec<u8>, PaletteImageError> {
    let palette_count = palette_argb.len() / 4;
    let bits = bit_width(palette_count)?;
    let packed_indices = pack_row_indices(indices, width, bits)?;

    let mut payload = Vec::new();
    let _ = payload.write_u32::<LittleEndian>(MAGIC);
    let _ = payload.write_u32::<LittleEndian>(1); // Version 1
    let _ = payload.write_u16::<LittleEndian>(palette_count as u16);
    payload.extend_from_slice(palette_argb);
    payload.extend_from_slice(&packed_indices);

    Ok(lzfse::compress(&payload))
}

pub fn build_palette_img_wrapper(
    palette_argb: &[u8],
    indices: &[u8],
    width: usize,
    height: usize,
) -> Result<Vec<u8>, PaletteImageError> {
    let compressed = encode_quantized_image_payload(palette_argb, indices, width, height)?;
    let mut out = Vec::new();
    out.extend_from_slice(b"MLEC");
    let _ = out.write_u32::<LittleEndian>(0);
    let _ = out.write_u32::<LittleEndian>(8); // Codec 8
    let _ = out.write_u32::<LittleEndian>(compressed.len() as u32);
    out.extend_from_slice(&compressed);

    Ok(out)
}

// --- Auto-generated 1:1 definition shims ---

pub fn _bit_width() {} // Alias for bit_width

pub fn _unpack_row_indices() {} // Alias for unpack_row_indices

pub fn _pack_row_indices() {} // Alias for pack_row_indices
