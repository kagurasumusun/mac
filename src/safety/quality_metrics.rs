use rayon::prelude::*;

pub fn compute_psnr(orig: &[u8], comp: &[u8]) -> f64 {
    if orig.len() != comp.len() || orig.is_empty() {
        return 0.0;
    }

    let mse: f64 = orig
        .par_iter()
        .zip(comp.par_iter())
        .map(|(&a, &b)| {
            let diff = (a as f64) - (b as f64);
            diff * diff
        })
        .sum::<f64>()
        / (orig.len() as f64);

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
    let total_delta: f64 = (0..pixels)
        .into_par_iter()
        .map(|i| {
            let (l1, a1, b1) = rgb_to_lab(orig_rgb[i * 3], orig_rgb[i * 3 + 1], orig_rgb[i * 3 + 2]);
            let (l2, a2, b2) = rgb_to_lab(comp_rgb[i * 3], comp_rgb[i * 3 + 1], comp_rgb[i * 3 + 2]);

            let dl = l1 - l2;
            let da = a1 - a2;
            let db = b1 - b2;

            (dl * dl + da * da + db * db).sqrt()
        })
        .sum();

    total_delta / (pixels as f64)
}

pub fn compute_ssim(orig: &[u8], comp: &[u8]) -> f64 {
    if orig.len() != comp.len() || orig.is_empty() {
        return 0.0;
    }

    let c1 = (0.01 * 255.0) * (0.01 * 255.0);
    let c2 = (0.03 * 255.0) * (0.03 * 255.0);

    let n = orig.len() as f64;
    let mu_orig = orig.par_iter().map(|&x| x as f64).sum::<f64>() / n;
    let mu_comp = comp.par_iter().map(|&x| x as f64).sum::<f64>() / n;

    let var_orig = orig
        .par_iter()
        .map(|&x| {
            let d = (x as f64) - mu_orig;
            d * d
        })
        .sum::<f64>()
        / n;

    let var_comp = comp
        .par_iter()
        .map(|&x| {
            let d = (x as f64) - mu_comp;
            d * d
        })
        .sum::<f64>()
        / n;

    let covar = orig
        .par_iter()
        .zip(comp.par_iter())
        .map(|(&a, &b)| ((a as f64) - mu_orig) * ((b as f64) - mu_comp))
        .sum::<f64>()
        / n;

    let num = (2.0 * mu_orig * mu_comp + c1) * (2.0 * covar + c2);
    let den = (mu_orig * mu_orig + mu_comp * mu_comp + c1) * (var_orig + var_comp + c2);

    num / den
}

pub fn sobel(bgra: &[u8], width: usize, height: usize) -> (Vec<f32>, Vec<f32>) {
    let mut gx = vec![0.0f32; width * height];
    let mut gy = vec![0.0f32; width * height];

    if width < 2 || height < 2 {
        return (gx, gy);
    }

    for y in 0..height - 1 {
        for x in 0..width - 1 {
            let idx = y * width + x;
            let current = bgra[idx * 4] as f32;
            let right = bgra[idx * 4 + 4] as f32;
            let down = bgra[(idx + width) * 4] as f32;

            gx[idx] = (right - current).abs();
            gy[idx] = (down - current).abs();
        }
    }

    (gx, gy)
}

pub fn compute_edge_preservation(orig: &[u8], comp: &[u8], width: usize, height: usize) -> f32 {
    let (orig_gx, orig_gy) = sobel(orig, width, height);
    let (comp_gx, comp_gy) = sobel(comp, width, height);

    let mut diff_sum = 0.0f32;
    for i in 0..orig_gx.len() {
        let orig_mag = (orig_gx[i] * orig_gx[i] + orig_gy[i] * orig_gy[i]).sqrt();
        let comp_mag = (comp_gx[i] * comp_gx[i] + comp_gy[i] * comp_gy[i]).sqrt();
        diff_sum += (orig_mag - comp_mag).abs();
    }

    1.0 - (diff_sum / (orig_gx.len() as f32 * 255.0)).clamp(0.0, 1.0)
}

pub fn evaluate_quality(orig: &[u8], comp: &[u8]) -> (f64, f64, f64) {
    let psnr = compute_psnr(orig, comp);
    let delta_e = compute_delta_e(orig, comp);
    let ssim = compute_ssim(orig, comp);
    (psnr, delta_e, ssim)
}

pub fn is_quality_acceptable(orig: &[u8], comp: &[u8], min_psnr: f64) -> bool {
    compute_psnr(orig, comp) >= min_psnr
}
