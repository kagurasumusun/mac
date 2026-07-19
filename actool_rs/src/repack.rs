use crate::bom::BOMStore;
use crate::bomwriter::BOMWriter;
use std::path::Path;

pub fn repack<P: AsRef<Path>>(src: P, dst: P) -> Result<(), String> {
    let store = BOMStore::from_path(src).map_err(|e| e.to_string())?;
    let mut writer = BOMWriter::new();

    let mut ids: Vec<u32> = store.blocks.keys().copied().collect();
    ids.sort();

    let mut names_by_id = std::collections::HashMap::new();
    for (name, id) in &store.variables {
        names_by_id.insert(*id, name.clone());
    }

    for id in ids {
        if let Ok(data) = store.block_data(id) {
            let name = names_by_id.get(&id).cloned();
            writer.add_block(data.to_vec(), name);
        }
    }

    std::fs::write(dst, writer.build()).map_err(|e| e.to_string())
}

// --- Auto-generated 1:1 definition shims ---

pub fn main() {}
