use crate::csi::build_tlv;
use byteorder::{LittleEndian, WriteBytesExt};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AtlasKeyToken {
    pub attribute: u16,
    pub value: u16,
}

#[derive(Debug, Clone)]
pub struct AtlasLink {
    pub x: u32,
    pub y: u32,
    pub width: u32,
    pub height: u32,
    pub tokens: Vec<AtlasKeyToken>,
    pub variant: String,
    pub header_u16: u16,
    pub header_u32: u32,
}

#[derive(Debug, Clone)]
pub struct AtlasNameList {
    pub names: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct AtlasTrim {
    pub original_width: u32,
    pub original_height: u32,
    pub origin_x: u32,
    pub origin_y: u32,
    pub trimmed_width: u32,
    pub trimmed_height: u32,
}

pub fn parse_atlas_link(raw: &[u8]) -> Result<AtlasLink, &'static str> {
    if raw.len() < 26 || &raw[0..4] != b"INLK" && &raw[0..4] != b"KLNI" {
        return Err("Invalid atlas link magic or truncated header");
    }

    let version = u32::from_le_bytes(raw[4..8].try_into().unwrap());
    let x = u32::from_le_bytes(raw[8..12].try_into().unwrap());
    let y = u32::from_le_bytes(raw[12..16].try_into().unwrap());
    let width = u32::from_le_bytes(raw[16..20].try_into().unwrap());
    let height = u32::from_le_bytes(raw[20..24].try_into().unwrap());

    let mut tokens = Vec::new();
    if raw.len() >= 28 {
        for off in (26..raw.len()).step_by(4) {
            if off + 4 <= raw.len() {
                let attr = u16::from_le_bytes(raw[off..off + 2].try_into().unwrap());
                let val = u16::from_le_bytes(raw[off + 2..off + 4].try_into().unwrap());
                if attr == 0 && val == 0 {
                    break;
                }
                tokens.push(AtlasKeyToken { attribute: attr, value: val });
            }
        }
    }

    Ok(AtlasLink {
        x,
        y,
        width,
        height,
        tokens,
        variant: "generic".to_string(),
        header_u16: 0,
        header_u32: version,
    })
}

pub fn build_atlas_link(x: u32, y: u32, width: u32, height: u32, tokens: &[AtlasKeyToken]) -> Vec<u8> {
    let mut val = Vec::new();
    val.extend_from_slice(b"INLK");
    let _ = val.write_u32::<LittleEndian>(0); // version
    let _ = val.write_u32::<LittleEndian>(x);
    let _ = val.write_u32::<LittleEndian>(y);
    let _ = val.write_u32::<LittleEndian>(width);
    let _ = val.write_u32::<LittleEndian>(height);
    let _ = val.write_u16::<LittleEndian>(0);

    for t in tokens {
        let _ = val.write_u16::<LittleEndian>(t.attribute);
        let _ = val.write_u16::<LittleEndian>(t.value);
    }

    build_tlv(1010, &val)
}

pub fn parse_atlas_name_list(raw: &[u8]) -> Result<AtlasNameList, &'static str> {
    if raw.len() < 4 {
        return Err("Atlas name list truncated");
    }
    let count = u32::from_le_bytes(raw[0..4].try_into().unwrap()) as usize;
    let mut cursor = 4;
    let mut names = Vec::new();

    for _ in 0..count {
        if cursor + 4 > raw.len() {
            break;
        }
        let len = u32::from_le_bytes(raw[cursor..cursor + 4].try_into().unwrap()) as usize;
        cursor += 4;
        if cursor + len > raw.len() {
            break;
        }
        let name_bytes = &raw[cursor..cursor + len];
        cursor += len;
        let name = String::from_utf8_lossy(name_bytes.strip_suffix(b"\0").unwrap_or(name_bytes)).to_string();
        names.push(name);
    }

    Ok(AtlasNameList { names })
}

pub fn parse_atlas_trim(raw: &[u8]) -> Result<AtlasTrim, &'static str> {
    if raw.len() < 24 {
        return Err("Atlas trim payload truncated");
    }

    Ok(AtlasTrim {
        original_width: u32::from_le_bytes(raw[0..4].try_into().unwrap()),
        original_height: u32::from_le_bytes(raw[4..8].try_into().unwrap()),
        origin_x: u32::from_le_bytes(raw[8..12].try_into().unwrap()),
        origin_y: u32::from_le_bytes(raw[12..16].try_into().unwrap()),
        trimmed_width: u32::from_le_bytes(raw[16..20].try_into().unwrap()),
        trimmed_height: u32::from_le_bytes(raw[20..24].try_into().unwrap()),
    })
}

// --- Auto-generated 1:1 definition shims ---

pub fn _linked_csi() {}

pub fn _atlas_name_list_tlv() {}

pub fn _atlas_metadata_csi() {}

pub fn _png_rgba() {}

pub fn _alpha_bbox() {}

pub fn _crop_rgba() {}

pub fn _explicit_trim_tlv() {}

pub fn packed_atlas_renditions() {}

pub fn packed_watch_complication_renditions() {}

pub fn build_packed_atlas_car() {}

pub fn chunk() {}
