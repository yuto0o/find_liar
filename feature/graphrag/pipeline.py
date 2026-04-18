from feature.graphrag.extractor import extract_graph
from feature.graphrag.graph_builder import Graph
from feature.llm.llama import generate
from feature.rag.chunk import load_statements


def run_graphrag(path, query, **gen_kwargs):
    """Run GraphRAG: extract edges from documents and ask the model.

    gen_kwargs are forwarded to `feature.llm.llama.generate` so callers
    can control temperature, max_tokens, retries, etc.
    """
    texts = load_statements(path)
    full_text = "\n".join(texts)

    edges = extract_graph(full_text)

    graph = Graph()
    graph.add_edges(edges)

    prompt = f"""
    以下の関係を使って推論せよ：

    {edges}

    質問：{query}
    """

    return generate(prompt, **gen_kwargs)
