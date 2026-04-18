import numpy as np

from feature.llm.llama import generate
from feature.rag.chunk import load_statements
from feature.rag.embed import embed
from feature.rag.vectorstore import VectorStore


def run_rag(data_path, query, top_k=5):
    texts = load_statements(data_path)

    embeddings = embed(texts)
    store = VectorStore(embeddings.shape[1])
    store.add(embeddings, texts)

    q_emb = embed([query])
    retrieved = store.search(np.array(q_emb), top_k)

    prompt = f"""
    以下の証言から推論してください：
    {retrieved}

    質問：{query}
    """

    return generate(prompt)
