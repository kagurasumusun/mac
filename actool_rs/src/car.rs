use crate::bom::{BOMError, BOMStore};
use crate::csi::{parse_csi, CSIHeader};
use crate::tree::read_leaf_entries;
use byteorder::{BigEndian, ByteOrder, LittleEndian};
use std::collections::HashMap;

pub const ATTRIBUTE_NAMES: &[(u16, &str)] = &[
    (0, "kCRThemeLookName"),
    (1, "kCRThemeElementName"),
    (2, "kCRThemePartName"),
    (3, "kCRThemeSizeName"),
    (4, "kCRThemeDirectionName"),
    (5, "kCRThemePlaceholderName"),
    (6, "kCRThemeValueName"),
    (7, "kCRThemeAppearanceName"),
    (8, "kCRThemeDimension1Name"),
    (9, "kCRThemeDimension2Name"),
    (10, "kCRThemeStateName"),
    (11, "kCRThemeLayerName"),
    (12, "kCRThemeScaleName"),
    (13, "kCRThemeLocalizationName"),
    (14, "kCRThemePresentationStateName"),
    (15, "kCRThemeIdiomName"),
    (16, "kCRThemeSubtypeName"),
    (17, "kCRThemeIdentifierName"),
    (18, "kCRThemePreviousValueName"),
    (19, "kCRThemePreviousStateName"),
    (20, "kCRThemeSizeClassHorizontalName"),
    (21, "kCRThemeSizeClassVerticalName"),
    (22, "kCRThemeMemoryClassName"),
    (23, "kCRThemeGraphicsClassName"),
    (24, "kCRThemeDisplayGamutName"),
    (25, "kCRThemeDeploymentTargetName"),
    (26, "kCRThemeGlyphWeightName"),
    (27, "kCRThemeGlyphSizeName"),
];

#[derive(Debug, Clone)]
pub struct CARHeader {
    pub byte_order: String,
    pub core_ui_version: u32,
    pub storage_version: u32,
    pub storage_timestamp: u32,
    pub rendition_count: u32,
    pub schema_version: u32,
    pub main_version: String,
    pub version_string: String,
    pub identifier: String,
    pub associated_checksum: u32,
    pub color_space_id: u32,
    pub key_semantics: u32,
}

#[derive(Debug, Clone)]
pub struct ExtendedMetadata {
    pub authoring_tool: String,
}

#[derive(Debug, Clone)]
pub struct Facet {
    pub name: String,
    pub cursor_hotspot: (u16, u16),
    pub attributes: Vec<(u16, u16)>,
}

impl Facet {
    pub fn named_attributes(&self) -> HashMap<String, u16> {
        let mut map = HashMap::new();
        for &(attr, val) in &self.attributes {
            let attr_name = ATTRIBUTE_NAMES
                .iter()
                .find(|&&(a, _)| a == attr)
                .map(|&(_, n)| n.to_string())
                .unwrap_or_else(|| format!("UNKNOWN({})", attr));
            map.insert(attr_name, val);
        }
        map
    }
}

#[derive(Debug, Clone)]
pub struct NamedValueRegistryEntry {
    pub name: String,
    pub value: u16,
}

#[derive(Debug, Clone)]
pub struct KeyFormat {
    pub byte_order: String,
    pub attributes: Vec<u32>,
}

impl KeyFormat {
    pub fn names(&self) -> Vec<String> {
        self.attributes
            .iter()
            .map(|&attr| {
                ATTRIBUTE_NAMES
                    .iter()
                    .find(|&&(a, _)| (a as u32) == attr)
                    .map(|&(_, n)| n.to_string())
                    .unwrap_or_else(|| format!("UNKNOWN({})", attr))
            })
            .collect()
    }
}

#[derive(Debug, Clone)]
pub struct Rendition {
    pub key_values: Vec<u16>,
    pub key: HashMap<String, u16>,
    pub csi: CSIHeader,
}

pub fn _cstring(raw: &[u8]) -> String {
    let end = raw.iter().position(|&b| b == 0).unwrap_or(raw.len());
    String::from_utf8_lossy(&raw[..end]).to_string()
}

