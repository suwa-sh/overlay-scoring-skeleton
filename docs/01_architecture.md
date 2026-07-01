# アーキテクチャ (as-built)

overlay-scoring-skeleton は、**rules-as-data で書いた readiness / scoring 定義を、組織ごとに安全に拡張する overlay エンジン**の起点テンプレートです。新しい readiness/scoring 系リポは、このリポを clone して定義とスコアリングだけを足すことで、拡張モデル (add / strengthen) と検証ロジックを再実装せずに済みます。

## 構造 (C4)

### システムコンテキスト

```mermaid
graph TD
  author["定義作者<br/>readiness/scoring OSS の作り手"]
  org["導入組織<br/>自社ルールで拡張する利用者"]
  skeleton["overlay-scoring-skeleton<br/>overlay エンジン + 定義スキーマ"]
  downstream["派生リポ<br/>ai-delegation-readiness / shared-infra-incident-readiness / 今後の readiness OSS"]

  author -->|"clone して定義とスコアリングを追加"| skeleton
  skeleton -->|"共通エンジンを提供"| downstream
  org -->|"overlay で add / strengthen"| downstream
```

- **定義作者**: フラットな `items` 定義とスコアリング CLI を書く。エンジンと検証は skeleton から継承する。
- **導入組織**: 派生リポの base 定義を fork せず、overlay で項目追加・閾値厳格化だけ行う。
- **派生リポ**: skeleton のエンジンを複製し、ドメイン固有の定義 (`definitions/*.yaml`) と consumer (スコアリング CLI) を持つ。

### コンテナ

```mermaid
graph LR
  basedef["base 定義<br/>definitions/*.yaml"]
  overlay["overlay<br/>examples/overlays/*.yaml"]
  engine["overlay エンジン<br/>src/overlay_scoring/overlay.py"]
  schema["定義スキーマ<br/>schemas/definition.schema.json"]
  merged["merged 定義<br/>(メモリ上)"]
  consumer["consumer<br/>スコアリング CLI (派生リポ)"]

  basedef -->|"load_yaml"| engine
  overlay -->|"apply_overlays"| engine
  schema -.->|"validate"| basedef
  engine -->|"MergeResult.merged"| merged
  merged -->|"group_items で projection"| consumer
```

| コンテナ | 役割 |
|---|---|
| base 定義 | フラット `items` リスト。`extension_points` で拡張可能点を宣言する正本 |
| overlay | 組織固有の `add` / `strengthen`。base を書き換えず重ねる |
| overlay エンジン | overlay を検証しながら base に適用し merged 定義を返す。派生リポへ複製する |
| 定義スキーマ | id 規約・extension_points 形状を JSON Schema で enforce |
| consumer | merged 定義を `group_items` で group 化して読み、スコア/verdict を出す (派生リポ側) |

### コンポーネント (エンジン内部)

```mermaid
graph TD
  apply["apply_overlays / apply_overlay<br/>複数 overlay を順に適用 (最初の違反で停止)"]
  parse["_parse_extension_points<br/>add セレクタ / strengthen 仕様を抽出"]
  add["_apply_add<br/>id 衝突 / prefix 実在 / group scope を検証して追加"]
  strengthen["_apply_strengthen<br/>宣言フィールドのみ / 方向厳守 / 弱化拒否"]
  validate["validate_definition<br/>base の構造整合 (孤立 leaf / 重複 id)"]
  group["group_items<br/>フラット items を順序保持で group 化"]

  apply --> parse
  apply --> add
  apply --> strengthen
  parse --> add
  parse --> strengthen
```

## データ

### 概念モデル

```mermaid
graph TD
  definition["Definition<br/>1 フレームワーク"]
  item["Item<br/>group ヘッダ または leaf"]
  ep["ExtensionPoint<br/>拡張可能点の宣言"]
  overlay["Overlay<br/>組織拡張"]
  merged["MergedDefinition"]

  definition -->|"1..N 保持"| item
  definition -->|"0..N 宣言"| ep
  overlay -->|"extends 一致で対象を指す"| definition
  overlay -->|"add / strengthen"| merged
  definition -->|"deepcopy + マージ"| merged
```

| エンティティ | 説明 |
|---|---|
| Definition | 1 つの readiness/scoring フレームワーク。`name` / `separator` / `extension_points` / `items` |
| Item | `items` の 1 要素。id が `<group>` ならヘッダ (group レベル数値を持つ)、`<group>.<leaf>` なら leaf (明細 + opaque payload) |
| ExtensionPoint | overlay で何が許されるかの宣言。`{group セレクタ, allow: add|strengthen, level, field, direction}` |
| Overlay | `extends` で base を指し、`add` (項目追加) と `strengthen` (数値厳格化) のみ行う |
| MergedDefinition | base を deepcopy し overlay を適用した結果。source order は保持される |

### 情報モデル (エンジンの返り値)

```mermaid
classDiagram
  class MergeResult {
    +dict merged
    +list~str~ applied
    +list~MergeViolation~ violations
    +bool ok
  }
  class MergeViolation {
    +str path
    +str kind
    +str message
  }
  class StrengthenSpec {
    +str group_sel
    +str level
    +str field
    +str direction
  }
  MergeResult "1" o-- "0..N" MergeViolation
```

- `MergeResult.ok` は `violations` が空のとき真。consumer は `ok` が偽なら例外にする。
- `MergeViolation.kind` の例: `extends_mismatch` / `id_collision` / `unknown_group` / `weakening_rejected` / `unsupported_op` / `invalid_overlay`。
- `StrengthenSpec` は `extension_points` から抽出した strengthen 可能フィールドの内部表現。

### id 規約 (1 階層固定)

- `<group>` (セパレータ無し) = group ヘッダ。group レベルの数値 (合否閾値・SLA など) を持つ。
- `<group>.<leaf>` (セパレータ 1 個) = leaf。明細フィールドと、エンジンが解釈しない opaque payload を持つ。
- **ungrouped leaf (セパレータ無しの非ヘッダ) は不可**。leaf の `<group>` prefix は必ず実在するヘッダを指す (タイプミスは検証で弾かれる)。
