use crate::quality_metrics::rgb_to_lab;

/// Implements the full CIEDE2000 (ΔE00) Color Difference Formula according to ISO/CIE 11664-6:2014.
/// CIEDE2000 models human visual perception (HVS) with extreme precision, correcting for
/// lightness, chroma, hue, and blue-region non-linearities.
///
/// Threshold: ΔE00 <= 1.0 is the strict Just Noticeable Difference (JND) limit for 100% of human observers.
pub fn compute_ciede2000(lab1: (f64, f64, f64), lab2: (f64, f64, f64)) -> f64 {
    let (l1, a1, b1) = lab1;
    let (l2, a2, b2) = lab2;

    let c1_star = (a1 * a1 + b1 * b1).sqrt();
    let c2_star = (a2 * a2 + b2 * b2).sqrt();
    let c_bar_star = (c1_star + c2_star) / 2.0;

    let c_bar_7 = c_bar_star.powi(7);
    let pow_25_7 = 25.0f64.powi(7);
    let g = 0.5 * (1.0 - (c_bar_7 / (c_bar_7 + pow_25_7)).sqrt());

    let a1_prime = (1.0 + g) * a1;
    let a2_prime = (1.0 + g) * a2;

    let c1_prime = (a1_prime * a1_prime + b1 * b1).sqrt();
    let c2_prime = (a2_prime * a2_prime + b2 * b2).sqrt();

    let h1_prime = if a1_prime == 0.0 && b1 == 0.0 {
        0.0
    } else {
        let mut deg = b1.atan2(a1_prime).to_degrees();
        if deg < 0.0 {
            deg += 360.0;
        }
        deg
    };

    let h2_prime = if a2_prime == 0.0 && b2 == 0.0 {
        0.0
    } else {
        let mut deg = b2.atan2(a2_prime).to_degrees();
        if deg < 0.0 {
            deg += 360.0;
        }
        deg
    };

    let delta_l_prime = l2 - l1;
    let delta_c_prime = c2_prime - c1_prime;

    let delta_h_prime_deg = if c1_prime * c2_prime == 0.0 {
        0.0
    } else if (h2_prime - h1_prime).abs() <= 180.0 {
        h2_prime - h1_prime
    } else if h2_prime - h1_prime > 180.0 {
        h2_prime - h1_prime - 360.0
    } else {
        h2_prime - h1_prime + 360.0
    };

    let delta_h_prime = 2.0 * (c1_prime * c2_prime).sqrt() * ((delta_h_prime_deg / 2.0).to_radians().sin());

    let l_bar_prime = (l1 + l2) / 2.0;
    let c_bar_prime = (c1_prime + c2_prime) / 2.0;

    let h_bar_prime = if c1_prime * c2_prime == 0.0 {
        h1_prime + h2_prime
    } else if (h1_prime - h2_prime).abs() <= 180.0 {
        (h1_prime + h2_prime) / 2.0
    } else if h1_prime + h2_prime < 360.0 {
        (h1_prime + h2_prime + 360.0) / 2.0
    } else {
        (h1_prime + h2_prime - 360.0) / 2.0
    };

    let t = 1.0 - 0.17 * ((h_bar_prime - 30.0).to_radians().cos())
        + 0.24 * ((2.0 * h_bar_prime).to_radians().cos())
        + 0.32 * ((3.0 * h_bar_prime + 6.0).to_radians().cos())
        - 0.20 * ((4.0 * h_bar_prime - 63.0).to_radians().cos());

    let delta_theta = 30.0 * (-(((h_bar_prime - 275.0) / 25.0).powi(2))).exp();

    let c_bar_prime_7 = c_bar_prime.powi(7);
    let r_c = 2.0 * (c_bar_prime_7 / (c_bar_prime_7 + pow_25_7)).sqrt();

    let s_l = 1.0 + (0.015 * (l_bar_prime - 50.0).powi(2)) / (20.0 + (l_bar_prime - 50.0).powi(2)).sqrt();
    let s_c = 1.0 + 0.045 * c_bar_prime;
    let s_h = 1.0 + 0.015 * c_bar_prime * t;

    let r_t = -(r_c * (2.0 * delta_theta.to_radians()).sin());

    let term_l = delta_l_prime / s_l;
    let term_c = delta_c_prime / s_c;
    let term_h = delta_h_prime / s_h;

    (term_l * term_l + term_c * term_c + term_h * term_h + r_t * term_c * term_h).sqrt()
}

pub fn compute_image_ciede2000(orig_rgb: &[u8], comp_rgb: &[u8]) -> f64 {
    if orig_rgb.len() != comp_rgb.len() || orig_rgb.len() % 3 != 0 {
        return 0.0;
    }

    let pixels = orig_rgb.len() / 3;
    let mut total_delta = 0.0f64;

    for i in 0..pixels {
        let lab1 = rgb_to_lab(orig_rgb[i * 3], orig_rgb[i * 3 + 1], orig_rgb[i * 3 + 2]);
        let lab2 = rgb_to_lab(comp_rgb[i * 3], comp_rgb[i * 3 + 1], comp_rgb[i * 3 + 2]);
        total_delta += compute_ciede2000(lab1, lab2);
    }

    total_delta / (pixels as f64)
}
