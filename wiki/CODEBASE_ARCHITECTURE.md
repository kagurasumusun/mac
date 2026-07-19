# 🏗 Codebase Architecture & 100% Pure Rust Architecture (`Apple-Toolsets`)

このドキュメントは、**`Apple-Toolsets`** （旧 `Apple-actool-py`）の 100% Pure Rust リファレンス実装における全 57 モジュールの役割、内部データフロー、並列処理モデル、および依存関係の徹底解説である。

---

## 1. 100% Pure Rust Workspace Architecture

リポジトリは 100% Pure Rust (`apple-toolsets`) へ完全移行され、トップレベルの `src/` ディレクトリに集約されました。

```
Apple-Toolsets/ (1 Branch: main)
├── Cargo.toml               # パッケージ設定 & 実行バイナリ定義
├── Cargo.lock               # 依存関係バージョンロック
├── src/                     # 100% Pure Rust ソースコード構造
│   ├── lib.rs               # パブリック API Re-export (1:1 API 互換)
│   ├── main.rs / bin/       # 実行バイナリ (actool-rs, car-info, car-repack, pdf-car)
│   ├── core/                # [1] Low-Level BOM, CAR, B-Tree & CSI バイナリコア
│   ├── codecs/              # [2] Rayon 並列 LZFSE, CBCK, DMP2, ASTC コーデック層
│   ├── safety/              # [3] ISO/CIE 11664-6 & 人間工学安全ガードレール層
│   ├── assets/              # [4] スプライトアトラス, 多層スタック, PBR 3D, 音声層
│   └── tools/               # [5] コンパイラ, CAREditor API, マウント, 修復エンジン
├── wiki/                    # 1:20 情報密度のマスター技術仕様書体系
└── tests/                   # Native Rust 統合テストスイート (20/20 Passed, 0 Warnings)
```

---

## 2. 57 Modules Breakdown (機能階層別マッピング)

### 2.1 Core Submodule (`src/core/`) — コンテナ・ストレージ層
- **`bom.rs`**: BOMStore 32 バイトヘッダ・インデックステーブル・変数テーブルのパーサー。
- **`bomwriter.rs`**: Big-Endian BOMStore アロケータおよびブロックビルダー。
- **`car.rs`**: `CARHEADER` (436B) および `KEYFORMAT` の解析ラッパー。
- **`carwriter.rs`**: CAR アーカイブ全体の最終組み立てと B-Tree 構築。
- **`carinfo.rs`**: `.car` インスペクションおよび構造ツリー JSON ダンプ。
- **`coreui.rs`**: CoreUI プロファイル解決 (`CoreUIProfile`)。
- **`csi.rs`**: 184 バイト CSI ヘッダパース（`ISTC`/`CTSI`）および TLV ビルダー。
- **`facet_hash_lookup.rs`**: 16 ビット Polynomial Hash16 と 100% 精度ルックアップテーブル。
- **`multi_database.rs`**: 複数 CAR データベースの併合・衝突解決。
- **`tree.rs`**: BOM B-Tree デスクリプタ (`b"tree"`) およびノード読み込み器。
- **`zero_code_db.rs`**: ベゼル（Bezel）・グリフ（Glyph）・エフェクトデータベース。

### 2.2 Codecs Submodule (`src/codecs/`) — 画像コーデック・圧縮・タイリング層
- **`lzfse.rs`**: 純粋 LZFSE パススルーおよびストリーム圧縮/解凍。
- **`lzfse_compat.rs` / `lzfse_optimized.rs`**: 高速ハッシュ検索付き LZFSE ブロックコンプレッサ。
- **`cbck.rs`**: MLEC Mode 3 Codec 4/11 CBCK チャンクエンコーダ（Rayon 並列処理）。
- **`cbck_complete.rs`**: 2D チャンクサイズ動的最適化付き CBCK コーデック。
- **`smart_cbck.rs`**: Dirty Alpha 洗浄 ＆ エントロピー予測型 CBCK エンコーダ。
- **`dmp2mini.rs`**: Deepmap v1, v2, v3 (Mini ISA), v4 形式の処理。
- **`paletteimg.rs`**: インデックスカラーパレット化（`MLEC` Codec 8）。
- **`ultrahd.rs`**: 4K/8K/16K 画像の 2D 空間格子（Spatial Grid）タイリング。
- **`astc_native.rs`**: 128-bit Native ASTC GPU-Direct ハードウェアブロックエンコーダ。
- **`astc_compression.rs` / `astc_optimized.rs` / `astc_optimizer.rs`**: ASTC 圧縮シミュレータとオプティマイザ。
- **`planar_delta_lzfse.rs`**: B/G/R/A チャネル分離＋1D 差分予測＋LZFSE。
- **`lpc_lzfse.rs`**: ローカルパレット量子化＋LZFSE。
- **`hybrid_compression.rs`**: マルチ手法同時評価型ハイブリッドコンプレッサ。
- **`alpha_compression.rs`**: ALPHA 並列コンプレッサ。
- **`nexus_compression.rs`**: Predictive DPCM, YCoCg, Wavelet, DCT 候補競合エンコーダ。
- **`omega_compression.rs` / `omega_plus.rs`**: 品質閾値ゲート付き OMEGA エンコーダ。
- **`omni_compression.rs` / `omniv2_compression.rs` / `ultimate_compression.rs`**: OMNI / Ultimate エンコーダ。
- **`tet_complete.rs`, `tet_compression.rs`, `tet_full.rs`, `tet_ultimate.rs`, `tet_variants.rs`**: 3,193 技法分類 TET 圧縮エンジン群。
- **`ai_quantizer.rs`**: Floyd-Steinberg ディザリング付き知覚減色器。
- **`semantic_fusion.rs`**: エッジ密度領域別セマンティック異種アトラス結合器。

