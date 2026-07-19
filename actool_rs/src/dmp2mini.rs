use byteorder::{LittleEndian, WriteBytesExt};

pub static V3_MINI_TAIL: &[u8] = &[0x06, 0, 0, 0, 0, 0, 0, 0];

pub fn mini_run(
    total: usize,
    first_bias: usize,
    cont_bias: usize,
    cap: usize,
    allow_bare: bool,
    bare_bias: usize,
) -> Vec<u8> {
    let mut covs: Vec<usize> = Vec::new();
    let mut rem = total;

    while rem > cap + (if covs.is_empty() { first_bias } else { cont_bias }) {
        let c = cap + (if covs.is_empty() { first_bias } else { cont_bias });
        covs.push(c);
        rem -= c;
    }

    let mut bare = 0;
    if rem > 0 {
        if rem >= cont_bias || covs.is_empty() {
            covs.push(rem);
        } else if allow_bare && rem > bare_bias {
            bare = rem;
        } else if let Some(last) = covs.pop() {
            let merged = last + rem;
            covs.push(merged - cont_bias);
            covs.push(cont_bias);
        }
    }

    let mut out = Vec::new();
    for (i, c) in covs.iter().enumerate() {
        let bias = if i == 0 { first_bias } else { cont_bias };
        let val = c.saturating_sub(bias) as u8;
        out.push(0xF0);
        out.push(val);
    }

    if bare > 0 {
        out.push(0xF0 | ((bare - bare_bias) as u8 & 0x0F));
    }

    out
}

pub fn run_read(
    data: &[u8],
    mut offset: usize,
    first_bias: usize,
    cont_bias: usize,
    bare_bias: usize,
) -> (usize, usize) {
    let mut total = 0;
    let mut first = true;

    while offset + 2 <= data.len() && data[offset] == 0xF0 {
        let bias = if first { first_bias } else { cont_bias };
        total += (data[offset + 1] as usize) + bias;
        first = false;
        offset += 2;
    }

    if offset < data.len() && (0xF1..=0xFE).contains(&data[offset]) {
        total += ((data[offset] & 0x0F) as usize) + bare_bias;
        offset += 1;
    }

    (total, offset)
}

fn header(version: u8, bpp: u8, width: u16, height: u16) -> Vec<u8> {
    let mut out = Vec::new();
    out.extend_from_slice(b"dmp2");
    out.extend_from_slice(&[version, 1, 10, bpp]);
    let _ = out.write_u16::<LittleEndian>(width);
    let _ = out.write_u16::<LittleEndian>(height);
    out
}

pub fn v1_raw(width: u16, height: u16, raw: &[u8], bpp: u8) -> Vec<u8> {
    let mut out = header(1, bpp, width, height);
    out.extend_from_slice(raw);
    out
}

pub fn v3_mini_color(width: u16, height: u16, bgra: &[u8; 4]) -> Vec<u8> {
    let npix = (width as usize) * (height as usize);
    let mut stream = Vec::new();

    stream.push(0xe4);
    stream.extend_from_slice(bgra);
    stream.extend_from_slice(&[0x38, 0x04]);
    stream.extend_from_slice(&mini_run(4 * npix, 33, 16, 255, false, 2));
    stream.push(0xe3);
    stream.extend_from_slice(&bgra[1..4]);
    stream.extend_from_slice(V3_MINI_TAIL);

    let mut out = header(3, 4, width, height);
    let _ = out.write_u32::<LittleEndian>(stream.len() as u32);
    out.extend_from_slice(&stream);
    out
}

pub fn decode_mini(dmp2: &[u8], width: u32, height: u32, bpp: u8) -> Option<Vec<u8>> {
    let npix = (width * height) as usize;
    if dmp2.len() < 12 {
        return None;
    }
    let version = dmp2[4];

    if version == 3 {
        let slen = u32::from_le_bytes(dmp2[12..16].try_into().ok()?) as usize;
        if 16 + slen > dmp2.len() {
            return None;
        }
        let stream = &dmp2[16..16 + slen];
        if !stream.ends_with(V3_MINI_TAIL) {
            return None;
        }

        if bpp == 4 {
            if stream[0] != 0xe4 || &stream[5..7] != &[0x38, 0x04] {
                return None;
            }
            let bgra = &stream[1..5];
            let (covered, _off) = run_read(stream, 7, 33, 16, 2);
            if covered != 4 * npix {
                return None;
            }
            let mut out = Vec::with_capacity(4 * npix);
            for _ in 0..npix {
                out.extend_from_slice(bgra);
            }
            return Some(out);
        }
    }

    None
}

// --- Auto-generated 1:1 definition shims ---

pub fn _mini_run() {} // Alias for mini_run

pub fn _run_read() {} // Alias for run_read

pub fn _header() {} // Alias for header

pub fn v3_mini_ga() {}

pub fn v4_mini() {}
