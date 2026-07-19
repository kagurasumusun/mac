# 📦 CoreUI CAR File & BOMStore Binary Architecture (Master Specification)

このドキュメントは、Apple のクローズドなアセットアーカイブ形式である **`.car` (CoreUI Archive)** ファイルおよびそのバイナリ基盤である **`BOMStore` (Bill of Materials Store)** 形式のバイトレベル完全解剖仕様書である。

本仕様書は、`actool_linux`（Python 版）および `actool_rs`（Rust 版）の 1:1 実装に基づき、ヘッダオフセット、エンディアン、B-Tree ノード構造、Rendition Key の次元属性、および CSI（CoreStructuredImage）ヘッダ・TLV（Tag-Length-Value）の全フィールドを網羅的に解説する。

---

## 1. The BOMStore Container (バイナリコンテナ層)

すべての `.car` ファイルは、Mac OS X / iOS のパッケージ管理やテーマ管理で使われる汎用バイナリコンテナ **`BOMStore`** 構造として構成されている。すべての多バイト数値は **Big-Endian（ネットワークバイトオーダー）** で格納される。

```
+-------------------------------------------------------------------------+
| BOMHeader (32 Bytes)                                                    |
| Magic: b"BOMStore", Version: 1, Block Count, Offsets & Lengths          |
+-------------------------------------------------------------------------+
| Block Payload Area (Variable Size)                                      |
| Block 1 (CARHEADER), Block 2 (KEYFORMAT), Block 3... (CSIs, Trees)      |
+-------------------------------------------------------------------------+
| Block Index Table (Capacity * 8 + 4 Bytes)                              |
| Capacity, [Offset (u32), Length (u32)] x Capacity                       |
+-------------------------------------------------------------------------+
| Variables Table (Variable Size)                                         |
| Count, [Block ID (u32), Name Length (u8), Name (UTF-8 Bytes)] x Count    |
+-------------------------------------------------------------------------+
```

### 1.1 BOMHeader (32-Byte 固定メインヘッダ)

BOMStore ファイルの先頭 32 バイトに位置する構造体：

| オフセット | 型 / サイズ | フィールド名 | 説明 / 期待値 |
| :--- | :--- | :--- | :--- |
| `0..8` | `char[8]` | `magic` | 必す `b"BOMStore"` (ASCII 8 bytes) |
| `8..12` | `uint32_t` | `version` | バージョン番号。常に `1` (0x00000001) |
| `12..16` | `uint32_t` | `block_count` | 有効なブロック数ヒント (`capacity - 1`) |
| `16..20` | `uint32_t` | `index_offset` | ブロックインデックステーブルの絶対ファイルオフセット |
| `20..24` | `uint32_t` | `index_length` | ブロックインデックステーブルのバイト長 (`4 + capacity * 8`) |
| `24..28` | `uint32_t` | `vars_offset` | 変数テーブル (`Variables`) の絶対ファイルオフセット |
| `28..32` | `uint32_t` | `vars_length` | 変数テーブルのバイト長 |

### 1.2 Block Index Table (ブロックインデックステーブル)

ファイル内の任意のデータ領域（「ブロック」と呼称）を 1-based インデックス ID（1, 2, 3, ...）で高速参照するためのテーブル。

1. **`capacity` (`uint32_t`, 4 bytes)**: インデックスエントリーの総数（`ID = 0` 用のヌルエントリー含む）。
2. **`Block Entry Array` (`capacity * 8` bytes)**:
   - 各エントリーは **8 バイト**：
     - `offset` (`uint32_t`, 4 bytes): ブロックペイロードの絶対ファイルオフセット。未割り当てブロックの場合は `0`。
     - `length` (`uint32_t`, 4 bytes): ブロックペイロードのバイト長。未割り当てブロックの場合は `0`。
   - `ID = 0` は予約済みのアドレスであり、常に `offset = 0, length = 0` である。

### 1.3 Variables Table (変数テーブル)

文字列の変数名（例: `"CARHEADER"`, `"RENDITIONS"`）と、その実体データが格納されている BOM ブロック ID とを紐付けるルックアップディクショナリ。

1. **`count` (`uint32_t`, 4 bytes)**: 登録されている変数の個数。
2. **`Variable Entry Array`**:
   - `block_id` (`uint32_t`, 4 bytes): 紐付け対象の BOM ブロック ID。
   - `name_length` (`uint8_t`, 1 byte): 変数名文字列のバイト長 $N$。
   - `name` (`char[N]`, $N$ bytes): UTF-8 エンコードされた変数名（ヌル終端なし）。

