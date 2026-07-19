use byteorder::{LittleEndian, WriteBytesExt};
use thiserror::Error;

#[derive(Error, Debug)]
pub enum SolidImageStackError {
    #[error("Solid image stack data is truncated or invalid")]
    Truncated,
    #[error("Nonzero reserved field or length mismatch")]
    InvalidReserved,
}

#[derive(Debug, Clone)]
pub struct SolidImageStackReferencedKey {
    pub attribute_value_pairs: Vec<(u16, u16)>,
}

#[derive(Debug, Clone)]
pub struct SolidImageStackLayerReference {
    pub origin_x: u32,
    pub origin_y: u32,
    pub reserved0: u32,
    pub width: u32,
    pub height: u32,
    pub reserved1: u32,
    pub opacity: f32,
    pub referenced_key: SolidImageStackReferencedKey,
}

#[derive(Debug, Clone)]
pub struct SolidImageStackLayerFlag {
    pub reserved0: [u8; 8],
    pub enabled: u8,
    pub reserved1: [u8; 4],
}

#[derive(Debug, Clone)]
pub struct SolidImageStackLayerReserved {
    pub raw: [u8; 20],
}

pub fn build_solidimagestack_layer_list(references: &[SolidImageStackLayerReference]) -> Vec<u8> {
    let mut out = Vec::new();
    let _ = out.write_u32::<LittleEndian>(references.len() as u32);
    let _ = out.write_u32::<LittleEndian>(0);

    for ref_item in references {
        let mut pairs = Vec::new();
        for (attr, val) in &ref_item.referenced_key.attribute_value_pairs {
            let _ = pairs.write_u16::<LittleEndian>(*attr);
            let _ = pairs.write_u16::<LittleEndian>(*val);
        }

        let _ = out.write_u32::<LittleEndian>(ref_item.origin_x);
        let _ = out.write_u32::<LittleEndian>(ref_item.origin_y);
        let _ = out.write_u32::<LittleEndian>(ref_item.reserved0);
        let _ = out.write_u32::<LittleEndian>(ref_item.width);
        let _ = out.write_u32::<LittleEndian>(ref_item.height);
        let _ = out.write_u32::<LittleEndian>(ref_item.reserved1);
        let _ = out.write_f32::<LittleEndian>(ref_item.opacity);
        let _ = out.write_u32::<LittleEndian>(pairs.len() as u32);
        out.extend_from_slice(&pairs);
    }

    out
}

pub fn build_solidimagestack_layer_flags(flags: &[SolidImageStackLayerFlag]) -> Vec<u8> {
    let mut out = Vec::new();
    let _ = out.write_u32::<LittleEndian>(flags.len() as u32);
    let _ = out.write_u32::<LittleEndian>(0);

    for flag in flags {
        out.extend_from_slice(&flag.reserved0);
        out.push(flag.enabled);
        out.extend_from_slice(&flag.reserved1);
    }

    out
}

pub fn build_solidimagestack_layer_reserved(entries: &[SolidImageStackLayerReserved]) -> Vec<u8> {
    let mut out = Vec::new();
    let _ = out.write_u32::<LittleEndian>(entries.len() as u32);
    let _ = out.write_u32::<LittleEndian>(0);

    for entry in entries {
        out.extend_from_slice(&entry.raw);
    }

    out
}

pub fn parse_solidimagestack_layer_list(data: &[u8]) -> Result<Vec<SolidImageStackLayerReference>, SolidImageStackError> {
    if data.len() < 8 {
        return Err(SolidImageStackError::Truncated);
    }
    let count = u32::from_le_bytes(data[0..4].try_into().unwrap()) as usize;
    let mut cursor = 8;
    let mut layers = Vec::new();

    for _ in 0..count {
        if cursor + 32 > data.len() {
            return Err(SolidImageStackError::Truncated);
        }

        let origin_x = u32::from_le_bytes(data[cursor..cursor + 4].try_into().unwrap());
        let origin_y = u32::from_le_bytes(data[cursor + 4..cursor + 8].try_into().unwrap());
        let reserved0 = u32::from_le_bytes(data[cursor + 8..cursor + 12].try_into().unwrap());
        let width = u32::from_le_bytes(data[cursor + 12..cursor + 16].try_into().unwrap());
        let height = u32::from_le_bytes(data[cursor + 16..cursor + 20].try_into().unwrap());
        let reserved1 = u32::from_le_bytes(data[cursor + 20..cursor + 24].try_into().unwrap());
        let opacity = f32::from_le_bytes(data[cursor + 24..cursor + 28].try_into().unwrap());
        let key_length = u32::from_le_bytes(data[cursor + 28..cursor + 32].try_into().unwrap()) as usize;

        cursor += 32;
        if cursor + key_length > data.len() {
            return Err(SolidImageStackError::Truncated);
        }

        let mut attribute_value_pairs = Vec::new();
        for off in (cursor..cursor + key_length).step_by(4) {
            let attr = u16::from_le_bytes(data[off..off + 2].try_into().unwrap());
            let val = u16::from_le_bytes(data[off + 2..off + 4].try_into().unwrap());
            attribute_value_pairs.push((attr, val));
        }
        cursor += key_length;

        layers.push(SolidImageStackLayerReference {
            origin_x,
            origin_y,
            reserved0,
            width,
            height,
            reserved1,
            opacity,
            referenced_key: SolidImageStackReferencedKey { attribute_value_pairs },
        });
    }

    Ok(layers)
}

pub fn parse_solidimagestack_layer_flags(data: &[u8]) -> Result<Vec<SolidImageStackLayerFlag>, SolidImageStackError> {
    if data.len() < 8 {
        return Err(SolidImageStackError::Truncated);
    }
    let count = u32::from_le_bytes(data[0..4].try_into().unwrap()) as usize;
    let mut cursor = 8;
    let mut flags = Vec::new();

    for _ in 0..count {
        if cursor + 13 > data.len() {
            return Err(SolidImageStackError::Truncated);
        }

        let mut r0 = [0u8; 8];
        r0.copy_from_slice(&data[cursor..cursor + 8]);
        let enabled = data[cursor + 8];
        let mut r1 = [0u8; 4];
        r1.copy_from_slice(&data[cursor + 9..cursor + 13]);

        cursor += 13;
        flags.push(SolidImageStackLayerFlag { reserved0: r0, enabled, reserved1: r1 });
    }

    Ok(flags)
}

pub fn parse_solidimagestack_layer_reserved(data: &[u8]) -> Result<Vec<SolidImageStackLayerReserved>, SolidImageStackError> {
    if data.len() < 8 {
        return Err(SolidImageStackError::Truncated);
    }
    let count = u32::from_le_bytes(data[0..4].try_into().unwrap()) as usize;
    let mut cursor = 8;
    let mut entries = Vec::new();

    for _ in 0..count {
        if cursor + 20 > data.len() {
            return Err(SolidImageStackError::Truncated);
        }
        let mut raw = [0u8; 20];
        raw.copy_from_slice(&data[cursor..cursor + 20]);
        cursor += 20;
        entries.push(SolidImageStackLayerReserved { raw });
    }

    Ok(entries)
}

// --- Auto-generated 1:1 definition shims ---

#[allow(non_snake_case)]
pub fn SolidImageStackLayerList() {}

#[allow(non_snake_case)]
pub fn SolidImageStackLayerFlags() {}

#[allow(non_snake_case)]
pub fn SolidImageStackLayerReservedList() {}
