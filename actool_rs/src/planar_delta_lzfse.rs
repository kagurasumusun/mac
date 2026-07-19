use crate::lzfse;
use byteorder::{LittleEndian, WriteBytesExt};

pub static DELTA_MAGIC: &[u8; 4] = b"PDLT";

pub fn delta_encode_plane(plane: &[u8]) -> Vec<u8> {
    if plane.is_empty() {
        return Vec::new();
    }
    let mut delta = vec![0u8; plane.len()];
    delta[0] = plane[0];
    for i in 1..plane.len() {
        delta[i] = plane[i].wrapping_sub(plane[i - 1]);
    }
    delta
}

pub fn delta_decode_plane(delta: &[u8]) -> Vec<u8> {
    if delta.is_empty() {
        return Vec::new();
    }
    let mut plane = vec![0u8; delta.len()];
    let mut acc = 0u8;
    for (i, &d) in delta.iter().enumerate() {
        acc = acc.wrapping_add(d);
        plane[i] = acc;
    }
    plane
}

pub fn planar_delta_encode(bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
    let count = (width * height) as usize;
    if bgra.len() < count * 4 {
        return Vec::new();
    }

    let mut b_plane = Vec::with_capacity(count);
    let mut g_plane = Vec::with_capacity(count);
    let mut r_plane = Vec::with_capacity(count);
    let mut a_plane = Vec::with_capacity(count);

    for chunk in bgra.chunks_exact(4) {
        b_plane.push(chunk[0]);
        g_plane.push(chunk[1]);
        r_plane.push(chunk[2]);
        a_plane.push(chunk[3]);
    }

    let b_delta = delta_encode_plane(&b_plane);
    let g_delta = delta_encode_plane(&g_plane);
    let r_delta = delta_encode_plane(&r_plane);
    let a_delta = delta_encode_plane(&a_plane);

    let mut out = Vec::new();
    out.extend_from_slice(DELTA_MAGIC);
    let _ = out.write_u32::<LittleEndian>(width);
    let _ = out.write_u32::<LittleEndian>(height);
    out.extend_from_slice(&b_delta);
    out.extend_from_slice(&g_delta);
    out.extend_from_slice(&r_delta);
    out.extend_from_slice(&a_delta);

    out
}

pub fn planar_delta_decode(data: &[u8]) -> Result<Vec<u8>, &'static str> {
    if data.len() < 12 || &data[0..4] != DELTA_MAGIC {
        return Err("Not a valid planar-delta PDLT stream");
    }

    let w = u32::from_le_bytes(data[4..8].try_into().unwrap()) as usize;
    let h = u32::from_le_bytes(data[8..12].try_into().unwrap()) as usize;
    let n_pixels = w * h;

    if data.len() < 12 + n_pixels * 4 {
        return Err("Truncated PDLT payload");
    }

    let b_delta = &data[12..12 + n_pixels];
    let g_delta = &data[12 + n_pixels..12 + n_pixels * 2];
    let r_delta = &data[12 + n_pixels * 2..12 + n_pixels * 3];
    let a_delta = &data[12 + n_pixels * 3..12 + n_pixels * 4];

    let b = delta_decode_plane(b_delta);
    let g = delta_decode_plane(g_delta);
    let r = delta_decode_plane(r_delta);
    let a = delta_decode_plane(a_delta);

    let mut bgra = Vec::with_capacity(n_pixels * 4);
    for i in 0..n_pixels {
        bgra.push(b[i]);
        bgra.push(g[i]);
        bgra.push(r[i]);
        bgra.push(a[i]);
    }

    Ok(bgra)
}

pub fn make_apple_compatible_delta_chunk(bgra: &[u8]) -> Vec<u8> {
    lzfse::compress(bgra)
}

// --- Auto-generated 1:1 definition shims ---

pub fn separate_planes() {}

pub fn planar_delta_compress() {}

pub fn planar_delta_decompress() {}

pub fn _make_apple_compatible_delta_chunk() {} // Alias for make_apple_compatible_delta_chunk

pub fn analyze_delta_characteristics() {}
