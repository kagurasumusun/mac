use crate::cbck::encode_cbck;
use crate::dmp2mini;
use crate::lzfse;
use crate::ultrahd::{classify_resolution_tier, encode_ultrahd_tiled_cbck, UltraHDTier};
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
    pub tlvs: Vec<TLV>,
    pub rendition_data: Vec<u8>,
}

#[derive(Debug, Clone)]
pub struct TLV {
    pub tag: u32,
    pub value: Vec<u8>,
}

pub fn parse_csi(data: &[u8]) -> Result<CSIHeader, crate::bom::BOMError> {
    if data.len() < 184 {
        return Err(crate::bom::BOMError::TruncatedHeader);
    }

    let is_little = match &data[0..4] {
        b"ISTC" => true,
        b"CTSI" => false,
        _ => return Err(crate::bom::BOMError::InvalidMagic(data[0..4].to_vec())),
    };

    let mut magic = [0u8; 4];
    magic.copy_from_slice(&data[0..4]);

    let (version, flags, width, height, scale) = if is_little {
        (
            u32::from_le_bytes(data[4..8].try_into().unwrap()),
            u32::from_le_bytes(data[8..12].try_into().unwrap()),
            u32::from_le_bytes(data[12..16].try_into().unwrap()),
            u32::from_le_bytes(data[16..20].try_into().unwrap()),
            u32::from_le_bytes(data[20..24].try_into().unwrap()),
        )
    } else {
        (
            u32::from_be_bytes(data[4..8].try_into().unwrap()),
            u32::from_be_bytes(data[8..12].try_into().unwrap()),
            u32::from_be_bytes(data[12..16].try_into().unwrap()),
            u32::from_be_bytes(data[16..20].try_into().unwrap()),
            u32::from_be_bytes(data[20..24].try_into().unwrap()),
        )
    };

    let mut pixel_format = [0u8; 4];
    pixel_format.copy_from_slice(&data[24..28]);

    let (color_space_id, layout) = if is_little {
        (
            u32::from_le_bytes(data[28..32].try_into().unwrap()),
            u32::from_le_bytes(data[32..36].try_into().unwrap()),
        )
    } else {
        (
            u32::from_be_bytes(data[28..32].try_into().unwrap()),
            u32::from_be_bytes(data[32..36].try_into().unwrap()),
        )
    };

    let name_end = data[40..168].iter().position(|&b| b == 0).unwrap_or(128);
    let name = String::from_utf8_lossy(&data[40..40 + name_end]).to_string();

    let (tlv_len, payload_len) = if is_little {
        (
            u32::from_le_bytes(data[168..172].try_into().unwrap()) as usize,
            u32::from_le_bytes(data[180..184].try_into().unwrap()) as usize,
        )
    } else {
        (
            u32::from_be_bytes(data[168..172].try_into().unwrap()) as usize,
            u32::from_be_bytes(data[180..184].try_into().unwrap()) as usize,
        )
    };

    let mut tlvs = Vec::new();
    let mut cursor = 184;
    let tlv_end = cursor + tlv_len;

    while cursor + 8 <= tlv_end && cursor + 8 <= data.len() {
        let (tag, len) = if is_little {
            (
                u32::from_le_bytes(data[cursor..cursor + 4].try_into().unwrap()),
                u32::from_le_bytes(data[cursor + 4..cursor + 8].try_into().unwrap()) as usize,
            )
        } else {
            (
                u32::from_be_bytes(data[cursor..cursor + 4].try_into().unwrap()),
                u32::from_be_bytes(data[cursor + 4..cursor + 8].try_into().unwrap()) as usize,
            )
        };
        cursor += 8;

        if cursor + len <= data.len() {
            tlvs.push(TLV {
                tag,
                value: data[cursor..cursor + len].to_vec(),
            });
            cursor += len;
        } else {
            break;
        }
    }

    let rendition_data = if 184 + tlv_len + payload_len <= data.len() {
        data[184 + tlv_len..184 + tlv_len + payload_len].to_vec()
    } else {
        Vec::new()
    };

    Ok(CSIHeader {
        magic,
        version,
        flags,
        width,
        height,
        scale,
        pixel_format,
        color_space_id,
        layout,
        name,
        tlvs,
        rendition_data,
    })
}

pub fn build_tlv(tag: u32, value: &[u8]) -> Vec<u8> {
    let mut out = Vec::new();
    let _ = out.write_u32::<LittleEndian>(tag);
    let _ = out.write_u32::<LittleEndian>(value.len() as u32);
    out.extend_from_slice(value);
    out
}

