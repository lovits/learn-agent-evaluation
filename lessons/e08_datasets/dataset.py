"""Dataset checks operate on evidence records, not fabricated Agent responses."""

import hashlib
import re
import unicodedata

FAMILY_SPLITS = {
    "upload_contract": "development",
    "directory_listing": "calibration",
    "file_edit": "holdout",
}


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def question_key(text):
    return re.sub(r"\W+", "", unicodedata.normalize("NFKC", text).casefold())


def structure_errors(candidate, documents):
    errors = []
    for key in ("id", "question", "reference", "family", "origin", "difficulty", "query_type"):
        if not isinstance(candidate.get(key), str) or not candidate[key].strip():
            errors.append("missing:" + key)
    if candidate.get("family") not in FAMILY_SPLITS:
        errors.append("unknown_family")
    if type(candidate.get("answerable")) is not bool:
        errors.append("answerability_required")
    evidence = candidate.get("evidence", [])
    if not evidence:
        errors.append("missing_evidence")
    for item in evidence:
        original = documents.get(item["id"])
        if original is None:
            errors.append("unknown_source")
        elif item.get("sha256") != digest(original["text"]):
            errors.append("stale_source")
    if candidate.get("actual_output") is not None:
        errors.append("candidate_is_not_an_executed_run")
    return errors


def audit(candidates, documents, support_verdicts):
    """All structurally valid candidates still need human approval before a real test set."""
    clusters = {}
    for row in candidates:
        clusters.setdefault(question_key(row["question"]), []).append(row)
    rows = []
    for row in candidates:
        errors = structure_errors(row, documents)
        cluster = clusters[question_key(row["question"])]
        duplicate_of = cluster[0]["id"] if cluster[0]["id"] != row["id"] else None
        if len({r["family"] for r in cluster}) > 1:
            errors.append("cross_family_duplicate")
        elif duplicate_of:
            errors.append("duplicate_question")
        verdict = support_verdicts.get(row["id"])
        if verdict is None:
            errors.append("automated_review_missing")
        elif verdict.get("supported") is not True:
            errors.append("reference_not_supported")
        if (
            row["query_type"] == "multi_hop"
            and (verdict or {}).get("requires_multiple_sources") is not True
        ):
            errors.append("multi_hop_not_established")
        rows.append(
            {
                **row,
                "split": FAMILY_SPLITS.get(row["family"]),
                "errors": errors,
                "duplicate_of": duplicate_of,
                "automated_review": verdict,
                "review_state": "quarantined" if errors else "pending_human",
                "eligible_for_human_review": not errors,
                "actual_output": None,
            }
        )
    return rows


def near_duplicates(candidates, threshold=0.8):
    """Lexical suggestions only: similar wording can ask genuinely different questions."""
    pairs = []
    for i, left in enumerate(candidates):
        a = set(re.findall(r"\w+", left["question"].casefold()))
        for right in candidates[i + 1 :]:
            b = set(re.findall(r"\w+", right["question"].casefold()))
            score = len(a & b) / len(a | b) if a | b else 0.0
            if score >= threshold:
                pairs.append({"left": left["id"], "right": right["id"], "jaccard": score})
    return pairs
