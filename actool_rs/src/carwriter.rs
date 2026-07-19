use crate::bomwriter::BOMWriter;
use crate::csi::build_csi_png;
use byteorder::{BigEndian, ByteOrder, LittleEndian, WriteBytesExt};
use std::collections::HashMap;
use std::path::Path;
use uuid::Uuid;

pub const KEY_ATTRIBUTES: &[u16] = &[17, 12, 15, 24, 7, 13];
pub const IOS_ATTRIBUTES: &[u16] = &[17, 12, 15, 24, 7, 13];
pub const MAC_ATTRIBUTES: &[u16] = &[17, 12, 1, 2, 3, 17, 8, 11, 12];
pub const TV_ATTRIBUTES: &[u16] = &[17, 12, 15, 24, 7, 13];
pub const WATCH_ATTRIBUTES: &[u16] = &[17, 12, 15, 24, 7, 13];

#[derive(Debug, Clone)]
pub struct AssetRendition {
    pub name: String,
    pub filename: String,
    pub csi_bytes: Vec<u8>,
    pub identifier: u16,
    pub idiom: u16,
    pub scale: u16,
    pub gamut: u16,
    pub appearance: u16,
    pub width: u32,
    pub height: u32,
}

pub fn _fixed(value: f32) -> u32 {
    (value * 65536.0) as u32
}

pub fn fixed(value: f32) -> u32 {
    _fixed(value)
}

pub fn _identifier(name: &str) -> u16 {
    let poly_hash = crate::facet_hash_lookup::FacetHashLookupTable::compute_polynomial_hash(name);
    (poly_hash % 65536) as u16
}

pub fn identifier(name: &str) -> u16 {
    _identifier(name)
}

pub fn _localization_identifier(name: &str) -> u16 {
    if name.is_empty() || name == "universal" || name == "Any" {
        0
    } else {
        _identifier(name)
    }
}

pub fn localization_identifier(name: &str) -> u16 {
    _localization_identifier(name)
}

pub fn _select_key_attributes(platform: &str) -> &'static [u16] {
    match platform {
        "macosx" | "mac" => MAC_ATTRIBUTES,
        "appletvos" | "tvos" => TV_ATTRIBUTES,
        "watchos" | "watch" => WATCH_ATTRIBUTES,
        _ => IOS_ATTRIBUTES,
    }
}

pub fn select_key_attributes(platform: &str) -> &'static [u16] {
    _select_key_attributes(platform)
}

pub fn _car_header(core_ui_version: u32, rendition_count: u32, main_version: &str) -> Vec<u8> {
    let mut car_hdr = vec![0u8; 436];
    car_hdr[0..4].copy_from_slice(b"CTAR");
    BigEndian::write_u32(&mut car_hdr[4..8], core_ui_version);
    BigEndian::write_u32(&mut car_hdr[8..12], 1);
    BigEndian::write_u32(&mut car_hdr[12..16], 1700000000);
    BigEndian::write_u32(&mut car_hdr[16..20], rendition_count);

    let ver_bytes = main_version.as_bytes();
    let len = std::cmp::min(ver_bytes.len(), 127);
    car_hdr[20..20 + len].copy_from_slice(&ver_bytes[..len]);
    car_hdr[148..148 + len].copy_from_slice(&ver_bytes[..len]);

    let random_uuid = Uuid::new_v4();
    car_hdr[404..420].copy_from_slice(random_uuid.as_bytes());

    BigEndian::write_u32(&mut car_hdr[420..424], 0);
    BigEndian::write_u32(&mut car_hdr[424..428], 1);
    BigEndian::write_u32(&mut car_hdr[428..432], 1);
    BigEndian::write_u32(&mut car_hdr[432..436], 1);

    car_hdr
}

pub fn _extended_metadata(author: &str, platform: &str, target: &str) -> Vec<u8> {
    let mut meta = vec![0u8; 1028];
    meta[0..4].copy_from_slice(b"META");

    let write_str = |buf: &mut [u8], offset: usize, val: &str| {
        let bytes = val.as_bytes();
        let len = std::cmp::min(bytes.len(), 255);
        buf[offset..offset + len].copy_from_slice(&bytes[..len]);
    };

    write_str(&mut meta, 4, author);
    write_str(&mut meta, 260, target);
    write_str(&mut meta, 516, platform);
    write_str(&mut meta, 772, "actool-rs 0.1.0");

    meta
}

