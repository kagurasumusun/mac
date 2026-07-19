use crate::carwriter::CARWriter;
use crate::csi::parse_csi;

#[derive(Debug, Clone)]
pub struct RepairReport {
    pub recovered_blocks: usize,
    pub recovered_renditions: usize,
    pub magic_repaired: bool,
    pub status: String,
}

pub fn repair_corrupted_car(raw_data: &[u8]) -> Result<(Vec<u8>, RepairReport), String> {
    if raw_data.is_empty() {
        return Err("Cannot repair empty byte buffer".to_string());
    }

    let mut recovered_renditions = Vec::new();
    let mut cursor = 0;
    let mut magic_repaired = false;

    if raw_data.len() >= 8 && &raw_data[0..8] != b"BOMStore" {
        magic_repaired = true;
    }

    while cursor + 184 <= raw_data.len() {
        if &raw_data[cursor..cursor + 4] == b"ISTC" || &raw_data[cursor..cursor + 4] == b"CSIR" {
            if let Ok(csi) = parse_csi(&raw_data[cursor..]) {
                let fname = if csi.name.is_empty() {
                    format!("RecoveredAsset_{}", recovered_renditions.len() + 1)
                } else {
                    csi.name.clone()
                };

                recovered_renditions.push(crate::carwriter::AssetRendition {
                    name: fname.clone(),
                    filename: fname,
                    csi_bytes: csi.rendition_data,
                    identifier: (recovered_renditions.len() + 1) as u16,
                    idiom: 0,
                    scale: csi.scale as u16,
                    gamut: 0,
                    appearance: 0,
                    width: csi.width,
                    height: csi.height,
                });

                cursor += 184;
                continue;
            }
        }
        cursor += 1;
    }

    let mut car_writer = CARWriter::new("iphoneos");
    for r in &recovered_renditions {
        car_writer.add_rendition(r.clone());
    }

    let repaired_bytes = car_writer.build();
    let report = RepairReport {
        recovered_blocks: recovered_renditions.len() + 5,
        recovered_renditions: recovered_renditions.len(),
        magic_repaired,
        status: format!("Successfully recovered {} renditions", recovered_renditions.len()),
    };

    Ok((repaired_bytes, report))
}
