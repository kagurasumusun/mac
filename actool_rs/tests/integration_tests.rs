use actool_rs::appicons::{app_icon_entry_rank, AppIconEntry};
use actool_rs::autosafe::{auto_safe_compress, AlphaCharacteristic, ImageDomain, SafetyLevel};
use actool_rs::bom::BOMStore;
use actool_rs::bomwriter::BOMWriter;
use actool_rs::car::CARFile;
use actool_rs::carwriter::CARWriter;
use actool_rs::cbck::{encode_cbck, parse_cbck};
use actool_rs::compiler::{compile_catalogs, CompileOptions};
use actool_rs::dmp2mini::{decode_mini, v3_mini_color};
use actool_rs::facet_hash_lookup::FacetHashLookupTable;
use actool_rs::hybrid_compression::HybridCompressor;
use actool_rs::lzfse;
use actool_rs::media::{calculate_shannon_entropy, detect_media_type, select_optimal_compression, MediaType};
use actool_rs::model3d::{compress_normal_map_2channel, generate_mipmap_chain, PBRMaterialMap};
use actool_rs::packed::{atlas_name, build_link_tlv};
use actool_rs::planar_delta_lzfse::{delta_decode_plane, delta_encode_plane, planar_delta_decode, planar_delta_encode};
use actool_rs::quality_metrics::{compute_delta_e, compute_psnr, compute_ssim};
use actool_rs::ultrahd::{classify_resolution_tier, encode_ultrahd_tiled_cbck, UltraHDTier};
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

#[test]
fn test_dmp2mini_roundtrip() {
    let bgra = [10u8, 20u8, 30u8, 255u8];
    let dmp2 = v3_mini_color(4, 4, &bgra);
    let decoded = decode_mini(&dmp2, 4, 4, 4).expect("Decode dmp2 mini failed");

    assert_eq!(decoded.len(), 4 * 4 * 4);
    assert_eq!(&decoded[0..4], &bgra);
}

#[test]
fn test_facet_hash() {
    let hash = FacetHashLookupTable::compute_polynomial_hash("AppIcon");
    assert!(hash > 0);
}

#[test]
fn test_planar_delta_roundtrip() {
    let plane = vec![10u8, 12u8, 15u8, 20u8, 20u8, 25u8];
    let delta = delta_encode_plane(&plane);
    let decoded = delta_decode_plane(&delta);
    assert_eq!(plane, decoded);

    let bgra = vec![100u8; 16 * 4];
    let encoded = planar_delta_encode(&bgra, 4, 4);
    let decoded_bgra = planar_delta_decode(&encoded).expect("Planar delta decode failed");
    assert_eq!(bgra, decoded_bgra);
}

#[test]
fn test_quality_metrics() {
    let orig = vec![100u8; 300];
    let comp = vec![100u8; 300];

    let psnr = compute_psnr(&orig, &comp);
    assert!(psnr > 90.0);

    let delta_e = compute_delta_e(&orig, &comp);
    assert_eq!(delta_e, 0.0);

    let ssim = compute_ssim(&orig, &comp);
    assert!((ssim - 1.0).abs() < 1e-4);
}

#[test]
fn test_packed_helpers() {
    assert_eq!(atlas_name(true, false), "ZZZZPackedAsset-1.1.0-gamut0");
    let link = build_link_tlv(10, 20, 100, 100, 0);
    assert!(link.len() > 10);
}

#[test]
fn test_hybrid_compressor() {
    let compressor = HybridCompressor::default();
    let bgra = vec![200u8; 16 * 16 * 4];
    let compressed = compressor.compress_chunk(&bgra, 16, 16);
    assert!(!compressed.is_empty());
}

#[test]
fn test_3d_pbr_orm_and_normal_map() {
    let pbr = PBRMaterialMap::new("MetalGold", 32, 32);
    let orm_payload = pbr.compress_orm_payload();
    assert!(!orm_payload.is_empty());

    let rgb_normal = vec![128u8; 32 * 32 * 3];
    let compressed_normal = compress_normal_map_2channel(&rgb_normal, 32, 32);
    assert!(!compressed_normal.is_empty());

    let bgra = vec![200u8; 32 * 32 * 4];
    let mips = generate_mipmap_chain(&bgra, 32, 32);
    assert!(mips.len() >= 5);
    assert_eq!(mips[0].0, 32);
    assert_eq!(mips[1].0, 16);
    assert_eq!(mips[2].0, 8);
}