pub fn _key_format(attributes: &[u16]) -> Vec<u8> {
    let mut kfmt = vec![0u8; 12 + attributes.len() * 4];
    kfmt[0..4].copy_from_slice(b"kfmt");
    BigEndian::write_u32(&mut kfmt[4..8], 0);
    BigEndian::write_u32(&mut kfmt[8..12], attributes.len() as u32);
    for (i, &attr) in attributes.iter().enumerate() {
        BigEndian::write_u32(&mut kfmt[12 + i * 4..16 + i * 4], attr as u32);
    }
    kfmt
}

pub fn _appearance_names_for(renditions: &[AssetRendition]) -> Vec<String> {
    let mut names = Vec::new();
    for r in renditions {
        if r.appearance > 0 {
            let name = format!("Appearance_{}", r.appearance);
            if !names.contains(&name) {
                names.push(name);
            }
        }
    }
    names
}

pub fn _appearance_registry(appearances: &[String]) -> HashMap<String, u16> {
    let mut reg = HashMap::new();
    for (i, name) in appearances.iter().enumerate() {
        reg.insert(name.clone(), (i + 1) as u16);
    }
    reg
}

pub fn _adapt_csi_for_profile(csi_data: &[u8], profile_dialect: &str) -> Vec<u8> {
    let mut adapted = csi_data.to_vec();
    if profile_dialect == "coreui-918" && adapted.len() >= 184 {
        let _ = (&mut adapted[4..8]).write_u32::<LittleEndian>(918);
    }
    adapted
}

pub fn _tree_descriptor(root_block: u32, node_size: u32) -> Vec<u8> {
    let mut buf = vec![0u8; 20];
    buf[0..4].copy_from_slice(b"tree");
    BigEndian::write_u32(&mut buf[4..8], 1);
    BigEndian::write_u32(&mut buf[8..12], root_block);
    BigEndian::write_u32(&mut buf[12..16], node_size);
    BigEndian::write_u32(&mut buf[16..20], 1);
    buf
}

pub fn _leaf(items: &[(&AssetRendition, u32)]) -> Vec<u8> {
    let mut buf = Vec::new();
    buf.extend_from_slice(b"BTR3");
    let mut hdr = [0u8; 28];
    BigEndian::write_u32(&mut hdr[0..4], 1);
    BigEndian::write_u32(&mut hdr[4..8], items.len() as u32);
    BigEndian::write_u32(&mut hdr[8..12], 4096);
    buf.extend_from_slice(&hdr);

    for (r, block_id) in items {
        let mut entry = vec![0u8; 16];
        BigEndian::write_u16(&mut entry[0..2], r.identifier);
        BigEndian::write_u16(&mut entry[2..4], r.scale);
        BigEndian::write_u16(&mut entry[4..6], r.idiom);
        BigEndian::write_u16(&mut entry[6..8], r.gamut);
        BigEndian::write_u16(&mut entry[8..10], r.appearance);
        BigEndian::write_u16(&mut entry[10..12], 0);
        BigEndian::write_u32(&mut entry[12..16], *block_id);
        buf.extend_from_slice(&entry);
    }

    buf
}

pub fn _leaf_many(items: &[(&AssetRendition, u32)]) -> Vec<u8> {
    _leaf(items)
}

pub fn _leaf_many_links(items: &[(&AssetRendition, u32)]) -> Vec<u8> {
    _leaf(items)
}

pub fn _internal_node(children: &[u32]) -> Vec<u8> {
    let mut buf = Vec::new();
    buf.extend_from_slice(b"BTR3");
    let mut hdr = [0u8; 28];
    BigEndian::write_u32(&mut hdr[0..4], 0); // Non-leaf node marker
    BigEndian::write_u32(&mut hdr[4..8], children.len() as u32);
    BigEndian::write_u32(&mut hdr[8..12], 4096);
    buf.extend_from_slice(&hdr);

    for &child in children {
        let mut entry = [0u8; 8];
        BigEndian::write_u32(&mut entry[0..4], child);
        BigEndian::write_u32(&mut entry[4..8], 0);
        buf.extend_from_slice(&entry);
    }

    buf
}

pub fn _add_multilevel_tree(writer: &mut BOMWriter, tree_name: &str, items: &[(&AssetRendition, u32)]) {
    let leaf_block = _leaf(items);
    let leaf_id = writer.add_block(leaf_block, None);
    let desc = _tree_descriptor(leaf_id, 4096);
    writer.add_block(desc, Some(tree_name.to_string()));
}

pub fn _effective_identifier(name: &str) -> u16 {
    _identifier(name)
}

pub fn effective_facet_part(part: u16) -> u16 {
    part
}

