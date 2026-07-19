use crate::compiler::{compile_catalogs, CompileOptions};
use std::env;
use std::path::PathBuf;
use std::process;

pub fn main_cli() {
    let args: Vec<String> = env::args().collect();

    let mut compile_dir = None;
    let mut inputs = Vec::new();
    let mut platform = "iphoneos".to_string();
    let mut target = "15.0".to_string();
    let mut app_icon = None;
    let mut optimize = None;
    let mut export_dep = None;
    let mut output_format = "human".to_string();

    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--compile" => {
                if i + 1 < args.len() {
                    compile_dir = Some(PathBuf::from(&args[i + 1]));
                    i += 1;
                }
            }
            "--platform" => {
                if i + 1 < args.len() {
                    platform = args[i + 1].clone();
                    i += 1;
                }
            }
            "--minimum-deployment-target" => {
                if i + 1 < args.len() {
                    target = args[i + 1].clone();
                    i += 1;
                }
            }
            "--app-icon" => {
                if i + 1 < args.len() {
                    app_icon = Some(args[i + 1].clone());
                    i += 1;
                }
            }
            "--optimize" => {
                if i + 1 < args.len() {
                    optimize = Some(args[i + 1].clone());
                    i += 1;
                }
            }
            "--export-dependency-info" => {
                if i + 1 < args.len() {
                    export_dep = Some(PathBuf::from(&args[i + 1]));
                    i += 1;
                }
            }
            "--output-format" => {
                if i + 1 < args.len() {
                    output_format = args[i + 1].clone();
                    i += 1;
                }
            }
            "--version" => {
                println!("actool-rs version 0.1.0");
                process::exit(0);
            }
            arg if !arg.starts_with('-') => {
                inputs.push(PathBuf::from(arg));
            }
            _ => {}
        }
        i += 1;
    }

    if let Some(out_dir) = compile_dir {
        if inputs.is_empty() {
            eprintln!("actool-rs: error: no input asset catalogs provided.");
            process::exit(1);
        }

        let options = CompileOptions {
            inputs,
            output_dir: out_dir,
            platform,
            minimum_deployment_target: target,
            app_icon,
            optimize,
            export_dependency_info: export_dep,
            output_format,
        };

        match compile_catalogs(options) {
            Ok(result) => {
                for diag in &result.diagnostics {
                    println!("[{:?}] {}", diag.level, diag.message);
                }
                for f in &result.output_files {
                    println!("{}", f.display());
                }
            }
            Err(err) => {
                eprintln!("actool-rs: error: {}", err);
                process::exit(1);
            }
        }
    } else {
        println!("actool-rs version 0.1.0");
        println!("Usage: actool-rs [catalogs...] --compile <out_dir> --platform <platform>");
    }
}