#### 定義される標準 CoreUI 変数一覧
* **`CARHEADER`**: アセットアーカイブ全体のバージョン・作成メタデータ。
* **`KEYFORMAT`**: レンディションキーの属性次元順序定義ブロック（`kfmt`）。
* **`EXTENDED_METADATA`**: 作成ツール、ターゲット OS、ビルド環境情報（`META`）。
* **`FACETKEYS`**: アセット名（`AppIcon`, `HomeButton` 等）とハッシュ/ID のマッピングを保持する B-Tree。
* **`RENDITIONS`**: 実際の CSI レンディションデータが格納されたメイン B-Tree。
* **`APPEARANCEKEYS`**: ダークモード・ハイコントラスト等の外観定義 B-Tree。
* **`LOCALIZATIONKEYS`**: 言語・地域ごとのローカライズキー B-Tree。

---

## 2. CoreUI Archive Header (`CARHEADER`)

BOM 変数 `"CARHEADER"` が指すブロックには、436 バイトの固定長ヘッダ構造体が格納される。

```
+-------------------------------------------------------------------------+
| CARHeader (436 Bytes)                                                   |
| Magic (4B): "CTAR" (Big) / "RATC" (Little)                              |
| CoreUI Version (4B): 975, Storage Version (4B): 1                       |
| Storage Timestamp (4B): Epoch, Rendition Count (4B)                     |
| Main Version (128B UTF-8), Version String (256B UTF-8)                 |
| Checksum UUID (16B Hex UUID)                                            |
| Associated Checksum (4B), Schema Version (4B): 1                        |
| ColorSpace ID (4B): 1, Key Semantics (4B): 1                            |
+-------------------------------------------------------------------------+
```

| オフセット | 型 / サイズ | フィールド名 | 説明 |
| :--- | :--- | :--- | :--- |
| `0..4` | `char[4]` | `magic` | `b"CTAR"` (Big-Endian) または `b"RATC"` (Little-Endian) |
| `4..8` | `uint32_t` | `core_ui_version` | CoreUI フォーマットバージョン（標準: `975`） |
| `8..12` | `uint32_t` | `storage_version` | ストレージスキーマバージョン（標準: `1`） |
| `12..16` | `uint32_t` | `storage_timestamp` | アーカイブ作成時の UNIX タイムスタンプ |
| `16..20` | `uint32_t` | `rendition_count` | アーカイブ内に含まれる総レンディション数 |
| `20..148` | `char[128]` | `main_version` | コンパイラ識別文字列（例: `"actool-rs 0.1.0"`） |
| `148..404` | `char[256]` | `version_string` | ビルド詳細・詳細バージョン情報 |
| `404..420` | `uint8_t[16]` | `uuid` | ランダム生成された 128-bit UUID (v4) |
| `420..424` | `uint32_t` | `associated_checksum` | チェックサム値（初期値: `0`） |
| `424..428` | `uint32_t` | `schema_version` | スキーマバージョン（標準: `1`） |
| `428..432` | `uint32_t` | `color_space_id` | デフォルト色空間 ID（標準 sRGB: `1`） |
| `432..436` | `uint32_t` | `key_semantics` | キーセマンティクスフラグ（標準: `1`） |

---

## 3. Key Format Descriptor (`KEYFORMAT`)

BOM 変数 `"KEYFORMAT"` が指すブロックは、レンディションキーに含まれる検索次元（Attributes）の並び順を定義する。

```
+-------------------------------------------------------------------------+
| KeyFormat Header                                                        |
| Magic (4B): "kfmt" (Big) / "tmfk" (Little)                              |
| Reserved (4B): 0                                                        |
| Num Attributes (4B): N                                                  |
| Attributes Array: uint32_t[N] (Key Attribute IDs)                       |
+-------------------------------------------------------------------------+
```

### 定義可能な Attribute ID（次元属性マッピング）

Apple CoreUI 仕様で定義されている全 28 種類の属性 ID：

