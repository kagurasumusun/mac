#[derive(Debug, Clone)]
pub struct AtlasItem {
    pub name: String,
    pub width: u32,
    pub height: u32,
    pub data: Vec<u8>,
}

#[derive(Debug, Clone)]
pub struct PackedAtlasRegion {
    pub name: String,
    pub x: u32,
    pub y: u32,
    pub width: u32,
    pub height: u32,
}

#[derive(Debug, Clone)]
pub struct PackedAtlas {
    pub total_width: u32,
    pub total_height: u32,
    pub regions: Vec<PackedAtlasRegion>,
    pub buffer: Vec<u8>,
}

/// Simple shelf-packing algorithm for building texture atlases
pub fn pack_atlas(items: &[AtlasItem]) -> PackedAtlas {
    if items.is_empty() {
        return PackedAtlas {
            total_width: 0,
            total_height: 0,
            regions: Vec::new(),
            buffer: Vec::new(),
        };
    }

    let mut sorted_items: Vec<(usize, &AtlasItem)> = items.iter().enumerate().collect();
    sorted_items.sort_by(|a, b| b.1.height.cmp(&a.1.height));

    let mut current_x = 0;
    let mut current_y = 0;
    let mut shelf_height = 0;

    let atlas_width = 2048; // Standard 2048x2048 atlas max size
    let mut max_y = 0;

    let mut regions = Vec::new();

    for (_idx, item) in sorted_items {
        if current_x + item.width > atlas_width {
            current_x = 0;
            current_y += shelf_height;
            shelf_height = 0;
        }

        regions.push(PackedAtlasRegion {
            name: item.name.clone(),
            x: current_x,
            y: current_y,
            width: item.width,
            height: item.height,
        });

        current_x += item.width;
        shelf_height = std::cmp::max(shelf_height, item.height);
        max_y = std::cmp::max(max_y, current_y + item.height);
    }

    let total_height = max_y;
    let total_width = atlas_width;

    // Composite BGRA atlas buffer
    let mut buffer = vec![0u8; (total_width * total_height * 4) as usize];

    for r in &regions {
        let item = items.iter().find(|i| i.name == r.name).unwrap();
        if item.data.len() != (item.width * item.height * 4) as usize {
            continue;
        }

        for y in 0..item.height {
            let src_row = (y * item.width * 4) as usize;
            let dst_row = (((r.y + y) * total_width + r.x) * 4) as usize;
            let len = (item.width * 4) as usize;

            if dst_row + len <= buffer.len() {
                buffer[dst_row..dst_row + len].copy_from_slice(&item.data[src_row..src_row + len]);
            }
        }
    }

    PackedAtlas {
        total_width,
        total_height,
        regions,
        buffer,
    }
}
