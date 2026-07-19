# 🖼 Apple's Image Compression Codecs, Deepmap & CBCK Anatomy (Master Specification)

このドキュメントは、Apple CoreUI および iOS / macOS グラフィックスサブシステムで採用されている非公開画像圧縮コーデック群（**Deepmap `dmp2`**, **CBCK `MLEC/KCBC`**, **Ultra-HD 2D Spatial Tiling**, **ASTC GPU-Direct Hardware Blocks**）の解剖結果および実装仕様書である。

---

## 1. Deepmap (`dmp2`) Grammar & Micro-ISA

`Deepmap` は、PNG や JPEG などの一般的な静止画圧縮形式と異なり、GPU メモリ（VRAM）へ即座に転送可能なピクセルストライド（BGRA / GA8 等）を保ちつつ、CPU の解凍オーバーヘッドを最小化するために Apple が設計した特殊な構造体フォーマットである。

### 1.1 `dmp2` の 4 つの文法バージョン

Apple の CoreUI 描画エンジンは、画像解像度や色数に応じて 4 つの `dmp2` 文法を使い分ける：

```
+-------------------------------------------------------------------------+
| dmp2 Container Header                                                   |
| Magic (4B): "dmp2"                                                      |
| Version (1B), Subversion (1B), Flags (2B)                               |
| Width (u16), Height (u16)                                               |
+-------------------------------------------------------------------------+
  ├── Version 1 (Raw Pass-Through): 生ピクセル直接配置
  ├── Version 2 (LZFSE Stream Frame): 生ピクセルを LZFSE 圧縮
  ├── Version 3 (Mini ISA Stream): 超軽量 RLE/ISA 命令ストリーム解凍
  └── Version 4 (Palette Quantized): 8-bit インデックスカラー + LZFSE
```

#### ① Version 1: `v1_raw` (極小画像・単色フォールバック)
- **適用条件**: 画像サイズが $8$ ピクセル以下（例: $2 \times 4$）、または伸長解凍命令のオーバーヘッドが非圧縮バイト数を上回る場合。
- **構造**: `dmp2` 12 バイトヘッダに続いて、非圧縮の BGRA 生ピクセルバッファ（$W \times H \times 4$ バイト）が直列配置される。

#### ② Version 2: `v2_lzfse` (中間標準)
- **構造**: 12 バイトヘッダの後に 4 バイトのストリーム長 $L_{stream}$ が続き、その直後から純粋な LZFSE 圧縮ストリームが接続される。

#### ③ Version 3: `v3_mini` (DMP2 Mini ISA 命令ストリーム)
- **構造**: 最小限のメモリフットプリントで単色グラデーションや小さな UI アイコンをデコードするためのマイクロプロセッサライクな命令セット（Mini ISA）。

##### DMP2 Mini ISA オコード仕様一覧
- **`0x68 0x01 0x00`**: ISA セクション導入プロローグ。
- **`0xF0 V`**: 透過ピクセル（または背景色）のランレングスエンコーディング（RLE）。初回バイアス 25 / 継続バイアス 16 で繰り越しカウント。
- **`0xF1 .. 0xFE`**: ショートゼロラン（3〜17 ピクセルの短い透過ラン）。
- **`0xE1 XX`**: パレットインデックス/カラーリテラル挿入命令（1 ピクセル展開）。
- **`0x38 0x01`**: 行コピー命令（上の行のピクセル列をそのまま 1 行分複製）。
- **`0xE2 0x00 0x00` / `0xE3 0x00 0x00 0x00`**: ピクセル総数 $\pmod 4$ のアライメント調整用ストリーム終端マーカー。
- **`0x06` + 7-byte zeros**: DMP2 ISA ストリームの最終終端シーケンス（`V3_MINI_TAIL`）。

#### ④ Version 4: `v4_palette` (8-bit インデックスカラーパレット)
- **適用条件**: ユニーク色数が 255 色以下の UI アセット。
- **構造**: Swatch 0（完全透過 `(0,0,0,0)` 用）を予約とし、最大 255 色の RGBA パレットテーブルを保持。ピクセル平面は 8-bit インデックス配列として LZFSE 圧縮される。

---

## 2. CBCK (Chunked Bitmap Compression) Architecture

画面解像度の拡大（4K/8K）や巨大なスプライトアトラスの登場に伴い、単一の LZFSE ストリームで巨大画像を圧縮すると **「一部のアイコンを描画したいだけでも数MBの画像全体を CPU/RAM 上で全解凍しなければならない」** という重大なボトルネックが発生する。

この課題を解決するため、Apple は画像を独立解凍可能な「帯状チャンク」に分割する **CBCK (MLEC / KCBC)** フォーマットを導入した。

```
+-------------------------------------------------------------------------+
| MLEC Container Header (16 Bytes)                                        |
| Magic: b"MLEC", Mode: 3 (u32), Codec: 4/11 (u32), Chunk Count: N (u32)  |
+-------------------------------------------------------------------------+
| KCBC Chunk 1 (16B Header + LZFSE Stream)                                |
| Magic: b"KCBC", Y Offset (u16), Rows (u16), Raw Len (u32), Comp Len...  |
+-------------------------------------------------------------------------+
| KCBC Chunk 2 (16B Header + LZFSE Stream)                                |
+-------------------------------------------------------------------------+
| KCBC Chunk N...                                                         |
+-------------------------------------------------------------------------+
```

