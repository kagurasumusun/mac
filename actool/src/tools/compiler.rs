use crate::appicons::{app_icon_entry_rank, AppIconEntry};
use crate::carwriter::CARWriter;
use crate::catalog::{load_catalog, safe_resolve_file, Asset};
use crate::diagnostics::{format_xml_plist, Diagnostic};

use image::GenericImageView;
use serde_json::{json, Value};
use std::fs;
use std::path::PathBuf;

#[derive(Debug, Clone)]
pub struct CompileOptions {
    pub inputs: Vec<PathBuf>,
    pub output_dir: PathBuf,
    pub platform: String,
    pub minimum_deployment_target: String,
    pub app_icon: Option<String>,
    pub optimize: Option<String>,
    pub export_dependency_info: Option<PathBuf>,
    pub output_format: String,
}

#[derive(Debug)]
pub struct CompileResult {
    pub diagnostics: Vec<Diagnostic>,
    pub output_files: Vec<PathBuf>,
}

pub fn color_component(val: f32) -> u8 {
    (val.clamp(0.0, 1.0) * 255.0).round() as u8
}

pub fn layer_depth(asset: &Asset) -> usize {
    asset.directory.components().count()
}

pub fn appearance_for(entry_appearance: Option<&str>) -> u16 {
    match entry_appearance {
        Some("dark") | Some("luminosity") => 1,
        Some("tinted") => 2,
        _ => 0,
    }
}

pub fn partial_info(platform: &str, target: &str) -> Value {
    json!({
        "com.apple.actool.compilation-results": {
            "platform": platform,
            "minimum-deployment-target": target,
            "tool": "actool-rs"
        }
    })
}

pub fn resolve_image_stack_layers(asset: &Asset, assets: &[Asset]) -> Vec<PathBuf> {
    let mut layers = Vec::new();
    for entry in &asset.entries {
        if let Some(ref filename) = entry.filename {
            let layer_dir = asset.directory.join(filename);
            for candidate in assets {
                if candidate.kind == "image-stack-layer" && candidate.directory == layer_dir {
                    layers.push(candidate.directory.clone());
                }
            }
        }
    }
    layers
}

pub fn compile_brand_assets(
    inputs: &[PathBuf],
    options: &CompileOptions,
) -> Result<Vec<PathBuf>, String> {
    let mut car_writer = CARWriter::new(&options.platform);
    let mut counter = 100u16;

    for path in inputs {
        if let Ok(cat) = load_catalog(path) {
            for asset in &cat.assets {
                if asset.kind == "image" || asset.kind == "app-icon" {
                    car_writer.add_color(&asset.name, 0.5, 0.5, 0.5, 1.0, counter);
                    counter += 1;
                }
            }
        }
    }

    let bytes = car_writer.build();
    let car_path = options.output_dir.join("BrandAssets.car");
    fs::write(&car_path, &bytes).map_err(|e| e.to_string())?;
    Ok(vec![car_path])
}