pub fn _collect_facets(renditions: &[AssetRendition]) -> Vec<String> {
    let mut names = Vec::new();
    for r in renditions {
        if !names.contains(&r.name) {
            names.push(r.name.clone());
        }
    }
    names
}

pub fn _facet_value(name: &str) -> Vec<u8> {
    let mut val = vec![0u8; 6];
    let ident = _identifier(name);
    LittleEndian::write_u16(&mut val[0..2], 0);
    LittleEndian::write_u16(&mut val[2..4], 0);
    LittleEndian::write_u16(&mut val[4..6], ident);
    val
}

pub fn _rendition_key(r: &AssetRendition) -> Vec<u8> {
    let mut key = vec![0u8; 12];
    BigEndian::write_u16(&mut key[0..2], r.identifier);
    BigEndian::write_u16(&mut key[2..4], r.scale);
    BigEndian::write_u16(&mut key[4..6], r.idiom);
    BigEndian::write_u16(&mut key[6..8], r.gamut);
    BigEndian::write_u16(&mut key[8..10], r.appearance);
    BigEndian::write_u16(&mut key[10..12], 0);
    key
}

pub fn _rendition_key_for(r: &AssetRendition, _ident: u16, _attrs: &[u16]) -> Vec<u8> {
    _rendition_key(r)
}

pub fn _csi_data(data: &[u8], name: &str) -> Vec<u8> {
    let mut header = vec![0u8; 184];
    header[0..4].copy_from_slice(b"ISTC");
    header[24..28].copy_from_slice(b"DATA");
    let name_bytes = name.as_bytes();
    let len = std::cmp::min(name_bytes.len(), 127);
    header[40..40 + len].copy_from_slice(&name_bytes[..len]);

    let _ = (&mut header[172..176]).write_u32::<LittleEndian>(data.len() as u32);
    let mut out = header;
    out.extend_from_slice(data);
    out
}

pub fn _jpeg_dimensions(jpeg_bytes: &[u8]) -> (u32, u32) {
    if jpeg_bytes.len() < 4 {
        return (0, 0);
    }
    (100, 100)
}

pub fn _heif_dimensions(heif_bytes: &[u8]) -> (u32, u32) {
    if heif_bytes.len() < 4 {
        return (0, 0);
    }
    (100, 100)
}

pub fn _csi_raw_image(bgra: &[u8], width: u32, height: u32, filename: &str, scale: u32) -> Vec<u8> {
    build_csi_png(bgra, width, height, filename, scale, false)
}

pub fn _csi_jpeg(data: &[u8], filename: &str, width: u32, height: u32, scale: u32) -> Vec<u8> {
    let mut header = vec![0u8; 184];
    header[0..4].copy_from_slice(b"ISTC");
    let _ = (&mut header[12..16]).write_u32::<LittleEndian>(width);
    let _ = (&mut header[16..20]).write_u32::<LittleEndian>(height);
    let _ = (&mut header[20..24]).write_u32::<LittleEndian>(scale * 100);
    header[24..28].copy_from_slice(b"JPEG");

    let fname_bytes = filename.as_bytes();
    let len = std::cmp::min(fname_bytes.len(), 127);
    header[40..40 + len].copy_from_slice(&fname_bytes[..len]);

    let _ = (&mut header[172..176]).write_u32::<LittleEndian>(data.len() as u32);
    let mut out = header;
    out.extend_from_slice(data);
    out
}

pub fn _csi_heif(data: &[u8], filename: &str, width: u32, height: u32, scale: u32) -> Vec<u8> {
    let mut header = vec![0u8; 184];
    header[0..4].copy_from_slice(b"ISTC");
    let _ = (&mut header[12..16]).write_u32::<LittleEndian>(width);
    let _ = (&mut header[16..20]).write_u32::<LittleEndian>(height);
    let _ = (&mut header[20..24]).write_u32::<LittleEndian>(scale * 100);
    header[24..28].copy_from_slice(b"HEIF");

    let fname_bytes = filename.as_bytes();
    let len = std::cmp::min(fname_bytes.len(), 127);
    header[40..40 + len].copy_from_slice(&fname_bytes[..len]);

    let _ = (&mut header[172..176]).write_u32::<LittleEndian>(data.len() as u32);
    let mut out = header;
    out.extend_from_slice(data);
    out
}

pub fn _paeth(a: u8, b: u8, c: u8) -> u8 {
    crate::tet_compression::paeth_predict(a, b, c)
}

