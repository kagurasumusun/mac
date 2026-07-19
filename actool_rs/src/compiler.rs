use crate::appicons::{app_icon_entry_rank, AppIconEntry};
use crate::carwriter::CARWriter;
use crate::catalog::{load_catalog, safe_resolve_file};
use crate::diagnostics::{format_xml_plist, Diagnostic};
use image::GenericImageView;
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
            if asset.kind == "app-icon" {
                // If app_icon option is provided, filter by asset name
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
                        let bgra_bytes = img.to_rgba8().into_raw();

                        car_writer.add_png_image(
                            &asset.name,
                            &bgra_bytes,
                            w,
                            h,
                            1,
                            1,
                            rendition_id_counter,
                        );
                        rendition_id_counter += 1;

                        diagnostics.push(Diagnostic::notice(
                            format!("Compiled AppIcon: {}", asset.name),
                            Some(source_path),
                        ));
                    }
                }
            } else if asset.kind == "image" {
                for entry in &asset.entries {
                    if let Some(ref fname) = entry.filename {
                        if let Some(source_path) = safe_resolve_file(&asset.directory, fname) {
                            if let Ok(img) = image::open(&source_path) {
                                let (w, h) = img.dimensions();
                                let bgra_bytes = img.to_rgba8().into_raw();

                                let scale = entry
                                    .scale
                                    .as_deref()
                                    .and_then(|s| s.chars().next())
                                    .and_then(|c| c.to_digit(10))
                                    .unwrap_or(1) as u16;

                                car_writer.add_png_image(
                                    &asset.name,
                                    &bgra_bytes,
                                    w,
                                    h,
                                    scale,
                                    1,
                                    rendition_id_counter,
                                );
                                rendition_id_counter += 1;
                            }
                        }
                    }
                }
            }
        }
    }

    // Write Assets.car
    let car_bytes = car_writer.build();
    let car_path = options.output_dir.join("Assets.car");
    fs::write(&car_path, &car_bytes)
        .map_err(|e| format!("Failed to write Assets.car: {}", e))?;
    output_files.push(car_path.clone());

    // Write export dependency info if requested
    if let Some(ref dep_info_path) = options.export_dependency_info {
        let xml_content = format_xml_plist(&diagnostics, &output_files);
        let _ = fs::write(dep_info_path, xml_content);
    }

    Ok(CompileResult {
        diagnostics,
        output_files,
    })
}
