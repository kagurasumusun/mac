use actool_rs::bom::BOMStore;
use actool_rs::bomwriter::BOMWriter;
use std::env;
use std::fs;

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 3 {
        eprintln!("Usage: actool-car-repack <source> <destination>");
        std::process::exit(1);
    }

    let src_path = &args[1];
    let dst_path = &args[2];

    match BOMStore::from_path(src_path) {
        Ok(store) => {
            let mut writer = BOMWriter::new();
            let mut ids: Vec<u32> = store.blocks.keys().copied().collect();
            ids.sort();

            // Reverse map var names by id
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

            let repacked_bytes = writer.build();
            if let Err(e) = fs::write(dst_path, repacked_bytes) {
                eprintln!("actool-car-repack: write error: {}", e);
                std::process::exit(1);
            }
            println!("Successfully repacked {} -> {}", src_path, dst_path);
        }
        Err(e) => {
            eprintln!("actool-car-repack: error reading BOM store: {}", e);
            std::process::exit(1);
        }
    }
}
