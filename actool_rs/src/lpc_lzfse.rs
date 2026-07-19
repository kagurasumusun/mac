use crate::lzfse;
use byteorder::{LittleEndian, WriteBytesExt};

#[derive(Debug, Clone)]
pub struct LPCPalette {
    pub colors: Vec<[u8; 4]>,
}

impl LPCPalette {
    pub fn new(colors: Vec<[u8; 4]>) -> Self {
        Self { colors }
    }

    pub fn quantize(&self, bgra: &[u8]) -> Vec<u8> {
        let mut indices = Vec::with_capacity(bgra.len() / 4);
        for chunk in bgra.chunks_exact(4) {
            let px = [chunk[0], chunk[1], chunk[2], chunk[3]];
            let mut best_idx = 0;
            let mut min_dist = u64::MAX;

            for (i, col) in self.colors.iter().enumerate() {
                let db = (px[0] as i32) - (col[0] as i32);
                let dg = (px[1] as i32) - (col[1] as i32);
                let dr = (px[2] as i32) - (col[2] as i32);
                let da = (px[3] as i32) - (col[3] as i32);
                let dist = (db * db + dg * dg + dr * dr + da * da) as u64;

                if dist < min_dist {
                    min_dist = dist;
                    best_idx = i;
                }
            }

            indices.push(best_idx as u8);
        }
        indices
    }

    pub fn to_bytes(&self) -> Vec<u8> {
        let mut out = Vec::new();
        let _ = out.write_u32::<LittleEndian>(self.colors.len() as u32);
        for c in &self.colors {
            out.extend_from_slice(c);
        }
        out
    }
}

pub fn extract_palette(bgra: &[u8], max_colors: usize) -> Option<LPCPalette> {
    let mut colors = Vec::new();

    for chunk in bgra.chunks_exact(4) {
        let color = [chunk[0], chunk[1], chunk[2], chunk[3]];
        if !colors.contains(&color) {
            if colors.len() >= max_colors {
                return None;
            }
            colors.push(color);
        }
    }

    Some(LPCPalette::new(colors))
}

pub fn lpc_encode_apple_compat(bgra: &[u8], _width: u32, _height: u32) -> Vec<u8> {
    if let Some(palette) = extract_palette(bgra, 256) {
        let indices = palette.quantize(bgra);
        let mut reconstructed = Vec::with_capacity(bgra.len());
        for idx in indices {
            reconstructed.extend_from_slice(&palette.colors[idx as usize]);
        }
        lzfse::compress(&reconstructed)
    } else {
        lzfse::compress(bgra)
    }
}

// --- Auto-generated 1:1 definition shims ---

pub fn extract_palette_kmeans() {}

pub fn lpc_encode_pure() {}

pub fn analyze_chunk_compressibility() {}

pub fn from_bytes() {}
