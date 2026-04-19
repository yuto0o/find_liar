from feature.graphrag.extractor import extract_graph
from feature.graphrag.graph_builder import GraphBuilder
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
    graph_builder = GraphBuilder()

    # populate graph builder with extracted edges
    try:
        for e in edges:
            # support either pydantic model or dict
            src = getattr(e, "source", None) or e.get("source")
            tgt = getattr(e, "target", None) or e.get("target")
            if src and tgt:
                graph_builder.G.add_edge(src, tgt)
    except Exception:
        # if edges are already in GraphExtractionSchema format, try using build_from_schema
        try:
            graph_builder.build_from_schema(edges)
        except Exception:
            pass

    system_prompt = f"""
    あなたはネットワークエンジニアです。以下のネットワーク構造とミッションに基づき、単一障害点(SPOF)を特定してください。

    {graph_builder.get_context_for_llm()}

    【思考のステップ】
    1. <think>タグ内で、[Papa]から広がるネットワーク（グループA）と、[Vortex]から広がるネットワーク（グループB）をマッピングしてください。
    2. グループAとグループBを繋いでいる唯一のサーバー（橋渡し役）を探してください。
    3. そのサーバーがダウンした場合、本当にルートが遮断されるか検証してください。

        """

    return generate(system_prompt, **gen_kwargs)
