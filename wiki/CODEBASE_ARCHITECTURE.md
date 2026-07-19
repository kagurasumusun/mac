# 🏗 Codebase Architecture & Unified Module Relations (Master Architecture)

このドキュメントは、`actool_linux` (Python 統合パッケージ) および `actool_rs` (Rust リファレンス実装) における全 57 モジュールの役割、内部データフロー、並列処理モデル、および依存関係の徹底解説である。

---

## 1. Top-Level Module Unification (レガシー層の統合とクリーン化)

かつて機能ごとに分散していた `nextgen/`, `research/`, `stable/` などのサブディレクトリは、本バージョンにおいて**トップレベルパッケージ（`actool_linux/`）へ完全に一本化・一元化**されました。古いモジュール参照は一切排除され、単一の明確な構成となっています。

```
/home/user/repo/
├── actool_linux/           # Python 統合パッケージ（全57モジュール）
│   ├── compiler.py         # コンパイルパイプライン司令塔
│   ├── carwriter.py        # BOMStore / CAR バイナリ構築の心臓部
│   ├── csi.py              # CoreStructuredImage 固定ヘッダ & TLV 解析
│   └── ... (全57モジュール)
├── actool_rs/              # 超高速 Rust パラレル実装
│   ├── Cargo.toml          # Rayon, Byteorder, Serde 依存関係
│   ├── src/                # 全57モジュールに対応する Rust ソース
│   └── tests/              # 統合テストスイート（integration_tests.rs）
└── wiki/                   # 技術仕様書・論文ドキュメント群
```

---

## 2. 57 Unified Modules Breakdown (機能階層別マッピング)

### 2.1 Binary Container & Data Store Layer (コンテナ・ストレージ層)
- **`bom.rs` / `bom.py`**: BOMStore 32 バイトヘッダ・インデックステーブル・変数テーブルのパーサー。
- **`bomwriter.rs` / `bomwriter.py`**: Big-Endian BOMStore アロケータおよびブロックビルダー。
- **`car.rs` / `car.py`**: `CARHEADER` (436B) および `KEYFORMAT` の読み込み専用解析ラッパー。
- **`carwriter.rs` / `carwriter.py`**: CAR アーカイブ全体の最終組み立てと B-Tree 構築。
- **`carinfo.rs` / `carinfo.py`**: `.car` インスペクションおよび構造ツリー JSON ダンプ。
- **`csi.rs` / `csi.py`**: 184 バイト CSI ヘッダパース（`ISTC`/`CTSI`）および TLV ビルダー。
- **`tree.rs` / `tree.py`**: BOM B-Tree デスクリプタ (`b"tree"`) およびノード読み込み器。
- **`facet_hash_lookup.rs` / `facet_hash_lookup.py`**: 16 ビット Polynomial Hash16 と 100% 精度ルックアップテーブル。
- **`multi_database.rs` / `multi_database.py`**: 複数 CAR データベースの併合・衝突解決。
- **`zero_code_db.rs` / `zero_code_db.py`**: ベゼル（Bezel）・グリフ（Glyph）・エフェクトデータベース。

