use actool_rs::bom::BOMStore;
use actool_rs::car::CARFile;
use std::env;

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        eprintln!("Usage: actool-car-info <path_to_car>");
        std::process::exit(1);
    }

    let path = &args[1];
    match BOMStore::from_path(path) {
        Ok(store) => match CARFile::from_bom_store(&store) {
            Ok(car) => {
                println!("CAR File Info for {}", path);
                println!("  Byte Order: {}", car.header.byte_order);
                println!("  CoreUI Version: {}", car.header.core_ui_version);
                println!("  Storage Version: {}", car.header.storage_version);
                println!("  Rendition Count: {}", car.header.rendition_count);
                println!("  Main Version: {}", car.header.main_version);
                println!("  Identifier: {}", car.header.identifier);
                println!("  Allocated Blocks: {}", car.block_count);
                println!("  Key Attributes: {:?}", car.key_format.attributes);
            }
            Err(e) => {
                eprintln!("actool-car-info: error parsing CAR header: {}", e);
                std::process::exit(1);
            }
        },
        Err(e) => {
            eprintln!("actool-car-info: error reading BOM store: {}", e);
            std::process::exit(1);
        }
    }
}
