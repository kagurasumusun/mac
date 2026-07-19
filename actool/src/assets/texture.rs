use byteorder::{LittleEndian, WriteBytesExt};
use thiserror::Error;

#[derive(Error, Debug)]
pub enum TextureRenditionError {
    #[error("Invalid texture payload or header")]
    InvalidHeader,
    #[error("Payload is truncated")]
    Truncated,
}

#[derive(Debug, Clone)]
pub struct TextureReference {
    pub payload_value: u32,
    pub reserved0: u32,
    pub u32_2: u32,
    pub u32_3: u32,
    pub u32_4: u32,
    pub key_pairs: Vec<(u16, u16)>,
}

#[derive(Debug, Clone)]
pub struct TextureAuxiliaryFlag {
    pub raw: [u8; 12],
    pub values: (u32, u32, u32),
}

pub fn build_texture_reference_payload(reference: &TextureReference) -> Vec<u8> {
    let mut pairs = Vec::new();
    for (attr, val) in &reference.key_pairs {
        let _ = pairs.write_u16::<LittleEndian>(*attr);
        let _ = pairs.write_u16::<LittleEndian>(*val);
    }

    let mut out = Vec::new();
    out.extend_from_slice(b"RTXT");
    let _ = out.write_u32::<LittleEndian>(reference.reserved0);
    let _ = out.write_u32::<LittleEndian>(reference.payload_value);
    let _ = out.write_u32::<LittleEndian>(reference.u32_2);
    let _ = out.write_u32::<LittleEndian>(reference.u32_3);
    let _ = out.write_u32::<LittleEndian>(reference.u32_4);
    let _ = out.write_u32::<LittleEndian>(pairs.len() as u32);
    let _ = out.write_u32::<LittleEndian>(0);
    out.extend_from_slice(&pairs);

    out
}

pub fn build_texture_auxiliary_flag(flag: &TextureAuxiliaryFlag) -> Vec<u8> {
    flag.raw.to_vec()
}

pub fn parse_texture_reference_payload(data: &[u8]) -> Result<TextureReference, TextureRenditionError> {
    if data.len() < 32 || &data[0..4] != b"RTXT" {
        return Err(TextureRenditionError::InvalidHeader);
    }

    let reserved0 = u32::from_le_bytes(data[4..8].try_into().unwrap());
    let payload_value = u32::from_le_bytes(data[8..12].try_into().unwrap());
    let u32_2 = u32::from_le_bytes(data[12..16].try_into().unwrap());
    let u32_3 = u32::from_le_bytes(data[16..20].try_into().unwrap());
    let u32_4 = u32::from_le_bytes(data[20..24].try_into().unwrap());
    let key_length = u32::from_le_bytes(data[24..28].try_into().unwrap()) as usize;

    if 32 + key_length > data.len() {
        return Err(TextureRenditionError::Truncated);
    }

    let mut key_pairs = Vec::new();
    for off in (32..32 + key_length).step_by(4) {
        let attr = u16::from_le_bytes(data[off..off + 2].try_into().unwrap());
        let val = u16::from_le_bytes(data[off + 2..off + 4].try_into().unwrap());
        key_pairs.push((attr, val));
    }

    Ok(TextureReference {
        payload_value,
        reserved0,
        u32_2,
        u32_3,
        u32_4,
        key_pairs,
    })
}

pub fn parse_texture_auxiliary_flag(data: &[u8]) -> Result<TextureAuxiliaryFlag, TextureRenditionError> {
    if data.len() != 12 {
        return Err(TextureRenditionError::Truncated);
    }
    let mut raw = [0u8; 12];
    raw.copy_from_slice(data);

    let v1 = u32::from_le_bytes(data[0..4].try_into().unwrap());
    let v2 = u32::from_le_bytes(data[4..8].try_into().unwrap());
    let v3 = u32::from_le_bytes(data[8..12].try_into().unwrap());

    Ok(TextureAuxiliaryFlag {
        raw,
        values: (v1, v2, v3),
    })
}
