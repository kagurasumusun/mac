use crate::cbck::encode_cbck;
use crate::lzfse;
use byteorder::{LittleEndian, WriteBytesExt};

#[derive(Debug, Clone)]
pub struct CSIHeader {
    pub magic: [u8; 4],
    pub version: u32,
    pub flags: u32,
    pub width: u32,
    pub height: u32,
    pub scale: u32,
    pub pixel_format: [u8; 4],
    pub color_space_id: u32,
    pub layout: u32,
    pub name: String,
}

#[derive(Debug, Clone)]
pub struct TLV {
    pub tag: u32,
    pub value: Vec<u8>,
}

pub fn build_tlv(tag: u32, value: &[u8]) -> Vec<u8> {
    let mut out = Vec::new();
    let _ = out.write_u32::<LittleEndian>(tag);
    let _ = out.write_u32::<LittleEndian>(value.len() as u32);
    out.extend_from_slice(value);
    out
}

pub fn build_csi_png(
    bgra: &[u8],
    width: u32,
    height: u32,
    filename: &str,
    scale: u32,
    prefer_cbck: bool,
) -> Vec<u8> {
    let row_bytes = width * 4;

    // TLVs
    let mut tlvs = Vec::new();

    // 1001 Metrics
    let mut val1001 = Vec::new();
    let _ = val1001.write_u32::<LittleEndian>(1);
    let _ = val1001.write_u32::<LittleEndian>(0);
    let _ = val1001.write_u32::<LittleEndian>(0);
    let _ = val1001.write_u32::<LittleEndian>(width);
    let _ = val1001.write_u32::<LittleEndian>(height);
    tlvs.extend_from_slice(&build_tlv(1001, &val1001));

    // 1003 Bounds
    let mut val1003 = Vec::new();
    let _ = val1003.write_u32::<LittleEndian>(1);
    let _ = val1003.write_u32::<LittleEndian>(0);
    let _ = val1003.write_u32::<LittleEndian>(0);
    let _ = val1003.write_u32::<LittleEndian>(0);
    let _ = val1003.write_u32::<LittleEndian>(0);
    let _ = val1003.write_u32::<LittleEndian>(width);
    let _ = val1003.write_u32::<LittleEndian>(height);
    tlvs.extend_from_slice(&build_tlv(1003, &val1003));

    // 1004 Scale (float 1.0, 2.0, 3.0)
    let scale_f32 = scale as f32;
    let mut val1004 = [0u8; 8];
    val1004[4..8].copy_from_slice(&scale_f32.to_le_bytes());
    tlvs.extend_from_slice(&build_tlv(1004, &val1004));

    // 1006 Layout format
    let mut val1006 = Vec::new();
    let _ = val1006.write_u32::<LittleEndian>(1);
    tlvs.extend_from_slice(&build_tlv(1006, &val1006));

    // 1007 Row bytes
    let mut val1007 = Vec::new();
    let _ = val1007.write_u32::<LittleEndian>(row_bytes);
    tlvs.extend_from_slice(&build_tlv(1007, &val1007));

    // Payload: either CBCK (MLEC) or LZFSE stream
    let payload = if prefer_cbck && (row_bytes * height > 0x155555) && height > 1 {
        encode_cbck(bgra, width, height, 4, true)
    } else {
        lzfse::compress(bgra)
    };

    // CSIR / ISTC Header (184 bytes fixed length header)
    let mut header = vec![0u8; 184];
    header[0..4].copy_from_slice(b"ISTC");
    let _ = (&mut header[4..8]).write_u32::<LittleEndian>(1); // Version
    let _ = (&mut header[8..12]).write_u32::<LittleEndian>(0); // Flags
    let _ = (&mut header[12..16]).write_u32::<LittleEndian>(width);
    let _ = (&mut header[16..20]).write_u32::<LittleEndian>(height);
    let _ = (&mut header[20..24]).write_u32::<LittleEndian>(scale * 100);
    header[24..28].copy_from_slice(b"BGRA");
    let _ = (&mut header[28..32]).write_u32::<LittleEndian>(1); // Color space sRGB
    let _ = (&mut header[32..36]).write_u32::<LittleEndian>(1000); // Layout

    // Set name at offset 40
    let name_bytes = filename.as_bytes();
    let name_len = std::cmp::min(name_bytes.len(), 127);
    header[40..40 + name_len].copy_from_slice(&name_bytes[..name_len]);

    // Metadata & payload length fields
    let _ = (&mut header[168..172]).write_u32::<LittleEndian>(tlvs.len() as u32);
    let _ = (&mut header[172..176]).write_u32::<LittleEndian>(payload.len() as u32);

    let mut out = Vec::new();
    out.extend_from_slice(&header);
    out.extend_from_slice(&tlvs);
    out.extend_from_slice(&payload);

    out
}
