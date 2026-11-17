"""Check evidence plumbing; retrieval and answer quality are later metrics."""

import hashlib

from .code import sent_contexts


def check_run(run):
    versions = {d["path"]: d["sha256"] for d in run["knowledge"]["documents"]}
    parts = [p for retrieval in run["retrievals"] for p in retrieval["hits"]]
    return {
        "search_observed": bool(run["retrievals"]),
        "source_versions_match": all(versions[p["path"]] == p["source_sha256"] for p in parts),
        "chunk_hashes_match": all(
            hashlib.sha256(p["text"].encode()).hexdigest() == p["sha256"] for p in parts
        ),
        "chunk_lengths_match": all(p["end"] - p["start"] == len(p["text"]) for p in parts),
        "sample_matches_model_input": run["sample"]["retrieval_context"]
        == sent_contexts(run["model_inputs"]),
    }
