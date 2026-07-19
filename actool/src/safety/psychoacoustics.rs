use crate::audio::compute_signal_to_noise_ratio_db;

/// Human Auditory Ergonomics (Psychoacoustics):
/// Minimum SNR >= 80.0 dB guarantees that audio noise floor remains below the threshold of
/// human perception in quiet listening conditions across all age groups.
pub const HUMAN_PERCEPTUAL_AUDIO_SNR_THRESHOLD_DB: f64 = 80.0;

pub fn evaluate_human_auditory_safety(
    original_pcm16: &[i16],
    processed_pcm16: &[i16],
) -> (bool, f64) {
    let snr_db = compute_signal_to_noise_ratio_db(original_pcm16, processed_pcm16);
    let is_safe = snr_db >= HUMAN_PERCEPTUAL_AUDIO_SNR_THRESHOLD_DB;
    (is_safe, snr_db)
}
