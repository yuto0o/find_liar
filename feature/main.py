import argparse
import logging

from feature.graphrag.pipeline import run_graphrag
from feature.metrics import metrics
from feature.rag.chunk import load_statements
from feature.rag.pipeline import run_rag

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)

DATA = "data/raw/sample_statements.txt"

query = "嘘つきは誰か？"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no-lightrag",
        action="store_true",
        help="Disable LightRAG integration and use local pipelines",
    )
    args = parser.parse_args()

    use_lightrag = not args.no_lightrag

    if use_lightrag:
        try:
            import asyncio

            # try to initialize LightRAG using our adapter; if anything fails,
            # fall back to the existing local pipelines
            from feature.llm.lightrag_adapter import embedding_func, llm_model_if_func

            try:
                from lightrag import LightRAG
            except Exception:
                # some installations expose different import paths
                from lightrag.hku import LightRAG  # type: ignore

            print("=== LightRAG (attempt) ===")

            # Dynamically build kwargs matching the LightRAG constructor
            import inspect

            texts = load_statements(DATA)

            init_kwargs = {}
            sig = None
            try:
                sig = inspect.signature(LightRAG)
                params = set(sig.parameters.keys())
            except Exception:
                params = set()

            # candidate parameter names
            storage_keys = [
                "storage_path",
                "storage",
                "persist_directory",
                "persist_path",
                "data_dir",
                "index_path",
                "db_path",
                "path",
            ]
            llm_keys = [
                "llm_model_func",
                "llm",
                "llm_model",
                "model_fn",
                "model_func",
            ]
            embed_keys = [
                "embedding_func",
                "embedding",
                "embed_fn",
                "embedder",
                "embedding_function",
            ]

            for k in storage_keys:
                if k in params:
                    init_kwargs[k] = "./data/graphrag_storage"
                    break

            for k in llm_keys:
                if k in params:
                    init_kwargs[k] = llm_model_if_func
                    break

            # Prepare a wrapped embedding func compatible with LightRAG's EmbeddingFunc
            wrapped_embedding_for_rag = None
            for k in embed_keys:
                if k in params:
                    try:
                        try:
                            from lightrag.utils import wrap_embedding_func_with_attrs
                        except Exception:
                            wrap_embedding_func_with_attrs = None

                        if wrap_embedding_func_with_attrs is not None:
                            # try to infer embedding dim from the local embed model
                            try:
                                from feature.rag import embed as _local_embed

                                model = _local_embed._get_model()
                                if hasattr(model, "get_sentence_embedding_dimension"):
                                    dim = model.get_sentence_embedding_dimension()
                                elif hasattr(model, "get_embedding_dimension"):
                                    dim = model.get_embedding_dimension()
                                else:
                                    dim = None
                            except Exception:
                                dim = None

                            if dim is None:
                                # conservative default if we cannot introspect the model
                                dim = 1536

                            # Prefer constructing EmbeddingFunc directly (more robust across lightrag versions)
                            try:
                                from lightrag.utils import EmbeddingFunc

                                wrapped_embedding_for_rag = EmbeddingFunc(
                                    embedding_dim=dim, func=embedding_func
                                )
                            except Exception:
                                # fallback to decorator if direct construction fails
                                try:
                                    wrapped_embedding_for_rag = (
                                        wrap_embedding_func_with_attrs(
                                            embedding_dim=dim
                                        )(embedding_func)
                                    )
                                except Exception:
                                    wrapped_embedding_for_rag = embedding_func
                        else:
                            wrapped_embedding_for_rag = embedding_func

                        init_kwargs[k] = wrapped_embedding_for_rag
                    except Exception:
                        init_kwargs[k] = embedding_func
                    break

            # If signature detection failed, try a reasonable default call
            try:
                # debug: show what kwargs we will pass to LightRAG
                try:
                    print("LightRAG init kwargs:")
                    for kk, vv in init_kwargs.items():
                        print(f"  {kk}: {type(vv)}")
                except Exception:
                    pass
                if init_kwargs:
                    rag = LightRAG(**init_kwargs)
                else:
                    # best-effort: pass common names
                    emb_arg = (
                        wrapped_embedding_for_rag
                        if wrapped_embedding_for_rag is not None
                        else embedding_func
                    )
                    try:
                        rag = LightRAG(
                            llm_model_func=llm_model_if_func, embedding_func=emb_arg
                        )
                    except TypeError:
                        rag = LightRAG(llm=llm_model_if_func, embedding=emb_arg)
            except Exception:
                # final fallback: try no-arg constructor then set attributes if possible
                rag = LightRAG()
                try:
                    if hasattr(rag, "set_llm"):
                        rag.set_llm(llm_model_if_func)
                    if hasattr(rag, "set_embedding"):
                        emb_arg = (
                            wrapped_embedding_for_rag
                            if wrapped_embedding_for_rag is not None
                            else embedding_func
                        )
                        rag.set_embedding(emb_arg)
                except Exception:
                    pass

            # Run initialization, ingestion, and query inside a single asyncio event loop
            try:

                async def _run_rag_workflow():
                    # initialize storages if available
                    try:
                        if hasattr(rag, "initialize_storages"):
                            await rag.initialize_storages()
                    except Exception:
                        logging.getLogger(__name__).exception(
                            "Failed to initialize LightRAG storages"
                        )

                    # ingestion: prefer async API if available
                    try:
                        if hasattr(rag, "ainsert"):
                            await rag.ainsert("\n".join(texts))
                        elif (
                            hasattr(rag, "add_documents")
                            and hasattr(rag, "ainsert") is False
                        ):
                            # fallback to sync API in thread
                            await asyncio.to_thread(
                                getattr(rag, "add_documents"), texts
                            )
                        elif hasattr(rag, "upsert"):
                            await asyncio.to_thread(getattr(rag, "upsert"), texts)
                    except Exception:
                        logging.getLogger(__name__).exception(
                            "Failed to ingest documents into LightRAG"
                        )

                    # query using async APIs where possible
                    try:
                        if hasattr(rag, "aquery"):
                            return await rag.aquery(query)
                        if hasattr(rag, "aask"):
                            return await rag.aask(query)
                        # fall back to running sync methods in a thread
                        if hasattr(rag, "query"):
                            return await asyncio.to_thread(getattr(rag, "query"), query)
                        if hasattr(rag, "ask"):
                            return await asyncio.to_thread(getattr(rag, "ask"), query)
                        if hasattr(rag, "run"):
                            return await asyncio.to_thread(getattr(rag, "run"), query)
                        if hasattr(rag, "search"):
                            return await asyncio.to_thread(
                                getattr(rag, "search"), query
                            )
                    except Exception:
                        logging.getLogger(__name__).exception("LightRAG query failed")
                    return None

                import asyncio

                res = asyncio.run(_run_rag_workflow())
                print(res)
            except Exception:
                logging.getLogger(__name__).exception(
                    "LightRAG run failed; falling back to local pipelines"
                )
                use_lightrag = False
        except Exception:
            logging.getLogger(__name__).exception(
                "LightRAG run failed; falling back to local pipelines"
            )
            use_lightrag = False

    if not use_lightrag:
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


if __name__ == "__main__":
    main()
