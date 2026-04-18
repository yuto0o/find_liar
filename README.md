# learn_graphRAG

短期実験用のローカルRAG/抽出パイプラインです。主にLLMを使ったテキストからの関係抽出（Graph extraction）と、RAG（Retrieval-Augmented Generation）による検証・補助、及び失敗ケースの収集と計測を目的としています。（まだgraphRAGもどき）

**できること**
- 証言やテキストから人物間の関係（`edges`）を抽出してJSONで出力するエクストラクタ（`feature/graphrag/extractor.py`）。
- LLMラッパー（`feature/llm/llama.py`）による遅延初期化・生成設定管理・`require_json` + 再生成（repair）ループの実装。
- 抽出結果・生出力・メタ情報をバージョン毎に `outputs/version_{i}/` に保存（`feature/outputs.py`）。
- 失敗ケースを自動集計し CSV 化するスクリプト（`feature/analyze_outputs.py`）。
- メトリクス収集と時系列永続化（`feature/metrics.py`）および Prometheus エクスポーターのフック。
- RAG 部分: 埋め込み（`feature/rag/embed.py`、sentence-transformers）、FAISS ベクトルストア（`feature/rag/vectorstore.py`）を利用した類似検索。

**特徴・設計方針**
- モデル出力は「純粋な JSON」の取得を優先し、失敗時は修復（repair）プロンプトで再生成してパース成功率を上げます。
- 全ての試行（raw attempts）、パース済み JSON、メタ情報を保存するので、後から失敗例を解析してプロンプト改善できます。
- 軽量でローカル実行可能（ローカルGGUFモデルなどを想定）。大きなログは `feature/metrics.py` で要約して CSV に永続化できます。

**セットアップ（開発環境）**
ローカルの仮想環境を使った例（お使いのワークフローに合わせてください）:

```bash
# 仮想環境作成/有効化
python -m venv .venv
source .venv/bin/activate

# パッケージ管理: uv を使っている場合の例（既に uv 環境で pandas を追加済み）
uv add numpy tqdm pydantic pandas

# または pip
pip install -r requirements.txt
```

**よく使うコマンド**

```bash
# メイン実行（デモ）：versioned outputs と metrics を生成します
python -m feature.main

# outputs を解析して失敗ケースを CSV にまとめる
python -m feature.analyze_outputs --outputs outputs --csv outputs/failure_cases.csv
```

**Pandas を使った簡単な集計例**
`uv` 環境に `pandas` が入っているので、生成した `outputs/failure_cases.csv` を使って短時間で傾向分析できます。

```python
import pandas as pd

df = pd.read_csv('outputs/failure_cases.csv')
print(df[['version','success','repaired','parsed_edges_count']])
print(df.groupby('repaired').size())
```

**主要ファイル**
- `feature/graphrag/extractor.py` — 抽出ロジック、JSON 抽出/修復、outputs 保存連携。
- `feature/llm/llama.py` — LLM 呼び出しラッパー（遅延ロード、retry/repair ロジック）。
- `feature/outputs.py` — versioned 保存ユーティリティ。
- `feature/analyze_outputs.py` — outputs を走査して `outputs/failure_cases.csv` を作る。
- `feature/metrics.py` — メトリクス収集・CSV 永続化・Prometheus hook。

**運用メモ / Tips**
- 厳格な「純粋JSONのみ」指示はモデル品質に依存します。実運用では「厳格→修復→保存→解析」のループを回す運用が現実的です。
- `outputs/` を定期的に集計するジョブ（cron や CI）を追加すると傾向把握が楽になります。
- Prometheus を使う場合は `prometheus_client` をインストールして `feature.metrics.start_prometheus_exporter()` を main 起動時に有効化してください。

**貢献・拡張案**
- CI に `pytest` を組み込み自動集計を定期実行するジョブの追加。
- `pydantic` v2 への移行（`@validator` → `@field_validator`）と型チェック強化。
- `feature/analyze_outputs.py` を Jupyter に移して可視化ダッシュボードを作る（`pandas` + `matplotlib` / `seaborn`）。

---

このリポジトリでやりたいことや追加したい機能があれば教えてください。README の追記・整形、例の追加も対応します。

