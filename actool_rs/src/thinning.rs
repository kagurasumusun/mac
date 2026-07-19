use crate::carwriter::AssetRendition;

pub static IDIOMS: &[(&str, u16)] = &[
    ("universal", 0),
    ("iphone", 1),
    ("phone", 1),
    ("ipad", 2),
    ("pad", 2),
    ("tv", 3),
    ("car", 4),
    ("carplay", 4),
    ("watch", 5),
    ("marketing", 6),
    ("mac", 7),
    ("vision", 8),
    ("visionos", 8),
];

#[derive(Debug, Clone, Default)]
pub struct ThinningOptions {
    pub idiom: Option<String>,
    pub scale: Option<u16>,
    pub appearance: Option<u16>,
    pub localization: Option<String>,
    pub keep_fallbacks: bool,
}

impl ThinningOptions {
    pub fn new() -> Self {
        Self {
            idiom: None,
            scale: None,
            appearance: None,
            localization: None,
            keep_fallbacks: true,
        }
    }

    pub fn idiom_id(&self) -> Option<u16> {
        let name = self.idiom.as_ref()?;
        for &(k, v) in IDIOMS {
            if k == name {
                return Some(v);
            }
        }
        name.parse::<u16>().ok()
    }

    pub fn metadata_arguments(&self) -> String {
        let mut fields = Vec::new();
        if let Some(id) = self.idiom_id() {
            fields.push(format!("idiom {}", id));
        }
        if let Some(s) = self.scale {
            fields.push(format!("scale {}", s));
        }
        if let Some(a) = self.appearance {
            fields.push(format!("appearance {}", a));
        }
        if let Some(ref l) = self.localization {
            fields.push(format!("localization {}", l));
        }
        fields.join(" ")
    }
}

pub fn thin_renditions(renditions: Vec<AssetRendition>, options: &ThinningOptions) -> Vec<AssetRendition> {
    let target_idiom = options.idiom_id();
    let mut selected = Vec::new();

    for r in renditions {
        if let Some(idiom) = target_idiom {
            let allowed = idiom == r.idiom || (options.keep_fallbacks && r.idiom == 0) || r.idiom == 6;
            if !allowed {
                continue;
            }
        }

        if let Some(scale) = options.scale {
            if r.scale != scale {
                continue;
            }
        }

        if let Some(app) = options.appearance {
            let allowed_app = app == r.appearance || (options.keep_fallbacks && r.appearance == 0);
            if !allowed_app {
                continue;
            }
        }

        selected.push(r);
    }

    selected
}
