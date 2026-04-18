from typing import List, Optional

import faiss
import numpy as np


class VectorStore:
    def __init__(self, dim: int):
        if not isinstance(dim, int) or dim <= 0:
            raise ValueError("dim must be a positive integer")
        self.dim = dim
        self.index = faiss.IndexFlatL2(dim)
        self.texts: List[str] = []

    def add(self, embeddings, texts: List[str]):
        arr = np.asarray(embeddings)
        if arr.ndim != 2 or arr.shape[1] != self.dim:
            raise ValueError(f"embeddings must be 2D with shape (n, {self.dim})")
        arr = arr.astype(np.float32)
        if len(texts) != arr.shape[0]:
            raise ValueError("number of texts must match number of embeddings")
        self.index.add(arr)
        self.texts.extend(texts)

    def search(self, query_emb, k: int) -> List[Optional[str]]:
        q = np.asarray(query_emb)
        if q.ndim == 1:
            q = q.reshape(1, -1)
        if q.shape[1] != self.dim:
            raise ValueError(f"query_emb must have dimension {self.dim}")
        q = q.astype(np.float32)
        D, I = self.index.search(q, k)
        results: List[Optional[str]] = []
        for idx in I[0]:
            if idx < 0 or idx >= len(self.texts):
                results.append(None)
            else:
                results.append(self.texts[idx])
        return results
