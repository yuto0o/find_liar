from typing import List, Union

import numpy as np

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        from feature.config import EMBED_MODEL

        _model = SentenceTransformer(EMBED_MODEL)
    return _model


def embed(texts: Union[str, List[str]]) -> np.ndarray:
    """Embed a single string or a list of strings and return a numpy array (float32).

    Raises TypeError for invalid inputs.
    """
    if isinstance(texts, str):
        texts = [texts]
    if not isinstance(texts, (list, tuple)) or not all(
        isinstance(t, str) for t in texts
    ):
        raise TypeError("texts must be a string or list of strings")

    model = _get_model()
    emb = model.encode(list(texts), convert_to_numpy=True)
    arr = np.asarray(emb, dtype=np.float32)
    # ensure 2D
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    return arr
