# overlay-scoring-skeleton

rules-as-data な **readiness / scoring 定義**を、組織ごとに**安全に拡張**するための overlay エンジンと定義スキーマの起点テンプレートです。

> readiness / scoring 定義 = チェック項目・閾値・マトリクスなどを、コードではなく YAML データとして書いた評価フレームワークのことです。

## 提供する価値

- **拡張モデルを再実装しなくてよい**: 「項目を追加する / 閾値を厳しくする」だけを許し、既存項目の上書き・削除・緩和は機械的に拒否する overlay の仕組みが最初から入っています。組織は base 定義を fork せずに自社ルールを重ねられます。
- **定義が壊れにくい**: 項目のグループ分けを自由なタグ命名ではなく **id の構造 (1 階層固定)** で表すため、命名ミスで表示や集計が崩れません。不正な拡張 (未宣言フィールドの変更、閾値の緩和、存在しないグループへの追加) は検証時に弾かれます。
- **明細データを自由に持てる**: 各項目は評価に使う数値のほかに、任意の入れ子データ (RACI セル、条件分岐、参照 id など) をそのまま保持できます。エンジンはこれらを解釈せず素通しします。
- **一貫性**: 複数の readiness/scoring OSS が同じ拡張モデル・同じ検証規則を共有できます。

## データモデル

定義は単一のフラットな `items` リストです。id で 1 階層のグループを表します。

- `<group>` (区切り文字なし) = **グループヘッダ**。合否閾値や SLA などグループ単位の数値を持ちます。
- `<group>.<leaf>` (区切り文字 1 個) = **リーフ**。明細フィールドと任意の入れ子データを持ちます。

区切り文字は既定で `.` です (`separator` で変更可)。区切りなしのリーフ (ungrouped leaf) は許されません。

```yaml
version: 1
name: my-framework
separator: "."
extension_points:
  - {group: "L*", allow: add}                                          # L* グループにリーフを追加してよい
  - {group: "L*", level: group, field: revise, allow: strengthen, direction: higher}
items:
  - {id: "L1", label: 基礎層, pass: 1.0, revise: 0.5}   # グループヘッダ (数値はここ)
  - {id: "L1.Q1", text: 判断基準は文書化されているか, weight: 1.0}   # リーフ
```

拡張 (overlay) は `add` と `strengthen` の 2 操作だけです。

```yaml
extends: my-framework
add:
  - {id: "L1.Q9", text: 自社固有の追加質問, weight: 1.0}
strengthen:
  "L1": {revise: 0.8}   # 0.5 -> 0.8 (higher = より厳しい。緩和は拒否される)
```

## インストール

ライブラリとして使う場合は PyPI から入れます。

```bash
pip install overlay-scoring-skeleton
```

導入すると、利用側は使っているエンジンのバージョンを取得できます。

```python
import overlay_scoring
print(overlay_scoring.__version__)
```

## Quick start

このリポを clone して開発・テストする場合は、依存を入れてテストを実行します。

```bash
python3 -m venv .venv
./.venv/bin/pip install ".[dev]"
./.venv/bin/python -m pytest tests/ -q     # 26 tests
```

エンジンはライブラリとして使います。

```python
from overlay_scoring import load_yaml, apply_overlays, group_items, validate_definition

base = load_yaml("definitions/example-four-layer.yaml")
assert validate_definition(base) == []                       # base の構造整合を確認

result = apply_overlays(base, ["examples/overlays/sample-four-layer.yaml"])
if not result.ok:
    raise SystemExit([f"{v.path}: {v.message}" for v in result.violations])

groups = group_items(result.merged)                          # 順序を保ったまま group 化
for gid, g in groups.items():
    header, leaves = g["header"], g["leaves"]
    ...                                                       # スコアリングは利用側で実装
```

## 想定ワークフロー (準備 → 実行 → 解釈)

新しい readiness/scoring OSS を作る流れです。

1. **準備 — 定義を書く**: このリポを clone し、`definitions/` に自分のフレームワークを 1 ファイル書きます。グループヘッダに閾値を、リーフに明細を置き、`extension_points` で「どのグループに追加してよいか / どの数値をどちら向きに厳格化してよいか」を宣言します。`schemas/definition.schema.json` で形を検証できます。
2. **実行 — overlay を適用する**: 導入組織は `add` / `strengthen` だけの overlay を書きます。`apply_overlays(base, [overlay, ...])` が違反を検証しながら重ね、最初の違反で止めて `MergeResult` を返します。
3. **解釈 — merged を読む**: `group_items(merged)` でフラットな items を「グループ → ヘッダ + リーフ」に順序保持で畳み込み、ヘッダの数値としきい値、リーフの明細を使ってスコアや判定を出します (このスコアリング部分が各リポ固有の実装です)。

## 検証される拡張ルール

- リーフの追加はその `<group>` プレフィックスが実在するときだけ許可 (タイプミスを検出)。
- id 衝突・既存項目の上書き・削除は拒否。
- `strengthen` は宣言済みの数値フィールドのみ、宣言した方向 (`higher` / `lower`) にのみ許可。緩和・非数値・宣言外フィールドは拒否。
- 複数 overlay は順に適用し、最初に違反した overlay で停止します。

## リポ構成

| パス | 役割 |
|---|---|
| `src/overlay_scoring/overlay.py` | overlay エンジン (canonical 実装) |
| `schemas/definition.schema.json` | 定義スキーマ |
| `definitions/example-*.yaml` | 移行済みサンプル定義 (round-trip fixture) |
| `examples/overlays/*.yaml` | overlay サンプル |
| `tests/` | エンジンの全境界条件テスト |
| `docs/01_architecture.md` | 構造 (C4) とデータモデル |
| `docs/migration-map.md` | 既存フレームワークをこのモデルへ移す対応表 |
