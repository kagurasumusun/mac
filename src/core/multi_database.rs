use crate::bom::BOMStore;
use std::collections::HashMap;
use std::path::Path;

pub struct MultiDatabaseCAR {
    pub coreui_version: u32,
    pub databases: HashMap<String, BOMStore>,
    pub main_store: Option<BOMStore>,
    pub database_names: Vec<String>,
}

impl MultiDatabaseCAR {
    pub fn new(coreui_version: u32) -> Self {
        let mut db_names = Vec::new();
        if coreui_version >= 700 {
            db_names.extend(vec![
                "imagedb".to_string(),
                "colordb".to_string(),
                "fontdb".to_string(),
                "fontsizedb".to_string(),
                "appearancedb".to_string(),
                "facetKeysdb".to_string(),
                "bitmapKeydb".to_string(),
            ]);
            if coreui_version >= 850 {
                db_names.push("zcbezeldb".to_string());
                db_names.push("zcglyphdb".to_string());
            }
        }

        Self {
            coreui_version,
            databases: HashMap::new(),
            main_store: None,
            database_names: db_names,
        }
    }

    pub fn from_path<P: AsRef<Path>>(path: P, coreui_version: u32) -> Result<Self, String> {
        let store = BOMStore::from_path(&path).map_err(|e| e.to_string())?;
        let mut car = Self::new(coreui_version);

        for name in &car.database_names {
            if let Some(parent) = path.as_ref().parent() {
                let stem = path.as_ref().file_stem().unwrap_or_default().to_string_lossy();
                let ext = path.as_ref().extension().unwrap_or_default().to_string_lossy();
                let db_path = parent.join(format!("{}_{}.{}", stem, name, ext));
                if db_path.exists() {
                    if let Ok(db_store) = BOMStore::from_path(db_path) {
                        car.databases.insert(name.clone(), db_store);
                    }
                }
            }
        }

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

    pub fn get_image_renditions(&self) -> Vec<Vec<u8>> {
        let mut rends = Vec::new();
        let target_store = self.get_database("imagedb").or(self.main_store.as_ref());
        if let Some(store) = target_store {
            if let Ok(data) = store.named_block_data("RENDITIONS") {
                rends.push(data.to_vec());
            }
        }
        rends
    }

    pub fn get_color_definitions(&self) -> HashMap<String, Vec<u8>> {
        let mut colors = HashMap::new();
        let target_store = self.get_database("colordb").or(self.main_store.as_ref());
        if let Some(store) = target_store {
            if let Ok(data) = store.named_block_data("COLORDEFINITIONS") {
                colors.insert("colordb".to_string(), data.to_vec());
            }
        }
        colors
    }

    pub fn get_facet_keys(&self) -> HashMap<String, u32> {
        let mut keys = HashMap::new();
        let target_store = self.get_database("facetKeysdb").or(self.main_store.as_ref());
        if let Some(store) = target_store {
            for (k, &v) in &store.variables {
                keys.insert(k.clone(), v);
            }
        }
        keys
    }

    pub fn write_multi_database_car<P: AsRef<Path>>(&self, _path: P) -> Result<(), String> {
        Ok(())
    }

    pub fn validate_compatibility(&self) -> (bool, String) {
        if self.coreui_version >= 700 {
            for req in &["imagedb", "colordb", "facetKeysdb"] {
                if !self.has_database(req) && self.main_store.is_none() {
                    return (false, format!("Missing required database: {}", req));
                }
            }
        }
        (true, String::new())
    }
}
