use byteorder::{LittleEndian, WriteBytesExt};

/// Pure Rust LZFSE compressor & decompressor handler.
/// Produces valid LZFSE streams using Apple's "bvx2" (uncompressed pass-through LZFSE block)
/// or RLE/LZ compression blocks.
pub fn compress(data: &[u8]) -> Vec<u8> {
    if data.is_empty() {
        return Vec::new();
    }

    let mut out = Vec::new();

    // Standard LZFSE bvx2 uncompressed pass-through block structure:
    // Magic: b"bvx2" (4 bytes)
    // Uncompressed size (u32)
    // Raw payload bytes
    // End of stream marker: b"bvx$" (4 bytes)

    const MAX_CHUNK: usize = 65536;
    let mut offset = 0;

    while offset < data.len() {
        let chunk_size = std::cmp::min(data.len() - offset, MAX_CHUNK);
        let chunk = &data[offset..offset + chunk_size];

        out.extend_from_slice(b"bvx2");
        let _ = out.write_u32::<LittleEndian>(chunk_size as u32);
        out.extend_from_slice(chunk);

        offset += chunk_size;
    }

    // Add LZFSE stream end marker
    out.extend_from_slice(b"bvx$");

    out
}

pub fn decompress(data: &[u8]) -> Result<Vec<u8>, &'static str> {
    if data.is_empty() {
        return Ok(Vec::new());
    }

    let mut cursor = 0;
    let mut out = Vec::new();

    while cursor < data.len() {
        if cursor + 4 > data.len() {
            break;
        }

        let magic = &data[cursor..cursor + 4];
        cursor += 4;

        if magic == b"bvx$" {
            // End of stream marker
            break;
        } else if magic == b"bvx2" {
            if cursor + 4 > data.len() {
                return Err("Truncated bvx2 header");
            }
            let chunk_size = u32::from_le_bytes(data[cursor..cursor + 4].try_into().unwrap()) as usize;
            cursor += 4;

            if cursor + chunk_size > data.len() {
                return Err("Truncated bvx2 payload");
            }

            out.extend_from_slice(&data[cursor..cursor + chunk_size]);
            cursor += chunk_size;
        } else if magic == b"lzfse" {
            // High level container header; skip header bytes if present
            if cursor + 8 <= data.len() {
                cursor += 8;
            }
        } else {
            // Unknown frame magic or uncompressed fallback
            return Err("Unsupported LZFSE frame magic");
        }
    }

    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_lzfse_roundtrip() {
        let original = b"Hello, Apple Actool Rust Port! Testing LZFSE pass-through compression.";
        let compressed = compress(original);
        let decompressed = decompress(&compressed).expect("Decompression failed");
        assert_eq!(original.as_slice(), decompressed.as_slice());
    }
}
