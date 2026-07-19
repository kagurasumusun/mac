use crate::bomwriter::BOMWriter;
use crate::csi::build_csi_png;
use byteorder::{BigEndian, ByteOrder};
use uuid::Uuid;

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

pub struct CARWriter {
    renditions: Vec<AssetRendition>,
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
        identifier: u16,
    ) {
        let filename = format!("{}.png", name);
        let csi_bytes = build_csi_png(
            bgra,
            width,
            height,
            &filename,
            scale as u32,
            true,
        );

        self.add_rendition(AssetRendition {
            name: name.to_string(),
            filename,
            csi_bytes,
            identifier,
            idiom,
            scale,
            gamut: 0,
            appearance: 0,
            width,
            height,
        });
    }

    pub fn build(&self) -> Vec<u8> {
        let mut writer = BOMWriter::new();

        // 1. Write CARHEADER block
        let mut car_hdr = vec![0u8; 436];
        car_hdr[0..4].copy_from_slice(b"CTAR"); // Big endian magic
        BigEndian::write_u32(&mut car_hdr[4..8], 975); // coreUI version
        BigEndian::write_u32(&mut car_hdr[8..12], 1); // storage version
        BigEndian::write_u32(&mut car_hdr[12..16], 1700000000); // timestamp
        BigEndian::write_u32(&mut car_hdr[16..20], self.renditions.len() as u32); // rendition count

        let main_ver = b"actool-rs 0.1.0";
        car_hdr[20..20 + main_ver.len()].copy_from_slice(main_ver);
        car_hdr[148..148 + main_ver.len()].copy_from_slice(main_ver);

        let random_uuid = Uuid::new_v4();
        car_hdr[404..420].copy_from_slice(random_uuid.as_bytes());

        BigEndian::write_u32(&mut car_hdr[420..424], 0); // checksum
        BigEndian::write_u32(&mut car_hdr[424..428], 1); // schema
        BigEndian::write_u32(&mut car_hdr[428..432], 1); // color space sRGB
        BigEndian::write_u32(&mut car_hdr[432..436], 1); // key semantics

        writer.add_block(car_hdr, Some("CARHEADER".to_string()));

        // 2. Write KEYFORMAT block
        // Attributes: 17 (Identifier), 12 (Scale), 15 (Idiom), 24 (Gamut), 7 (Appearance), 13 (Localization)
        let mut kfmt = vec![0u8; 36];
        kfmt[0..4].copy_from_slice(b"kfmt");
        BigEndian::write_u32(&mut kfmt[4..8], 0);
        BigEndian::write_u32(&mut kfmt[8..12], 6); // 6 key attributes
        let attrs = [17u32, 12, 15, 24, 7, 13];
        for (i, attr) in attrs.iter().enumerate() {
            BigEndian::write_u32(&mut kfmt[12 + i * 4..16 + i * 4], *attr);
        }
        writer.add_block(kfmt, Some("KEYFORMAT".to_string()));

        // 3. Write Rendition CSI payload blocks and B-Tree
        let mut rendition_blocks = Vec::new();
        for r in &self.renditions {
            let block_id = writer.add_block(r.csi_bytes.clone(), None);
            rendition_blocks.push((r, block_id));
        }

        // 4. Build FACET KEYS, CAR KEY (RENDITIONS), APPEARANCE KEYS, LOCALIZATION KEYS tree blocks
        let facet_tree = build_btree_block(&[]);
        writer.add_block(facet_tree, Some("FACETKEYS".to_string()));

        let rend_tree = build_btree_block(&rendition_blocks);
        writer.add_block(rend_tree, Some("CAR KEY".to_string()));

        let app_tree = build_btree_block(&[]);
        writer.add_block(app_tree, Some("APPEARANCEKEYS".to_string()));

        let loc_tree = build_btree_block(&[]);
        writer.add_block(loc_tree, Some("LOCALIZATIONKEYS".to_string()));

        writer.build()
    }
}

fn build_btree_block(items: &[(&AssetRendition, u32)]) -> Vec<u8> {
    let mut buf = Vec::new();

    // B-Tree header: b"BTREE" (4B magic / 8B header), version 1, count, page_size 4096
    buf.extend_from_slice(b"BTR3");
    let mut hdr = [0u8; 28];
    BigEndian::write_u32(&mut hdr[0..4], 1); // version
    BigEndian::write_u32(&mut hdr[4..8], items.len() as u32); // count
    BigEndian::write_u32(&mut hdr[8..12], 4096); // page size
    buf.extend_from_slice(&hdr);

    // Leaf entries
    for (r, block_id) in items {
        let mut entry = vec![0u8; 16];
        BigEndian::write_u16(&mut entry[0..2], r.identifier);
        BigEndian::write_u16(&mut entry[2..4], r.scale);
        BigEndian::write_u16(&mut entry[4..6], r.idiom);
        BigEndian::write_u16(&mut entry[6..8], r.gamut);
        BigEndian::write_u16(&mut entry[8..10], r.appearance);
        BigEndian::write_u16(&mut entry[10..12], 0); // localization
        BigEndian::write_u32(&mut entry[12..16], *block_id);
        buf.extend_from_slice(&entry);
    }

    buf
}
