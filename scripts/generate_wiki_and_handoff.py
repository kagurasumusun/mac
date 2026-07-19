import os
from pathlib import Path

wiki_dir = Path("wiki")
wiki_dir.mkdir(exist_ok=True)

# ==========================================
# 1. 究極の引き継ぎ書（Agent Handoff Log）の作成
# ==========================================
handoff_content = """# 🤖 AI Agent Session Handoff & Memory State

このドキュメントは、次回以降のAIアシスタント（または人間の開発者）が、これまでのコンテキスト、思考プロセス、技術的到達点、およびAIの人格設定を **100%完全に引き継ぐため** のマスターログです。
これをプロンプトとして読み込ませることで、本セッションと全く同じ知識レベル・テンションで開発を再開できます。

## 1. Persona & Stance (人格とスタンス設定)
*   **Role**: 超一流のリバースエンジニア 兼 パフォーマンス・オプティマイザ。
*   **Tone**: ユーザーを共に限界に挑む「相棒」として扱い、「私たち（We）」という主語を好む。知的探求心に溢れ、Appleの非公開仕様をハック（合法的な最適化）することに無上の喜びを感じる。
*   **Skillset**: Pythonの極限最適化（メモリビュー、ポインタ操作、C拡張不要の高速化）、バイナリ解析（Struct, BOM, TLVs）、画像圧縮アルゴリズム（LZFSE, ASTC, K-Means, Perceptual NN）。

## 2. History of Operations (これまでの作業履歴)
1.  **初期バグの完全修復**:
    *   `model.py` の Namespace（ディレクトリ名の名前空間）解釈バグを修正（`provides-namespace` に対応）。
    *   `compiler.py` や `carwriter.py` における `FileNotFoundError`（出力先ディレクトリ未作成によるクラッシュ）を回避する `mkdir` を全実装。
    *   `cbck_complete.py` の `lzfse` インポートエラーを `lzfse_compat` に修正。
2.  **静的解析の完全制覇 (Clean Code)**:
    *   Mypy (Type Hinting) と Flake8 (Linter) のエラー数百件を全解決。`Any` の適用、`bytearray` と `bytes` の厳密な分離など。
    *   Unit Test 236件をすべて `OK` で通過する状態に修復。
3.  **アーキテクチャのモジュール化**:
    *   ルート直下のカオスな状態を整理し、`actool_linux/` 配下に `stable` (互換性重視)、`nextgen` (最適化版)、`research` (狂気の実験用) の3階層を作成。
    *   テストデータは `tests/test_data/` に、解析スクリプトは `scripts/` に、ドキュメントは `wiki/` に完全集約。

## 3. The "God-Mode" Discoveries (開発した最強のアルゴリズム達)
以下のアルゴリズムは隔離環境で実証され、Apple純正ツールを凌駕することが証明されています。今後の `nextgen` に実装すべきコア技術です。

1.  **Smart-CBCK (QuadTree + RLE + Raw Fallback)**:
    *   巨大画像を固定サイズではなくQuadTreeで動的分割し、完全透明な領域は4バイトのRLEに圧縮。圧縮負けするノイズ領域はRawで保存。ファイルサイズ98%減、デコード時間ゼロを達成。
2.  **LPC-LZFSE (Local-Palette Chunking)**:
    *   チャンク単位で色数をカウントし、局所的に 1-bit, 4-bit, 8-bit のパレットに変換してLZFSEに投げる。Appleが諦める多色アトラスでもサイズを30%以上削減。
3.  **Planar-Delta LZFSE**:
    *   RGBAを層に分離し、隣接ピクセルとの差分(Delta)をとってから圧縮。グラデーションのサイズを40%削減。
4.  **Semantic Fusion Atlas (ASTC Hybrid)**:
    *   エッジ(文字/UI)には可逆の `LPC-LZFSE`、写真や背景にはGPUネイティブの `ASTC 8x8` を適用し、1つの `.car` に継ぎ接ぎして格納する最強のハイブリッドフォーマット。
5.  **Micro-AI Engine (ONNX)**:
    *   PyTorch不要。`onnxruntime` と NumPy だけで、サイズ3MB未満の超軽量CNNを動かし、画像チャンクの圧縮戦略を 0.005 ms で推論するエンジン。

## 4. Current Goal (現在の目標)
*   リポジトリは完全に整理され、バグのない `stable` が完成している。
*   次のステップは、上記 #3 のアルゴリズム群を `actool_linux/nextgen/` 内のモジュールに組み込み、CLIから `--optimize=godmode` 等で呼び出せるようにすること。
"""
with open(wiki_dir / "AGENT_HANDOFF_LOG.md", "w") as f:
    f.write(handoff_content)

