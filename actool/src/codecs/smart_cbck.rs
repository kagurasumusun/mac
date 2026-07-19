use crate::cbck::encode_cbck;
use crate::lzfse;
use byteorder::{LittleEndian, WriteBytesExt};

pub const APPLE_CBCK_RAW_CAP: usize = 0x155555;

pub const STRATEGY_LZFSE: u8 = 0;
pub const STRATEGY_CLEAN_ALPHA: u8 = 1;
pub const STRATEGY_AGGRESSIVE: u8 = 2;

pub struct SmartCBCKEncoder {
    pub clean_alpha: bool,
    pub chunk_raw_cap: usize,
}

impl Default for SmartCBCKEncoder {
    fn default() -> Self {
        Self::new(true)
    }
}

impl SmartCBCKEncoder {
    pub fn new(clean_alpha: bool) -> Self {
        Self {
            clean_alpha,
            chunk_raw_cap: APPLE_CBCK_RAW_CAP,
        }
    }

    pub fn _load_ai_model(&self) -> bool {
        true
    }

    pub fn _predict_strategy(&self, chunk_bgra: &[u8], width: u32, height: u32) -> u8 {
        let total_pixels = (width * height) as usize;
        if total_pixels == 0 || chunk_bgra.len() < total_pixels * 4 {
            return STRATEGY_LZFSE;
        }

        let mut transparent_count = 0;
        for chunk in chunk_bgra.chunks_exact(4) {
            if chunk[3] == 0 {
                transparent_count += 1;
            }
        }

        let alpha_zero_ratio = (transparent_count as f32) / (total_pixels as f32);

        if alpha_zero_ratio > 0.8 {
            STRATEGY_CLEAN_ALPHA
        } else {
            STRATEGY_LZFSE
        }
    }

    pub fn _clean_dirty_transparency(bgra: &mut [u8]) {
        for chunk in bgra.chunks_exact_mut(4) {
            if chunk[3] == 0 {
                chunk[0] = 0;
                chunk[1] = 0;
                chunk[2] = 0;
            }
        }
    }

    pub fn _compute_rows_per_chunk(&self, width: u32, height: u32) -> Vec<(u32, u32)> {
        let row_bytes = (width * 4) as usize;
        let rows_per = std::cmp::max(1, self.chunk_raw_cap / std::cmp::max(1, row_bytes)) as u32;

        let mut bands = Vec::new();
        let mut y = 0;
        while y < height {
            let rows = std::cmp::min(rows_per, height - y);
            bands.push((y, rows));
            y += rows;
        }
        bands
    }

    pub fn encode_chunk(&self, bgra_data: &[u8], width: u32, height: u32) -> Vec<u8> {
        let mut chunk = bgra_data.to_vec();

        if self.clean_alpha {
            Self::_clean_dirty_transparency(&mut chunk);
        }

        let strategy = self._predict_strategy(&chunk, width, height);

        if strategy == STRATEGY_AGGRESSIVE {
            for px in chunk.chunks_exact_mut(4) {
                px[0] = (px[0] >> 2) << 2;
                px[1] = (px[1] >> 2) << 2;
                px[2] = (px[2] >> 2) << 2;
            }
        }

        let compressed = lzfse::compress(&chunk);

        let mut out = Vec::new();
        out.extend_from_slice(b"KCBC");
        let _ = out.write_u32::<LittleEndian>(0);
        let _ = out.write_u32::<LittleEndian>(0);
        let _ = out.write_u32::<LittleEndian>(height);
        let _ = out.write_u32::<LittleEndian>(compressed.len() as u32);
        out.extend_from_slice(&compressed);

        out
    }

    pub fn encode(&self, bgra_data: &[u8], width: u32, height: u32) -> Vec<u8> {
        encode_cbck(bgra_data, width, height, 4, self.clean_alpha)
    }
}

pub fn smart_encode_png_cbck(
    bgra_premultiplied: &[u8],
    width: u32,
    height: u32,
    filename: &str,
    scale: u32,
    clean_alpha: bool,
) -> Vec<u8> {
    let encoder = SmartCBCKEncoder::new(clean_alpha);
    let payload = encoder.encode(bgra_premultiplied, width, height);

    let mut tlvs = Vec::new();

    let mut val1001 = Vec::new();
    let _ = val1001.write_u32::<LittleEndian>(1);
    let _ = val1001.write_u32::<LittleEndian>(0);
    let _ = val1001.write_u32::<LittleEndian>(0);
    let _ = val1001.write_u32::<LittleEndian>(width);
    let _ = val1001.write_u32::<LittleEndian>(height);
    tlvs.extend_from_slice(&crate::csi::build_tlv(1001, &val1001));

    let mut header = vec![0u8; 184];
    header[0..4].copy_from_slice(b"ISTC");
    let _ = (&mut header[12..16]).write_u32::<LittleEndian>(width);
    let _ = (&mut header[16..20]).write_u32::<LittleEndian>(height);
    let _ = (&mut header[20..24]).write_u32::<LittleEndian>(scale * 100);
    header[24..28].copy_from_slice(b"BGRA");

    let fname_bytes = filename.as_bytes();
    let len = std::cmp::min(fname_bytes.len(), 127);
    header[40..40 + len].copy_from_slice(&fname_bytes[..len]);

    let _ = (&mut header[168..172]).write_u32::<LittleEndian>(tlvs.len() as u32);
    let _ = (&mut header[172..176]).write_u32::<LittleEndian>(1);
    let _ = (&mut header[176..180]).write_u32::<LittleEndian>(0);
    let _ = (&mut header[180..184]).write_u32::<LittleEndian>(payload.len() as u32);

    let mut out = header;
    out.extend_from_slice(&tlvs);
    out.extend_from_slice(&payload);
    out
}
