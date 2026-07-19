use crate::bom::BOMStore;
use crate::car::CARFile;
use crate::carwriter::{AssetRendition, CARWriter};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

pub struct CAREditor {
    pub platform: String,
    pub renditions: HashMap<String, AssetRendition>,
}

impl CAREditor {
    pub fn new(platform: &str) -> Self {
        Self {
            platform: platform.to_string(),
            renditions: HashMap::new(),
        }
    }

    pub fn load<P: AsRef<Path>>(car_path: P) -> Result<Self, String> {
        let store = BOMStore::from_path(&car_path).map_err(|e| e.to_string())?;
        let car = CARFile::from_bom_store(&store).map_err(|e| e.to_string())?;

        let mut editor = Self::new("iphoneos");
        for (i, r) in car.renditions.iter().enumerate() {
            let name = if r.csi.name.is_empty() {
                format!("Asset_{}", i + 1)
            } else {
                r.csi.name.clone()
            };

            let csi_full_block = crate::csi::build_csi_png(
                &r.csi.rendition_data,
                r.csi.width,
                r.csi.height,
                &name,
                r.csi.scale,
                false,
            );

            let rend = AssetRendition {
                name: name.clone(),
                filename: format!("{}.png", name),
                csi_bytes: csi_full_block,
                identifier: (i + 1) as u16,
                idiom: 0,
                scale: r.csi.scale as u16,
                gamut: 0,
                appearance: 0,
                width: r.csi.width,
                height: r.csi.height,
            };
            editor.renditions.insert(name, rend);
        }

        Ok(editor)
    }

    pub fn add_or_replace_image(&mut self, name: &str, bgra: &[u8], width: u32, height: u32) {
        let csi_bytes = crate::csi::build_csi_png(bgra, width, height, name, 1, true);
        let rend = AssetRendition {
            name: name.to_string(),
            filename: format!("{}.png", name),
            csi_bytes,
            identifier: (self.renditions.len() + 1) as u16,
            idiom: 0,
            scale: 1,
            gamut: 0,
            appearance: 0,
            width,
            height,
        };
        self.renditions.insert(name.to_string(), rend);
    }

    pub fn remove_asset(&mut self, name: &str) -> bool {
        self.renditions.remove(name).is_some()
    }

    pub fn save<P: AsRef<Path>>(&self, output_path: P) -> Result<(), String> {
        let mut car_writer = CARWriter::new(&self.platform);
        for r in self.renditions.values() {
            car_writer.add_rendition(r.clone());
        }
        let bytes = car_writer.build();
        fs::write(output_path, bytes).map_err(|e| e.to_string())
    }
}
