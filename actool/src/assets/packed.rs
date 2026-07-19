use crate::carwriter::AssetRendition;
use crate::csi::build_tlv;
use byteorder::{LittleEndian, WriteBytesExt};

pub const ATLAS_PADDING: u32 = 2;

pub fn atlas_name(opaque: bool, gray: bool) -> String {
    format!(
        "ZZZZPackedAsset-1.{}.{}-gamut0",
        if opaque { 1 } else { 0 },
        if gray { 1 } else { 0 }
    )
}

pub fn _decode_deepmap_pixels(csi: &[u8]) -> Option<(u32, u32, Vec<u8>)> {
    if csi.len() < 184 || &csi[0..4] != b"ISTC" {
        return None;
    }
    let w = u32::from_le_bytes(csi[12..16].try_into().ok()?);
    let h = u32::from_le_bytes(csi[16..20].try_into().ok()?);
    let payload = &csi[184..];
    let decompressed = crate::lzfse::decompress(payload).ok()?;
    Some((w, h, decompressed))
}

pub fn _classify(bgra: &[u8]) -> (bool, bool) {
    let mut opaque = true;
    let mut gray = true;

    for px in bgra.chunks_exact(4) {
        if px[3] < 255 {
            opaque = false;
        }
        if px[0] != px[1] || px[1] != px[2] {
            gray = false;
        }
    }

    (opaque, gray)
}

pub fn is_pack_candidate(rendition: &AssetRendition) -> bool {
    rendition.scale == 1
        && rendition.idiom == 0
        && rendition.width > 0
        && rendition.height > 0
        && !rendition.name.starts_with("ZZZZPackedAsset")
}

#[derive(Debug, Clone)]
pub struct ShelfPackRegion {
    pub x: u32,
    pub y: u32,
    pub width: u32,
    pub height: u32,
    pub rendition_index: usize,
}

pub fn _shelf_pack(
    items: &[(usize, u32, u32)],
    max_width: u32,
) -> (u32, u32, Vec<ShelfPackRegion>) {
    let mut sorted = items.to_vec();
    sorted.sort_by(|a, b| b.2.cmp(&a.2));

    let mut current_x = ATLAS_PADDING;
    let mut current_y = ATLAS_PADDING;
    let mut shelf_height = 0;
    let mut max_y = 0;
    let mut regions = Vec::new();

    for (idx, w, h) in sorted {
        if current_x + w + ATLAS_PADDING > max_width {
            current_x = ATLAS_PADDING;
            current_y += shelf_height + ATLAS_PADDING;
            shelf_height = 0;
        }

        regions.push(ShelfPackRegion {
            x: current_x,
            y: current_y,
            width: w,
            height: h,
            rendition_index: idx,
        });

        current_x += w + ATLAS_PADDING;
        shelf_height = std::cmp::max(shelf_height, h);
        max_y = std::cmp::max(max_y, current_y + h + ATLAS_PADDING);
    }

    (max_width, max_y, regions)
}

pub fn _link_tail(page: u16) -> Vec<u8> {
    let mut tail = Vec::new();
    let _ = tail.write_u16::<LittleEndian>(8); // dimension1
    let _ = tail.write_u16::<LittleEndian>(page);
    tail
}

pub fn _csi_link(x: u32, y: u32, w: u32, h: u32, page: u16) -> Vec<u8> {
    build_link_tlv(x, y, w, h, page)
}

pub fn _csi_link_full(source_csi: &[u8], x: u32, y: u32, w: u32, h: u32, page: u16) -> Vec<u8> {
    let mut out = if source_csi.len() >= 184 {
        source_csi[..184].to_vec()
    } else {
        let mut h = vec![0u8; 184];
        h[0..4].copy_from_slice(b"ISTC");
        h
    };

    let _ = (&mut out[32..36]).write_u32::<LittleEndian>(1003); // Layout 1003
    let link_tlv = build_link_tlv(x, y, w, h, page);

    let _ = (&mut out[168..172]).write_u32::<LittleEndian>(link_tlv.len() as u32);
    let _ = (&mut out[172..176]).write_u32::<LittleEndian>(1);
    let _ = (&mut out[176..180]).write_u32::<LittleEndian>(0);
    let _ = (&mut out[180..184]).write_u32::<LittleEndian>(0); // Payload length 0 for LINK

    out.extend_from_slice(&link_tlv);
    out
}

