use crate::lzfse;

#[derive(Debug, Clone)]
pub struct PBRMaterialMap {
    pub name: String,
    pub width: u32,
    pub height: u32,
    pub occlusion: Vec<u8>,
    pub roughness: Vec<u8>,
    pub metallic: Vec<u8>,
}

impl PBRMaterialMap {
    pub fn new(name: &str, width: u32, height: u32) -> Self {
        let count = (width * height) as usize;
        Self {
            name: name.to_string(),
            width,
            height,
            occlusion: vec![255; count],
            roughness: vec![128; count],
            metallic: vec![0; count],
        }
    }

    /// Pack Occlusion (R), Roughness (G), Metallic (B) into a single ORM BGRA texture.
    /// Saves 66% GPU memory for 3D PBR Material rendering on Metal / VisionOS / ARKit.
    pub fn pack_orm_texture(&self) -> Vec<u8> {
        let count = (self.width * self.height) as usize;
        let mut bgra = Vec::with_capacity(count * 4);

        for i in 0..count {
            let o = self.occlusion.get(i).copied().unwrap_or(255);
            let r = self.roughness.get(i).copied().unwrap_or(128);
            let m = self.metallic.get(i).copied().unwrap_or(0);

            // BGRA layout: B=Metallic, G=Roughness, R=Occlusion, A=255
            bgra.push(m);
            bgra.push(r);
            bgra.push(o);
            bgra.push(255);
        }

        bgra
    }

    pub fn compress_orm_payload(&self) -> Vec<u8> {
        let bgra = self.pack_orm_texture();
        crate::cbck::encode_cbck(&bgra, self.width, self.height, 4, true)
    }
}

/// Tangent-space Normal Map Compression (packs Nx, Ny into 2 channels for Metal GPU)
pub fn compress_normal_map_2channel(
    normal_rgb: &[u8],
    width: u32,
    height: u32,
) -> Vec<u8> {
    let count = (width * height) as usize;
    if normal_rgb.len() < count * 3 {
        return lzfse::compress(normal_rgb);
    }

    let mut packed = Vec::with_capacity(count * 4);
    for i in 0..count {
        let nx = normal_rgb[i * 3];
        let ny = normal_rgb[i * 3 + 1];

        // Store Nx in R, Ny in G, reconstruct Nz on Metal GPU: Nz = sqrt(1 - Nx^2 - Ny^2)
        packed.push(0);  // B
        packed.push(ny); // G
        packed.push(nx); // R
        packed.push(255); // A
    }

    crate::cbck::encode_cbck(&packed, width, height, 4, true)
}

/// Generates mipmap chain levels for 3D textures
pub fn generate_mipmap_chain(
    bgra: &[u8],
    width: u32,
    height: u32,
) -> Vec<(u32, u32, Vec<u8>)> {
    let mut mipmaps = Vec::new();
    let mut current_w = width;
    let mut current_h = height;
    let mut current_bgra = bgra.to_vec();

    mipmaps.push((current_w, current_h, current_bgra.clone()));

    while current_w > 1 && current_h > 1 {
        let next_w = std::cmp::max(1, current_w / 2);
        let next_h = std::cmp::max(1, current_h / 2);

        let mut next_bgra = Vec::with_capacity((next_w * next_h * 4) as usize);

        for y in 0..next_h {
            for x in 0..next_w {
                let src_x = x * 2;
                let src_y = y * 2;

                let idx0 = ((src_y * current_w + src_x) * 4) as usize;
                let idx1 = ((src_y * current_w + (src_x + 1)) * 4) as usize;
                let idx2 = (((src_y + 1) * current_w + src_x) * 4) as usize;
                let idx3 = (((src_y + 1) * current_w + (src_x + 1)) * 4) as usize;

                if idx3 + 4 <= current_bgra.len() {
                    let b = ((current_bgra[idx0] as u32 + current_bgra[idx1] as u32 + current_bgra[idx2] as u32 + current_bgra[idx3] as u32) / 4) as u8;
                    let g = ((current_bgra[idx0 + 1] as u32 + current_bgra[idx1 + 1] as u32 + current_bgra[idx2 + 1] as u32 + current_bgra[idx3 + 1] as u32) / 4) as u8;
                    let r = ((current_bgra[idx0 + 2] as u32 + current_bgra[idx1 + 2] as u32 + current_bgra[idx2 + 2] as u32 + current_bgra[idx3 + 2] as u32) / 4) as u8;
                    let a = ((current_bgra[idx0 + 3] as u32 + current_bgra[idx1 + 3] as u32 + current_bgra[idx2 + 3] as u32 + current_bgra[idx3 + 3] as u32) / 4) as u8;

                    next_bgra.push(b);
                    next_bgra.push(g);
                    next_bgra.push(r);
                    next_bgra.push(a);
                } else {
                    next_bgra.extend_from_slice(&[0, 0, 0, 0]);
                }
            }
        }

        current_w = next_w;
        current_h = next_h;
        current_bgra = next_bgra;
        mipmaps.push((current_w, current_h, current_bgra.clone()));
    }

    mipmaps
}
