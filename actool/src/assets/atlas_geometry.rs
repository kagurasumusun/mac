pub fn improved_shelf_pack(
    rects: &[(u32, u32)],
    max_width: u32,
    max_height: u32,
) -> (Vec<(u32, u32)>, u32, u32) {
    let mut sorted: Vec<(usize, u32, u32)> = rects
        .iter()
        .enumerate()
        .map(|(idx, &(w, h))| (idx, w, h))
        .collect();

    sorted.sort_by(|a, b| (b.1 * b.2, b.2).cmp(&(a.1 * a.2, a.2)));

    let mut positions = vec![(0u32, 0u32); rects.len()];
    let mut shelves: Vec<(u32, u32, u32)> = Vec::new();

    let mut atlas_width = 0u32;
    let mut atlas_height = 0u32;

    for (idx, w, h) in sorted {
        let mut placed = false;

        for shelf in shelves.iter_mut() {
            if shelf.2 + w <= max_width && h <= shelf.1 {
                positions[idx] = (shelf.2, shelf.0);
                shelf.2 += w;
                atlas_width = std::cmp::max(atlas_width, shelf.2);
                placed = true;
                break;
            }
        }

        if !placed {
            if atlas_height + h <= max_height {
                positions[idx] = (0, atlas_height);
                shelves.push((atlas_height, h, w));
                atlas_width = std::cmp::max(atlas_width, w);
                atlas_height += h;
            } else {
                positions[idx] = (0, atlas_height);
                atlas_height += h;
            }
        }
    }

    (positions, atlas_width, atlas_height)
}

pub fn apple_style_pack(
    rects: &[(u32, u32)],
    max_width: u32,
    _max_height: u32,
) -> (Vec<(u32, u32)>, u32, u32) {
    let mut sorted_indices: Vec<usize> = (0..rects.len()).collect();
    sorted_indices.sort_by(|&i, &j| (rects[j].0 * rects[j].1).cmp(&(rects[i].0 * rects[i].1)));

    let mut skyline: Vec<(u32, u32, u32)> = vec![(0, 0, max_width)];
    let mut positions = vec![(0u32, 0u32); rects.len()];

    let mut atlas_width = 0u32;
    let mut atlas_height = 0u32;

    for idx in sorted_indices {
        let (w, h) = rects[idx];
        let w_aligned = ((w + 3) / 4) * 4;
        let h_aligned = ((h + 3) / 4) * 4;

        let mut best_pos = None;
        let mut best_y = u32::MAX;
        let mut best_x = u32::MAX;

        for &(sky_x, sky_y, sky_w) in &skyline {
            if sky_w >= w_aligned {
                if sky_y < best_y || (sky_y == best_y && sky_x < best_x) {
                    best_y = sky_y;
                    best_x = sky_x;
                    best_pos = Some((sky_x, sky_y));
                }
            }
        }

        let pos = best_pos.unwrap_or((0, atlas_height));
        positions[idx] = pos;

        let x = pos.0;
        let y = pos.1;
        let new_y = y + h_aligned;

        let mut new_skyline = Vec::new();
        for &(sky_x, sky_y, sky_w) in &skyline {
            if sky_x + sky_w <= x || sky_x >= x + w_aligned {
                new_skyline.push((sky_x, sky_y, sky_w));
            } else if sky_x < x {
                new_skyline.push((sky_x, sky_y, x - sky_x));
            } else if sky_x + sky_w > x + w_aligned {
                new_skyline.push((x + w_aligned, sky_y, sky_x + sky_w - (x + w_aligned)));
            }
        }

        new_skyline.push((x, new_y, w_aligned));
        new_skyline.sort_by_key(|s| s.0);

        let mut merged_skyline: Vec<(u32, u32, u32)> = Vec::new();
        for seg in new_skyline {
            if let Some(last) = merged_skyline.last_mut() {
                if last.1 == seg.1 && last.0 + last.2 == seg.0 {
                    last.2 += seg.2;
                    continue;
                }
            }
            merged_skyline.push(seg);
        }

        skyline = merged_skyline;
        atlas_width = std::cmp::max(atlas_width, x + w_aligned);
        atlas_height = std::cmp::max(atlas_height, new_y);
    }

    (positions, atlas_width, atlas_height)
}

pub fn calculate_packing_efficiency(positions: &[(u32, u32)], rects: &[(u32, u32)], atlas_w: u32, atlas_h: u32) -> f32 {
    let _ = positions;
    let used_area: u32 = rects.iter().map(|&(w, h)| w * h).sum();
    let atlas_area = atlas_w * atlas_h;
    if atlas_area == 0 {
        0.0
    } else {
        (used_area as f32) / (atlas_area as f32)
    }
}
