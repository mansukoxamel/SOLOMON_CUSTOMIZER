# 3/26 Spark Ball 24ID runtime 6502静的解析

解析日: 2026-07-18
対象バージョン: v0.9.40 / commit `5db3d29` 後の作業ツリー
対象: `magatu_skc/core/spark24_runtime.py`、適用元`magatu_skc/core/spark_ball_variant.py`、入口`magatu_skc/core/new_enemy_runtime.py`
一次資料: `解析資料/ROM完全解析/solomon_commented.asm`、日本版原作ROM、現行mapper66 workstate、`docs/new_enemy_id_placement_audit.md`

## 結論

Spark Ball 24ID runtimeは、専用ID `$C0-$D7`を3種類×4方向×2速度へ割り当て、原作Spark Ball AI `$A929/$A92D`を再利用する179Bの統合runtimeである。

- `$C0-$C7`: 指定したLIFE百の位の間、座標commitを止める停止型。
- `$C8-$CF`: 原作移動を続け、frame counter maskによりOAMだけを隠す透明型。
- `$D0-$D7`: 指定digitへ入った最初に方向を反転し、そのdigitの間は座標commitを止める停止後反転型。
- 各8IDは前半4IDが速度1、後半4IDが速度2。下位2bitは右・左・上・下である。
- 旧Dragon/Golem借用runtimeは無効で、現行ROMへ書かれるのはSpark24統合runtimeだけである。

全4 code chunkは命令境界で末尾まで分解でき、AI速度選択、停止、反転latch、透明OAM、property fallbackの生きた経路に確定動作バグは見つからなかった。現行workstateのruntimeと3hookはbuilderに一致し、設定無変更の`apply()`は変更0件だった。

一方で、writerの防御と保守性に関する問題を2件記録する。runtime配置先179Bの既存内容を一切検査せず上書きすることと、無効化済み借用runtime一式が同じモジュールへ残っていることである。この解析では修正していない。

## 24IDの割当

| 種類 | 速度1 | 速度2 | 動作 |
|---|---|---|---|
| 停止 | `$C0-$C3` | `$C4-$C7` | 指定LIFE digit中は座標commitを止める |
| 透明 | `$C8-$CB` | `$CC-$CF` | 移動は継続し、描画だけ周期的に隠す |
| 停止後反転 | `$D0-$D3` | `$D4-$D7` | digit進入時に1回反転し、その間停止 |

各4IDの方向順は共通である。

| ID offset下位2bit | UI方向 | 原作Spark内部`sub[6]` |
|---:|---|---:|
| 0 | 右 | 3 |
| 1 | 左 | 2 |
| 2 | 上 | 1 |
| 3 | 下 | 0 |

新敵setup入口はSpark24を原作Spark metadata groupへ送り、原作初期化がtype下位2bitから方向別entryを選ぶ。方向値をruntime内で独自に再生成していないため、`sub[7]`の次方向予約も原作setup/initと一組で成立する。

## 原作Spark Ballの基本構造

原作Spark Ballには2つのAI入口がある。

```text
$A929  LDX #$00       速度1
$A92D  LDX #$04       速度2
```

`sub[6]`の方向0-3へXの速度group offset 0/4を足し、次の表を読む。

```text
$A9DF vx: 00 00 DE 22 | 00 00 B4 4C
$A9E7 vy: 22 DE 00 00 | 4C B4 00 00
```

Spark AIは速度byteを固定小数点へ展開し、現在座標と足し、4隅のブロック衝突から反射state 0-15を選ぶ。反射handlerは`sub[6]`を現在方向、`sub[7]`を次方向予約として更新する。

最後は多くの経路が`$AB13`へ集約される。

```text
$AB13  LDY #$07
       LDA $02,X
       STA ($2E),Y    次のY座標をcommit
       LDY #$0A
       LDA $03,X
       STA ($2E),Y    次のX座標をcommit
       RTS
```

ここで書くmain `[7]/[10]`は座標である。停止型が`$AB13`を飛ばすことは、速度byteを0へするのではなく「今回計算した次座標を採用しない」ことを意味する。

## 現行hookと共通入口

| 場所 | 変更後 | 役割 |
|---:|---|---|
| 新敵AI共通入口 `$BBE2` | Spark24範囲なら`JMP $BEC0` | 速度1/2を選び原作Spark AIへ送る |
| 新敵setup入口 `$BC32` | metadata group offset `$14` | 原作Spark setup metadataを選ぶ |
| 新敵init入口 `$BC84` | `JSR $9D1C` | 原作entity初期化を行う |
| 新敵animation入口 `$BCD0` | `JMP $8789` | 原作Spark animation更新を使う |
| `$AB13` | `JMP $BECD` | 停止/反転判定後に原作座標commitを再現 |
| `$A2CC` | `JSR $BF43` | Spark24はproperty `$19`、その他はPanel helperへfallback |
| `$85FA` | `JMP $BF53` + NOP | 原作OAM attr書込み後、透明型だけYを`$F8`へする |

