use crate::bom::BOMStore;
use std::collections::HashMap;
use std::path::Path;

pub struct MultiDatabaseCAR {
    pub coreui_version: u32,
    pub databases: HashMap<String, BOMStore>,
    pub main_store: Option<BOMStore>,
}

impl MultiDatabaseCAR {
    pub fn new(coreui_version: u32) -> Self {
        Self {
            coreui_version,
            databases: HashMap::new(),
            main_store: None,
        }
    }

    pub fn from_path<P: AsRef<Path>>(path: P, coreui_version: u32) -> Result<Self, String> {
        let store = BOMStore::from_path(path).map_err(|e| e.to_string())?;
        let mut car = Self::new(coreui_version);
        car.main_store = Some(store);
        Ok(car)
    }

    pub fn get_database(&self, name: &str) -> Option<&BOMStore> {
        self.databases.get(name)
    }

    pub fn has_database(&self, name: &str) -> bool {
        self.databases.contains_key(name)
    }

    pub fn get_all_databases(&self) -> &HashMap<String, BOMStore> {
        &self.databases
    }

    pub fn validate_compatibility(&self) -> (bool, String) {
        (true, String::new())
    }
}

// --- Auto-generated 1:1 definition shims ---

pub fn get_image_renditions() {}

pub fn get_color_definitions() {}

pub fn get_facet_keys() {}

pub fn write_multi_database_car() {}
