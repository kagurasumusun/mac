use byteorder::{BigEndian, ByteOrder};

pub struct BOMWriter {
    blocks: Vec<(u32, Vec<u8>, Option<String>)>,
    next_id: u32,
}

impl Default for BOMWriter {
    fn default() -> Self {
        Self::new()
    }
}

impl BOMWriter {
    pub fn new() -> Self {
        Self {
            blocks: Vec::new(),
            next_id: 1,
        }
    }

    pub fn add_block(&mut self, data: Vec<u8>, name: Option<String>) -> u32 {
        let id = self.next_id;
        self.next_id += 1;
        self.blocks.push((id, data, name));
        id
    }

    pub fn build(&self) -> Vec<u8> {
        let mut out = Vec::new();

        // 1. BOMHeader placeholder (32 bytes)
        out.extend_from_slice(b"BOMStore");
        out.extend_from_slice(&[0u8; 24]); // Version 1, count, index_off, index_len, vars_off, vars_len

        // 2. Block Payloads
        let mut block_locations: Vec<(u32, u32, u32)> = Vec::new(); // (id, offset, length)
        for (id, data, _) in &self.blocks {
            let offset = out.len() as u32;
            let length = data.len() as u32;
            out.extend_from_slice(data);
            block_locations.push((*id, offset, length));
        }

        // 3. Block Index Table
        let index_offset = out.len() as u32;
        let capacity = (self.blocks.len() + 1) as u32;
        let mut index_buf = Vec::new();
        let mut cap_bytes = [0u8; 4];
        BigEndian::write_u32(&mut cap_bytes, capacity);
        index_buf.extend_from_slice(&cap_bytes);

        // Null block 0
        index_buf.extend_from_slice(&[0u8; 8]);

        // Allocated blocks
        for (_, offset, length) in &block_locations {
            let mut buf = [0u8; 8];
            BigEndian::write_u32(&mut buf[0..4], *offset);
            BigEndian::write_u32(&mut buf[4..8], *length);
            index_buf.extend_from_slice(&buf);
        }

        let index_length = index_buf.len() as u32;
        out.extend_from_slice(&index_buf);

        // 4. Variables Table
        let variables_offset = out.len() as u32;
        let named_blocks: Vec<(&String, u32)> = self
            .blocks
            .iter()
            .filter_map(|(id, _, name)| name.as_ref().map(|n| (n, *id)))
            .collect();

        let mut vars_buf = Vec::new();
        let mut count_bytes = [0u8; 4];
        BigEndian::write_u32(&mut count_bytes, named_blocks.len() as u32);
        vars_buf.extend_from_slice(&count_bytes);

        for (name, id) in named_blocks {
            let mut id_bytes = [0u8; 4];
            BigEndian::write_u32(&mut id_bytes, id);
            vars_buf.extend_from_slice(&id_bytes);

            let name_bytes = name.as_bytes();
            vars_buf.push(name_bytes.len() as u8);
            vars_buf.extend_from_slice(name_bytes);
        }

        let variables_length = vars_buf.len() as u32;
        out.extend_from_slice(&vars_buf);

        // 5. Update BOMHeader at offset 8
        BigEndian::write_u32(&mut out[8..12], 1); // version = 1
        BigEndian::write_u32(&mut out[12..16], capacity); // block_count_hint
        BigEndian::write_u32(&mut out[16..20], index_offset);
        BigEndian::write_u32(&mut out[20..24], index_length);
        BigEndian::write_u32(&mut out[24..28], variables_offset);
        BigEndian::write_u32(&mut out[28..32], variables_length);

        out
    }
}
