use crate::ciede2000::compute_image_ciede2000;
use crate::quality_metrics::{compute_edge_preservation, compute_psnr, compute_ssim};
use serde_json::json;

/// Human Ergonomics Ergonomic Safety Standard:
/// - ΔE00 <= 1.0 (CIEDE2000 JND threshold: 100% human observer imperceptibility)
/// - PSNR >= 45.0 dB (virtually mathematical lossless)
/// - SSIM >= 0.99 (structural integrity)
/// - Edge Preservation >= 0.99 (sharp font/text/UI edges)
#[derive(Debug, Clone)]
pub struct ErgonomicHumanVisionReport {
    pub is_imperceptible_to_all_humans: bool,
    pub delta_e_00: f64,
    pub psnr_db: f64,
    pub ssim: f64,
    pub edge_preservation: f32,
    pub jnd_status: String,
}

pub fn evaluate_human_visual_ergonomics(
    orig_bgra: &[u8],
    comp_bgra: &[u8],
    width: usize,
    height: usize,
) -> ErgonomicHumanVisionReport {
    let psnr = compute_psnr(orig_bgra, comp_bgra);
    let ssim = compute_ssim(orig_bgra, comp_bgra);
    let edge_pres = compute_edge_preservation(orig_bgra, comp_bgra, width, height);

    // Extract RGB for CIEDE2000
    let count = std::cmp::min(orig_bgra.len(), comp_bgra.len()) / 4;
    let mut orig_rgb = Vec::with_capacity(count * 3);
    let mut comp_rgb = Vec::with_capacity(count * 3);

    for i in 0..count {
        orig_rgb.push(orig_bgra[i * 4 + 2]); // R
        orig_rgb.push(orig_bgra[i * 4 + 1]); // G
        orig_rgb.push(orig_bgra[i * 4]);     // B

        comp_rgb.push(comp_bgra[i * 4 + 2]);
        comp_rgb.push(comp_bgra[i * 4 + 1]);
        comp_rgb.push(comp_bgra[i * 4]);
    }

    let delta_e_00 = compute_image_ciede2000(&orig_rgb, &comp_rgb);

    // Strict Ergonomic Threshold: ΔE00 <= 1.0, PSNR >= 45dB, SSIM >= 0.99, Edge >= 0.99
    let is_imperceptible = delta_e_00 <= 1.0 && psnr >= 45.0 && ssim >= 0.99 && edge_pres >= 0.99;

    ErgonomicHumanVisionReport {
        is_imperceptible_to_all_humans: is_imperceptible,
        delta_e_00,
        psnr_db: psnr,
        ssim,
        edge_preservation: edge_pres,
        jnd_status: if is_imperceptible {
            "PERFECT_HUMAN_IMPERCEPTIBLE_JND".to_string()
        } else {
            "REJECTED_HERGONOMICS_FALLBACK_TO_BIT_EXACT".to_string()
        },
    }
}

pub fn get_ergonomics_json(report: &ErgonomicHumanVisionReport) -> serde_json::Value {
    json!({
        "is_imperceptible_to_all_humans": report.is_imperceptible_to_all_humans,
        "delta_e_00_iso_cie_11664": report.delta_e_00,
        "psnr_db": report.psnr_db,
        "ssim": report.ssim,
        "edge_preservation_score": report.edge_preservation,
        "jnd_status": report.jnd_status
    })
}