pub fn parse_extended_metadata(raw: &[u8]) -> Result<ExtendedMetadata, BOMError> {
    if raw.len() < 1028 {
        return Err(BOMError::TruncatedHeader);
    }
    let tool = _cstring(&raw[772..1028]);
    Ok(ExtendedMetadata {
        authoring_tool: tool,
    })
}

pub fn parse_facet(name_raw: &[u8], value_raw: &[u8]) -> Result<Facet, BOMError> {
    let name = String::from_utf8_lossy(name_raw).to_string();
    if value_raw.len() < 6 {
        return Err(BOMError::TruncatedHeader);
    }
    let hx = u16::from_le_bytes(value_raw[0..2].try_into().unwrap());
    let hy = u16::from_le_bytes(value_raw[2..4].try_into().unwrap());
    let count = u16::from_le_bytes(value_raw[4..6].try_into().unwrap()) as usize;

    let mut attributes = Vec::new();
    for i in 0..count {
        let off = 6 + i * 4;
        if off + 4 <= value_raw.len() {
            let attr = u16::from_le_bytes(value_raw[off..off + 2].try_into().unwrap());
            let val = u16::from_le_bytes(value_raw[off + 2..off + 4].try_into().unwrap());
            attributes.push((attr, val));
        }
    }

    Ok(Facet {
        name,
        cursor_hotspot: (hx, hy),
        attributes,
    })
}

pub fn parse_named_value_registry_entry(
    key_raw: &[u8],
    value_raw: &[u8],
) -> Result<NamedValueRegistryEntry, BOMError> {
    let name = String::from_utf8_lossy(key_raw).to_string();
    if value_raw.len() < 2 {
        return Err(BOMError::TruncatedHeader);
    }
    let val = u16::from_le_bytes(value_raw[0..2].try_into().unwrap());
    Ok(NamedValueRegistryEntry { name, value: val })
}

pub fn parse_rendition(
    key_raw: &[u8],
    value_raw: &[u8],
    key_format: &KeyFormat,
) -> Result<Rendition, BOMError> {
    let count = key_format.attributes.len();
    let is_little = key_format.byte_order == "little";

    let mut key_values = Vec::new();
    for i in 0..count {
        let off = i * 2;
        if off + 2 <= key_raw.len() {
            let v = if is_little {
                u16::from_le_bytes(key_raw[off..off + 2].try_into().unwrap())
            } else {
                u16::from_be_bytes(key_raw[off..off + 2].try_into().unwrap())
            };
            key_values.push(v);
        }
    }

    let mut key_map = HashMap::new();
    for (&attr, &val) in key_format.attributes.iter().zip(key_values.iter()) {
        let attr_name = ATTRIBUTE_NAMES
            .iter()
            .find(|&&(a, _)| (a as u32) == attr)
            .map(|&(_, n)| n.to_string())
            .unwrap_or_else(|| format!("UNKNOWN({})", attr));
        key_map.insert(attr_name, val);
    }

    let csi = parse_csi(value_raw)?;
    Ok(Rendition {
        key_values,
        key: key_map,
        csi,
    })
}

