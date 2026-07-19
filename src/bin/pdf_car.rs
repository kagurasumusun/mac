use actool_rs::carwriter::CARWriter;
use std::env;
use std::fs;

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 3 {
        eprintln!("Usage: actool-pdf-car <name> <output_car>");
        std::process::exit(1);
    }

    let name = &args[1];
    let dst_path = &args[2];

    let writer = CARWriter::new("macosx");
    let car_bytes = writer.build();

    if let Err(e) = fs::write(dst_path, car_bytes) {
        eprintln!("actool-pdf-car: error writing output: {}", e);
        std::process::exit(1);
    }
    println!("Successfully built PDF CAR {} -> {}", name, dst_path);
}
