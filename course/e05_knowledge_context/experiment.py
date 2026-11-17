"""Compare k and per-search context limits with one fixed query and document snapshot."""

import uuid

from eval_course.knowledge import catalog
from eval_course.records import save
from eval_course.tinyrag import retrieve


def main():
    documents = catalog()
    query = "Atlas 补丁发布前的检查要求 测试命令 发布条件"
    rows = []
    for k, context_limit in [(1, 1), (3, 1), (3, 2)]:
        hits = retrieve(query, limit=k, documents=documents)
        rows.append(
            {"k": k, "context_limit": context_limit, "hits": hits, "selected": hits[:context_limit]}
        )
    print(
        save(
            {
                "run_id": uuid.uuid4().hex,
                "kind": "native_retrieval_probe",
                "query": query,
                "knowledge_manifest": [
                    {key: d[key] for key in ["path", "sha256"]} for d in documents
                ],
                "rows": rows,
            },
            prefix="e05-suite",
        )
    )


if __name__ == "__main__":
    main()