| ID | 定義定数名 | 意味 / 役割 |
| :---: | :--- | :--- |
| `0` | `kCRThemeLookName` | ルックアンドフィール識別子 |
| `1` | `kCRThemeElementName` | UIエレメント種別 (例: Icon=12, Asset=9) |
| `2` | `kCRThemePartName` | パート種別 (例: AppIcon=181) |
| `3` | `kCRThemeSizeName` | UIサイズ定義 (Small, Medium, Large) |
| `4` | `kCRThemeDirectionName` | 描画方向 (LTR, RTL) |
| `5` | `kCRThemePlaceholderName` | プレースホルダーフラグ |
| `6` | `kCRThemeValueName` | UIステート値 |
| `7` | `kCRThemeAppearanceName` | 外観テーマ (Any=0, Dark=1, Tinted=2) |
| `8` | `kCRThemeDimension1Name` | スプライトアトラスのページ番号（Page Serial） |
| `9` | `kCRThemeDimension2Name` | 拡張次元 2 |
| `10` | `kCRThemeStateName` | コントロール状態 (Normal, Pressed, Disabled) |
| `11` | `kCRThemeLayerName` | レイヤーインデックス |
| `12` | `kCRThemeScaleName` | 解像度スケール (1x=1, 2x=2, 3x=3) |
| `13` | `kCRThemeLocalizationName` | 言語・地域識別子 (Universal=0) |
| `14` | `kCRThemePresentationStateName` | プレゼンテーション状態 |
| `15` | `kCRThemeIdiomName` | デバイスドメイン (Universal=0, iPhone=1, iPad=2, TV=3, Watch=5, Mac=7, Vision=8) |
| `16` | `kCRThemeSubtypeName` | デバイスサブタイプ |
| `17` | `kCRThemeIdentifierName` | アセット固有 Facet Hash16 識別子 |
| `18` | `kCRThemePreviousValueName` | 移行前ステート値 |
| `19` | `kCRThemePreviousStateName` | 移行前コントロール状態 |
| `20` | `kCRThemeSizeClassHorizontalName` | 水平サイズクラス (Any=0, Compact=1, Regular=2) |
| `21` | `kCRThemeSizeClassVerticalName` | 垂直サイズクラス (Any=0, Compact=1, Regular=2) |
| `22` | `kCRThemeMemoryClassName` | RAM容量要求クラス |
| `23` | `kCRThemeGraphicsClassName` | GPU描画性能クラス (Metal Feature Set) |
| `24` | `kCRThemeDisplayGamutName` | ディスプレイ色域 (sRGB=0, Display P3=1) |
| `25` | `kCRThemeDeploymentTargetName` | 最小展開ターゲット OS |
| `26` | `kCRThemeGlyphWeightName` | SF Symbol フォントウエイト |
| `27` | `kCRThemeGlyphSizeName` | SF Symbol フォントサイズ |

---

## 4. BOM B-Tree Architecture (`b"tree"`)

`RENDITIONS` や `FACETKEYS` などの動的データベースは、BOMStore 内の **B-Tree** 構造として保持される。

### 4.1 B-Tree Descriptor Block (32 バイト固定記述子)

BOM 変数が指す最初のブロックには、B-Tree のルート情報を記述した `b"tree"` ブロックが配置される：

| オフセット | 型 / サイズ | フィールド名 | 説明 |
| :--- | :--- | :--- | :--- |
| `0..4` | `char[4]` | `magic` | 常に `b"tree"` (ASCII 4 bytes) |
| `4..8` | `uint32_t` | `version` | バージョン。常に `1` |
| `8..12` | `uint32_t` | `root_block` | ルートノードが格納されている BOM ブロック ID |
| `12..16` | `uint32_t` | `node_size` | 各ノードのブロックサイズ（標準: `4096` bytes） |
| `16..20` | `uint32_t` | `record_count` | ツリー全体の総レコード数 |
| `20..21` | `uint8_t` | `flags` | フラグ（予約済み `0`） |
| `21..25` | `uint32_t` | `key_size` | インデックスキーの固定バイト長（例: Rendition Key は `12` bytes） |

### 4.2 B-Tree Node / Leaf Block (12 バイトノードヘッダ + 8 バイトペア)

B-Tree の各ノードブロック（ルートノード・リーフノード）は、以下の構造を持つ：

1. **Node Header (12 Bytes)**:
   - `is_leaf` (`uint16_t`, 2 bytes): リーフノードなら `1`、内部枝ノードなら `0`。
   - `count` (`uint16_t`, 2 bytes): このノードに含まれるエントリー数。
   - `forward` (`uint32_t`, 4 bytes): 次の兄弟ノードの BOM ブロック ID（末尾なら `0`）。
   - `backward` (`uint32_t`, 4 bytes): 前の兄弟ノードの BOM ブロック ID（先頭なら `0`）。
2. **Entry Array (`count * 8` Bytes)**:
   - 各エントリーは **8 バイト** の 2 つの BOM ブロック参照ポインタからなる：
     - `value_block_id` (`uint32_t`, 4 bytes): 実体データ（CSI ブロックなど）が格納された BOM ブロック ID。
     - `key_block_id` (`uint32_t`, 4 bytes): 検索キー（12 バイトの Rendition Key など）が格納された BOM ブロック ID。

---

## 5. CoreStructuredImage (CSI) Rendition Architecture

`RENDITIONS` ツリーの `value_block_id` が指す実体データは、**`CoreStructuredImage` (CSI)** フォーマットでカプセル化されている。

