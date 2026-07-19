use crate::lzfse;
use byteorder::{LittleEndian, WriteBytesExt};
use rayon::prelude::*;

pub static DELTA_MAGIC: &[u8; 4] = b"PDLT";

pub fn separate_planes(bgra: &[u8]) -> (Vec<u8>, Vec<u8>, Vec<u8>, Vec<u8>) {
    let count = bgra.len() / 4;
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

    (b_plane, g_plane, r_plane, a_plane)
}

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

    let (b_plane, g_plane, r_plane, a_plane) = separate_planes(bgra);

    // Parallel processing across color planes B, G, R, A using Rayon
    let planes = vec![b_plane, g_plane, r_plane, a_plane];
    let deltas: Vec<Vec<u8>> = planes.par_iter().map(|p| delta_encode_plane(p)).collect();

    let mut out = Vec::with_capacity(12 + count * 4);
    out.extend_from_slice(DELTA_MAGIC);
    let _ = out.write_u32::<LittleEndian>(width);
    let _ = out.write_u32::<LittleEndian>(height);
    out.extend_from_slice(&deltas[0]);
    out.extend_from_slice(&deltas[1]);
    out.extend_from_slice(&deltas[2]);
    out.extend_from_slice(&deltas[3]);

    out
}

pub fn planar_delta_decode(data: &[u8]) -> Result<Vec<u8>, &'static str> {
    if data.len() < 12 || &data[0..4] != DELTA_MAGIC {
        return Err("Not a valid planar-delta PDLT stream");
    }

    let w = u32::from_le_bytes(data[4..8].try_into().unwrap()) as usize;
    let h = u32::from_le_bytes(data[8..12].try_into().unwrap()) as usize;
    let n_pixels = w.checked_mul(h).ok_or("Invalid dimensions: multiplication overflow")?;

    if data.len() < 12 + n_pixels * 4 {
        return Err("Truncated PDLT payload");
    }

    let b_delta = &data[12..12 + n_pixels];
    let g_delta = &data[12 + n_pixels..12 + n_pixels * 2];
    let r_delta = &data[12 + n_pixels * 2..12 + n_pixels * 3];
    let a_delta = &data[12 + n_pixels * 3..12 + n_pixels * 4];

    let deltas = vec![b_delta, g_delta, r_delta, a_delta];
    let planes: Vec<Vec<u8>> = deltas.par_iter().map(|d| delta_decode_plane(d)).collect();

    let b = &planes[0];
    let g = &planes[1];
    let r = &planes[2];
    let a = &planes[3];

    let mut bgra = Vec::with_capacity(n_pixels * 4);
    for i in 0..n_pixels {
        bgra.push(b[i]);
        bgra.push(g[i]);
        bgra.push(r[i]);
        bgra.push(a[i]);
    }

    Ok(bgra)
}

pub fn planar_delta_compress(bgra: &[u8], width: u32, height: u32) -> Vec<u8> {
    let raw = planar_delta_encode(bgra, width, height);
    lzfse::compress(&raw)
}

pub fn planar_delta_decompress(compressed: &[u8]) -> Result<Vec<u8>, &'static str> {
    let raw = lzfse::decompress(compressed)?;
    planar_delta_decode(&raw)
}

pub fn make_apple_compatible_delta_chunk(bgra: &[u8]) -> Vec<u8> {
    lzfse::compress(bgra)
}

pub fn analyze_delta_characteristics(bgra: &[u8]) -> (f32, &'static str) {
    if bgra.is_empty() {
        return (0.0, "lzfse_direct");
    }
    (0.85, "delta")
}
