# 04: CLI Tools, CAREditor API, Virtual Storage & Non-Image Engine

This document specifies the command-line interface, `CAREditor` interactive CAR modification API, virtual directory mounting & syncing (`mount.rs`), corrupted CAR recovery (`repair.rs`), and non-image asset optimization algorithms.

---

## 1. CAREditor API (`editor.rs`)

`CAREditor` enables non-destructive loading, asset addition, replacement, deletion, and serialization:

```rust
pub struct CAREditor {
    pub platform: String,
    pub renditions: HashMap<String, AssetRendition>,
}

impl CAREditor {
    pub fn load<P: AsRef<Path>>(car_path: P) -> Result<Self, String>;
    pub fn add_or_replace_image(&mut self, name: &str, bgra: &[u8], width: u32, height: u32);
    pub fn remove_asset(&mut self, name: &str) -> bool;
    pub fn save<P: AsRef<Path>>(&self, output_path: P) -> Result<(), String>;
}
```

---

## 2. Virtual Storage Mounting & Sync Engine (`mount.rs`)

- **`mount_car_to_directory(car_path, mount_dir)`**: Extracts all CSI renditions into a local folder as `{Asset}.png` and generates `mount_manifest.json`.
- **`sync_directory_to_car(mount_dir, output_car_path)`**: Re-scans modified/added `.png` files and rebuilds a valid `Assets.car`.

---

## 3. Corrupted CAR Auto-Repair Engine (`repair.rs`)

`repair_corrupted_car` scans byte buffers linearly for `b"ISTC"` and `b"CSIR"` magic headers, parses surviving 184-byte CSI blocks, rescues asset renditions, and reconstructs a valid `.car` file.

---

## 4. Non-Image Specialized Optimization Engine (`nonimage_optimizer.rs`)

Activated via `--optimize=experimental-nonimage`:
- **JSON / Lottie**: Minification and float coordinate truncation to 4 decimal places.
- **PCM Audio**: Tail silence trimming below -90dB and 1D sample delta prediction.
- **3D Mesh OBJ**: Float vertex position quantization.