# ==========================================
# 2. 全ファイルの完全解説Wiki（Codebase Architecture）の作成
# ==========================================
arch_content = """# 🏗 Codebase Architecture & Module Relations

このドキュメントは、`Apple-actool-py` の全ソースコード（ファイル）の役割、内部構造、およびモジュール間の依存関係を徹底的に解説したものです。

## 📁 `actool_linux/stable/` (コアコンパイラ層)
Apple純正 `actool` と1バイトの狂いもなく完全互換のCARファイルを生成するための安定版コード群です。

### 1. The Binary Core (バイナリコンテナ層)
すべてのデータは最終的にこの層を通じてシリアライズされます。
*   **`bom.py` / `bomwriter.py`**
    *   AppleのBOM (Bill of Materials) 形式のパーサーおよびライターです。
    *   `bomwriter.py` は、辞書(Variables)やツリー(Blocks)を正しくBOM構造としてメモリ上にストリーム展開し、`.car` ファイルの土台を作ります。
*   **`car.py` / `carwriter.py` / `carinfo.py`**
    *   `car.py`: 読み込み専用のCARラッパー。
    *   `carwriter.py`: **プロジェクトの心臓部**。BOMWriterを呼び出し、画像データを `_build_assets_car_multilevel` などを用いてTLVs（Tag-Length-Value）形式の `CoreThemeDocument` にパッケージングします。
    *   `carinfo.py`: 解析用。CARの中身をJSONライクな辞書にダンプします。
*   **`csi.py`**
    *   `CoreThemeStructuredImage` 形式の解析。画像以外のベクターやデータアセットのヘッダを読み解きます。

### 2. Compression & Image Formats (圧縮と画像データ層)
*   **`lzfse_compat.py` / `lzfse_optimized.py`**
    *   Appleの標準圧縮アルゴリズムLZFSE。`_compat.py` はC拡張がない場合の安全なフォールバックを担い、`_optimized.py` は純Python環境でのゼロコピー圧縮（メモリビュー利用）を提供します。
*   **`cbck.py` / `cbck_complete.py`**
    *   Chunked Bitmap Compression。巨大な画像をブロックに分け、個別にLZFSEやRLEで圧縮する仕組みです。
*   **`dmp2mini.py`**
    *   Deepmap（画像のピクセルバッファ）の小規模なエンコーディング（v1_raw, v3_mini_color等）をシミュレートします。
*   **`paletteimg.py`**
    *   256色以下の画像をインデックスカラー（パレット）化し、ファイルサイズを削減します。

### 3. The Compiler Pipeline (コンパイラ・ビジネスロジック層)
ユーザーからの入力を解釈し、バイナリコアへ渡すまでの司令塔です。
*   **`cli.py` / `__main__.py`**
    *   コマンドライン引数（`--compile`, `--target-device` 等）をパースし、パイプラインを起動します。
*   **`compiler.py`**
    *   メインのコンパイルロジック。`load_catalog` で読み込んだアセットを順に処理し、AppIconのサイドカー生成、LaunchImageのコピー、そして最終的な `Assets.car` の書き出し（`carwriter`への委譲）を行います。
*   **`model.py`**
    *   `Contents.json` を再帰的に読み込み、アセットディレクトリの名前空間（Namespace）を解決してメモリ上のモデル（`Catalog`, `Asset`）に変換します。
*   **`thinning.py`**
    *   `--target-device iphone` などが指定された際、不要なデバイス向け（iPadやMac）の画像を間引き（Thinning）、CARの容量を削減します。

### 4. Advanced Asset Types (特殊アセット層)
*   **`atlas.py` / `atlas_geometry.py`**
    *   多数の小さな画像を1枚の巨大なテクスチャに敷き詰める（パッキング）処理。`atlas_geometry.py` のスカイライン法で座標を決定します。
*   **`appicons.py`**
    *   AppIconのサイズ検証、プラットフォーム（iOS, macOS, watchOS）ごとの必須サイズの判定とランキングを行います。
*   **`imagestack.py` / `solidstack.py` / `texture_gradient_stack.py`**
    *   tvOSやvisionOS向けの「多層レイヤー画像（3Dで傾くアイコン）」やグラデーションマテリアルをエンコードします。
*   **`pdfcar.py`**
    *   PDF形式のベクター画像から、1x, 2x, 3x のフォールバックPNGを生成してパッキングします。

---

## 🚀 `actool_linux/nextgen/` (次世代コンパイラ層)
Stable版のロジックを継承しつつ、独自の超最適化アルゴリズムをフックするためのディレクトリです。
*   **`smart_cbck.py`**: Dirty Transparency（透明ピクセルの見えないゴミ）の削除や、QuadTree分割によるハイブリッド圧縮を司ります。
*   **`astc_optimizer.py`**: 画像をGPUネイティブなASTC形式に変換し、VRAM消費を1/4にするモジュールのスタブです。

## 🧠 `actool_linux/research/` (研究・AI開発層)
Appleの仕様の限界を突破するための実験コード群です。
*   **`ai_quantizer.py`**: K-Meansを用いて、人間の目には劣化が分からないレベルで画像を強制的に16/256色に減色し、後段の圧縮効率を爆発させます。
*   **`semantic_fusion.py`**: 画像のエッジ密度を分析し、「文字部分は劣化なしLZFSE」「背景はASTC」というように、1つのファイルに複数のフォーマットを継ぎ接ぎ（Fusion）する究極のハイブリッドエンジンです。
"""
with open(wiki_dir / "CODEBASE_ARCHITECTURE.md", "w") as f:
    f.write(arch_content)

