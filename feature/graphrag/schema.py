from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# Primary edge model used by the extractor
class Edge(BaseModel):
    source: str = Field(..., description="接続元のノード名")
    target: str = Field(..., description="接続先のノード名")
    relation: Literal["supports", "contradicts", "same"] = Field(
        ..., description="関係性（supports|contradicts|same）"
    )


class GraphOutput(BaseModel):
    edges: List[Edge]
    explanation: Optional[str] = Field(None, description="任意の説明や思考過程")


# Backwards-compatible schema for tools that expect a richer extraction schema
class NetworkNode(BaseModel):
    name: str = Field(..., description="サーバーの名前（例: Kilo, Quebecなど）")


class NetworkEdge(BaseModel):
    source: str = Field(..., description="接続元のサーバー名")
    target: str = Field(..., description="接続先のサーバー名")


class GraphExtractionSchema(BaseModel):
    thought_process: Optional[str] = Field(
        None, description="抽出を行う際の思考プロセス"
    )
    nodes: Optional[List[NetworkNode]] = Field(
        None, description="抽出されたノードのリスト"
    )
    edges: Optional[List[NetworkEdge]] = Field(
        None, description="サーバー間の接続リスト"
    )
