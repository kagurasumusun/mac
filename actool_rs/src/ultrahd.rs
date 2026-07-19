use crate::lzfse;
use byteorder::{LittleEndian, WriteBytesExt};
use rayon::prelude::*;
use serde_json::json;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum UltraHDTier {
    Standard,       // < 4K
    Resolution4K,   // >= 3840 x 2160
    Resolution8K,   // >= 7680 x 4320
    Resolution16K,  // >= 15360 x 8640
}

pub fn classify_resolution_tier(width: u32, height: u32) -> UltraHDTier {
    let max_dim = std::cmp::max(width, height);
    if max_dim >= 15360 {
        UltraHDTier::Resolution16K
    } else if max_dim >= 7680 {
        UltraHDTier::Resolution8K
    } else if max_dim >= 3840 {
        UltraHDTier::Resolution4K
    } else {
        UltraHDTier::Standard
    }
}

/// Ultra-HD Tiled Grid CBCK Encoder for 4K/8K/16K images
/// Uses 2D spatial tiles (e.g. 512x512) and Rayon parallel thread pools
/// to prevent memory exhaustion and achieve maximum multi-threaded performance.
pub fn encode_ultrahd_tiled_cbck(
    bgra: &[u8],
    width: u32,
    height: u32,
    tile_dim: u32,
    clean_alpha: bool,
) -> Vec<u8> {
    let tier = classify_resolution_tier(width, height);
    let effective_tile = match tier {
        UltraHDTier::Resolution16K => 1024,
        UltraHDTier::Resolution8K => 512,
        UltraHDTier::Resolution4K => 256,
        UltraHDTier::Standard => tile_dim,
    };

    let tiles_x = (width + effective_tile - 1) / effective_tile;
    let tiles_y = (height + effective_tile - 1) / effective_tile;

    // Build 2D grid coordinates for parallel tile processing
    let mut tile_coords = Vec::new();
    for ty in 0..tiles_y {
        for tx in 0..tiles_x {
            tile_coords.push((tx, ty));
        }
    }

    let kcbc_chunks: Vec<Vec<u8>> = tile_coords
        .par_iter()
        .map(|&(tx, ty)| {
            let x_off = tx * effective_tile;
            let y_off = ty * effective_tile;
            let w = std::cmp::min(effective_tile, width.saturating_sub(x_off));
            let h = std::cmp::min(effective_tile, height.saturating_sub(y_off));

            let mut tile_pixels = Vec::with_capacity((w * h * 4) as usize);

            for y in 0..h {
                let py = y_off + y;
                let row_start = ((py * width + x_off) * 4) as usize;
                let row_len = (w * 4) as usize;

                if row_start + row_len <= bgra.len() {
                    let mut row = bgra[row_start..row_start + row_len].to_vec();
                    if clean_alpha {
                        for px in row.chunks_exact_mut(4) {
                            if px[3] == 0 {
                                px[0] = 0;
                                px[1] = 0;
                                px[2] = 0;
                            }
                        }
                    }
                    tile_pixels.extend_from_slice(&row);
                } else {
                    tile_pixels.extend_from_slice(&vec![0u8; row_len]);
                }
            }

            let compressed = lzfse::compress(&tile_pixels);

            let mut kcbc = Vec::with_capacity(16 + compressed.len());
            kcbc.extend_from_slice(b"KCBC");
            let _ = kcbc.write_u16::<LittleEndian>(x_off as u16);
            let _ = kcbc.write_u16::<LittleEndian>(y_off as u16);
            let _ = kcbc.write_u32::<LittleEndian>(tile_pixels.len() as u32);
            let _ = kcbc.write_u32::<LittleEndian>(compressed.len() as u32);
            kcbc.extend_from_slice(&compressed);

            kcbc
        })
        .collect();

    let mut payload = Vec::new();
    payload.extend_from_slice(b"MLEC");
    let _ = payload.write_u32::<LittleEndian>(3); // Mode 3
    let _ = payload.write_u32::<LittleEndian>(4); // Codec 4
    let _ = payload.write_u32::<LittleEndian>(kcbc_chunks.len() as u32);

    for chunk in kcbc_chunks {
        payload.extend_from_slice(&chunk);
    }

    payload
}

pub fn get_ultrahd_report(width: u32, height: u32, raw_bytes_size: usize) -> serde_json::Value {
    let tier = classify_resolution_tier(width, height);
    json!({
        "width": width,
        "height": height,
        "total_pixels": width * height,
        "uncompressed_vram_bytes": raw_bytes_size,
        "resolution_tier": format!("{:?}", tier),
        "recommended_tile_size": match tier {
            UltraHDTier::Resolution16K => 1024,
            UltraHDTier::Resolution8K => 512,
            UltraHDTier::Resolution4K => 256,
            UltraHDTier::Standard => 64,
        }
    })
}
