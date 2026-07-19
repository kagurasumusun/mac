use crate::bom::{BOMError, BOMStore};
use byteorder::{BigEndian, ByteOrder};

#[derive(Debug, Clone)]
pub struct TreeDescriptor {
    pub version: u32,
    pub root_block: u32,
    pub node_size: usize,
    pub path_count: u32,
}

#[derive(Debug, Clone)]
pub struct TreeEntry {
    pub key_block: u32,
    pub value_block: u32,
    pub key: Vec<u8>,
    pub value: Vec<u8>,
}

pub fn parse_descriptor(raw: &[u8]) -> Result<TreeDescriptor, BOMError> {
    if raw.len() < 20 {
        return Err(BOMError::TruncatedHeader);
    }
    if &raw[0..4] != b"tree" {
        return Err(BOMError::InvalidMagic(raw[0..4].to_vec()));
    }
    let version = BigEndian::read_u32(&raw[4..8]);
    if version != 1 {
        return Err(BOMError::UnsupportedVersion(version));
    }
    let root_block = BigEndian::read_u32(&raw[8..12]);
    let node_size = BigEndian::read_u32(&raw[12..16]) as usize;
    let path_count = BigEndian::read_u32(&raw[16..20]);

    Ok(TreeDescriptor {
        version,
        root_block,
        node_size,
        path_count,
    })
}

pub fn read_leaf_entries(store: &BOMStore, name: &str) -> Result<Vec<TreeEntry>, BOMError> {
    let raw_desc = store.named_block_data(name)?;
    if raw_desc.len() < 20 || &raw_desc[0..4] != b"tree" {
        return Ok(Vec::new());
    }

    let desc = parse_descriptor(raw_desc)?;
    if desc.root_block == 0 {
        return Ok(Vec::new());
    }

    let node_data = store.block_data(desc.root_block)?;
    parse_btr3_leaf_entries(store, node_data)
}

fn parse_btr3_leaf_entries(store: &BOMStore, node_data: &[u8]) -> Result<Vec<TreeEntry>, BOMError> {
    if node_data.len() < 12 {
        return Ok(Vec::new());
    }

    let is_leaf = BigEndian::read_u16(&node_data[0..2]) == 1;
    let count = BigEndian::read_u16(&node_data[2..4]) as usize;

    let mut entries = Vec::new();
    let mut cursor = 12;

    for _ in 0..count {
        if cursor + 8 > node_data.len() {
            break;
        }

        let val_ref = BigEndian::read_u32(&node_data[cursor..cursor + 4]);
        let key_ref = BigEndian::read_u32(&node_data[cursor + 4..cursor + 8]);
        cursor += 8;

        let key_bytes = store.block_data(key_ref).unwrap_or(&[]).to_vec();
        let val_bytes = store.block_data(val_ref).unwrap_or(&[]).to_vec();

        if is_leaf {
            entries.push(TreeEntry {
                key_block: key_ref,
                value_block: val_ref,
                key: key_bytes,
                value: val_bytes,
            });
        }
    }

    Ok(entries)
}

pub fn visit<F: FnMut(&TreeEntry)>(entries: &[TreeEntry], mut visitor: F) {
    for entry in entries {
        visitor(entry);
    }
}