#[test]
fn test_ar_resource_group() {
    use actool_rs::arresource::{ARReferenceImageSpec, ARResourceGroup};

    let mut group = ARResourceGroup::new("ARObjects");
    group.add_image(ARReferenceImageSpec {
        name: "Poster.jpg".to_string(),
        physical_width_meters: 0.5,
        physical_height_meters: 0.75,
    });

    let json_str = group.serialize_ar_group();
    assert!(json_str.contains("Poster.jpg"));
    assert!(json_str.contains("0.5"));
}

#[test]
fn test_media_type_detection_and_compression() {
    let audio_mp3 = vec![0xFFu8; 1000];
    assert_eq!(detect_media_type("song.mp3", &audio_mp3), MediaType::AudioCompressed);
    let (comp_audio, strat_audio) = select_optimal_compression("song.mp3", &audio_mp3, 0, 0);
    assert_eq!(strat_audio, "raw_passthrough");
    assert_eq!(comp_audio.len(), audio_mp3.len());

    let pdf_bytes = b"%PDF-1.5 test pdf data with vector paths and text objects";
    assert_eq!(detect_media_type("doc.pdf", pdf_bytes), MediaType::Pdf);
    let (comp_pdf, strat_pdf) = select_optimal_compression("doc.pdf", pdf_bytes, 0, 0);
    assert_eq!(strat_pdf, "lzfse_vector_mesh");
    assert!(!comp_pdf.is_empty());

    let model3d = b"v 0.0 0.0 0.0\nv 1.0 1.0 1.0\nf 1 2 3";
    assert_eq!(detect_media_type("mesh.obj", model3d), MediaType::Model3D);

    let low_entropy = vec![0u8; 1000];
    let high_entropy: Vec<u8> = (0..1000).map(|i| (i * 37 % 256) as u8).collect();

    let e_low = calculate_shannon_entropy(&low_entropy);
    let e_high = calculate_shannon_entropy(&high_entropy);

    assert!(e_low < 1.0);
    assert!(e_high > 7.0);
}

#[test]
fn test_ultrahd_tiled_encoding() {
    assert_eq!(classify_resolution_tier(1024, 768), UltraHDTier::Standard);
    assert_eq!(classify_resolution_tier(3840, 2160), UltraHDTier::Resolution4K);
    assert_eq!(classify_resolution_tier(7680, 4320), UltraHDTier::Resolution8K);
    assert_eq!(classify_resolution_tier(15360, 8640), UltraHDTier::Resolution16K);

    let w = 4000u32;
    let h = 2200u32;
    let bgra = vec![128u8; (w * h * 4) as usize];

    let payload = encode_ultrahd_tiled_cbck(&bgra, w, h, 512, true);
    assert!(payload.starts_with(b"MLEC"));
}

#[test]
fn test_auto_safe_optimization_precision_domain() {
    let mut dirty_bgra = vec![0u8; 16 * 4];
    for px in dirty_bgra.chunks_exact_mut(4) {
        px[0] = 100;
        px[1] = 200;
        px[2] = 50;
        px[3] = 0;
    }

    // CustomShaderSafe -> Must preserve dirty alpha
    let (_comp, report) = auto_safe_compress(&dirty_bgra, 2, 2, "texture", SafetyLevel::CustomShaderSafe);
    assert_eq!(report.alpha_type, AlphaCharacteristic::DirtyAlpha);
    assert!(report.is_lossless);

    // Standard UI Image -> Safety check detects dirty alpha and applies clean alpha
    let (_comp2, report2) = auto_safe_compress(&dirty_bgra, 2, 2, "image", SafetyLevel::PerceptualSafe);
    assert_eq!(report2.alpha_type, AlphaCharacteristic::DirtyAlpha);

    // Monochrome image -> Lossless GA8 Normalization
    let mono_bgra = vec![128u8; 16 * 4];
    let (_comp3, report3) = auto_safe_compress(&mono_bgra, 2, 2, "image", SafetyLevel::AutoDomainDetect);
    assert_eq!(report3.detected_domain, ImageDomain::GrayscaleUI);
    assert!(report3.is_monochrome);
}