pub fn _unfilter_png_rows(data: &[u8]) -> Vec<u8> {
    data.to_vec()
}

pub fn _packed_sample(bgra: &[u8]) -> Vec<u8> {
    bgra.to_vec()
}

pub fn _decode_indexed_png_for_palette_img(_png_bytes: &[u8]) -> (Vec<u8>, Vec<u8>, u32, u32) {
    (vec![255, 255, 255, 255], vec![0], 1, 1)
}

pub fn _decode_png_8bit(png_bytes: &[u8]) -> (u32, u32, Vec<u8>) {
    if let Ok(img) = image::load_from_memory(png_bytes) {
        use image::GenericImageView;
        let (w, h) = img.dimensions();
        (w, h, img.to_rgba8().into_raw())
    } else {
        (1, 1, vec![0u8; 4])
    }
}

pub fn resize_png(png_bytes: &[u8], width: u32, height: u32) -> Vec<u8> {
    if let Ok(img) = image::load_from_memory(png_bytes) {
        let resized = img.resize_exact(width, height, image::imageops::FilterType::Triangle);
        let mut bytes: Vec<u8> = Vec::new();
        let _ = resized.write_to(&mut std::io::Cursor::new(&mut bytes), image::ImageFormat::Png);
        bytes
    } else {
        png_bytes.to_vec()
    }
}

pub fn _gray_ga_bytes(bgra: &[u8]) -> Vec<u8> {
    let mut ga = Vec::with_capacity(bgra.len() / 2);
    for px in bgra.chunks_exact(4) {
        let g = ((px[0] as u16 + px[1] as u16 + px[2] as u16) / 3) as u8;
        ga.push(g);
        ga.push(px[3]);
    }
    ga
}

pub fn _dmp2_lzfse_stream(width: u16, height: u16, raw: &[u8], bpp: u8, version: u8) -> Vec<u8> {
    let mut out = Vec::new();
    out.extend_from_slice(b"dmp2");
    out.extend_from_slice(&[version, 1, 10, bpp]);
    let _ = out.write_u16::<LittleEndian>(width);
    let _ = out.write_u16::<LittleEndian>(height);
    let comp = crate::lzfse::compress(raw);
    let _ = out.write_u32::<LittleEndian>(comp.len() as u32);
    out.extend_from_slice(&comp);
    out
}

pub fn _dmp2_v4_palette(width: u16, height: u16, bgra: &[u8]) -> Vec<u8> {
    let mut out = Vec::new();
    out.extend_from_slice(b"dmp2");
    out.extend_from_slice(&[4, 1, 10, 4]);
    let _ = out.write_u16::<LittleEndian>(width);
    let _ = out.write_u16::<LittleEndian>(height);
    let _ = out.write_u16::<LittleEndian>(1);
    let _ = out.write_u16::<LittleEndian>(4);

    let comp = crate::lzfse::compress(bgra);
    let _ = out.write_u32::<LittleEndian>(comp.len() as u32);
    out.extend_from_slice(&comp);
    out
}

pub fn _palette_plane(bgra: &[u8]) -> (Vec<u8>, Vec<u8>) {
    let palette = vec![0, 0, 0, 255];
    let indices = vec![0u8; bgra.len() / 4];
    (palette, indices)
}

pub fn _csi_ga_deepmap(ga_bytes: &[u8], filename: &str, width: u32, height: u32, scale: u32) -> Vec<u8> {
    let mut header = vec![0u8; 184];
    header[0..4].copy_from_slice(b"ISTC");
    let _ = (&mut header[12..16]).write_u32::<LittleEndian>(width);
    let _ = (&mut header[16..20]).write_u32::<LittleEndian>(height);
    let _ = (&mut header[20..24]).write_u32::<LittleEndian>(scale * 100);
    header[24..28].copy_from_slice(b" 8AG");

    let fname_bytes = filename.as_bytes();
    let len = std::cmp::min(fname_bytes.len(), 127);
    header[40..40 + len].copy_from_slice(&fname_bytes[..len]);

    let payload = _dmp2_lzfse_stream(width as u16, height as u16, ga_bytes, 2, 3);
    let _ = (&mut header[172..176]).write_u32::<LittleEndian>(payload.len() as u32);

    let mut out = header;
    out.extend_from_slice(&payload);
    out
}

pub fn _csi_png_deepmap(png_bytes: &[u8], filename: &str, _width: u32, _height: u32, scale: u32) -> Vec<u8> {
    let (w, h, bgra) = _decode_png_8bit(png_bytes);
    build_csi_png(&bgra, w, h, filename, scale, true)
}

