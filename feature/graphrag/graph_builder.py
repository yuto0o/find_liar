import networkx as nx

from .schema import GraphExtractionSchema


class GraphBuilder:
    def __init__(self):
        self.G = nx.Graph()

    def build_from_schema(self, extracted_data: GraphExtractionSchema):
        for edge in extracted_data.edges:
            self.G.add_edge(edge.source, edge.target)

    # LLMに渡すための「お膳立て」機能
    def get_context_for_llm(self) -> str:
        # 例：各ノードがどこに繋がっているかを箇条書きにして出力
        context = "【ネットワーク構造】\n"
        for node in self.G.nodes():
            neighbors = list(self.G.neighbors(node))
            context += f"- {node} は {', '.join(neighbors)} と接続されています。\n"
        return context
