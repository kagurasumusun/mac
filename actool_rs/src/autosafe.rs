use crate::lzfse;
use crate::quality_metrics::{compute_delta_e, compute_psnr, compute_ssim};
use serde_json::json;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SafetyLevel {
    StrictLossless, // Zero modification allowed (100% bit-exact)
    PerceptualSafe, // PSNR > 40dB, ΔE < 2.3, SSIM > 0.95
    CustomShaderSafe, // Preserves exact RGB in alpha=0 regions for custom GPU shaders
}

#[derive(Debug, Clone)]
pub struct OptimizationReport {
    pub is_lossless: bool,
    pub dirty_alpha_detected: bool,
    pub preserved_dirty_alpha: bool,
    pub psnr_db: f64,
    pub delta_e: f64,
    pub ssim: f64,
    pub applied_strategy: String,
}

pub fn auto_safe_compress(
    bgra: &[u8],
    width: u32,
    height: u32,
    asset_kind: &str,
    safety_level: SafetyLevel,
) -> (Vec<u8>, OptimizationReport) {
    let count = (width * height * 4) as usize;
    if bgra.len() < count || count == 0 {
        let compressed = lzfse::compress(bgra);
        return (
            compressed,
            OptimizationReport {
                is_lossless: true,
                dirty_alpha_detected: false,
                preserved_dirty_alpha: false,
                psnr_db: 99.0,
                delta_e: 0.0,
                ssim: 1.0,
                applied_strategy: "lzfse_passthrough".to_string(),
            },
        );
    }

    // 1. Inspect Alpha Channel for Dirty Alpha
    let mut dirty_alpha_count = 0usize;
    for px in bgra.chunks_exact(4) {
        if px[3] == 0 && (px[0] > 0 || px[1] > 0 || px[2] > 0) {
            dirty_alpha_count += 1;
        }
    }

    let dirty_alpha_detected = dirty_alpha_count > 0;
    let must_preserve_dirty_alpha = dirty_alpha_detected
        && (safety_level == SafetyLevel::CustomShaderSafe
            || safety_level == SafetyLevel::StrictLossless
            || asset_kind == "data"
            || asset_kind == "texture");

    // 2. Non-image datasets / StrictLossless / CustomShaderSafe with dirty alpha -> Pure Lossless LZFSE
    if safety_level == SafetyLevel::StrictLossless || asset_kind == "data" || must_preserve_dirty_alpha {
        let compressed = lzfse::compress(bgra);
        return (
            compressed,
            OptimizationReport {
                is_lossless: true,
                dirty_alpha_detected,
                preserved_dirty_alpha: dirty_alpha_detected,
                psnr_db: 99.0,
                delta_e: 0.0,
                ssim: 1.0,
                applied_strategy: "strict_lossless_lzfse".to_string(),
            },
        );
    }

    // 3. Candidate: Lossless LZFSE baseline
    let default_compressed = lzfse::compress(bgra);

    // 4. Candidate: Clean Alpha
    if !must_preserve_dirty_alpha && dirty_alpha_detected {
        let mut cleaned = bgra.to_vec();
        for px in cleaned.chunks_exact_mut(4) {
            if px[3] == 0 {
                px[0] = 0;
                px[1] = 0;
                px[2] = 0;
            }
        }

        let cleaned_compressed = lzfse::compress(&cleaned);
        if cleaned_compressed.len() < default_compressed.len() {
            return (
                cleaned_compressed,
                OptimizationReport {
                    is_lossless: true,
                    dirty_alpha_detected: true,
                    preserved_dirty_alpha: false,
                    psnr_db: 99.0,
                    delta_e: 0.0,
                    ssim: 1.0,
                    applied_strategy: "lossless_clean_alpha_lzfse".to_string(),
                },
            );
        }
    }

    // 5. Candidate: Perceptual Quality-Gated Subtle Optimization
    if safety_level == SafetyLevel::PerceptualSafe && !must_preserve_dirty_alpha {
        let mut subtle = bgra.to_vec();
        for px in subtle.chunks_exact_mut(4) {
            px[0] = (px[0] / 4) * 4;
            px[1] = (px[1] / 4) * 4;
            px[2] = (px[2] / 4) * 4;
        }

        let psnr = compute_psnr(bgra, &subtle);
        let delta_e = compute_delta_e(bgra, &subtle);
        let ssim = compute_ssim(bgra, &subtle);

        if psnr >= 40.0 && delta_e <= 2.3 && ssim >= 0.95 {
            let subtle_compressed = lzfse::compress(&subtle);
            if subtle_compressed.len() < default_compressed.len() {
                return (
                    subtle_compressed,
                    OptimizationReport {
                        is_lossless: false,
                        dirty_alpha_detected,
                        preserved_dirty_alpha: false,
                        psnr_db: psnr,
                        delta_e,
                        ssim,
                        applied_strategy: "perceptual_quality_gated".to_string(),
                    },
                );
            }
        }
    }

    (
        default_compressed,
        OptimizationReport {
            is_lossless: true,
            dirty_alpha_detected,
            preserved_dirty_alpha: dirty_alpha_detected,
            psnr_db: 99.0,
            delta_e: 0.0,
            ssim: 1.0,
            applied_strategy: "lossless_fallback".to_string(),
        },
    )
}

pub fn get_safety_report_json(report: &OptimizationReport) -> serde_json::Value {
    json!({
        "is_lossless": report.is_lossless,
        "dirty_alpha_detected": report.dirty_alpha_detected,
        "preserved_dirty_alpha": report.preserved_dirty_alpha,
        "quality_psnr_db": report.psnr_db,
        "quality_delta_e": report.delta_e,
        "quality_ssim": report.ssim,
        "applied_strategy": report.applied_strategy
    })
}
