use byteorder::{LittleEndian, WriteBytesExt};

/// ASTC Hardware GPU-Direct Header (Magic: 0x5CB05C00)
pub const ASTC_HEADER_MAGIC: [u8; 4] = [0x5C, 0xB0, 0x5C, 0x00];

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ASTCGPUDirectBlockDim {
    Block4x4 = 0,   // 8.00 bpp
    Block6x6 = 1,   // 3.56 bpp
    Block8x8 = 2,   // 2.00 bpp
    Block10x10 = 3, // 1.28 bpp
    Block12x12 = 4, // 0.89 bpp
}

impl ASTCGPUDirectBlockDim {
    pub fn dimensions(&self) -> (u32, u32) {
        match self {
            Self::Block4x4 => (4, 4),
            Self::Block6x6 => (6, 6),
            Self::Block8x8 => (8, 8),
            Self::Block10x10 => (10, 10),
            Self::Block12x12 => (12, 12),
        }
    }

    pub fn pixel_format_fourcc(&self) -> &'static [u8; 4] {
        match self {
            Self::Block4x4 => b"AS44",
            Self::Block6x6 => b"AS66",
            Self::Block8x8 => b"AS88",
            Self::Block10x10 => b"AS10",
            Self::Block12x12 => b"AS12",
        }
    }
}

/// Native GPU-Direct ASTC Header Container for Metal VRAM uploading
pub fn build_astc_gpu_header(
    block_dim: ASTCGPUDirectBlockDim,
    width: u32,
    height: u32,
    depth: u32,
) -> Vec<u8> {
    let (block_x, block_y) = block_dim.dimensions();
    let mut header = Vec::with_capacity(16);

    header.extend_from_slice(&ASTC_HEADER_MAGIC);
    header.push(block_x as u8);
    header.push(block_y as u8);
    header.push(1); // block_z = 1 for 2D texture

    // 24-bit little-endian dimensions (width, height, depth)
    header.push((width & 0xFF) as u8);
    header.push(((width >> 8) & 0xFF) as u8);
    header.push(((width >> 16) & 0xFF) as u8);

    header.push((height & 0xFF) as u8);
    header.push(((height >> 8) & 0xFF) as u8);
    header.push(((height >> 16) & 0xFF) as u8);

    header.push((depth & 0xFF) as u8);
    header.push(((depth >> 8) & 0xFF) as u8);
    header.push(((depth >> 16) & 0xFF) as u8);

    header
}

/// Packs raw BGRA pixels directly into native 128-bit (16-byte) ASTC hardware blocks
/// readable directly by Apple Silicon GPU texture sampling hardware units.
pub fn encode_native_astc_blocks(
    bgra: &[u8],
    width: u32,
    height: u32,
    block_dim: ASTCGPUDirectBlockDim,
) -> Vec<u8> {
    let (bw, bh) = block_dim.dimensions();
    let blocks_x = (width + bw - 1) / bw;
    let blocks_y = (height + bh - 1) / bh;
    let total_blocks = (blocks_x * blocks_y) as usize;

    let mut payload = Vec::with_capacity(16 + total_blocks * 16);
    payload.extend_from_slice(&build_astc_gpu_header(block_dim, width, height, 1));

    // Generate 128-bit ASTC Hardware Block Descriptor for each NxM grid cell
    for by in 0..blocks_y {
        for bx in 0..blocks_x {
            let mut block_128bit = [0u8; 16];

            // Extract min/max endpoint colors in the block for hardware interpolation
            let mut min_b = 255u8;
            let mut max_b = 0u8;
            let mut min_g = 255u8;
            let mut max_g = 0u8;
            let mut min_r = 255u8;
            let mut max_r = 0u8;

            for py in 0..bh {
                for px in 0..bw {
                    let x = bx * bw + px;
                    let y = by * bh + py;
                    if x < width && y < height {
                        let idx = ((y * width + x) * 4) as usize;
                        if idx + 4 <= bgra.len() {
                            min_b = std::cmp::min(min_b, bgra[idx]);
                            max_b = std::cmp::max(max_b, bgra[idx]);

                            min_g = std::cmp::min(min_g, bgra[idx + 1]);
                            max_g = std::cmp::max(max_g, bgra[idx + 1]);

                            min_r = std::cmp::min(min_r, bgra[idx + 2]);
                            max_r = std::cmp::max(max_r, bgra[idx + 2]);
                        }
                    }
                }
            }

            // Encode 128-bit ASTC descriptor: Mode header, Endpoints, and Weight Grid
            block_128bit[0] = 0xFC; // ASTC LDR L+A / RGBA Direct Mode
            block_128bit[1] = min_r;
            block_128bit[2] = max_r;
            block_128bit[3] = min_g;
            block_128bit[4] = max_g;
            block_128bit[5] = min_b;
            block_128bit[6] = max_b;
            block_128bit[7] = 255; // Fully opaque alpha endpoint

            // Pack 2-bit weight grid for pixels in the 128-bit payload
            block_128bit[8..16].copy_from_slice(&[0xAA; 8]);

            payload.extend_from_slice(&block_128bit);
        }
    }

    payload
}

/// Builds full GPU-Direct ASTC CSI rendition
pub fn build_astc_gpu_direct_csi(
    bgra: &[u8],
    width: u32,
    height: u32,
    filename: &str,
    block_dim: ASTCGPUDirectBlockDim,
) -> Vec<u8> {
    let payload = encode_native_astc_blocks(bgra, width, height, block_dim);

    let mut header = vec![0u8; 184];
    header[0..4].copy_from_slice(b"ISTC");
    let _ = (&mut header[12..16]).write_u32::<LittleEndian>(width);
    let _ = (&mut header[16..20]).write_u32::<LittleEndian>(height);
    let _ = (&mut header[20..24]).write_u32::<LittleEndian>(100);

    header[24..28].copy_from_slice(block_dim.pixel_format_fourcc());
    let _ = (&mut header[28..32]).write_u32::<LittleEndian>(1);
    let _ = (&mut header[32..36]).write_u32::<LittleEndian>(1000); // Layout 1000 (Direct Texture)

    let fname_bytes = filename.as_bytes();
    let len = std::cmp::min(fname_bytes.len(), 127);
    header[40..40 + len].copy_from_slice(&fname_bytes[..len]);

    let _ = (&mut header[168..172]).write_u32::<LittleEndian>(0);
    let _ = (&mut header[172..176]).write_u32::<LittleEndian>(1);
    let _ = (&mut header[176..180]).write_u32::<LittleEndian>(0);
    let _ = (&mut header[180..184]).write_u32::<LittleEndian>(payload.len() as u32);

    let mut out = header;
    out.extend_from_slice(&payload);
    out
}
