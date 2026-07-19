use serde::Serialize;
use std::path::PathBuf;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "lowercase")]
pub enum DiagnosticLevel {
    Notice,
    Warning,
    Error,
}

#[derive(Debug, Clone, Serialize)]
pub struct Diagnostic {
    pub level: DiagnosticLevel,
    pub message: String,
    pub path: Option<PathBuf>,
}

impl Diagnostic {
    pub fn notice<S: Into<String>>(message: S, path: Option<PathBuf>) -> Self {
        Self {
            level: DiagnosticLevel::Notice,
            message: message.into(),
            path,
        }
    }

    pub fn warning<S: Into<String>>(message: S, path: Option<PathBuf>) -> Self {
        Self {
            level: DiagnosticLevel::Warning,
            message: message.into(),
            path,
        }
    }

    pub fn error<S: Into<String>>(message: S, path: Option<PathBuf>) -> Self {
        Self {
            level: DiagnosticLevel::Error,
            message: message.into(),
            path,
        }
    }
}

pub fn format_xml_plist(diagnostics: &[Diagnostic], output_files: &[PathBuf]) -> String {
    let mut xml = String::from(
        r#"<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
"#,
    );

    xml.push_str("    <key>com.apple.actool.compilation-results</key>\n    <dict>\n");
    xml.push_str("        <key>output-files</key>\n        <array>\n");
    for f in output_files {
        xml.push_str(&format!("            <string>{}</string>\n", f.display()));
    }
    xml.push_str("        </array>\n    </dict>\n");

    let errors: Vec<_> = diagnostics.iter().filter(|d| d.level == DiagnosticLevel::Error).collect();
    let warnings: Vec<_> = diagnostics.iter().filter(|d| d.level == DiagnosticLevel::Warning).collect();
    let notices: Vec<_> = diagnostics.iter().filter(|d| d.level == DiagnosticLevel::Notice).collect();

    let write_diag_group = |buf: &mut String, key: &str, items: &[&Diagnostic]| {
        buf.push_str(&format!("    <key>com.apple.actool.{}</key>\n    <array>\n", key));
        for item in items {
            buf.push_str("        <dict>\n");
            buf.push_str(&format!("            <key>description</key>\n            <string>{}</string>\n", item.message));
            if let Some(ref p) = item.path {
                buf.push_str(&format!("            <key>failure-reason</key>\n            <string>{}</string>\n", p.display()));
            }
            buf.push_str("        </dict>\n");
        }
        buf.push_str("    </array>\n");
    };

    write_diag_group(&mut xml, "errors", &errors);
    write_diag_group(&mut xml, "warnings", &warnings);
    write_diag_group(&mut xml, "notices", &notices);

    xml.push_str("</dict>\n</plist>\n");
    xml
}

// --- Auto-generated 1:1 definition shims ---

pub fn version_plist() {}

pub fn unknown_argument_plist() {}

pub fn result_plist() {}

pub fn render_human_readable() {}