### 2.2 Image Codecs, Compressors & Tiling Layer (画像コーデック・圧縮層)
- **`lzfse.rs` / `lzfse_compat.py`**: 純粋 LZFSE パススルーおよびストリーム圧縮/解解凍。
- **`lzfse_optimized.rs` / `lzfse_optimized.py`**: 高速ハッシュ検索付き LZFSE ブロックコンプレッサ。
- **`cbck.rs` / `cbck.py`**: MLEC Mode 3 Codec 4/11 CBCK チャンクエンコーダ（Rayon 並列処理）。
- **`cbck_complete.rs` / `cbck_complete.py`**: 2D チャンクサイズ動的最適化付き CBCK コーデック。
- **`smart_cbck.rs` / `smart_cbck.py`**: Dirty Alpha 洗浄 ＆ エントロピー予測型 CBCK エンコーダ。
- **`dmp2mini.rs` / `dmp2mini.py`**: Deepmap v1, v2, v3 (Mini ISA), v4 形式の処理。
- **`paletteimg.rs` / `paletteimg.py`**: インデックスカラーパレット化（`MLEC` Codec 8）。
- **`ultrahd.rs` / `ultrahd.py`**: 4K/8K/16K 画像の 2D 空間格子（Spatial Grid）タイリング。
- **`astc_native.rs` / `astc_native.py`**: 128-bit Native ASTC GPU-Direct ハードウェアブロックエンコーダ。
- **`astc_compression.rs` / `astc_compression.py`**: ASTC LDR RGBA ブロック擬似シミュレータ。
- **`astc_optimized.rs` / `astc_optimized.py`**: ブロック複雑度解析と終端点補間。
- **`astc_optimizer.rs` / `astc_optimizer.py`**: ASTC 最適化ルーター。
- **`planar_delta_lzfse.rs` / `planar_delta_lzfse.py`**: B/G/R/A チャネル分離＋1D 差分予測＋LZFSE。
- **`lpc_lzfse.rs` / `lpc_lzfse.py`**: ローカルパレット量子化＋LZFSE。
- **`hybrid_compression.rs` / `hybrid_compression.py`**: マルチ手法同時評価型ハイブリッドコンプレッサ。
- **`alpha_compression.rs` / `alpha_compression.py`**: ALPHA 並列コンプレッサ。
- **`nexus_compression.rs` / `nexus_compression.py`**: Predictive DPCM, YCoCg, Wavelet, DCT 候補競合エンコーダ。
- **`omega_compression.rs` / `omega_compression.py`**: 品質閾値ゲート付き OMEGA エンコーダ。
- **`omega_plus.rs` / `omega_plus.py`**: OMEGA+ 高度 RLE/Delta/Predictive エンコーダ。
- **`omni_compression.rs` / `omni_compression.py`**: OMNI コンプレッサ。
- **`omniv2_compression.rs` / `omniv2_compression.py`**: OMNIv2 コンプレッサ。
- **`ultimate_compression.rs` / `ultimate_compression.py`**: ブロック分類型 Ultimate エンコーダ。
- **`tet_complete.rs`, `tet_compression.rs`, `tet_full.rs`, `tet_ultimate.rs`, `tet_variants.rs`**: 3,193 技法分類 TET 圧縮エンジン群。
- **`ai_quantizer.rs` / `ai_quantizer.py`**: Floyd-Steinberg ディザリング付き知覚減色器。
- **`semantic_fusion.rs` / `semantic_fusion.py`**: エッジ密度領域別セマンティック異種アトラス結合器。

### 2.3 Perceptual Quality, Safety & Ergonomics Layer (人間工学・安全ガードレール層)
- **`ciede2000.rs` / `ciede2000.py`**: ISO/CIE 11664-6 CIEDE2000 ($\Delta E_{00}$) JND 色差計算関数。
- **`quality_metrics.rs` / `quality_metrics.py`**: PSNR, SSIM, Sobel エッジ保存度計算関数。
- **`ergonomics.rs` / `ergonomics.py`**: 人間視覚工学（HVS）弁別限界評価器。
- **`psychoacoustics.rs` / `psychoacoustics.py`**: 人間聴覚系（HAS）80dB SNR ノイズフロア評価器。
- **`autosafe.rs` / `autosafe.py`**: **AutoDomainDetect 4 ゲート安全システム & Dirty Alpha 自動保護**。

