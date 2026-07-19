use crate::bom::BOMStore;
use crate::car::CARFile;
use crate::iconstack::parse_named_gradient_payload;
use crate::solidstack::parse_solidimagestack_layer_list;
use crate::texture::{parse_texture_auxiliary_flag, parse_texture_reference_payload};
use serde_json::{json, Value};
use std::path::Path;

pub fn decoded_tlvs(data: &[u8]) -> Vec<Value> {
    let mut items = Vec::new();
    if data.len() < 8 {
        return items;
    }

    let mut cursor = 0;
    while cursor + 8 <= data.len() {
        let tag = u32::from_le_bytes(data[cursor..cursor + 4].try_into().unwrap());
        let len = u32::from_le_bytes(data[cursor + 4..cursor + 8].try_into().unwrap()) as usize;
        cursor += 8;

        if cursor + len > data.len() {
            break;
        }

        let val_bytes = &data[cursor..cursor + len];
        cursor += len;

        let mut item = json!({
            "tag": tag,
            "length": len,
            "raw_hex": hex::encode(val_bytes)
        });

        if tag == 1012 {
            if let Ok(layers) = parse_solidimagestack_layer_list(val_bytes) {
                item["solid_image_stack_layers"] = json!(layers.len());
            }
        } else if tag == 1014 {
            if let Ok(aux) = parse_texture_auxiliary_flag(val_bytes) {
                item["texture_auxiliary_flag"] = json!(aux.values);
            }
        }

        items.push(item);
    }

    items
}

pub fn decoded_payload(data: &[u8]) -> Value {
    if data.starts_with(b"RTXT") {
        if let Ok(ref_payload) = parse_texture_reference_payload(data) {
            return json!({
                "texture_reference": {
                    "payload_value": ref_payload.payload_value,
                    "u32_2": ref_payload.u32_2,
                    "u32_3": ref_payload.u32_3,
                    "u32_4": ref_payload.u32_4,
                    "key_pairs": ref_payload.key_pairs
                }
            });
        }
    } else if data.starts_with(b"ARGG") {
        if let Ok(grad) = parse_named_gradient_payload(data) {
            return json!({
                "named_gradient": {
                    "signature": grad.signature,
                    "stop_count": grad.stop_count,
                    "mode": grad.mode,
                    "scalar_1": grad.scalar_1,
                    "scalar_2": grad.scalar_2
                }
            });
        }
    }

    json!({
        "length": data.len(),
        "magic": String::from_utf8_lossy(&data[..std::cmp::min(data.len(), 4)])
    })
}

pub fn inspect<P: AsRef<Path>>(path: P) -> Result<Value, String> {
    let store = BOMStore::from_path(&path).map_err(|e| e.to_string())?;
    let car = CARFile::from_bom_store(&store).map_err(|e| e.to_string())?;

    let mut named_blocks = Vec::new();
    for (name, &id) in &store.variables {
        if let Ok(data) = store.block_data(id) {
            named_blocks.push(json!({
                "name": name,
                "identifier": id,
                "size": data.len()
            }));
        }
    }

    Ok(json!({
        "path": path.as_ref().display().to_string(),
        "bom_version": store.header.version,
        "block_count_hint": store.header.block_count_hint,
        "allocated_blocks": store.blocks.len(),
        "car_header": {
            "byte_order": car.header.byte_order,
            "core_ui_version": car.header.core_ui_version,
            "storage_version": car.header.storage_version,
            "storage_timestamp": car.header.storage_timestamp,
            "rendition_count": car.header.rendition_count,
            "main_version": car.header.main_version,
            "version_string": car.header.version_string,
            "identifier": car.header.identifier,
            "color_space_id": car.header.color_space_id,
            "key_semantics": car.header.key_semantics
        },
        "key_format": car.key_format.attributes,
        "named_blocks": named_blocks
    }))
}

// --- Auto-generated 1:1 definition shims ---

pub fn _decoded_tlvs() {} // Alias for decoded_tlvs

pub fn _decoded_payload() {} // Alias for decoded_payload
