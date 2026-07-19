use serde::Deserialize;

#[derive(Debug, Clone, Deserialize)]
pub struct AppIconEntry {
    pub idiom: Option<String>,
    pub size: Option<String>,
    pub scale: Option<String>,
    pub filename: Option<String>,
    pub platform: Option<String>,
}

pub fn app_icon_entry_rank(entry: &AppIconEntry, platform: &str) -> Option<(i32, u32, u32)> {
    let filename = entry.filename.as_ref()?;
    if filename.is_empty() {
        return None;
    }

    let idiom = entry.idiom.as_deref().unwrap_or("universal");
    let scale_str = entry.scale.as_deref().unwrap_or("1x");
    let scale = scale_str.chars().next().and_then(|c| c.to_digit(10)).unwrap_or(1);

    // Parse sidecar dimension WxH from size string (e.g. "60x60", "83.5x83.5", "1024x1024")
    let size_str = entry.size.as_deref().unwrap_or("1024x1024");
    let dim = parse_size_dim(size_str);

    let (width, height) = ((dim * scale as f32).round() as u32, (dim * scale as f32).round() as u32);

    // Platform idiom matching rank score
    let is_applicable = match platform {
        "iphoneos" | "ios" => idiom == "iphone" || idiom == "ipad" || idiom == "universal" || idiom == "ios-marketing",
        "macosx" | "mac" => idiom == "mac" || idiom == "universal",
        "watchos" | "watch" => idiom == "watch" || idiom == "watch-marketing" || idiom == "universal",
        "appletvos" | "tv" => idiom == "tvos" || idiom == "tvos-marketing" || idiom == "universal",
        _ => true,
    };

    if !is_applicable {
        return None;
    }

    let rank_score = match idiom {
        "ios-marketing" | "watch-marketing" | "tvos-marketing" => 100,
        "iphone" | "ipad" | "mac" | "watch" | "tvos" => 80,
        "universal" => 50,
        _ => 10,
    };

    Some((rank_score, width, height))
}

fn parse_size_dim(size_str: &str) -> f32 {
    let parts: Vec<&str> = size_str.split('x').collect();
    if !parts.is_empty() {
        if let Ok(val) = parts[0].parse::<f32>() {
            return val;
        }
    }
    1024.0
}
