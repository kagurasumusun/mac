use serde::Deserialize;
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Deserialize)]
pub struct ContentsJsonInfo {
    pub version: u32,
    pub author: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ContentsJsonImageEntry {
    pub idiom: Option<String>,
    pub size: Option<String>,
    pub scale: Option<String>,
    pub filename: Option<String>,
    pub platform: Option<String>,
    pub role: Option<String>,
    pub subtype: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ContentsJson {
    pub info: Option<ContentsJsonInfo>,
    pub images: Option<Vec<ContentsJsonImageEntry>>,
}

#[derive(Debug, Clone)]
pub struct Asset {
    pub name: String,
    pub kind: String,
    pub directory: PathBuf,
    pub entries: Vec<ContentsJsonImageEntry>,
}

pub struct Catalog {
    pub root: PathBuf,
    pub assets: Vec<Asset>,
}

pub fn load_catalog<P: AsRef<Path>>(root_path: P) -> Result<Catalog, String> {
    let root = root_path.as_ref().to_path_buf();
    if !root.is_dir() {
        return Err(format!("Catalog path is not a directory: {:?}", root));
    }

    let mut assets = Vec::new();
    scan_dir(&root, &mut assets);

    Ok(Catalog { root, assets })
}

fn scan_dir(dir: &Path, assets: &mut Vec<Asset>) {
    let entries = match fs::read_dir(dir) {
        Ok(e) => e,
        Err(_) => return,
    };

    for entry in entries.flatten() {
        let path = entry.path();
        if !path.is_dir() {
            continue;
        }

        let name = path.file_stem().unwrap_or_default().to_string_lossy().to_string();
        let extension = path.extension().unwrap_or_default().to_string_lossy().to_string();

        let kind = match extension.as_str() {
            "imageset" => "image",
            "appiconset" => "app-icon",
            "colorset" => "color",
            "symbolset" => "symbol",
            "dataset" => "data",
            "imagestack" => "image-stack",
            "complicationset" => "complication",
            _ => "",
        };

        if !kind.is_empty() {
            let contents_file = path.join("Contents.json");
            let mut image_entries = Vec::new();

            if contents_file.is_file() {
                if let Ok(data) = fs::read(&contents_file) {
                    if let Ok(json) = serde_json::from_slice::<ContentsJson>(&data) {
                        if let Some(imgs) = json.images {
                            image_entries = imgs;
                        }
                    }
                }
            }

            assets.push(Asset {
                name,
                kind: kind.to_string(),
                directory: path.clone(),
                entries: image_entries,
            });
        } else {
            // Recursively check subdirectories
            scan_dir(&path, assets);
        }
    }
}

/// Safely resolve relative file within base directory preventing directory traversal
pub fn safe_resolve_file(base_dir: &Path, relative: &str) -> Option<PathBuf> {
    let base = base_dir.canonicalize().ok()?;
    let target = base_dir.join(relative);

    // Normalize path components to check parent boundary
    let canonical = target.canonicalize().ok()?;
    if canonical.starts_with(&base) && canonical.is_file() {
        Some(canonical)
    } else {
        None
    }
}
