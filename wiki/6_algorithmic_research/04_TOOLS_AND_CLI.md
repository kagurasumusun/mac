# 🛠 Developer Tools, CAREditor API, Virtual Storage & Non-Image Engine (Master Specification)

このドキュメントは、`actool_rs` / `actool_linux` に搭載されているコマンドラインツール（CLI）、対話型 `.car` 編集エンジン（`CAREditor`）、仮想ストレージマウント/同期システム（`mount.rs`）、破損 CAR 自動修復リカバリエンジン（`repair.rs`）、および非画像アセット専門最適化エンジン（`nonimage_optimizer.rs`）の完全仕様書である。

---

## 1. Command Line Interface (CLI) Engine

`actool-rs`（Rust 高速バイナリ）および `actool-linux`（Python 互換レイヤ）は、Apple 純正 `actool` のコマンドライン引数およびビルドオプションと 100% のフラグ互換性を持つ。

### 1.1 CLI オプション仕様

```bash
actool-rs [catalogs...] --compile <out_dir> [options]
```

| フラグ | パラメータ | 説明 |
| :--- | :--- | :--- |
| `--compile` | `<directory>` | 生成物（`Assets.car`, `BrandAssets.car`）を出力するディレクトリパス |
| `--platform` | `<platform>` | ターゲットプラットフォーム (`iphoneos`, `macosx`, `appletvos`, `watchos`, `xros`) |
| `--minimum-deployment-target` | `<version>` | 最小展開ターゲット OS バージョン (例: `15.0`) |
| `--app-icon` | `<name>` | アプリケーションアイコン名（ビルドに含める特定の AppIconSet 指定） |
| `--optimize` | `<mode>` | 最適化モード (`smart`, `hybrid`, `alpha`, `omni`, `omega`, `experimental-nonimage`) |
| `--export-dependency-info` | `<path>` | ビルド情報・依存関係 plist XML の出力パス |
| `--output-format` | `<format>` | CLI 出力フォーマット (`human`, `xml-plist`) |

---

## 2. CAREditor API (`editor.rs`)

`CAREditor` は、既存の `.car` アーカイブをオンメモリにロードし、個別アセットの差分差替え、追加、削除、および再シリアライズを可能にする対話型プログラマブル API である。

### 2.1 API メソッド構造

```rust
pub struct CAREditor {
    pub platform: String,
    pub renditions: HashMap<String, AssetRendition>,
}

impl CAREditor {
    // CAR ファイルのロード & CSI 解読
    pub fn load<P: AsRef<Path>>(car_path: P) -> Result<Self, String>;

    // 画像アセットの追加または差替え（即座に CSI パッキング）
    pub fn add_or_replace_image(&mut self, name: &str, bgra: &[u8], width: u32, height: u32);

    // アセットの削除
    pub fn remove_asset(&mut self, name: &str) -> bool;

    // 変更後の .car ファイルとしての書き出し
    pub fn save<P: AsRef<Path>>(&self, output_path: P) -> Result<(), String>;
}
```

---

## 3. Virtual Storage Mounting & Sync Engine (`mount.rs`)

`.car` アーカイブを一般的なファイルシステムディレクトリとして「仮想マウント」し、外部ツール（Finder, Xcode, スクリプト等）で編集した後に双方向同期を行う機能。

```
+-------------------+      mount_car_to_directory()       +-------------------+
|  Assets.car       | ─────────────────────────────────► | Mounted Directory |
|  (BOM Binary)     |                                     | - HomeIcon.png    |
+-------------------+                                     | - ProfileIcon.png |
          ▲                sync_directory_to_car()        | - manifest.json   |
          └────────────────────────────────────────────── +-------------------+
```

### 3.1 マウント処理 (`mount_car_to_directory`)
1. `.car` アーカイブを展開し、含まれるすべての CSI レンディションを抽出。
2. マウント先ディレクトリに `{Asset_Name}.png` として個別に保存。
3. `mount_manifest.json` を生成し、メタデータ（元 CAR パス、アセット総数、Read/Write フラグ）を記録。

### 3.2 同期処理 (`sync_directory_to_car`)
1. マウント先ディレクトリ内の更新・追加された `.png` ファイルを自動スキャン。
2. CSI 形式または直接 BGRA データとしてパッキング。
3. 新しい `Assets.car` としてシリアライズ保存。

---

## 4. Corrupted CAR Auto-Repair Recovery Engine (`repair.rs`)

ヘッダ破壊、ビット化け、あるいは未完了書き込みによって壊れた `.car` アーカイブから、残存する CSI レンディションを全自動スキャンして救出・再生するエンジン。

### 4.1 修復アルゴリズム (`repair_corrupted_car`)
1. **BOMStore Magic 復元**: ファイル先頭が `b"BOMStore"` で壊れている場合、ヘッダの再再構築フラグを立てる。
2. **CSI シグネチャリニアスキャン**: バイトバッファ全体を 1 バイト刻みでリニア走査し、`b"ISTC"` または `b"CSIR"` マジックパターンを探す。
3. **CSI ヘッダー解析**: マジック発見位置から 184 バイトの CSI 固定ヘッダ構造体をパース。正常な CSI であれば名前・寸法・スケールを取得して `AssetRendition` として救出。
4. **CAR 再構築**: 救出された全レンディションを新しく正常な `BOMWriter` で再構築し、完全に正常動作する `.car` ファイルを再出力。

---

## 5. Non-Image Specialized Optimization Engines (`nonimage_optimizer.rs`)

非画像データ（`.dataset`）や特殊データ形式に対する高度なサイズ削減エンジン。**デフォルトでは原調バイト列（100% Lossless）が保持され、`--optimize=experimental-nonimage` 明示的指定時のみ有効化**される。

### 5.1 JSON & Lottie Animation Optimizer (`optimize_json_lottie`)
- **Minification**: 不要なホワイトスペース・改行コードの削除。
- **Float Quantization**: アニメーションキーフレーム座標の浮動小数点精度を 4 桁（`0.12345678` $\rightarrow$ `0.1235`）に打ち切り。
- **LZFSE**: 構造化コード圧縮。

### 5.2 Uncompressed PCM Audio Optimizer (`optimize_pcm_audio_advanced`)
- **Silence Tail Trimming**: 音声末尾の不可聴領域（$-90\text{ dB}$ 以下の消音サンプル）を自動検出してカット。
- **1D Sample Delta Prediction**: 隣接サンプル間の差分（Delta）を計算し、LZFSE のエントロピー圧縮率を爆発的に高める。

### 5.3 3D Mesh Geometry Quantizer (`optimize_3d_mesh_geometry`)
- **Vertex Quantization**: 3D OBJ / Mesh の 32-bit float 頂点座標 (`v x y z`) を高精度固定少数に量子化し、LZFSE 圧縮。

---

*Verified across all operating systems with full test coverage.*