### 2.3 Safety Submodule (`src/safety/`) — 人間工学・安全ガードレール層
- **`ciede2000.rs`**: ISO/CIE 11664-6 CIEDE2000 ($\Delta E_{00}$) JND 色差計算関数。
- **`quality_metrics.rs`**: PSNR, SSIM, Sobel エッジ保存度計算関数。
- **`ergonomics.rs`**: 人間視覚工学（HVS）弁別限界評価器。
- **`psychoacoustics.rs`**: 人間聴覚系（HAS）80dB SNR ノイズフロア評価器。
- **`autosafe.rs`**: **AutoDomainDetect 4 ゲート安全システム & Dirty Alpha 自動保護**。

### 2.4 Assets Submodule (`src/assets/`) — アセット型・アトラス・3D・メディア層
- **`atlas.rs` / `atlas_geometry.rs` / `packed.rs`**: スプライトアトラスパッキング & LINK レンディション (Layout 1003) 生成。
- **`appicons.rs`**: プラットフォーム別 AppIcon スケール・解像度評価ランキング。
- **`imagestack.rs` / `iconstack.rs` / `solidstack.rs`**: tvOS/visionOS 向け多層イメージ・アイコンスタック合成。
- **`texture.rs` / `texture_gradient_stack.rs`**: テクスチャ参照 Payload (`RTXT`) 及びグラデーション (`ARGG`) 解析。
- **`arresource.rs`**: ARKit 参照画像物理寸法メタデータシリアライザ。
- **`model3d.rs`**: PBR ORM テクスチャ結合 (66% VRAM 削減) & 接空間 2 チャンネルノーマルマップ。
- **`media.rs` / `audio.rs`**: シャノンエントロピー $H$ 解析、メディア分類器、PCM 1D Delta オーディオ圧縮。
- **`pdfcar.rs`**: Vector PDF ラスタライズ/コンパイル。
- **`thinning.rs`**: ターゲット Idiom/Scale フィルタリング (Thinning)。

### 2.5 Tools Submodule (`src/tools/`) — コンパイラ・編集・マウント・工具層
- **`capabilities.rs` / `diagnostics.rs` / `legacy_coreui_features.rs`**: Apple プラットフォーム診断 & plist フォーマッタ。
- **`catalog.rs` / `model.rs`**: `Contents.json` 解釈とパス安全解決 (`safe_resolve_file`)。
- **`compiler.rs`**: アセットカタログ (`.xcassets`) コンパイルパイプライン司令塔。
- **`cli.rs`**: コマンドライン引数パース・エントリポイント。
- **`editor.rs`**: オンメモリ CAR 編集 API (`CAREditor`)。
- **`mount.rs`**: 仮想ストレージマウント/双方向同期システム。
- **`nonimage_optimizer.rs`**: Lottie JSON 精度打切り, PCM 消音カット+1D Delta, 3D OBJ 頂点量子化。
- **`repack.rs` / `repair.rs`**: 壊れた CAR の自動救出修復 & BOM アロケーション再構成。

---

## 3. High Performance Parallel Execution (Rayon Thread Pools)

1. **CBCK Parallel Compression**:
   各帯状チャンクの LZFSE 圧縮を Rayon `.par_iter()` で全コアへ分散。
2. **Planar Delta 4-Plane Parallel Encoding**:
   `B`, `G`, `R`, `A` の 4 つの色平面の差分予測を 4 スレッド並列実行。
3. **Multi-Candidate Race Evaluation**:
   候補圧縮ストリームを全スレッドで並列実行し、最短バイト数を選択。
4. **Ultra-HD Tiled Grid 2D Parallel Pipeline**:
   16K/8K/4K 画像の 2D 空間タイル格子をロックフリーで並列エンコード。

---

*This architecture specification reflects the 100% Pure Rust build of Apple-Toolsets.*
