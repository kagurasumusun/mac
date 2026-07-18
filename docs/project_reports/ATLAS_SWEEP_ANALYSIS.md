# Atlas Sweep Analysis - 2026-07-17

## 概要
37ケースのアトラススイートをApple actoolとactool-linuxでコンパイルし、差分を解析しました。

## 修正内容
**v4パレットdmp2構造バグ修正** (commit: a5f76ae)
- packed.py: _atlas_dmp2関数からu32長プレフィックスを削除
- Apple形式: `header(16) + swatches(4*nsw) + mini_isa_stream`
- 旧形式: `header(16) + swatches(4*nsw) + u32_length + LZFSE_stream`
- テスト更新: test_atlas_and_links_roundtrip

## 差分解析結果

### 全体統計 (37ケース)
```
total_mismatches = 316
hash_only        = 258 (81.6%)  - facet hash16の違い（cosmetic）
payload_diff     =  37 (11.7%)  - ペイロード長の違い（全ケース）
size_diff        =  21 ( 6.6%)  - アトラスサイズの違い
```

### 残存する差分の詳細

#### 1. Facet Hash16 (258件 - cosmetic)
- **原因**: kCRThemeIdentifierNameのハッシュ関数が未解明
- **影響**: 機能的には問題なし（FACETKEYSレジストリが正しいマッピングを提供）
- **解析状況**: 93ペア収集済み、線形モデルでは説明不可、最終ミキシング関数が未特定
- **優先度**: 低（cosmetic）

#### 2. Payload Length (37件 - 全ケース)
- **原因**: Appleはmini ISAエンコーディング使用、actool-linuxはLZFSE使用
- **影響**: ペイロードサイズが数倍〜数十倍大きい（例: 179B vs 1464B）
- **解析状況**:
  - MLEC + dmp2構造は解明済み
  - v4パレットヘッダー形式は修正済み
  - mini ISAストリーム形式は部分的に解明（v3-mini 1-swatchは実装済み）
  - マルチスウォッチmini ISAは未実装
- **優先度**: 中（サイズ効率の問題、機能は正常）

#### 3. Atlas Size (21件)
- **原因**: パッカーのジオメトリ違い（guillotine vs MaxRects）
- **影響**: アトラスサイズが異なる（例: 144x120 vs 118x128）
- **解析状況**: AppleのMaxRects実装は未解明
- **優先度**: 低（機能は正常、メモリ効率の問題）

## Apple dmp2形式の解析

### MLECヘッダー (32 bytes)
```
offset  size  field
0       4     signature "MLEC"
4       4     mode (2=opaque, 0=translucent)
8       4     codec (11)
12      4     total_payload_length
16      4     version (1)
20      4     encoding (4 for BGRA, 2 for GA)
24      4     inner_payload_length
28      4     reserved (0)
```

### dmp2 v4 Palette形式
```
offset  size  field
0       4     signature "dmp2"
4       1     version (4)
5       1     nplanes (1)
6       1     nswatches_byte
7       1     bpp_byte (4)
8       2     width (u16 LE)
10      2     height (u16 LE)
12      2     nswatches (u16 LE)
14      2     bpp (u16 LE = 4)
16      4*n   swatches (BGRA)
16+4*n  ...   mini ISA stream (長さプレフィックスなし)
```

### mini ISAストリーム構造（観察例: s12_units 42x32）
```
68 01 00        - セクションイントロ
f0 12           - ゼロラン (18+25=43 pixels, first bias)
6e 07 f1        - グループオペコード（未解明）
6e 0c f1        - グループオペコード
...
38 2a           - 行コピー (dist=42, len=42)
f0 ff f0 ff f0 53 - ゼロラン（継続）
...
e2 00 00        - 終了マーカー（even pixel count）
06 00 00 00 00 00 00 00 - テール
```

### 未解明のオペコード
- `6N XX`: グループペイント（パレットインデックスとラン長をエンコード）
- `fX`: 短いゼロラン
- 正確なバイアス値とエンコーディング規則

## 今後の作業

### 短期（次回セッション）
1. **マルチスウォッチmini ISAエンコーダー実装**
   - 基本RLEエンコーダー（f0, e1, 38オペコード）
   - Appleストリームとの比較検証
   - ペイロードサイズ削減の効果測定

2. **facet hash16関数の解明**
   - 追加データ収集（200+ペア）
   - 非線形ミキシング関数の特定
   - 実装と検証

### 中期
3. **CoreUI 900台以前の解析**
   - tart/lume環境の構築
   - 古いmacOS (12.x, 13.x, 14.x) の起動
   - 古いXcode (14.x, 15.x, 16.x) のインストール
   - CoreUI 700, 800, 850, 918 のdmp2形式解析
   - 下位互換性の検証

4. **IconStack writer parity**
   - layout 1019/1020/1021 の完全実装
   - tvOS brandassets compositor

### 長期
5. **Apple LZFSE品質の改善**
   - bvx2テーブルの解析
   - 圧縮率の向上

6. **CBCK band-chunking heuristic**
   - Appleの行/チャンクヒューリスティックの解明

## テスト結果
- ローカル: 236 tests OK (11 skipped)
- リモートMac: 236 tests OK (11 skipped)
- Push: a5f76ae → origin/actool

## 環境情報
- ローカル: Linux (解析・開発)
- リモート: macOS 26.4 / Xcode 26.5 (検証・push)
- セッション: NjmPCuLO3zfzL9Vl43yi@uptermd.upterm.dev