AI共通入口は原作dispatch値`type-$14`をstackへ保存した状態でtypeを復元して分類する。Spark24へ入る時はPLAで再び`type-$14`をAへ戻す。`$BEC0`はそこから`$AC`を引くため、実質`type-$C0`を得る。

## AI速度dispatch `$BEC0`

```text
SEC
SBC #$AC        ; (type-$14)-($C0-$14) = type-$C0
AND #$04
BEQ slow
JMP $A92D
slow:
JMP $A929
```

各8ID内のbit2だけで速度を選ぶ。種類を示すbit3/bit4は速度選択へ影響しない。

| type offset | bit2 | AI |
|---:|---:|---:|
| 0-3 / 8-11 / 16-19 | 0 | `$A929`速度1 |
| 4-7 / 12-15 / 20-23 | 1 | `$A92D`速度2 |

原作AI入口は直後にXを0/4へ設定するため、dispatchがAとflagをclobberしても原作側契約を壊さない。

## 停止・反転dispatch `$BECD`

### 範囲分類

helperはmain typeを読み、`$C0-$D7`以外なら無条件で原作`$AB13`相当のcommitへ進む。

```text
$C0-$C7 -> pause_check
$C8-$CF -> commit
$D0-$D7 -> reverse_check
その他  -> commit
```

従ってglobal hook `$AB13`を原作Spark Ball `$28-$2F`も通るが、追加判定を受けず元と同じ2座標を書いてRTSする。

### 停止型

LIFE百の位RAM `$0439`を最大4個の設定digitと比較する。

- 一致: commitせずRTS。前回座標のままなので停止する。
- 不一致: `$02,X/$03,X`の計算済み座標をmain `[7]/[10]`へcommitする。

設定値は0-9、1-4種類である。4個未満は最後のdigitを複製して4比較slotを埋めるため、判定意味は変わらない。

### 停止後反転型

親自身の`sub[0]` bit2を「現在の選択digit区間ですでに反転した」latchとして使う。

選択digitへ入った時:

```text
latch=0
  -> latchを1
  -> sub[6] ^= 1
  -> sub[7] ^= 1
  -> commitせず停止

latch=1
  -> 何も変えずcommitせず停止
```

Spark方向encodeは`0<->1`が下/上、`2<->3`が左/右なので、XOR 1で4方向すべて正反対になる。現在方向と次方向予約の両方を反転するため、停止解除後の反射stateが片方だけ古い方向を使うこともない。

選択外digitではlatchをclearし、そのフレームから座標をcommitする。選択digitが連続して切り替わっても、その間に選択外digitを通らなければ同じ区間と扱い、再反転しない。これは現行仕様記述と一致する。

最後のdigit比較が全て不一致なら、最後のCMPは必ずZ=0である。その直後の`BNE reverse_clear`は事実上のunconditional branchとして成立する。

## 透明OAM dispatch `$BF53`

hook元`$85FA`は、2枚目spriteのattrを`$0216,X`へ書く原作末尾である。runtimeはその原作STAを先頭で再実行する。

その後、現在描画中entity typeが`$C8-$CF`の場合だけframe counter `$21`と設定maskをANDする。

- AND結果0: そのまま表示。
- AND結果非0: 2spriteのOAM Y `$0210,X/$0214,X`へ`$F8`を書き、画面外へ隠す。

最後は原作loop継続`$8608`へJMPする。XはOAM offsetのまま保持される。AとYはclobberするが、`$8608`以降は描画slot counter `$0C`だけで次entityへ進むため問題ない。

mask `$20/$30/$40/$60/$80`は単純な周期値ではなくbit maskである。`$40/$80`は表示・非表示が50%ずつだが、複数bitの`$30/$60`はAND結果0の区間だけ表示するため表示率は25%になる。これは既存UI選択肢と監査文書に記録された現行仕様であり、今回バグとは判定しない。

## property・setup・animation

### property

`$BF43`はspawn type `$05`を範囲比較する。

- `$C0-$D7`: A=`$19`でRTS。
- その他: `JMP $E6DF`でPanel/stock property selectorへfallback。

このためSparkのglobal property hookがPanel Monsterのpropertyを奪わない。

### setup

高IDをそのまま原作table indexへ入れると範囲外になる。新敵setup入口はSpark24全IDで`$0E=$14`とし、原作Spark groupのsetup table `$D9D3`を読む。原作`$8AC0`はentity type下位2bitを方向別indirect table indexに使うため、4方向が維持される。

### animation

新敵animation入口はSpark24を原作`$8789`へ送る。setup側で原作Spark metadata pointerが設定されているため、専用animation codeは不要である。

## register・flag・stack検査

