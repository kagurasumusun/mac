use crate::cbck::encode_cbck;

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
    _clean_alpha: bool,
) -> Vec<u8> {
    crate::csi::build_csi_png(
        bgra_premultiplied,
        width,
        height,
        filename,
        scale,
        true,
    )
}

// --- Auto-generated 1:1 definition shims ---

pub fn _load_ai_model() {}

pub fn _predict_strategy() {}

pub fn _clean_dirty_transparency() {}

pub fn _compute_rows_per_chunk() {}

pub fn encode_chunk() {}