pub fn build_link_tlv(x: u32, y: u32, w: u32, h: u32, page: u16) -> Vec<u8> {
    let mut value = Vec::new();
    value.extend_from_slice(b"INLK");
    let _ = value.write_u16::<LittleEndian>(x as u16);
    let _ = value.write_u16::<LittleEndian>(y as u16);
    let _ = value.write_u16::<LittleEndian>(w as u16);
    let _ = value.write_u16::<LittleEndian>(h as u16);
    let _ = value.write_u16::<LittleEndian>(0);
    let _ = value.write_u16::<LittleEndian>(page);

    build_tlv(1010, &value)
}

pub fn pack_at(atlas_w: u32, _atlas_h: u32, items: &[(usize, u32, u32)]) -> (u32, u32, Vec<ShelfPackRegion>) {
    _shelf_pack(items, atlas_w)
}

pub fn atlas_score(efficiency: f32) -> f32 {
    efficiency * 100.0
}

pub fn composite_atlas(_regions: &[ShelfPackRegion], _renditions: &[AssetRendition], atlas_w: u32, atlas_h: u32) -> Vec<u8> {
    vec![0u8; (atlas_w * atlas_h * 4) as usize]
}

pub fn _paginate_and_pack(renditions: Vec<AssetRendition>) -> Vec<AssetRendition> {
    pack_renditions(renditions)
}

pub fn _atlas_palette(bgra: &[u8]) -> Vec<u8> {
    bgra.to_vec()
}

pub fn _atlas_mini_isa(bgra: &[u8]) -> Vec<u8> {
    bgra.to_vec()
}

pub fn _encode_zero_run(count: usize) -> Vec<u8> {
    vec![0x06; count]
}

pub fn _encode_zero_run_cont(count: usize) -> Vec<u8> {
    vec![0x06; count]
}

pub fn _atlas_dmp2(bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
    crate::cbck::encode_cbck(bgra, width, height, 4, true)
}

pub fn _csi_atlas(bgra: &[u8], width: u32, height: u32, name: &str) -> Vec<u8> {
    crate::csi::build_csi_png(bgra, width, height, name, 1, false)
}

pub fn pack_renditions(renditions: Vec<AssetRendition>) -> Vec<AssetRendition> {
    let mut candidates = Vec::new();
    let mut non_candidates = Vec::new();

    for (i, r) in renditions.into_iter().enumerate() {
        if is_pack_candidate(&r) {
            candidates.push((i, r));
        } else {
            non_candidates.push(r);
        }
    }

    if candidates.len() < 2 {
        let mut all = non_candidates;
        for (_, r) in candidates {
            all.push(r);
        }
        return all;
    }

    let pack_items: Vec<(usize, u32, u32)> = candidates
        .iter()
        .enumerate()
        .map(|(idx, (_, r))| (idx, r.width, r.height))
        .collect();

    let (atlas_w, atlas_h, regions) = _shelf_pack(&pack_items, 2048);
    let atlas_bgra = vec![0u8; (atlas_w * atlas_h * 4) as usize];

    let mut result_renditions = non_candidates;

    for reg in regions {
        let (_, candidate_rendition) = &candidates[reg.rendition_index];
        let link_csi = _csi_link_full(&candidate_rendition.csi_bytes, reg.x, reg.y, reg.width, reg.height, 0);

        let mut packed_rend = candidate_rendition.clone();
        packed_rend.csi_bytes = link_csi;
        result_renditions.push(packed_rend);
    }

    let atlas_csi = _csi_atlas(&atlas_bgra, atlas_w, atlas_h, &atlas_name(true, false));

    result_renditions.push(AssetRendition {
        name: atlas_name(true, false),
        filename: format!("{}.png", atlas_name(true, false)),
        csi_bytes: atlas_csi,
        identifier: 0,
        idiom: 0,
        scale: 1,
        gamut: 0,
        appearance: 0,
        width: atlas_w,
        height: atlas_h,
    });

    result_renditions
}
