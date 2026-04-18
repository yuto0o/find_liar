from typing import List, Literal, Optional

from pydantic import BaseModel, Field, validator


class Edge(BaseModel):
    source: str = Field(..., description="話者")
    target: str = Field(..., description="対象人物")
    relation: str = Field(
        ...,
        description="関係ラベル。可能であれば 'supports'/'contradicts'/'same' に正規化されます。",
    )

    @validator("source", "target")
    def not_empty_and_reasonable_length(cls, v: str):
        if not isinstance(v, str) or not v.strip():
            raise ValueError("source/target must be a non-empty string")
        v = v.strip()
        if len(v) > 64:
            raise ValueError("source/target is too long")
        return v

    @validator("relation")
    def normalize_relation(cls, v: str):
        if not isinstance(v, str) or not v.strip():
            raise ValueError("relation must be a non-empty string")
        mapping = {
            "支持": "supports",
            "supports": "supports",
            "support": "supports",
            "支持する": "supports",
            "矛盾": "contradicts",
            "反論": "contradicts",
            "contradicts": "contradicts",
            "同一": "same",
            "同一人物": "same",
            "same": "same",
        }
        key = v.strip()
        # try exact mapping first
        if key in mapping:
            return mapping[key]
        # try lowercased english
        low = key.lower()
        if low in mapping:
            return mapping[low]
        # otherwise return raw string (preserve information)
        return key


class GraphOutput(BaseModel):
    edges: List[Edge]
    explanation: Optional[str] = Field(
        None, description="モデルが付与する追加の説明や思考過程（任意）"
    )