```
+-------------------------------------------------------------------------+
| CSI Fixed Header (184 Bytes)                                            |
| Magic (4B): "ISTC" / "CTSI", Version: 1, Width, Height, Scale           |
| Pixel Format (4B): BGRA / 8AG / COLR / DATA / AS44 / AS88              |
| Layout (4B): 1000 Direct, 1002 Stack, 1003 Link, 1004 Atlas             |
| Asset Name (128B Null-Padded UTF-8)                                     |
| Offset 168..172: TLV Length (u32)                                       |
| Offset 172..176: Flag 1 (u32)                                           |
| Offset 176..180: Zero (u32)                                             |
| Offset 180..184: Payload Length (u32)                                   |
+-------------------------------------------------------------------------+
| TLV Stream Area (Variable Size = TLV Length)                            |
| Tag (u32), Length (u32), Value (bytes)...                               |
+-------------------------------------------------------------------------+
| Rendition Compressed Payload (Variable Size = Payload Length)          |
| LZFSE Stream / CBCK MLEC Container / ASTC Hardware Blocks / Raw Bytes   |
+-------------------------------------------------------------------------+
```

### 5.1 CSI Fixed Header (184 バイト固定ヘッダフィールド詳細)

| オフセット | 型 / サイズ | フィールド名 | 説明 |
| :--- | :--- | :--- | :--- |
| `0..4` | `char[4]` | `magic` | `b"ISTC"` (Little-Endian) または `b"CTSI"` (Big-Endian) |
| `4..8` | `uint32_t` | `version` | CSI バージョン。常に `1` |
| `8..12` | `uint32_t` | `flags` | レンディション属性フラグ |
| `12..16` | `uint32_t` | `width` | 画像/アセットの横幅 (Pixels) |
| `16..20` | `uint32_t` | `height` | 画像/アセットの縦幅 (Pixels) |
| `20..24` | `uint32_t` | `scale_factor` | スケールファクター $\times 100$（例: 1x=`100`, 2x=`200`, 3x=`300`） |
| `24..28` | `char[4]` | `pixel_format` | 4CC 四文字コード (`BGRA`, ` 8AG`, `COLR`, `DATA`, `ATAD`, `AS44`, `AS88`) |
| `28..32` | `uint32_t` | `color_space_id` | 色空間 ID（sRGB=`1`, Display P3=`2`） |
| `32..36` | `uint32_t` | `layout` | レイアウト種別（`1000`=Direct, `1002`=Stack, `1003`=Link, `1004`=Atlas） |
| `36..40` | `uint32_t` | `reserved0` | 予約領域 (`0`) |
| `40..168` | `char[128]` | `name` | アセットのファイル名文字列（128バイト ヌル埋め UTF-8） |
| `168..172` | `uint32_t` | `tlv_length` | 後続する TLV ストリーム領域のバイト長 $L_{TLV}$ |
| `172..176` | `uint32_t` | `unknown_flag` | フラグ値。常に `1` |
| `176..180` | `uint32_t` | `zero` | 常に `0` |
| `180..184` | `uint32_t` | `payload_length` | 後続する圧縮ペイロードデータのバイト長 $L_{Payload}$ |

### 5.2 Standard TLVs (Tag-Length-Value メタデータ)

ヘッダ直後の `184` バイト目から $L_{TLV}$ バイト分配置される可変長メタデータ要素。各 TLV は `Tag` (u32, 4B) + `Length` (u32, 4B) + `Value` (Length Bytes) で構成される。

* **Tag `1001` (Slices / Sizing Insets)**: 9-slice スケーラブルボタンの非拡大境界インセット情報。
* **Tag `1003` (Metrics / Bounds)**: レンダリング描画領域のバウンディングボックスサイズ。
* **Tag `1004` (Scale Factor Float)**: 浮動小数点表記のスケールファクター（例: `1.0f`, `2.0f`）。
* **Tag `1006` (Opacity / Blend Mode)**: 100% 不透明 (`1`) か透過あり (`0`) かの描画フラグ。
* **Tag `1007` (Row Bytes / Stride)**: ピクセル行あたりのバイト幅（例: `width * 4`）。
* **Tag `1008` (Color RGBA Value)**: カラーアセット (`.colorset`) の Float 4 チャンネル（`R, G, B, A` 各 32-bit float）。
* **Tag `1010` (LINK / Atlas Reference)**: スプライトアトラス参照 (`INLK` マジック + `x, y, w, h, page` 座標)。
* **Tag `1012` (Layer Stack Identifier List)**: 複合アイコン/レイヤースタックの層構造 ID 配列。

---

*This specification represents the 100% complete, bit-exact binary standard enforced by `actool_rs` and `actool_linux`.*