pub fn make_adaptive_csi(
    bgra: &[u8],
    width: u32,
    height: u32,
    filename: &str,
    scale: u32,
    optimize_mode: Option<&str>,
) -> Vec<u8> {
    let total_pixels = (width * height) as usize;
    let row_bytes = width * 4;

    let payload = if total_pixels == 0 || bgra.len() < total_pixels * 4 {
        bgra.to_vec() // Preserve raw/pre-compressed payload directly without recursive re-compression
    } else {
        let tier = classify_resolution_tier(width, height);
        let first_px = &bgra[0..4];
        let is_uniform = bgra.chunks_exact(4).all(|px| px == first_px);
        let is_oversized = (row_bytes * height) > 0x155555;

        if tier != UltraHDTier::Standard {
            encode_ultrahd_tiled_cbck(bgra, width, height, 512, true)
        } else if let Some(mode) = optimize_mode {
            match mode {
                "smart" => crate::smart_cbck::SmartCBCKEncoder::new(true).encode(bgra, width, height),
                "hybrid" => crate::hybrid_compression::hybrid_compress_for_cbck(bgra, width, height),
                "alpha" => crate::alpha_compression::alpha_compress(bgra, width, height),
                "omni" => crate::omni_compression::omni_compress(bgra, width, height),
                "omega" => crate::omega_compression::omega_compress(bgra, width, height),
                _ => encode_cbck(bgra, width, height, 4, true),
            }
        } else if is_uniform {
            if total_pixels <= 8 {
                dmp2mini::v1_raw(width as u16, height as u16, bgra, 4)
            } else if total_pixels <= 128 {
                let mut px = [0u8; 4];
                px.copy_from_slice(first_px);
                dmp2mini::v3_mini_color(width as u16, height as u16, &px)
            } else {
                let comp = lzfse::compress(bgra);
                let mut out = Vec::new();
                out.extend_from_slice(b"dmp2");
                out.extend_from_slice(&[2, 1, 10, 4]);
                let _ = out.write_u16::<LittleEndian>(width as u16);
                let _ = out.write_u16::<LittleEndian>(height as u16);
                let _ = out.write_u32::<LittleEndian>(comp.len() as u32);
                out.extend_from_slice(&comp);
                out
            }
        } else if is_oversized {
            encode_cbck(bgra, width, height, 4, true)
        } else {
            lzfse::compress(bgra)
        }
    };

    let mut tlvs = Vec::new();

    let mut val1001 = Vec::new();
    let _ = val1001.write_u32::<LittleEndian>(1);
    let _ = val1001.write_u32::<LittleEndian>(0);
    let _ = val1001.write_u32::<LittleEndian>(0);
    let _ = val1001.write_u32::<LittleEndian>(width);
    let _ = val1001.write_u32::<LittleEndian>(height);
    tlvs.extend_from_slice(&build_tlv(1001, &val1001));

    let mut val1003 = Vec::new();
    let _ = val1003.write_u32::<LittleEndian>(1);
    let _ = val1003.write_u32::<LittleEndian>(0);
    let _ = val1003.write_u32::<LittleEndian>(0);
    let _ = val1003.write_u32::<LittleEndian>(0);
    let _ = val1003.write_u32::<LittleEndian>(0);
    let _ = val1003.write_u32::<LittleEndian>(width);
    let _ = val1003.write_u32::<LittleEndian>(height);
    tlvs.extend_from_slice(&build_tlv(1003, &val1003));

    let scale_f32 = scale as f32;
    let mut val1004 = [0u8; 8];
    val1004[4..8].copy_from_slice(&scale_f32.to_le_bytes());
    tlvs.extend_from_slice(&build_tlv(1004, &val1004));

    let mut val1006 = Vec::new();
    let _ = val1006.write_u32::<LittleEndian>(1);
    tlvs.extend_from_slice(&build_tlv(1006, &val1006));

    let mut val1007 = Vec::new();
    let _ = val1007.write_u32::<LittleEndian>(row_bytes);
    tlvs.extend_from_slice(&build_tlv(1007, &val1007));

    let mut header = vec![0u8; 184];
    header[0..4].copy_from_slice(b"ISTC");
    let _ = (&mut header[4..8]).write_u32::<LittleEndian>(1);
    let _ = (&mut header[8..12]).write_u32::<LittleEndian>(0);
    let _ = (&mut header[12..16]).write_u32::<LittleEndian>(width);
    let _ = (&mut header[16..20]).write_u32::<LittleEndian>(height);
    let _ = (&mut header[20..24]).write_u32::<LittleEndian>(scale * 100);
    header[24..28].copy_from_slice(b"BGRA");
    let _ = (&mut header[28..32]).write_u32::<LittleEndian>(1);
    let _ = (&mut header[32..36]).write_u32::<LittleEndian>(1000);

    let name_bytes = filename.as_bytes();
    let name_len = std::cmp::min(name_bytes.len(), 127);
    header[40..40 + name_len].copy_from_slice(&name_bytes[..name_len]);

    let _ = (&mut header[168..172]).write_u32::<LittleEndian>(tlvs.len() as u32);
    let _ = (&mut header[172..176]).write_u32::<LittleEndian>(1);
    let _ = (&mut header[176..180]).write_u32::<LittleEndian>(0);
    let _ = (&mut header[180..184]).write_u32::<LittleEndian>(payload.len() as u32);

    let mut out = header;
    out.extend_from_slice(&tlvs);
    out.extend_from_slice(&payload);

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
    make_adaptive_csi(
        bgra,
        width,
        height,
        filename,
        scale,
        if prefer_cbck { Some("smart") } else { None },
    )
}
