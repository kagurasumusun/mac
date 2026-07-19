#[derive(Debug, Clone)]
pub struct CoreUIProfile {
    pub name: String,
    pub header_version: u32,
    pub header_field2: u32,
    pub project_tag: String,
    pub header_tail: (u32, u32, u32, u32),
    pub apple_agent_token: String,
}

impl CoreUIProfile {
    pub fn program_string(&self) -> String {
        format!("@(#)PROGRAM:CoreUI  PROJECT:CoreUI-{}\n", self.project_tag)
    }

    pub fn writer_comment(&self) -> &'static str {
        "actool-rs clean-room writer"
    }
}

pub fn profile_for_platform(platform: Option<&str>) -> CoreUIProfile {
    let p = platform.unwrap_or("macosx").to_lowercase();
    if p == "macosx" || p == "mac" {
        CoreUIProfile {
            name: "coreui-975-macos".to_string(),
            header_version: 975,
            header_field2: 17,
            project_tag: "975 [LAR]".to_string(),
            header_tail: (0, 2, 1, 1),
            apple_agent_token: "AssetCatalogAgent-AssetRuntime".to_string(),
        }
    } else {
        CoreUIProfile {
            name: "coreui-975-device".to_string(),
            header_version: 975,
            header_field2: 17,
            project_tag: "975".to_string(),
            header_tail: (0, 2, 1, 2),
            apple_agent_token: "AssetCatalogSimulatorAgent".to_string(),
        }
    }
}

pub fn auto_select_profile(platform: Option<&str>, target: Option<&str>) -> CoreUIProfile {
    let plat = platform.unwrap_or("macosx").to_lowercase();
    let is_mac = plat == "macosx" || plat == "mac";

    if let Some(tgt) = target {
        if let Ok(ver) = tgt.split('.').next().unwrap_or("15").parse::<f32>() {
            if is_mac {
                if ver <= 11.0 {
                    return CoreUIProfile {
                        name: "coreui-700".to_string(),
                        header_version: 700,
                        header_field2: 16,
                        project_tag: "700".to_string(),
                        header_tail: (0, 1, 1, 1),
                        apple_agent_token: "AssetCatalogSimulatorAgent".to_string(),
                    };
                }
                if ver <= 13.0 {
                    return CoreUIProfile {
                        name: "coreui-850".to_string(),
                        header_version: 850,
                        header_field2: 16,
                        project_tag: "850".to_string(),
                        header_tail: (0, 4, 1, 1),
                        apple_agent_token: "AssetCatalogSimulatorAgent".to_string(),
                    };
                }
            }
        }
    }

    profile_for_platform(platform)
}

pub fn resolve_profile(profile_name: Option<&str>, platform: Option<&str>) -> CoreUIProfile {
    if let Some(pname) = profile_name {
        if pname.contains("918") {
            return CoreUIProfile {
                name: "coreui-918".to_string(),
                header_version: 918,
                header_field2: 17,
                project_tag: "918.5".to_string(),
                header_tail: (0, 5, 1, 1),
                apple_agent_token: "AssetCatalogSimulatorAgent".to_string(),
            };
        }
    }
    profile_for_platform(platform)
}
