import logging

from feature.graphrag.pipeline import run_graphrag
from feature.metrics import metrics
from feature.rag.pipeline import run_rag

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)

DATA = "data/raw/sample_statements.txt"

query = "嘘つきは誰か？"

print("=== RAG ===")
print(run_rag(DATA, query, top_k=5))

print("=== GraphRAG ===")
# Explicitly pass deterministic generation settings to reduce extra output
print(run_graphrag(DATA, query, temperature=0.0, max_tokens=4096, retries=2))

# Print metrics summary
try:
    print("\n" + metrics.report())
except Exception:
    logging.getLogger(__name__).exception("Failed to print metrics")
# persist metrics timeseries for later analysis
try:
    metrics.persist_snapshot_to_csv()
except Exception:
    logging.getLogger(__name__).exception("Failed to persist metrics to CSV")
