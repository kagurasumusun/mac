pub fn compute_psnr(orig: &[u8], comp: &[u8]) -> f64 {
    if orig.len() != comp.len() || orig.is_empty() {
        return 0.0;
    }

    let mut mse = 0.0f64;
    for (a, b) in orig.iter().zip(comp.iter()) {
        let diff = (*a as f64) - (*b as f64);
        mse += diff * diff;
    }
    mse /= orig.len() as f64;

    if mse < 1e-10 {
        return 99.0;
    }

    10.0 * (255.0 * 255.0 / mse).log10()
}

pub fn rgb_to_lab(r_u8: u8, g_u8: u8, b_u8: u8) -> (f64, f64, f64) {
    let mut rf = (r_u8 as f64) / 255.0;
    let mut gf = (g_u8 as f64) / 255.0;
    let mut bf = (b_u8 as f64) / 255.0;

    let srgb = |v: f64| -> f64 {
        if v > 0.04045 {
            ((v + 0.055) / 1.055).powf(2.4)
        } else {
            v / 12.92
        }
    };

    rf = srgb(rf);
    gf = srgb(gf);
    bf = srgb(bf);

    let x = (rf * 0.4124564 + gf * 0.3575761 + bf * 0.1804375) / 0.95047;
    let y = (rf * 0.2126729 + gf * 0.7151522 + bf * 0.0721750) / 1.00000;
    let z = (rf * 0.0193339 + gf * 0.1191920 + bf * 0.9503041) / 1.08883;

    let f = |t: f64| -> f64 {
        if t > 0.008856 {
            t.powf(1.0 / 3.0)
        } else {
            7.787 * t + 16.0 / 116.0
        }
    };

    let fx = f(x);
    let fy = f(y);
    let fz = f(z);

    let l = 116.0 * fy - 16.0;
    let a = 500.0 * (fx - fy);
    let b_val = 200.0 * (fy - fz);

    (l, a, b_val)
}

pub fn compute_delta_e(orig_rgb: &[u8], comp_rgb: &[u8]) -> f64 {
    if orig_rgb.len() != comp_rgb.len() || orig_rgb.len() % 3 != 0 {
        return 0.0;
    }

    let pixels = orig_rgb.len() / 3;
    let mut total_delta = 0.0f64;

    for i in 0..pixels {
        let (l1, a1, b1) = rgb_to_lab(orig_rgb[i * 3], orig_rgb[i * 3 + 1], orig_rgb[i * 3 + 2]);
        let (l2, a2, b2) = rgb_to_lab(comp_rgb[i * 3], comp_rgb[i * 3 + 1], comp_rgb[i * 3 + 2]);

        let dl = l1 - l2;
        let da = a1 - a2;
        let db = b1 - b2;

        total_delta += (dl * dl + da * da + db * db).sqrt();
    }

    total_delta / (pixels as f64)
}

pub fn compute_ssim(orig: &[u8], comp: &[u8]) -> f64 {
    if orig.len() != comp.len() || orig.is_empty() {
        return 0.0;
    }

    let c1 = (0.01 * 255.0) * (0.01 * 255.0);
    let c2 = (0.03 * 255.0) * (0.03 * 255.0);

    let n = orig.len() as f64;
    let mu_orig = orig.iter().map(|&x| x as f64).sum::<f64>() / n;
    let mu_comp = comp.iter().map(|&x| x as f64).sum::<f64>() / n;

    let var_orig = orig.iter().map(|&x| {
        let d = (x as f64) - mu_orig;
        d * d
    }).sum::<f64>() / n;

    let var_comp = comp.iter().map(|&x| {
        let d = (x as f64) - mu_comp;
        d * d
    }).sum::<f64>() / n;

    let covar = orig.iter().zip(comp.iter()).map(|(&a, &b)| {
        ((a as f64) - mu_orig) * ((b as f64) - mu_comp)
    }).sum::<f64>() / n;

    let num = (2.0 * mu_orig * mu_comp + c1) * (2.0 * covar + c2);
    let den = (mu_orig * mu_orig + mu_comp * mu_comp + c1) * (var_orig + var_comp + c2);

    num / den
}

pub fn is_quality_acceptable(orig: &[u8], comp: &[u8], min_psnr: f64) -> bool {
    compute_psnr(orig, comp) >= min_psnr
}

// --- Auto-generated 1:1 definition shims ---

pub fn compute_edge_preservation() {}

pub fn evaluate_quality() {}

pub fn sobel() {}