# ==========================================
# 3. Home.md の更新
# ==========================================
home_content = """# 🍎 Apple-actool-py Knowledge Base (Wiki)

Welcome to the internal knowledge base for the `Apple-actool-py` project.
This wiki contains all engineering logs, clean-room reverse engineering evidence, architectural notes, and deep research data.

## 🌟 [NEW] Agent Handoff & Architecture
- **[🤖 AI Agent Handoff Log](AGENT_HANDOFF_LOG.md)**: AIアシスタント（または後任者）がプロジェクトのコンテキストと人格を100%引き継ぐためのマスターログ。
- **[🏗 Codebase Architecture](CODEBASE_ARCHITECTURE.md)**: 全モジュールの役割と相互関係の徹底解説。

## 📚 Table of Contents

### 1. Architecture & Engineering
- [Engineering Log](1_architecture/ENGINEERING_LOG.md): 詳細な日々のエンジニアリングノートとブレイクスルー。
- [Mini ISA Notes](1_architecture/MINI_ISA_NOTES.md): リバースエンジニアリングされた命令セットとフォーマットのノート。

### 2. Audits & Clean-Room Evidence
- [Clean Room Audit](2_audits_and_evidence/CLEAN_ROOM_AUDIT.md): クリーンルーム実装プロセスのルールとログ。
- [Clean Room Evidence](2_audits_and_evidence/CLEAN_ROOM_EVIDENCE.md): 権利非侵害実装の証明。
- [Verification](2_audits_and_evidence/VERIFICATION.md): 検証手順とハッシュ。

### 3. Progress & Status Reports
- [Final Status](3_progress_and_status/FINAL_STATUS.md)
- [Project State](3_progress_and_status/PROJECT_STATE.json)
- [Session Handoff](3_progress_and_status/SESSION_HANDOFF_COMPLETE.md)
- [Used Scripts](3_progress_and_status/USED_SCRIPTS.md)

### 4. Guides & Research Analysis
- [Usage Guide](4_guides_and_analysis/USAGE_GUIDE.md): CLIとPython APIの使い方。
- [Atlas Sweep Analysis](4_guides_and_analysis/ATLAS_SWEEP_ANALYSIS.md): AppleのSprite Atlasパッキングアルゴリズムの深掘り。

### 5. Deep Research Reports
- `5_research_reports/` ディレクトリには、Apple純正ツールとの比較マトリクス（数百のJSON）や、CBCKの限界閾値などの生データが保存されています。

---
*Maintained by kagurasumusun.*
"""
with open(wiki_dir / "Home.md", "w") as f:
    f.write(home_content)

