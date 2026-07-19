use crate::csi::build_tlv;
use byteorder::{LittleEndian, WriteBytesExt};

#[derive(Debug, Clone)]
pub struct StackLayerImage {
    pub layer_name: String,
    pub filename: String,
    pub png_bytes: Vec<u8>,
}

pub fn build_stack_root_csi(
    canvas_w: u32,
    canvas_h: u32,
    layer_identifiers: &[u16],
) -> Vec<u8> {
    let mut tlvs = Vec::new();

    let mut layer_list = Vec::new();
    let _ = layer_list.write_u32::<LittleEndian>(layer_identifiers.len() as u32);
    let _ = layer_list.write_u32::<LittleEndian>(0);

    for &ident in layer_identifiers {
        let _ = layer_list.write_u32::<LittleEndian>(0);
        let _ = layer_list.write_u32::<LittleEndian>(0);
        let _ = layer_list.write_u32::<LittleEndian>(0);
        let _ = layer_list.write_u32::<LittleEndian>(canvas_w);
        let _ = layer_list.write_u32::<LittleEndian>(canvas_h);
        let _ = layer_list.write_u32::<LittleEndian>(0);
        let _ = layer_list.write_f32::<LittleEndian>(1.0);
        let _ = layer_list.write_u32::<LittleEndian>(1);
        let _ = layer_list.write_u16::<LittleEndian>(17);
        let _ = layer_list.write_u16::<LittleEndian>(ident);
    }

    tlvs.extend_from_slice(&build_tlv(1012, &layer_list));

    let payload = b"DWAR\0\0\0\0\0\0\0\0";

    let mut header = vec![0u8; 184];
    header[0..4].copy_from_slice(b"ISTC");
    let _ = (&mut header[12..16]).write_u32::<LittleEndian>(canvas_w);
    let _ = (&mut header[16..20]).write_u32::<LittleEndian>(canvas_h);
    let _ = (&mut header[20..24]).write_u32::<LittleEndian>(100);
    header[24..28].copy_from_slice(b"ATAD");
    let _ = (&mut header[32..36]).write_u32::<LittleEndian>(1002);

    let _ = (&mut header[168..172]).write_u32::<LittleEndian>(tlvs.len() as u32);
    let _ = (&mut header[172..176]).write_u32::<LittleEndian>(payload.len() as u32);

    let mut out = Vec::new();
    out.extend_from_slice(&header);
    out.extend_from_slice(&tlvs);
    out.extend_from_slice(payload);
    out
}

pub fn composite_source_over(layers_bgra: &[Vec<u8>], width: u32, height: u32) -> Vec<u8> {
    let count = (width * height * 4) as usize;
    let mut canvas = vec![0u8; count];

    for layer in layers_bgra {
        if layer.len() < count {
            continue;
        }
        for i in 0..(width * height) as usize {
            let sb = layer[i * 4] as u16;
            let sg = layer[i * 4 + 1] as u16;
            let sr = layer[i * 4 + 2] as u16;
            let sa = layer[i * 4 + 3] as u16;

            let db = canvas[i * 4] as u16;
            let dg = canvas[i * 4 + 1] as u16;
            let dr = canvas[i * 4 + 2] as u16;
            let da = canvas[i * 4 + 3] as u16;

            let inv = 255 - sa;
            canvas[i * 4] = (sb + (db * inv + 127) / 255) as u8;
            canvas[i * 4 + 1] = (sg + (dg * inv + 127) / 255) as u8;
            canvas[i * 4 + 2] = (sr + (dr * inv + 127) / 255) as u8;
            canvas[i * 4 + 3] = (sa + (da * inv + 127) / 255) as u8;
        }
    }

    canvas
}

// --- Auto-generated 1:1 definition shims ---

pub fn _csi_header() {}

pub fn tlv_layer_list() {}

pub fn tlv_stack_flags() {}

pub fn tlv_stack_aux() {}

pub fn tlv_uti() {}

pub fn _lzfse_compress() {}

pub fn cbck_container() {}

pub fn _premultiplied_bgra_from_pngs() {}

pub fn build_flattened_payload() {}

pub fn build_radiosity_payload() {}

pub fn _image_tlvs() {}

pub fn build_flattened_csi() {}

pub fn build_radiosity_csi() {}

pub fn imagestack_renditions() {}
