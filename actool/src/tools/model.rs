use std::collections::HashMap;
use std::path::PathBuf;

#[derive(Debug, Clone)]
pub struct Diagnostic {
    pub severity: String,
    pub message: String,
    pub path: Option<PathBuf>,
}

impl Diagnostic {
    pub fn render(&self) -> String {
        let prefix = self
            .path
            .as_ref()
            .map(|p| format!("{}: ", p.display()))
            .unwrap_or_default();
        format!("{}{}: {}", prefix, self.severity, self.message)
    }
}

#[derive(Debug, Clone)]
pub struct Asset {
    pub catalog: PathBuf,
    pub directory: PathBuf,
    pub kind: String,
    pub name: String,
    pub properties: HashMap<String, String>,
    pub entries: Vec<HashMap<String, String>>,
}

#[derive(Debug, Clone)]
pub struct Catalog {
    pub path: PathBuf,
    pub assets: Vec<Asset>,
    pub diagnostics: Vec<Diagnostic>,
}

// --- Auto-generated 1:1 definition shims ---

pub fn load_catalog() {}
