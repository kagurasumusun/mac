use actool_rs::appicons::{app_icon_entry_rank, AppIconEntry};
use actool_rs::bom::BOMStore;
use actool_rs::bomwriter::BOMWriter;
use actool_rs::car::CARFile;
use actool_rs::carwriter::CARWriter;
use actool_rs::cbck::{encode_cbck, parse_cbck};
use actool_rs::compiler::{compile_catalogs, CompileOptions};
use actool_rs::lzfse;
use std::fs;
use tempfile::tempdir;

#[test]
fn test_bom_roundtrip() {
    let mut writer = BOMWriter::new();
    let id1 = writer.add_block(b"Hello Block 1".to_vec(), Some("CARHEADER".to_string()));
    let id2 = writer.add_block(b"Hello Block 2".to_vec(), Some("KEYFORMAT".to_string()));

    let bytes = writer.build();
    let store = BOMStore::from_bytes(bytes).expect("BOMStore parse failed");

    assert_eq!(store.block_data(id1).unwrap(), b"Hello Block 1");
    assert_eq!(store.block_data(id2).unwrap(), b"Hello Block 2");
    assert_eq!(store.named_block_data("CARHEADER").unwrap(), b"Hello Block 1");
    assert_eq!(store.named_block_data("KEYFORMAT").unwrap(), b"Hello Block 2");
}

#[test]
fn test_lzfse_roundtrip() {
    let original = vec![0xABu8; 10000];
    let compressed = lzfse::compress(&original);
    let decompressed = lzfse::decompress(&compressed).expect("Decompression failed");
    assert_eq!(original, decompressed);
}

#[test]
fn test_cbck_roundtrip() {
    let w = 64u32;
    let h = 64u32;
    let bgra = vec![128u8; (w * h * 4) as usize];

    let payload = encode_cbck(&bgra, w, h, 4, true);
    let parsed = parse_cbck(&payload).expect("CBCK parse failed");

    assert_eq!(parsed.mode, 3);
    assert_eq!(parsed.codec, 4);
    assert!(!parsed.chunks.is_empty());
}

#[test]
fn test_csi_and_car_writer() {
    let mut car_writer = CARWriter::new("iphoneos");
    let bgra = vec![255u8; 32 * 32 * 4];

    car_writer.add_png_image("AppIcon", &bgra, 32, 32, 2, 1, 1);
    let car_bytes = car_writer.build();

    let store = BOMStore::from_bytes(car_bytes).expect("BOMStore parse failed");
    let car = CARFile::from_bom_store(&store).expect("CARFile parse failed");

    assert_eq!(car.header.byte_order, "big");
    assert_eq!(car.header.core_ui_version, 975);
    assert_eq!(car.header.rendition_count, 1);
}

#[test]
fn test_appicon_ranking() {
    let entry = AppIconEntry {
        idiom: Some("iphone".to_string()),
        size: Some("60x60".to_string()),
        scale: Some("2x".to_string()),
        filename: Some("icon60x60@2x.png".to_string()),
        platform: Some("iphoneos".to_string()),
    };

    let result = app_icon_entry_rank(&entry, "iphoneos");
    assert!(result.is_some());
    let (score, w, h) = result.unwrap();
    assert!(score > 0);
    assert_eq!(w, 120);
    assert_eq!(h, 120);
}

#[test]
fn test_compiler_flow() {
    let dir = tempdir().unwrap();
    let cat_dir = dir.path().join("App.xcassets");
    let icon_dir = cat_dir.join("AppIcon.appiconset");
    fs::create_dir_all(&icon_dir).unwrap();

    let contents_json = r#"{
      "images": [
        {"filename": "icon.png", "idiom": "iphone", "scale": "2x", "size": "60x60"}
      ],
      "info": {"author": "xcode", "version": 1}
    }"#;

    fs::write(icon_dir.join("Contents.json"), contents_json).unwrap();

    // Create 120x120 solid red image
    let img = image::RgbaImage::from_pixel(120, 120, image::Rgba([255, 0, 0, 255]));
    img.save(icon_dir.join("icon.png")).unwrap();

    let out_dir = dir.path().join("out");

    let options = CompileOptions {
        inputs: vec![cat_dir],
        output_dir: out_dir.clone(),
        platform: "iphoneos".to_string(),
        minimum_deployment_target: "15.0".to_string(),
        app_icon: None,
        optimize: Some("smart".to_string()),
        export_dependency_info: None,
        output_format: "human".to_string(),
    };

    let result = compile_catalogs(options).expect("Compilation failed");
    assert!(!result.output_files.is_empty());

    let car_path = out_dir.join("Assets.car");
    assert!(car_path.is_file());

    let store = BOMStore::from_path(&car_path).expect("Read Assets.car failed");
    assert!(store.variables.contains_key("CARHEADER"));
}