### 2.1 MLEC ヘッダ構造 (16 バイト)
- **`magic`** (`char[4]`): 常に `b"MLEC"`。
- **`mode`** (`uint32_t`): 常に `3`（CBCK チャンクモード）。
- **`codec`** (`uint32_t`): `4` (標準 LZFSE チャンク) または `11` (DMP2 内部ラップ)。
- **`chunk_count`** (`uint32_t`): 後続する `KCBC` チャンクの個数 $N$。

### 2.2 KCBC チャンクヘッダ構造 (16 バイト)
- **`magic`** (`char[4]`): 常に `b"KCBC"`。
- **`y_offset`** (`uint16_t`): 画像内におけるこのチャンクの開始 Y 座標 (Pixels)。
- **`rows`** (`uint16_t`): このチャンクに含まれる高さ行数 (Row Count)。
- **`raw_length`** (`uint32_t`): チャンク解凍後の非圧縮バイト数 ($W \times \text{rows} \times 4$)。
- **`compressed_length`** (`uint32_t`): LZFSE 圧縮ストリームのバイト長 $L_{chunk}$。
- **`payload`** (`uint8_t[L_{chunk}]`): LZFSE で圧縮された該当帯領域のピクセルバッファ。

#### Apple 純正 Chunk Raw Cap 閾値
Apple 純正 `actool` の実装解析により、1 チャンクあたりの非圧縮最大容量の上限は **`0x155555` バイト（約 1.39 MB）** に固定されている。`actool_rs` では `rows_per_chunk = max(1, 0x155555 / row_bytes)` を算出し、Rayon スレッドプールを用いて全チャンクを並列エンコード/デコードする。

---

## 3. Ultra-HD 2D Spatial Grid Tiling (4K / 8K / 16K)

8K (7680x4320) や 16K (15360x8640) などの超高解像度画像では、1 行あたりのバイト幅（Stride）が巨大化するため、従来の 1D 帯状分割（Row Bands）ではメモリ溢れが発生する。

`ultrahd.rs` では、解像度ティアに応じて画像を **2D 空間タイル格子（Spatial Grid）** に分割し、Rayon 並列処理で並行エンコードする：

```
+-------------------------------------------------------------------------+
| Ultra-HD Resolution Tier Classification                                 |
+-------------------------------------------------------------------------+
| Standard    : < 3840 px                     -> Row-Band CBCK            |
| 4K Tier     : >= 3840 x 2160 (Max >= 3840)  -> 256 x 256 Tiles          |
| 8K Tier     : >= 7680 x 4320 (Max >= 7680)  -> 512 x 512 Tiles          |
| 16K Tier    : >= 15360 x 8640 (Max >= 15360)-> 1024 x 1024 Tiles        |
+-------------------------------------------------------------------------+
```

各 2D タイルは、自身の `x_offset` および `y_offset` を持った `KCBC` チャンクとして独立生成され、デバイス側での部分空間サンプリングを可能にする。

---

## 4. ASTC GPU-Direct Hardware Block Formatting

Metal API / Apple Silicon（A11 Bionic 以降および M シリーズ GPU）は、**ASTC (Adaptive Scalable Texture Compression)** 128-bit ハードウェアブロックサンプリングユニットを内蔵している。

### 4.1 GPU-Direct ASTC の動作原理
一般的な画像は CPU 上で LZFSE 解凍を行ってから VRAM に転送されるが、`AS44` (Block 4x4) / `AS88` (Block 8x8) フォーマットでエンコードされた CSI レンディションは、**CPU 解凍工程を完全スキップ（0ms）** し、直接 VRAM（Metal テクスチャ領域）にそのままロードされる。

```
+-------------------------------------------------------------------------+
| ASTC GPU-Direct Container Header (16 Bytes)                             |
| Magic: 0x5CB05C00 (4B), BlockX (1B), BlockY (1B), BlockZ: 1 (1B)        |
| Width (24-bit LE, 3B), Height (24-bit LE, 3B), Depth (24-bit LE, 3B)    |
+-------------------------------------------------------------------------+
| 128-bit (16-Byte) ASTC Hardware Block #1                                |
| Mode Header (1B), Endpoints (7B), Weight Grid (8B)                      |
+-------------------------------------------------------------------------+
| 128-bit (16-Byte) ASTC Hardware Block #2...                             |
+-------------------------------------------------------------------------+
```

### 4.2 ASTC 128-bit Hardware Block Descriptor 構造
各 $N \times M$ ピクセルグリッドは、正確に **16 バイト (128-bit)** のハードウェアブロックにパッキングされる：
1. **Mode Header (Byte 0)**: `0xFC` (ASTC LDR RGBA Direct Mode)。
2. **Endpoint Colors (Bytes 1..7)**: グリッド内のカラー最小値/最大値（$R_{min}, R_{max}, G_{min}, G_{max}, B_{min}, B_{max}, A_{max}$）。
3. **Weight Grid (Bytes 8..15)**: 8 バイト（64-bit）の 2-bit ピクセル補間加重格子。

これにより、Metal GPU サンプラーユニットはシェーダー実行時にテクスチャ座標 $(u, v)$ から直接バイリニア補間補正を行いながら展開・描画を実行する。

---

*This document serves as the master engineering reference for image decompression and byte stream parsing across actool_rs.*
