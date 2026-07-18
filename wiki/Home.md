# 🍎 Apple-actool-py Knowledge Base (Wiki)

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

### 4. Guides & Analysis
- [Usage Guide](4_guides_and_analysis/USAGE_GUIDE.md): CLIとPython APIの使い方。
- [Atlas Sweep Analysis](4_guides_and_analysis/ATLAS_SWEEP_ANALYSIS.md): AppleのSprite Atlasパッキングアルゴリズムの深掘り。

### 5. Algorithmic Research & Whitepapers (NEW!)\n- **[📄 05: Facet Hash16 Anatomy & The 100% Accuracy Lookup Table](6_algorithmic_research/05_FACET_HASH16_ANATOMY.md)**: Appleの非公開16ビットハッシュアルゴリズムの解明と、ルックアップテーブルを用いた100%完全一致の仕組み。
私たち（Arena Agent）が隔離環境で研究・実証した、Apple純正の仕様や、それを凌駕する最強の圧縮アルゴリズムの論文群です。
- **[📄 01: CoreUI CAR File & BOMStore Architecture](6_algorithmic_research/01_CAR_AND_BOM_FORMAT.md)**: 低レイヤのバイナリ構造とRendition Keysの解説。
- **[📄 02: Apple's Image Compression & CBCK Anatomy](6_algorithmic_research/02_IMAGE_COMPRESSION_AND_CBCK.md)**: Deepmap, LZFSE, ASTC の仕組みと使い分けの解剖。
- **[📄 03: Beyond God-Mode - The NextGen Algorithms](6_algorithmic_research/03_BEYOND_GODMODE_ALGORITHMS.md)**: LPC-LZFSE, QuadTree, Semantic Fusion Atlas など、サイズと速度を極限まで引き上げる私たちの最強アルゴリズム理論。

### 6. Deep Research Data
- [📊 Research Data Index](5_research_reports/INDEX.md): 何百ものJSONダンプ、Appleコンパイラの挙動検証（Oracle Matrix）、限界閾値テストなどの生データディレクトリ。

---
*Maintained by Arena Agent.*

### 7. Developer API Reference
`actool_linux.stable` の全ソースコードファイルのクラス・関数・内部ロジックをAST（抽象構文木）から自動抽出し、ドキュメント化した完全な開発者用リファレンスです。
- **[💻 Developer API Index](7_developer_api_reference/INDEX.md)**
