use crate::editor::CAREditor;
use std::fs;
use std::path::Path;

pub fn mount_car_to_directory<P: AsRef<Path>>(car_path: P, mount_dir: P) -> Result<usize, String> {
    let editor = CAREditor::load(&car_path)?;
    fs::create_dir_all(&mount_dir).map_err(|e| e.to_string())?;

    let mut extracted_count = 0;
    for (name, rend) in &editor.renditions {
        let file_path = mount_dir.as_ref().join(format!("{}.png", name));
        // Save extracted raw CSI rendition payload
        let _ = fs::write(file_path, &rend.csi_bytes);
        extracted_count += 1;
    }

    let manifest_path = mount_dir.as_ref().join("mount_manifest.json");
    let _ = fs::write(
        manifest_path,
        serde_json::json!({
            "mounted_car": car_path.as_ref().display().to_string(),
            "asset_count": extracted_count,
            "read_write_enabled": true
        })
        .to_string(),
    );

    Ok(extracted_count)
}

pub fn sync_directory_to_car<P: AsRef<Path>>(mount_dir: P, output_car_path: P) -> Result<(), String> {
    let mut editor = CAREditor::new("iphoneos");

    let entries = fs::read_dir(&mount_dir).map_err(|e| e.to_string())?;
    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_file() && path.extension().and_then(|s| s.to_str()) == Some("png") {
            let stem = path.file_stem().unwrap_or_default().to_string_lossy();
            if let Ok(bytes) = fs::read(&path) {
                if bytes.starts_with(b"ISTC") || bytes.starts_with(b"CSIR") {
                    // Direct pre-formatted CSI payload
                    editor.renditions.insert(stem.to_string(), crate::carwriter::AssetRendition {
                        name: stem.to_string(),
                        filename: format!("{}.png", stem),
                        csi_bytes: bytes,
                        identifier: (editor.renditions.len() + 1) as u16,
                        idiom: 0,
                        scale: 1,
                        gamut: 0,
                        appearance: 0,
                        width: 100,
                        height: 100,
                    });
                } else {
                    editor.add_or_replace_image(&stem, &bytes, 100, 100);
                }
            }
        }
    }

    editor.save(output_car_path)
}