pub fn parse_car_header(data: &[u8]) -> Result<CARHeader, BOMError> {
    if data.len() < 436 {
        return Err(BOMError::TruncatedHeader);
    }

    let is_little = match &data[0..4] {
        b"RATC" => true,
        b"CTAR" => false,
        _ => return Err(BOMError::InvalidMagic(data[0..4].to_vec())),
    };

    let (core_ui, storage, timestamp, rendition_count) = if is_little {
        (
            LittleEndian::read_u32(&data[4..8]),
            LittleEndian::read_u32(&data[8..12]),
            LittleEndian::read_u32(&data[12..16]),
            LittleEndian::read_u32(&data[16..20]),
        )
    } else {
        (
            BigEndian::read_u32(&data[4..8]),
            BigEndian::read_u32(&data[8..12]),
            BigEndian::read_u32(&data[12..16]),
            BigEndian::read_u32(&data[16..20]),
        )
    };

    let main_version = _cstring(&data[20..148]);
    let version_string = _cstring(&data[148..404]);

    let uuid_bytes = &data[404..420];
    let identifier = format!(
        "{:02x}{:02x}{:02x}{:02x}-{:02x}{:02x}-{:02x}{:02x}-{:02x}{:02x}-{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}",
        uuid_bytes[0], uuid_bytes[1], uuid_bytes[2], uuid_bytes[3],
        uuid_bytes[4], uuid_bytes[5], uuid_bytes[6], uuid_bytes[7],
        uuid_bytes[8], uuid_bytes[9], uuid_bytes[10], uuid_bytes[11],
        uuid_bytes[12], uuid_bytes[13], uuid_bytes[14], uuid_bytes[15]
    );

    let (checksum, schema, color_space, key_semantics) = if is_little {
        (
            LittleEndian::read_u32(&data[420..424]),
            LittleEndian::read_u32(&data[424..428]),
            LittleEndian::read_u32(&data[428..432]),
            LittleEndian::read_u32(&data[432..436]),
        )
    } else {
        (
            BigEndian::read_u32(&data[420..424]),
            BigEndian::read_u32(&data[424..428]),
            BigEndian::read_u32(&data[428..432]),
            BigEndian::read_u32(&data[432..436]),
        )
    };

    Ok(CARHeader {
        byte_order: if is_little { "little" } else { "big" }.to_string(),
        core_ui_version: core_ui,
        storage_version: storage,
        storage_timestamp: timestamp,
        rendition_count,
        schema_version: schema,
        main_version,
        version_string,
        identifier,
        associated_checksum: checksum,
        color_space_id: color_space,
        key_semantics,
    })
}

pub fn parse_key_format(data: &[u8]) -> Result<KeyFormat, BOMError> {
    if data.len() < 12 {
        return Err(BOMError::TruncatedHeader);
    }

    let is_little = match &data[0..4] {
        b"tmfk" => true,
        b"kfmt" => false,
        _ => return Err(BOMError::InvalidMagic(data[0..4].to_vec())),
    };

    let count = if is_little {
        LittleEndian::read_u32(&data[8..12]) as usize
    } else {
        BigEndian::read_u32(&data[8..12]) as usize
    };

    let mut attributes = Vec::new();
    for i in 0..count {
        let off = 12 + i * 4;
        if off + 4 > data.len() {
            break;
        }
        let attr = if is_little {
            LittleEndian::read_u32(&data[off..off + 4])
        } else {
            BigEndian::read_u32(&data[off..off + 4])
        };
        attributes.push(attr);
    }

    Ok(KeyFormat {
        byte_order: if is_little { "little" } else { "big" }.to_string(),
        attributes,
    })
}

pub struct CARFile {
    pub header: CARHeader,
    pub key_format: KeyFormat,
    pub block_count: usize,
    pub facets: Vec<Facet>,
    pub renditions: Vec<Rendition>,
}

impl CARFile {
    pub fn from_bom_store(store: &BOMStore) -> Result<Self, BOMError> {
        let car_hdr_bytes = store.named_block_data("CARHEADER")?;
        let header = parse_car_header(car_hdr_bytes)?;

        let kfmt_bytes = store.named_block_data("KEYFORMAT")?;
        let key_format = parse_key_format(kfmt_bytes)?;

        let mut facets = Vec::new();
        if store.has_database("FACETKEYS") {
            if let Ok(entries) = read_leaf_entries(store, "FACETKEYS") {
                for e in entries {
                    if let Ok(f) = parse_facet(&e.key, &e.value) {
                        facets.push(f);
                    }
                }
            }
        }

        let mut renditions = Vec::new();
        if store.has_database("CAR KEY") {
            if let Ok(entries) = read_leaf_entries(store, "CAR KEY") {
                for e in entries {
                    if let Ok(r) = parse_rendition(&e.key, &e.value, &key_format) {
                        renditions.push(r);
                    }
                }
            }
        }

        Ok(Self {
            header,
            key_format,
            block_count: store.blocks.len(),
            facets,
            renditions,
        })
    }

    pub fn from_path<P: AsRef<std::path::Path>>(path: P) -> Result<Self, BOMError> {
        let store = BOMStore::from_path(path)?;
        Self::from_bom_store(&store)
    }
}
