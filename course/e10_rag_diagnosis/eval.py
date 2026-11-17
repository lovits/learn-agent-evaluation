"""Find the first observed evidence gap; keep noise arithmetic separate."""


def first_gap(documents, retrieved, selected, source):
    document = next((d for d in documents if d["path"] == source["path"]), None)
    if document is None:
        return "source_missing"
    if document["sha256"] != source["sha256"]:
        return "source_version"
    if not any(p["path"] == source["path"] for p in retrieved):
        return "retrieval_output"
    if not any(p["path"] == source["path"] for p in selected):
        return "context_assembly"
    return None


def noise_fraction(correct, relevant_support, irrelevant_support):
    if len({len(correct), len(relevant_support), len(irrelevant_support)}) != 1:
        raise ValueError("One support judgment is required per answer statement")
    if any(
        type(v) is not bool
        for group in [correct, relevant_support, irrelevant_support]
        for v in group
    ):
        raise ValueError("Support judgments must be booleans")
    if not correct:
        return {"relevant": None, "irrelevant": None}
    return {
        "relevant": sum(not c and r for c, r in zip(correct, relevant_support)) / len(correct),
        "irrelevant": sum(
            not c and i and not r for c, r, i in zip(correct, relevant_support, irrelevant_support)
        )
        / len(correct),
    }