pub fn compile_catalogs(options: CompileOptions) -> Result<CompileResult, String> {
    let mut diagnostics = Vec::new();
    let mut output_files = Vec::new();

    fs::create_dir_all(&options.output_dir)
        .map_err(|e| format!("Failed to create output directory: {}", e))?;

    let mut car_writer = CARWriter::new(&options.platform);
    let mut rendition_id_counter = 1u16;

    for input_path in &options.inputs {
        let catalog = match load_catalog(input_path) {
            Ok(c) => c,
            Err(err) => {
                diagnostics.push(Diagnostic::error(err.clone(), Some(input_path.clone())));
                continue;
            }
        };

        for asset in &catalog.assets {
            match asset.kind.as_str() {
                "app-icon" => {
                    if let Some(ref icon_name) = options.app_icon {
                        if icon_name != &asset.name {
                            continue;
                        }
                    }

                    let mut best_candidate: Option<(u32, u32, PathBuf)> = None;
                    let mut highest_rank = -1;

                    for entry in &asset.entries {
                        let app_entry = AppIconEntry {
                            idiom: entry.idiom.clone(),
                            size: entry.size.clone(),
                            scale: entry.scale.clone(),
                            filename: entry.filename.clone(),
                            platform: entry.platform.clone(),
                        };

                        if let Some((rank, req_w, req_h)) =
                            app_icon_entry_rank(&app_entry, &options.platform)
                        {
                            if let Some(ref fname) = entry.filename {
                                if let Some(resolved_path) =
                                    safe_resolve_file(&asset.directory, fname)
                                {
                                    if rank > highest_rank {
                                        highest_rank = rank;
                                        best_candidate = Some((req_w, req_h, resolved_path));
                                    }
                                }
                            }
                        }
                    }

                    if let Some((_req_w, _req_h, source_path)) = best_candidate {
                        if let Ok(img) = image::open(&source_path) {
                            let (w, h) = img.dimensions();
                            let mut bgra_bytes = img.to_rgba8().into_raw();
                            for px in bgra_bytes.chunks_exact_mut(4) {
                                px.swap(0, 2);
                            }

                            let csi_bytes = crate::csi::make_adaptive_csi(
                                &bgra_bytes,
                                w,
                                h,
                                &asset.name,
                                1,
                                options.optimize.as_deref(),
                            );

                            car_writer.add_rendition(crate::carwriter::AssetRendition {
                                name: asset.name.clone(),
                                filename: format!("{}.png", asset.name),
                                csi_bytes,
                                identifier: rendition_id_counter,
                                idiom: 0,
                                scale: 1,
                                gamut: 0,
                                appearance: 0,
                                width: w,
                                height: h,
                            });
                            rendition_id_counter += 1;

                            diagnostics.push(Diagnostic::notice(
                                format!("Compiled AppIcon: {}", asset.name),
                                Some(source_path),
                            ));
                        }
                    }
                }
                "image" => {
                    for entry in &asset.entries {
                        if let Some(ref fname) = entry.filename {
                            if let Some(source_path) = safe_resolve_file(&asset.directory, fname) {
                                if let Ok(img) = image::open(&source_path) {
                                    let (w, h) = img.dimensions();
                                    let mut bgra_bytes = img.to_rgba8().into_raw();
                                    for px in bgra_bytes.chunks_exact_mut(4) {
                                        px.swap(0, 2);
                                    }

                                    let scale = entry
                                        .scale
                                        .as_deref()
                                        .and_then(|s| s.chars().next())
                                        .and_then(|c| c.to_digit(10))
                                        .unwrap_or(1) as u16;

                                    let csi_bytes = crate::csi::make_adaptive_csi(
                                        &bgra_bytes,
                                        w,
                                        h,
                                        fname,
                                        scale as u32,
                                        options.optimize.as_deref(),
                                    );

                                    car_writer.add_rendition(crate::carwriter::AssetRendition {
                                        name: asset.name.clone(),
                                        filename: fname.clone(),
                                        csi_bytes,
                                        identifier: rendition_id_counter,
                                        idiom: 0,
                                        scale,
                                        gamut: 0,
                                        appearance: 0,
                                        width: w,
                                        height: h,
                                    });
                                    rendition_id_counter += 1;
                                }
                            }
                        }
                    }
                }
                "color" => {
                    car_writer.add_color(&asset.name, 1.0, 1.0, 1.0, 1.0, rendition_id_counter);
                    rendition_id_counter += 1;
                }
                "data" => {
                    for entry in &asset.entries {
                        if let Some(ref fname) = entry.filename {
                            if let Some(source_path) = safe_resolve_file(&asset.directory, fname) {
                                if let Ok(data_bytes) = fs::read(&source_path) {
                                    let rendition = if options.optimize.as_deref() == Some("experimental-nonimage") {
                                        let opt_res = crate::nonimage_optimizer::optimize_non_image_asset(fname, &data_bytes);
                                        crate::carwriter::data_rendition(&asset.name, &opt_res.payload)
                                    } else {
                                        crate::carwriter::data_rendition(&asset.name, &data_bytes)
                                    };

                                    car_writer.add_rendition(rendition);
                                    rendition_id_counter += 1;
                                }
                            }
                        }
                    }
                }
                _ => {}
            }
        }
    }

    // Apply Atlas packing post-processing (pack eligible 1x universal assets into ZZZZPackedAsset)
    car_writer.renditions = crate::packed::pack_renditions(car_writer.renditions);

    let car_bytes = car_writer.build();
    let car_path = options.output_dir.join("Assets.car");
    fs::write(&car_path, &car_bytes)
        .map_err(|e| format!("Failed to write Assets.car: {}", e))?;
    output_files.push(car_path.clone());

    if let Some(ref dep_info_path) = options.export_dependency_info {
        let xml_content = format_xml_plist(&diagnostics, &output_files);
        let _ = fs::write(dep_info_path, xml_content);
    }

    Ok(CompileResult {
        diagnostics,
        output_files,
    })
}
