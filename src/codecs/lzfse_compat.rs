use crate::lzfse;

pub fn have_c_extension() -> bool {
    false
}

pub fn is_valid_stream(data: &[u8]) -> bool {
    if data.len() < 4 {
        return false;
    }
    let magic = &data[0..4];
    magic == b"bvx2" || magic == b"lzfse" || magic == b"bvx$"
}

pub fn compress(data: &[u8]) -> Vec<u8> {
    lzfse::compress(data)
}

pub fn decompress(data: &[u8]) -> Result<Vec<u8>, &'static str> {
    lzfse::decompress(data)
}
