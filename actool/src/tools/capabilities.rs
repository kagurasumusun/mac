use serde_json::{json, Value};

pub fn capability_report() -> Value {
    json!({
        "tool": "actool-rs",
        "claims": {
            "container": { "implemented": true, "apple_assetutil": true },
            "images": { "implemented": true, "formats": ["PNG/deepmap2", "CBCK/LZFSE", "JPEG", "HEIF", "PDF", "SVG"] },
            "packed_atlas": { "implemented": true },
            "app_icons": { "implemented": true, "platforms": ["iOS", "iPadOS", "tvOS", "watchOS", "macOS", "visionOS"] }
        },
        "verified_hosts": ["Linux x86_64", "macOS / CoreUI"]
    })
}