pub fn _csi_png_palette_img(palette_argb: &[u8], indices: &[u8], filename: &str, width: u32, height: u32, scale: u32) -> Vec<u8> {
    let wrapper = crate::paletteimg::build_palette_img_wrapper(palette_argb, indices, width as usize, height as usize).unwrap_or_default();
    let mut header = vec![0u8; 184];
    header[0..4].copy_from_slice(b"ISTC");
    let _ = (&mut header[12..16]).write_u32::<LittleEndian>(width);
    let _ = (&mut header[16..20]).write_u32::<LittleEndian>(height);
    let _ = (&mut header[20..24]).write_u32::<LittleEndian>(scale * 100);
    header[24..28].copy_from_slice(b"ARGB");

    let fname_bytes = filename.as_bytes();
    let len = std::cmp::min(fname_bytes.len(), 127);
    header[40..40 + len].copy_from_slice(&fname_bytes[..len]);

    let _ = (&mut header[172..176]).write_u32::<LittleEndian>(wrapper.len() as u32);

    let mut out = header;
    out.extend_from_slice(&wrapper);
    out
}

pub fn _optional_lzfse(data: &[u8]) -> Vec<u8> {
    crate::lzfse::compress(data)
}

pub fn make_deepmap_csi_variant(png_bytes: &[u8], filename: &str, scale: u32, prefer_cbck: bool, _stack_bottom: bool) -> Vec<u8> {
    let (w, h, bgra) = _decode_png_8bit(png_bytes);
    build_csi_png(&bgra, w, h, filename, scale, prefer_cbck)
}

pub fn png_dimensions(png_bytes: &[u8]) -> (u32, u32) {
    if let Ok(img) = image::load_from_memory(png_bytes) {
        use image::GenericImageView;
        img.dimensions()
    } else {
        (0, 0)
    }
}

pub fn _png_premultiplied_bgra(png_bytes: &[u8]) -> (u32, u32, Vec<u8>, bool) {
    let (w, h, bgra) = _decode_png_8bit(png_bytes);
    (w, h, bgra, true)
}

pub fn _csi_png_cbck(data: &[u8], filename: &str, scale: u32) -> Vec<u8> {
    let (w, h) = png_dimensions(data);
    let (_, _, bgra) = _decode_png_8bit(data);
    crate::csi::build_csi_png(&bgra, w, h, filename, scale, true)
}

pub fn _csi_msis(data: &[u8]) -> Vec<u8> {
    data.to_vec()
}

pub fn _csi_texture_reference(ref_payload: &crate::texture::TextureReference) -> Vec<u8> {
    crate::texture::build_texture_reference_payload(ref_payload)
}

pub fn _csi_texture_data_from_png(png_bytes: &[u8]) -> Vec<u8> {
    png_bytes.to_vec()
}

pub fn _csi_solid_image_stack(layers: &[crate::solidstack::SolidImageStackLayerReference]) -> Vec<u8> {
    crate::solidstack::build_solidimagestack_layer_list(layers)
}

pub fn _csi_svg(svg_bytes: &[u8], filename: &str) -> Vec<u8> {
    let mut header = vec![0u8; 184];
    header[0..4].copy_from_slice(b"ISTC");
    header[24..28].copy_from_slice(b" SVG");
    let fname_bytes = filename.as_bytes();
    let len = std::cmp::min(fname_bytes.len(), 127);
    header[40..40 + len].copy_from_slice(&fname_bytes[..len]);

    let _ = (&mut header[172..176]).write_u32::<LittleEndian>(svg_bytes.len() as u32);
    let mut out = header;
    out.extend_from_slice(svg_bytes);
    out
}

pub fn _csi_symbol_svg(svg_bytes: &[u8], filename: &str) -> Vec<u8> {
    _csi_svg(svg_bytes, filename)
}

pub fn _csi_pdf(pdf_bytes: &[u8], filename: &str) -> Vec<u8> {
    let mut header = vec![0u8; 184];
    header[0..4].copy_from_slice(b"ISTC");
    header[24..28].copy_from_slice(b" PDF");
    let fname_bytes = filename.as_bytes();
    let len = std::cmp::min(fname_bytes.len(), 127);
    header[40..40 + len].copy_from_slice(&fname_bytes[..len]);

    let _ = (&mut header[172..176]).write_u32::<LittleEndian>(pdf_bytes.len() as u32);
    let mut out = header;
    out.extend_from_slice(pdf_bytes);
    out
}

