use crate::carwriter::CARWriter;

pub fn build_pdf_fallback_car(_name: &str) -> Vec<u8> {
    let writer = CARWriter::new("macosx");
    writer.build()
}

// --- Auto-generated 1:1 definition shims ---

pub fn main() {}