| 入口 | A | X | Y | stack/flag |
|---|---|---|---|---|
| AI `$BEC0` | type offset計算でclobber | 原作AI入口が0/4へ設定 | 保持 | stack不使用、tail JMP |
| pause/reverse `$BECD` | type/digit/座標でclobber | 原作座標indexを保持 | 0/1/7/10でclobber | stack不使用。停止RTSとcommit RTSの両方成立 |
| property `$BF43` | `$19`またはfallback入力 | 保持 | 保持 | stack不使用。JSR元へRTSまたはtail JMP |
| OAM `$BF53` | attr/type/frameでclobber | OAM offsetを保持 | 1でclobber | stack不使用、原作`$8608`へtail JMP |

runtime 179Bの内訳は次である。

| chunk | CPU | size | disassembly |
|---|---:|---:|---|
| AI dispatch | `$BEC0-$BECC` | 13B | 13B全消費 |
| pause/reverse | `$BECD-$BF42` | 118B | 118B全消費 |
| property | `$BF43-$BF52` | 16B | 16B全消費 |
| OAM | `$BF53-$BF72` | 32B | 32B全消費 |

全relative branchはbuilderが`-128..127`を検査し、全chunkが命令境界で末尾まで分解できた。

## ROM/RAM配置

| file | CPU | size | 内容 |
|---:|---:|---:|---|
| `0x3ED0-0x3F82` | `$BEC0-$BF72` | 179B | Spark24統合runtime |
| `0x3F83-0x400F` | `$BF73-$BFFF` | 141B | 現行runtime予約なし |

`RUNTIME_CAPACITY`は320Bだが、`RESERVED_SPANS`と正式管理簿は実使用179Bだけを予約し、残り141Bを空きとしている。新規RAM予約はなく、既存entity `sub[0]` bit2を停止後反転latchに使う。

## 確定した問題・保守上の問題

### [P2] runtime配置先179Bの所有署名を検査せず上書きする

`_apply_spark24()`は`$AB13/$A2CC/$85FA`のhook署名を全て検査してから書くため、hook異常時は先行変更しない。一方、`0x3ED0-0x3F82`のruntime本体については、次のどれであるかを検査しない。

- 現行Spark24 runtime
- 許容する空きbyte
- 未知の別code/data

hookが許容状態なら、runtime領域へ無条件に179Bを書く。通常の現行ROMではこの領域の所有者はSpark24であり、最新workstateも完全一致しているため、現時点の正常保存を壊す問題ではない。しかしwriter単体の衝突検出としては不足しており、未知内容をsilent overwriteできる。

また明示的な最小ROM長検査がない。通常保存は正しい拡張ROMを渡すが、writer APIのfail-closed契約としては弱い。

### [P3] 無効化済みborrowed-ID runtime一式が現行moduleへ残る

`spark_ball_variant.py`は`BORROWED_ID_RUNTIME_ENABLED=False`なので、現行`apply()`、`RESERVED_SPANS`、Panel property接続はいずれもSpark24側を使う。それでも旧Dragon/Golem借用用のAI wrapper、pause、property、animation、OAM builderと、約200行の別apply経路が同じmoduleに残る。

ROM領域を占有するdead 6502ではないため実行時副作用はない。しかし現行runtime解析で2系統が同時に生きているように見え、定数`CPU_PANEL_*`や旧hook互換を変更する際の誤編集要因になる。コメントの「後で再利用する」も、現在の専用24ID完成後の構成とは一致しない。

## 正常と確認した事項

- 24ID全ての種類・速度・方向mappingを展開し、範囲漏れなし
- 新敵AI入口がA=`type-$14`を復元してSpark24 AIへ渡すstack経路成立
- 速度bit2から`$A929/$A92D`を選ぶ全6 group成立
- `$C0-$C7/$C8-$CF/$D0-$D7`の3分岐境界成立
- pause digit一致/不一致の全branch成立
- reverse latch初回、継続、解除の全branch成立
- `sub[6]/sub[7]`双方のXOR 1が4方向を正反対へする
- 原作Spark `$28-$2F`はglobal `$AB13` hookを通っても無条件commit
- 透明型以外はglobal OAM hookで原作STAとloop復帰だけを実行
- propertyのPanel/stock fallback成立
- setup metadataとtype下位2bitによる4方向選択成立
- runtime 179Bと3hookが現行workstate/builderで一致
- 設定無変更`apply()`の変更0件・変更byte 0件
- 4 chunk全て命令分断なし

## 未実施と、この文書だけで保証しないこと

- 今回はROMを新規生成していない。
- Mesenで24IDを全方向・全速度・全digit・全透明maskについて新たに動的実行していない。既存監査にはユーザー動作確認済みと記録されている。
- 原作Sparkの反射state 0-15自体は原作ASMを参照したが、各壁形状を再度動的網羅していない。
- runtime領域の未知内容上書きとdisabled borrowed経路は記録のみで、コードは変更していない。