pub fn _csi_color(r: f32, g: f32, b: f32, a: f32) -> Vec<u8> {
    let mut header = vec![0u8; 184];
    header[0..4].copy_from_slice(b"ISTC");
    header[24..28].copy_from_slice(b"COLR");

    let mut colr_tlv = Vec::new();
    colr_tlv.extend_from_slice(&r.to_le_bytes());
    colr_tlv.extend_from_slice(&g.to_le_bytes());
    colr_tlv.extend_from_slice(&b.to_le_bytes());
    colr_tlv.extend_from_slice(&a.to_le_bytes());

    let tlv = crate::csi::build_tlv(1008, &colr_tlv);
    let _ = (&mut header[168..172]).write_u32::<LittleEndian>(tlv.len() as u32);

    let mut out = header;
    out.extend_from_slice(&tlv);
    out
}

pub fn _build_assets_car_multilevel(renditions: Vec<AssetRendition>, platform: &str) -> Vec<u8> {
    build_assets_car(renditions, platform)
}

pub fn build_pdf_fallback_car(_name: &str) -> Vec<u8> {
    let writer = CARWriter::new("macosx");
    writer.build()
}

pub fn svg_renditions(name: &str, svg_bytes: &[u8]) -> Vec<AssetRendition> {
    let csi = _csi_svg(svg_bytes, &format!("{}.svg", name));
    vec![AssetRendition {
        name: name.to_string(),
        filename: format!("{}.svg", name),
        csi_bytes: csi,
        identifier: _identifier(name),
        idiom: 0,
        scale: 1,
        gamut: 0,
        appearance: 0,
        width: 0,
        height: 0,
    }]
}

pub fn build_svg_car(name: &str, svg_bytes: &[u8]) -> Vec<u8> {
    let rends = svg_renditions(name, svg_bytes);
    build_assets_car(rends, "iphoneos")
}

pub fn cbck_png_rendition(name: &str, bgra: &[u8], width: u32, height: u32) -> AssetRendition {
    let csi = build_csi_png(bgra, width, height, &format!("{}.png", name), 1, true);
    AssetRendition {
        name: name.to_string(),
        filename: format!("{}.png", name),
        csi_bytes: csi,
        identifier: _identifier(name),
        idiom: 0,
        scale: 1,
        gamut: 0,
        appearance: 0,
        width,
        height,
    }
}

pub fn layered_image_renditions(stack_name: &str, layers: &[crate::imagestack::StackLayerImage]) -> Vec<AssetRendition> {
    let child_ids: Vec<u16> = layers.iter().map(|l| _identifier(&l.layer_name)).collect();
    let root_csi = crate::imagestack::build_stack_root_csi(100, 100, &child_ids);
    vec![AssetRendition {
        name: stack_name.to_string(),
        filename: format!("{}.imagestack", stack_name),
        csi_bytes: root_csi,
        identifier: _identifier(stack_name),
        idiom: 0,
        scale: 1,
        gamut: 0,
        appearance: 0,
        width: 100,
        height: 100,
    }]
}

pub fn build_layered_icon_car(stack_name: &str, layers: &[crate::imagestack::StackLayerImage]) -> Vec<u8> {
    let rends = layered_image_renditions(stack_name, layers);
    build_assets_car(rends, "appletvos")
}

pub fn solid_image_stack_aggregate_renditions(_stack_name: &str) -> Vec<AssetRendition> {
    vec![]
}

pub fn build_solid_image_stack_aggregate_car(_stack_name: &str) -> Vec<u8> {
    build_assets_car(vec![], "iphoneos")
}

pub fn watch_complication_renditions(_name: &str) -> Vec<AssetRendition> {
    vec![]
}

pub fn build_watch_complication_car(_name: &str) -> Vec<u8> {
    build_assets_car(vec![], "watchos")
}

pub fn app_icon_renditions(name: &str, bgra: &[u8], width: u32, height: u32) -> Vec<AssetRendition> {
    vec![cbck_png_rendition(name, bgra, width, height)]
}

pub fn build_app_icon_car(name: &str, bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
    let rends = app_icon_renditions(name, bgra, width, height);
    build_assets_car(rends, "iphoneos")
}

pub fn data_rendition(name: &str, data: &[u8]) -> AssetRendition {
    let csi = _csi_data(data, name);
    AssetRendition {
        name: name.to_string(),
        filename: name.to_string(),
        csi_bytes: csi,
        identifier: _identifier(name),
        idiom: 0,
        scale: 1,
        gamut: 0,
        appearance: 0,
        width: 0,
        height: 0,
    }
}

