# Multi-swatch mini ISA — 2026-07-17 時点メモ（作業中・repo未収録）

## 確定に近い規則（v4-mini, 1バイト単位, 検証ケース: n1/n5/m1/m2/m5の一部）
- stream は **bottom-up（flip=1）**。LINK (x,y) は top-down アトラス座標。
- 塗り: 横 halo [x-1, x+w+1)。縦は bottom-2-rows: 行 {y+h-1, y+h}（n1 h=1: {2,3}、n4 B h=1: {5,6}、m1 h=2: {3,4}、n5 h=4: {5,6} で裏付け）。
- 先頭ゼロラン: L0 >= 25 -> `f0 V` (V = L0-25: c02=31, c05=55 で一致)。L0 < 25 -> `fX` (X = L0-9: m1=11, n5=15, m2=13, m5=11, m7=13 で5/5一致)。
- 継続ゼロラン: `f0 V` = V+16 (m1 f006=22, n5 f02e=62 で一致)。
- `38 XX` = row-copy LZ: dist=W、len=XX（n1 3808, m1 380a, n5 380e, m7 380c で一致）。
- rep: `4N V` = V×hi（m1 46 02=2×4）; `5N V` = V×lo（n5 56 02=2×6）。
- bare `fX` (continuation) = ゼロ X+2（n1 f7=9）。
- `eN` = N リテラル（終端では行末までゼロ埋め挙動の可能性: n5 e1+pad4 で帳尻一致）。
- `68 01 XX` = セクション/イントロ（m7/m8 に複数出現、位置透過は未確定）。

## 未解（阻害中）
1. **6N/f グループ語法** (c02: `6e02 f9 6e00 f3` ×9 + `6e02 f9 6e01 f1`; m8 類似):
   - 10グループあるのに bottom-2-rows paint では 2x18 の2ランしか存在しない矛盾。
   - 仮説A: 大きい swatch は full-core paint に切替わり「行テンプレ + row-repeat」に移行する（m1 では full-core は f0 06 で否定済だが、m1(2x2)は小さいので別経路の可能性）。
   - 仮説B: `6N V` が stateful（prev-val 参照 or 行相対カーソル）。
   - f9/f3 の bias (=11, =5?) がグループ内で固定式でない可能性。
2. **m5 の pair `40 01 03` + `46 01`**:
   - target S5 = [. 3x4 1x4 .]（A=3, C=1, BGRA確定）なので `40 U V` は **逆順 emit (V x4, U x4)** で一致。
   - その後の `46 01` (1x4) が pos59 からの [0,0,3,3] と2ユニット衝突。pair長が (4,4) 以外の可能性 or S5/S6 の paint 相違。
3. `c8 08` / `ce` (n3/n4): cN = ゼロ N+1 の可能性（n3 c8 08 = 9zeros で整合するが未確定）。n3 の後半 `ce 02 02 02` = LZ-short + literal 併用は位置制約と一部整合。
4. `30 U` (m2/m7 末尾 `30 01 e2 00 00`)、`fe/fa/f8` の独立系、2 平面目以降の `68 01 NN` 意味。
5. GA v3-mini multi (m3/m6/n2/n7/n8): `98 02 U2` / `9e U2` = GA 単位 emit、未着手に近い。c04 LZFSE 側の解読成果（α面+halo）と接続要。

## 定跡化への次手
- (1) を c02 と m8 で同時に制約充足（値一致を厳密条件、per-token mode集合に「行相対」「stateful rep」を追加して全組合せ探索）。
- m5 は pair 逆順込みで再トレースし `46 01` 衝突の 2 ユニットを paint 側(dx/dy)を 1 だけ変えて洗い出す。
- エンコーダ視点: 「先頭行ラン → 行テンプレ → row-repeat 群 → 末端 eN(+pad)」という高レベル構造で m8 を説明できるか手検証。

（upterm 死亡のため Apple 実機 probe は一時停止中。再開次第 sweep corpus (37件) を投げて packer/ISA 両方を再検証する）
