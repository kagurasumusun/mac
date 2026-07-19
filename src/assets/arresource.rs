use serde::Deserialize;
use serde_json::json;

#[derive(Debug, Clone, Deserialize)]
pub struct ARReferenceImageSpec {
    pub name: String,
    pub physical_width_meters: f32,
    pub physical_height_meters: f32,
}

pub struct ARResourceGroup {
    pub name: String,
    pub reference_images: Vec<ARReferenceImageSpec>,
}

impl ARResourceGroup {
    pub fn new(name: &str) -> Self {
        Self {
            name: name.to_string(),
            reference_images: Vec::new(),
        }
    }

    pub fn add_image(&mut self, image: ARReferenceImageSpec) {
        self.reference_images.push(image);
    }

    pub fn serialize_ar_group(&self) -> String {
        json!({
            "ar_group": self.name,
            "reference_images": self.reference_images.iter().map(|img| json!({
                "name": img.name,
                "physical_width": img.physical_width_meters,
                "physical_height": img.physical_height_meters
            })).collect::<Vec<_>>()
        }).to_string()
    }
}
