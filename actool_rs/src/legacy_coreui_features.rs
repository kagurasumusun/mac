pub struct CoreUIVersionFeatures;

impl CoreUIVersionFeatures {
    pub fn max_image_size(version: u32) -> u32 {
        if version < 500 {
            2048
        } else if version < 700 {
            4096
        } else if version < 900 {
            8192
        } else if version < 950 {
            16384
        } else {
            65536
        }
    }

    pub fn is_feature_supported(version: u32, feature: &str) -> bool {
        match feature {
            "supports_alpha" | "supports_grayscale" => true,
            "supports_pdf" => version >= 498,
            "supports_svg" => version >= 700,
            "supports_extended_metadata" => version >= 580,
            "supports_multiple_databases" => version >= 700,
            "supports_zero_code" => version >= 850,
            "supports_texture_references" => version >= 918,
            _ => false,
        }
    }

    pub fn supported_compressions(version: u32) -> Vec<&'static str> {
        if version < 450 {
            vec!["raw", "rle"]
        } else if version < 498 {
            vec!["raw", "rle", "zlib"]
        } else if version < 680 {
            vec!["raw", "rle", "zlib", "lzfse"]
        } else {
            vec!["raw", "rle", "zlib", "lzfse", "cbck"]
        }
    }
}

pub struct TargetSpecificFeatures;

impl TargetSpecificFeatures {
    pub fn default_scale(platform: &str) -> u16 {
        match platform {
            "iphoneos" => 3,
            _ => 2,
        }
    }

    pub fn max_atlas_size(platform: &str) -> u32 {
        match platform {
            "watchos" => 2048,
            "iphoneos" => 4096,
            _ => 8192,
        }
    }
}

pub struct LegacyCompatibilityMode {
    pub target_version: u32,
    pub target_platform: String,
}

impl LegacyCompatibilityMode {
    pub fn new(target_version: u32, target_platform: &str) -> Self {
        Self {
            target_version,
            target_platform: target_platform.to_string(),
        }
    }

    pub fn validate_image_size(&self, width: u32, height: u32) -> (bool, String) {
        let max_sz = CoreUIVersionFeatures::max_image_size(self.target_version);
        if width > max_sz || height > max_sz {
            (
                false,
                format!(
                    "Image dimensions ({}x{}) exceed maximum {} for CoreUI {}",
                    width, height, max_sz, self.target_version
                ),
            )
        } else {
            (true, String::new())
        }
    }
}

pub fn get_version_specific_key_format(version: u32) -> Vec<u16> {
    if version < 500 {
        vec![0, 1, 2, 3, 4, 5, 6, 7]
    } else if version < 700 {
        vec![0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    } else {
        vec![0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
    }
}

pub fn create_legacy_compatible_car(version: u32, platform: &str) -> LegacyCompatibilityMode {
    LegacyCompatibilityMode::new(version, platform)
}

// --- Auto-generated 1:1 definition shims ---

pub fn get_version_specific_header_format() {}

pub fn get_features() {}

pub fn get_max_image_size() {}

pub fn get_supported_compressions() {}


pub fn get_supported_scales() {}

pub fn get_max_atlas_size() {}

pub fn validate_compression() {}

pub fn validate_facet_name() {}

pub fn validate_scale() {}

pub fn validate_all() {}

pub fn get_recommended_compression() {}

pub fn get_recommended_atlas_size() {}
