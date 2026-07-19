use crate::lzfse;
use serde_json::json;
use std::path::Path;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MediaType {
    Image,
    AudioCompressed,   // mp3, m4a, aac (already compressed, pass-through)
    AudioUncompressed, // wav, caf (compress with LZFSE)
    Video,             // mp4, mov, m4v (pass-through)
    Pdf,               // pdf vector document
    VectorSvg,         // svg
    Model3D,           // usdz, obj, gltf, reality
    JsonLottie,        // json, lottie
    BinaryData,
}

pub fn calculate_shannon_entropy(data: &[u8]) -> f64 {
    if data.is_empty() {
        return 0.0;
    }

    let mut counts = [0u64; 256];
    for &b in data {
        counts[b as usize] += 1;
    }

    let total = data.len() as f64;
    let mut entropy = 0.0f64;

    for &count in &counts {
        if count > 0 {
            let p = (count as f64) / total;
            entropy -= p * p.log2();
        }
    }

    entropy
}

pub fn detect_media_type(filename: &str, data: &[u8]) -> MediaType {
    let path = Path::new(filename);
    let ext = path
        .extension()
        .unwrap_or_default()
        .to_string_lossy()
        .to_lowercase();

    match ext.as_str() {
        "png" | "jpg" | "jpeg" | "heic" | "heif" | "bmp" | "tiff" => MediaType::Image,
        "mp3" | "m4a" | "aac" => MediaType::AudioCompressed,
        "wav" | "caf" | "aiff" => MediaType::AudioUncompressed,
        "mp4" | "mov" | "m4v" => MediaType::Video,
        "pdf" => MediaType::Pdf,
        "svg" => MediaType::VectorSvg,
        "usdz" | "obj" | "gltf" | "glb" | "reality" | "scn" => MediaType::Model3D,
        "json" | "lottie" | "xcstrings" => MediaType::JsonLottie,
        _ => {
            // Check byte signature magic numbers
            if data.starts_with(b"\x89PNG") || data.starts_with(b"\xFF\xD8\xFF") {
                MediaType::Image
            } else if data.starts_with(b"%PDF") {
                MediaType::Pdf
            } else if data.starts_with(b"PK\x03\x04") {
                // USDZ or Zip container
                MediaType::Model3D
            } else {
                MediaType::BinaryData
            }
        }
    }
}

pub fn select_optimal_compression(
    filename: &str,
    data: &[u8],
    width: u32,
    height: u32,
) -> (Vec<u8>, &'static str) {
    let media_type = detect_media_type(filename, data);
    let entropy = calculate_shannon_entropy(data);

    match media_type {
        MediaType::AudioCompressed | MediaType::Video => {
            // Audio/Video files are already H.264/AAC compressed -> store raw pass-through to avoid CPU waste or expansion
            (data.to_vec(), "raw_passthrough")
        }
        MediaType::Pdf | MediaType::VectorSvg | MediaType::JsonLottie | MediaType::Model3D => {
            // Highly compressible text/mesh/vector/3D geometry -> heavy LZFSE compression
            let compressed = lzfse::compress(data);
            (compressed, "lzfse_vector_mesh")
        }
        MediaType::AudioUncompressed | MediaType::BinaryData => {
            if entropy > 7.9 {
                // High entropy payload -> raw pass-through
                (data.to_vec(), "raw_high_entropy")
            } else {
                let compressed = lzfse::compress(data);
                (compressed, "lzfse_binary")
            }
        }
        MediaType::Image => {
            let row_bytes = width * 4;
            if row_bytes * height > 0x155555 {
                let compressed = crate::cbck::encode_cbck(data, width, height, 4, true);
                (compressed, "cbck_mlec_chunks")
            } else {
                let compressed = lzfse::compress(data);
                (compressed, "lzfse_image")
            }
        }
    }
}

pub fn get_media_optimization_report(filename: &str, data: &[u8]) -> serde_json::Value {
    let media_type = detect_media_type(filename, data);
    let entropy = calculate_shannon_entropy(data);
    let (compressed, strategy) = select_optimal_compression(filename, data, 100, 100);

    json!({
        "filename": filename,
        "original_size": data.len(),
        "compressed_size": compressed.len(),
        "entropy_bits_per_byte": entropy,
        "media_type": format!("{:?}", media_type),
        "chosen_strategy": strategy,
        "savings_ratio": if data.is_empty() { 0.0 } else { 1.0 - (compressed.len() as f64 / data.len() as f64) }
    })
}
