use crate::lzfse;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ASTCBlockSize {
    Block4x4 = 0,
    Block6x6 = 1,
    Block8x8 = 2,
    Block10x10 = 3,
    Block12x12 = 4,
}

pub struct ASTCClassCompressor {
    pub clean_alpha: bool,
    pub target_bpp: f32,
}

impl Default for ASTCClassCompressor {
    fn default() -> Self {
        Self::new(true, 2.0)
    }
}

impl ASTCClassCompressor {
    pub fn new(clean_alpha: bool, target_bpp: f32) -> Self {
        Self { clean_alpha, target_bpp }
    }

    pub fn _select_block_size(&self, block_bgra: &[u8], width: usize, height: usize) -> ASTCBlockSize {
        let pixels = width * height;
        if pixels == 0 || block_bgra.len() < pixels * 4 {
            return ASTCBlockSize::Block8x8;
        }

        let (complexity, _var, _trans) = crate::astc_optimized::analyze_block_complexity(block_bgra);

        if complexity > 15.0 {
            ASTCBlockSize::Block4x4
        } else if complexity > 8.0 {
            ASTCBlockSize::Block6x6
        } else if complexity > 4.0 {
            ASTCBlockSize::Block8x8
        } else if complexity > 2.0 {
            ASTCBlockSize::Block10x10
        } else {
            ASTCBlockSize::Block12x12
        }
    }

    pub fn _astc_emulate_block(&self, block_bgra: &[u8], block_size: ASTCBlockSize) -> Vec<u8> {
        let levels = match block_size {
            ASTCBlockSize::Block4x4 => 32,
            ASTCBlockSize::Block6x6 => 16,
            ASTCBlockSize::Block8x8 => 8,
            ASTCBlockSize::Block10x10 => 4,
            ASTCBlockSize::Block12x12 => 2,
        };

        let mut out = Vec::with_capacity(block_bgra.len());
        let scale_y = 256.0 / (levels as f32);
        let scale_cocg = 256.0 / ((levels * 2) as f32);

        for px in block_bgra.chunks_exact(4) {
            let b = px[0] as f32;
            let g = px[1] as f32;
            let r = px[2] as f32;
            let a = px[3];

            let y = b / 4.0 + g / 2.0 + r / 4.0;
            let co = b / 2.0 - r / 2.0 + 128.0;
            let cg = -b / 4.0 + g / 2.0 - r / 4.0 + 128.0;

            let y_q = (y / scale_y).round() * scale_y;
            let co_q = (co / scale_cocg).round() * scale_cocg;
            let cg_q = (cg / scale_cocg).round() * scale_cocg;

            let r_rec = (y_q + co_q - 128.0).clamp(0.0, 255.0) as u8;
            let g_rec = (y_q + cg_q - 128.0).clamp(0.0, 255.0) as u8;
            let b_rec = (y_q - co_q - cg_q + 256.0).clamp(0.0, 255.0) as u8;

            out.push(b_rec);
            out.push(g_rec);
            out.push(r_rec);
            out.push(a);
        }

        out
    }

    pub fn compress_chunk(&self, bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
        let mut chunk = bgra.to_vec();
        if self.clean_alpha {
            for px in chunk.chunks_exact_mut(4) {
                if px[3] == 0 {
                    px[0] = 0;
                    px[1] = 0;
                    px[2] = 0;
                }
            }
        }

        let bs = self._select_block_size(&chunk, width as usize, height as usize);
        let emulated = self._astc_emulate_block(&chunk, bs);
        lzfse::compress(&emulated)
    }

    pub fn compress_image(&self, bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
        crate::cbck::encode_cbck(bgra, width, height, 4, self.clean_alpha)
    }
}

pub fn astc_compress(bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
    let compressor = ASTCClassCompressor::default();
    compressor.compress_chunk(bgra, width, height)
}