### 2.4 Advanced Asset Types & Packing Layer (アセット型・アトラス層)
- **`atlas.py` / `atlas.rs`**: 1x ユニバーサル画像の連結アトラス (ZZZZPackedAsset) 生成。
- **`atlas_geometry.py` / `atlas_geometry.rs`**: スカイライン法およびシェルフパッキング位置決定。
- **`packed.py` / `packed.rs`**: アトラス分離と `LINK` レンディション (Layout 1003) 生成。
- **`appicons.py` / `appicons.rs`**: プラットフォーム別 AppIcon スケール・解像度評価ランキング。
- **`imagestack.py` / `imagestack.rs`**: tvOS/visionOS 向け多層イメージスタック合成 (Layout 1002)。
- **`iconstack.py` / `iconstack.rs`**: 3D アイコンスタックグラデーション Payload 解析。
- **`solidstack.py` / `solidstack.rs`**: 単色ソリッドレイヤースタック構造解析。
- **`texture.rs` / `texture.py`**: テクスチャ参照 Payload (`RTXT`) 解析。
- **`texture_gradient_stack.rs` / `texture_gradient_stack.py`**: グラデーションストップ Payload (`ARGG`) 解析。
- **`arresource.rs` / `arresource.py`**: ARKit 参照画像物理寸法メタデータシリアライザ。
- **`model3d.rs` / `model3d.py`**: PBR ORM テクスチャ結合 (66% VRAM 削減) & 接空間 2 チャンネルノーマルマップ。
- **`media.rs` / `media.py`**: シャノンエントロピー $H$ 解析とメディア分類器。
- **`pdfcar.rs` / `pdfcar.py`**: Vector PDF ラスタライズ/コンパイル。
- **`thinning.rs` / `thinning.py`**: ターゲット Idiom/Scale フィルタリング (Thinning)。

### 2.5 Non-Image Optimizers, Editing & Tools Layer (編集・ツール・非画像層)
- **`nonimage_optimizer.rs` / `nonimage_optimizer.py`**: Lottie JSON 精度打切り, PCM 消音カット+1D Delta, 3D OBJ 頂点量子化。
- **`editor.rs` / `editor.py`**: オンメモリ CAR 編集 API (`CAREditor`)。
- **`mount.rs` / `mount.py`**: 仮想ストレージマウント/双方向同期システム。
- **`repair.rs` / `repair.py`**: 壊れた CAR からの CSI シグネチャ自動救出修復エンジン。
- **`repack.rs` / `repack.py`**: BOM アロケーションテーブル最適化再構成。
- **`compiler.rs` / `compiler.py`**: アセットカタログ (`.xcassets`) コンパイルパイプライン。
- **`cli.rs` / `cli.py`**: コマンドライン引数パース・エントリポイント。
- **`catalog.rs` / `catalog.py`**: `Contents.json` 解釈とパス安全解決 (`safe_resolve_file`)。
- **`coreui.rs` / `coreui.py`**: プロファイル解決 (`CoreUIProfile`)。
- **`capabilities.rs` / `capabilities.py`**: 機能検出フラグ。
- **`diagnostics.rs` / `diagnostics.py`**: 診断メッセージと Apple plist XML 契約フォーマッタ。
- **`legacy_coreui_features.rs` / `legacy_coreui_features.py`**: 互換機能レイヤ。

---

## 3. High Performance Parallel Architecture (Rayon Thread Pools)

`actool_rs` では、CPU コアを 100% 活用するため Rayon データ並列スレッドプールを組み込んでいます：

1. **CBCK Row-Bands Parallel Compression**:
   各帯状チャンクの LZFSE 圧縮を Rayon `.par_iter()` で全コアへ分散。
2. **Planar Delta 4-Plane Parallel Encoding**:
   `B`, `G`, `R`, `A` の 4 つの色平面の差分予測を 4 スレッド並列実行。
3. **Multi-Candidate Candidate Race Evaluation**:
   NEXUS / ALPHA / OMEGA で提案される複数圧縮ストリーム候補を全スレッドで並列圧縮し、最短バイト数を選択。
4. **Ultra-HD Tiled Grid 2D Parallel Pipeline**:
   16K/8K/4K 画像の全 2D 空間タイル格子をロックフリーで並列エンコード。

---

*This master architectural diagram reflects the production system state as of July 2026.*
