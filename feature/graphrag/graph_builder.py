from typing import List

from feature.graphrag.schema import Edge


class Graph:
    def __init__(self):
        self.edges: List[Edge] = []

    def add_edges(self, edges):
        if not isinstance(edges, (list, tuple)):
            raise TypeError("edges must be a list of Edge or dict")
        for e in edges:
            if isinstance(e, dict):
                e = Edge(**e)
            elif isinstance(e, Edge):
                pass
            else:
                raise TypeError("each edge must be a dict or Edge instance")
            self.edges.append(e)