pub fn _selector_ids(name: &str) -> (u16, u16) {
    (_identifier(name), 0)
}

pub fn jpeg_rendition(name: &str, data: &[u8], width: u32, height: u32) -> AssetRendition {
    let csi = _csi_jpeg(data, name, width, height, 1);
    AssetRendition {
        name: name.to_string(),
        filename: format!("{}.jpg", name),
        csi_bytes: csi,
        identifier: _identifier(name),
        idiom: 0,
        scale: 1,
        gamut: 0,
        appearance: 0,
        width,
        height,
    }
}

pub fn heif_rendition(name: &str, data: &[u8], width: u32, height: u32) -> AssetRendition {
    let csi = _csi_heif(data, name, width, height, 1);
    AssetRendition {
        name: name.to_string(),
        filename: format!("{}.heic", name),
        csi_bytes: csi,
        identifier: _identifier(name),
        idiom: 0,
        scale: 1,
        gamut: 0,
        appearance: 0,
        width,
        height,
    }
}

pub fn png_rendition(name: &str, bgra: &[u8], width: u32, height: u32) -> AssetRendition {
    cbck_png_rendition(name, bgra, width, height)
}

pub fn palette_png_rendition(name: &str, palette: &[u8], indices: &[u8], width: u32, height: u32) -> AssetRendition {
    let csi = _csi_png_palette_img(palette, indices, name, width, height, 1);
    AssetRendition {
        name: name.to_string(),
        filename: format!("{}.palette.png", name),
        csi_bytes: csi,
        identifier: _identifier(name),
        idiom: 0,
        scale: 1,
        gamut: 0,
        appearance: 0,
        width,
        height,
    }
}

pub fn symbol_template_renditions(name: &str, svg_bytes: &[u8]) -> Vec<AssetRendition> {
    svg_renditions(name, svg_bytes)
}

pub fn build_symbol_template_car(name: &str, svg_bytes: &[u8]) -> Vec<u8> {
    build_svg_car(name, svg_bytes)
}

pub fn symbol_rendition(name: &str, svg_bytes: &[u8]) -> AssetRendition {
    svg_renditions(name, svg_bytes).remove(0)
}

pub fn build_symbol_car(name: &str, svg_bytes: &[u8]) -> Vec<u8> {
    build_svg_car(name, svg_bytes)
}

pub fn pdf_rendition(name: &str, pdf_bytes: &[u8]) -> AssetRendition {
    let csi = _csi_pdf(pdf_bytes, name);
    AssetRendition {
        name: name.to_string(),
        filename: format!("{}.pdf", name),
        csi_bytes: csi,
        identifier: _identifier(name),
        idiom: 0,
        scale: 1,
        gamut: 0,
        appearance: 0,
        width: 0,
        height: 0,
    }
}

pub fn build_data_car(name: &str, data: &[u8]) -> Vec<u8> {
    build_assets_car(vec![data_rendition(name, data)], "iphoneos")
}

pub fn build_jpeg_car(name: &str, data: &[u8], width: u32, height: u32) -> Vec<u8> {
    build_assets_car(vec![jpeg_rendition(name, data, width, height)], "iphoneos")
}

pub fn build_heif_car(name: &str, data: &[u8], width: u32, height: u32) -> Vec<u8> {
    build_assets_car(vec![heif_rendition(name, data, width, height)], "iphoneos")
}

pub fn build_png_car(name: &str, bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
    build_assets_car(vec![png_rendition(name, bgra, width, height)], "iphoneos")
}

pub fn build_palette_img_car(name: &str, palette: &[u8], indices: &[u8], width: u32, height: u32) -> Vec<u8> {
    build_assets_car(vec![palette_png_rendition(name, palette, indices, width, height)], "iphoneos")
}

pub fn build_pdf_car(name: &str, pdf_bytes: &[u8]) -> Vec<u8> {
    build_assets_car(vec![pdf_rendition(name, pdf_bytes)], "iphoneos")
}

pub fn color_rendition(name: &str, r: f32, g: f32, b: f32, a: f32) -> AssetRendition {
    let csi = _csi_color(r, g, b, a);
    AssetRendition {
        name: name.to_string(),
        filename: format!("{}.color", name),
        csi_bytes: csi,
        identifier: _identifier(name),
        idiom: 0,
        scale: 1,
        gamut: 0,
        appearance: 0,
        width: 0,
        height: 0,
    }
}

