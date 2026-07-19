use byteorder::{BigEndian, ByteOrder};
use std::collections::HashMap;
use std::path::Path;
use thiserror::Error;

#[derive(Error, Debug)]
pub enum BOMError {
    #[error("File is shorter than 32-byte BOM header")]
    TruncatedHeader,
    #[error("Invalid BOM magic: {0:?}")]
    InvalidMagic(Vec<u8>),
    #[error("Unsupported BOMStore version: {0}")]
    UnsupportedVersion(u32),
    #[error("{label} range outside file: offset={offset}, length={length}")]
    OutOfRange {
        label: &'static str,
        offset: usize,
        length: usize,
    },
    #[error("Block index capacity invalid or truncated: {0}")]
    InvalidCapacity(u32),
    #[error("Variables table entry truncated or count too high: {0}")]
    InvalidVariables(u32),
    #[error("Unknown block identifier: {0}")]
    UnknownBlock(u32),
    #[error("Unknown named block: {0}")]
    UnknownName(String),
    #[error("Variable name is not valid UTF-8")]
    InvalidUtf8,
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BOMHeader {
    pub version: u32,
    pub block_count_hint: u32,
    pub index_offset: usize,
    pub index_length: usize,
    pub variables_offset: usize,
    pub variables_length: usize,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Block {
    pub identifier: u32,
    pub offset: usize,
    pub length: usize,
}

pub struct BOMStore {
    data: Vec<u8>,
    pub header: BOMHeader,
    pub blocks: HashMap<u32, Block>,
    pub variables: HashMap<String, u32>,
}

impl BOMStore {
    pub const MAGIC: &'static [u8; 8] = b"BOMStore";

    pub fn from_bytes(data: Vec<u8>) -> Result<Self, BOMError> {
        if data.len() < 32 {
            return Err(BOMError::TruncatedHeader);
        }

        if &data[0..8] != Self::MAGIC {
            return Err(BOMError::InvalidMagic(data[0..8].to_vec()));
        }

        let version = BigEndian::read_u32(&data[8..12]);
        if version != 1 {
            return Err(BOMError::UnsupportedVersion(version));
        }

        let block_count_hint = BigEndian::read_u32(&data[12..16]);
        let index_offset = BigEndian::read_u32(&data[16..20]) as usize;
        let index_length = BigEndian::read_u32(&data[20..24]) as usize;
        let variables_offset = BigEndian::read_u32(&data[24..28]) as usize;
        let variables_length = BigEndian::read_u32(&data[28..32]) as usize;

        let check_range = |offset: usize, length: usize, label: &'static str| {
            if offset > data.len() || length > data.len().saturating_sub(offset) {
                Err(BOMError::OutOfRange {
                    label,
                    offset,
                    length,
                })
            } else {
                Ok(())
            }
        };

        check_range(index_offset, index_length, "block index")?;
        check_range(variables_offset, variables_length, "variables")?;

        let header = BOMHeader {
            version,
            block_count_hint,
            index_offset,
            index_length,
            variables_offset,
            variables_length,
        };

        // Parse block index
        let raw_index = &data[index_offset..index_offset + index_length];
        if raw_index.len() < 4 {
            return Err(BOMError::InvalidCapacity(0));
        }
        let capacity = BigEndian::read_u32(&raw_index[0..4]);
        let required = 4 + (capacity as usize) * 8;
        if capacity > 1_000_000 || required > raw_index.len() {
            return Err(BOMError::InvalidCapacity(capacity));
        }

        let mut blocks = HashMap::new();
        for identifier in 1..capacity {
            let entry_off = 4 + (identifier as usize) * 8;
            let offset = BigEndian::read_u32(&raw_index[entry_off..entry_off + 4]) as usize;
            let length = BigEndian::read_u32(&raw_index[entry_off + 4..entry_off + 8]) as usize;
            if offset == 0 && length == 0 {
                continue;
            }
            check_range(offset, length, "block payload")?;
            blocks.insert(
                identifier,
                Block {
                    identifier,
                    offset,
                    length,
                },
            );
        }

        // Parse variables
        let raw_vars = &data[variables_offset..variables_offset + variables_length];
        if raw_vars.len() < 4 {
            return Err(BOMError::InvalidVariables(0));
        }
        let count = BigEndian::read_u32(&raw_vars[0..4]);
        if count > 100_000 {
            return Err(BOMError::InvalidVariables(count));
        }

        let mut cursor = 4;
        let mut variables = HashMap::new();
        for _ in 0..count {
            if cursor + 5 > raw_vars.len() {
                return Err(BOMError::InvalidVariables(count));
            }
            let identifier = BigEndian::read_u32(&raw_vars[cursor..cursor + 4]);
            let name_len = raw_vars[cursor + 4] as usize;
            cursor += 5;
            if cursor + name_len > raw_vars.len() {
                return Err(BOMError::InvalidVariables(count));
            }
            let name_bytes = &raw_vars[cursor..cursor + name_len];
            cursor += name_len;

            let name = std::str::from_utf8(name_bytes)
                .map_err(|_| BOMError::InvalidUtf8)?
                .to_string();
            variables.insert(name, identifier);
        }

        Ok(Self {
            data,
            header,
            blocks,
            variables,
        })
    }

    pub fn from_path<P: AsRef<Path>>(path: P) -> Result<Self, BOMError> {
        let bytes = std::fs::read(path)?;
        Self::from_bytes(bytes)
    }

    pub fn block_data(&self, identifier: u32) -> Result<&[u8], BOMError> {
        let blk = self
            .blocks
            .get(&identifier)
            .ok_or(BOMError::UnknownBlock(identifier))?;
        Ok(&self.data[blk.offset..blk.offset + blk.length])
    }

    pub fn named_block_data(&self, name: &str) -> Result<&[u8], BOMError> {
        let id = self
            .variables
            .get(name)
            .ok_or_else(|| BOMError::UnknownName(name.to_string()))?;
        self.block_data(*id)
    }
}
