use crate::lzfse;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BlockType {
    Solid = 0,
    Gradient = 1,
    Edge = 2,
    Texture = 3,
    Transparent = 4,
}

pub struct UltimateCompressor {
    pub block_size: usize,
    pub clean_alpha: bool,
}

impl Default for UltimateCompressor {
    fn default() -> Self {
        Self::new(16, true)
    }
}

impl UltimateCompressor {
    pub fn new(block_size: usize, clean_alpha: bool) -> Self {
        Self {
            block_size,
            clean_alpha,
        }
    }

    pub fn classify_block(&self, block_bgra: &[u8]) -> BlockType {
        let pixels = block_bgra.len() / 4;
        if pixels == 0 {
            return BlockType::Solid;
        }

        let mut zero_alpha_count = 0;
        let mut unique_colors = Vec::new();

        for px in block_bgra.chunks_exact(4) {
            if px[3] == 0 {
                zero_alpha_count += 1;
            }
            let color = [px[0], px[1], px[2], px[3]];
            if !unique_colors.contains(&color) {
                unique_colors.push(color);
            }
        }

        if (zero_alpha_count as f32) / (pixels as f32) > 0.95 {
            return BlockType::Transparent;
        }

        if unique_colors.len() == 1 || (unique_colors.len() <= 4 && pixels <= 64) {
            return BlockType::Solid;
        }

        if unique_colors.len() <= 32 {
            return BlockType::Edge;
        }

        BlockType::Texture
    }

    pub fn compress_solid(&self, block_bgra: &[u8]) -> Vec<u8> {
        if block_bgra.len() >= 4 {
            block_bgra[0..4].to_vec()
        } else {
            vec![0, 0, 0, 255]
        }
    }

    pub fn compress_gradient(&self, block_bgra: &[u8]) -> Vec<u8> {
        let step = 16u8;
        let mut out = block_bgra.to_vec();
        for px in out.chunks_exact_mut(4) {
            px[0] = (px[0] / step) * step;
            px[1] = (px[1] / step) * step;
            px[2] = (px[2] / step) * step;
        }
        lzfse::compress(&out)
    }

    pub fn compress_edge(&self, block_bgra: &[u8]) -> Vec<u8> {
        if let Some(palette) = crate::lpc_lzfse::extract_palette(block_bgra, 32) {
            let indices = palette.quantize(block_bgra);
            let mut rec = Vec::with_capacity(block_bgra.len());
            for idx in indices {
                rec.extend_from_slice(&palette.colors[idx as usize]);
            }
            lzfse::compress(&rec)
        } else {
            lzfse::compress(block_bgra)
        }
    }

    pub fn compress_texture(&self, block_bgra: &[u8]) -> Vec<u8> {
        let mut out = Vec::with_capacity(block_bgra.len());
        for px in block_bgra.chunks_exact(4) {
            let b = px[0] as f32;
            let g = px[1] as f32;
            let r = px[2] as f32;
            let a = px[3];

            let y = 0.299 * r + 0.587 * g + 0.114 * b;
            let cb = -0.169 * r - 0.331 * g + 0.500 * b + 128.0;
            let cr = 0.500 * r - 0.419 * g - 0.081 * b + 128.0;

            let y_q = (y / 8.0).round() * 8.0;
            let cb_q = (cb / 16.0).round() * 16.0;
            let cr_q = (cr / 16.0).round() * 16.0;

            let r_rec = (y_q + 1.402 * (cr_q - 128.0)).clamp(0.0, 255.0) as u8;
            let g_rec = (y_q - 0.344 * (cb_q - 128.0) - 0.714 * (cr_q - 128.0)).clamp(0.0, 255.0) as u8;
            let b_rec = (y_q + 1.772 * (cb_q - 128.0)).clamp(0.0, 255.0) as u8;

            out.push(b_rec);
            out.push(g_rec);
            out.push(r_rec);
            out.push(a);
        }
        lzfse::compress(&out)
    }

    pub fn compress_transparent(&self, block_bgra: &[u8]) -> Vec<u8> {
        let mut out = block_bgra.to_vec();
        for px in out.chunks_exact_mut(4) {
            if px[3] == 0 {
                px[0] = 0;
                px[1] = 0;
                px[2] = 0;
            }
        }
        lzfse::compress(&out)
    }

    pub fn compress_chunk(&self, chunk_bgra: &[u8], _width: u32, _height: u32) -> Vec<u8> {
        let btype = self.classify_block(chunk_bgra);
        match btype {
            BlockType::Solid => self.compress_solid(chunk_bgra),
            BlockType::Gradient => self.compress_gradient(chunk_bgra),
            BlockType::Edge => self.compress_edge(chunk_bgra),
            BlockType::Texture => self.compress_texture(chunk_bgra),
            BlockType::Transparent => self.compress_transparent(chunk_bgra),
        }
    }

    pub fn compress_image(&self, bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
        crate::cbck::encode_cbck(bgra, width, height, 4, self.clean_alpha)
    }
}

pub fn ultimate_compress(bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
    let comp = UltimateCompressor::default();
    comp.compress_image(bgra, width, height)
}