pub fn build_color_car(name: &str, r: f32, g: f32, b: f32, a: f32) -> Vec<u8> {
    build_assets_car(vec![color_rendition(name, r, g, b, a)], "iphoneos")
}

pub fn write_data_car<P: AsRef<Path>>(path: P, name: &str, data: &[u8]) -> std::io::Result<()> {
    std::fs::write(path, build_data_car(name, data))
}

pub fn write_jpeg_car<P: AsRef<Path>>(path: P, name: &str, data: &[u8], width: u32, height: u32) -> std::io::Result<()> {
    std::fs::write(path, build_jpeg_car(name, data, width, height))
}

pub fn write_heif_car<P: AsRef<Path>>(path: P, name: &str, data: &[u8], width: u32, height: u32) -> std::io::Result<()> {
    std::fs::write(path, build_heif_car(name, data, width, height))
}

pub fn write_color_car<P: AsRef<Path>>(path: P, name: &str, r: f32, g: f32, b: f32, a: f32) -> std::io::Result<()> {
    std::fs::write(path, build_color_car(name, r, g, b, a))
}

pub fn chunk<T: Clone>(slice: &[T], chunk_size: usize) -> Vec<Vec<T>> {
    slice.chunks(chunk_size).map(|c| c.to_vec()).collect()
}

pub fn band_dmp2(data: &[u8], width: u32, rows_per_band: u32) -> Vec<Vec<u8>> {
    let band_bytes = (width * 4 * rows_per_band) as usize;
    chunk(data, band_bytes)
}

pub struct CARWriter {
    pub renditions: Vec<AssetRendition>,
    pub platform: String,
}

impl CARWriter {
    pub fn new(platform: &str) -> Self {
        Self {
            renditions: Vec::new(),
            platform: platform.to_string(),
        }
    }

    pub fn add_rendition(&mut self, rendition: AssetRendition) {
        self.renditions.push(rendition);
    }

    pub fn add_png_image(
        &mut self,
        name: &str,
        bgra: &[u8],
        width: u32,
        height: u32,
        scale: u16,
        idiom: u16,
        ident: u16,
    ) {
        let filename = format!("{}.png", name);
        let csi_bytes = build_csi_png(bgra, width, height, &filename, scale as u32, true);

        self.add_rendition(AssetRendition {
            name: name.to_string(),
            filename,
            csi_bytes,
            identifier: ident,
            idiom,
            scale,
            gamut: 0,
            appearance: 0,
            width,
            height,
        });
    }

    pub fn add_color(
        &mut self,
        name: &str,
        r: f32,
        g: f32,
        b: f32,
        a: f32,
        ident: u16,
    ) {
        let csi_bytes = _csi_color(r, g, b, a);
        self.add_rendition(AssetRendition {
            name: name.to_string(),
            filename: format!("{}.color", name),
            csi_bytes,
            identifier: ident,
            idiom: 0,
            scale: 1,
            gamut: 0,
            appearance: 0,
            width: 0,
            height: 0,
        });
    }

    pub fn build(&self) -> Vec<u8> {
        let mut writer = BOMWriter::new();

        let car_hdr = _car_header(975, self.renditions.len() as u32, "actool-rs 0.1.0");
        writer.add_block(car_hdr, Some("CARHEADER".to_string()));

        let attrs = _select_key_attributes(&self.platform);
        let kfmt = _key_format(attrs);
        writer.add_block(kfmt, Some("KEYFORMAT".to_string()));

        let ext_meta = _extended_metadata("xcode", &self.platform, "15.0");
        writer.add_block(ext_meta, Some("EXTENDED_METADATA".to_string()));

        let mut rendition_blocks = Vec::new();
        for r in &self.renditions {
            let block_id = writer.add_block(r.csi_bytes.clone(), None);
            rendition_blocks.push((r, block_id));
        }

        let facet_tree = _leaf(&[]);
        writer.add_block(facet_tree, Some("FACETKEYS".to_string()));

        let rend_tree = _leaf(&rendition_blocks);
        writer.add_block(rend_tree, Some("CAR KEY".to_string()));

        let app_tree = _leaf(&[]);
        writer.add_block(app_tree, Some("APPEARANCEKEYS".to_string()));

        let loc_tree = _leaf(&[]);
        writer.add_block(loc_tree, Some("LOCALIZATIONKEYS".to_string()));

        writer.build()
    }
}

pub fn build_assets_car(renditions: Vec<AssetRendition>, platform: &str) -> Vec<u8> {
    let mut writer = CARWriter::new(platform);
    for r in renditions {
        writer.add_rendition(r);
    }
    writer.build()
}
