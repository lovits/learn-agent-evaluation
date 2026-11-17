"""Keep observed provider counters separate from elapsed time and unknown billing."""


def usage_ledger(metadata):
    records = [u for item in metadata for u in item.get("usage", [])]
    fields = (
        "input_tokens",
        "cached_input_tokens",
        "cache_write_input_tokens",
        "output_tokens",
        "reasoning_output_tokens",
    )
    totals = {}
    for name in fields:
        complete = bool(metadata) and all(item.get("usage") for item in metadata)
        complete = complete and all(type(u.get(name)) is int and u[name] >= 0 for u in records)
        totals[name] = sum(u[name] for u in records) if complete else None
    return {
        "successful_responses": len(metadata),
        "responses_with_usage": sum(bool(item.get("usage")) for item in metadata),
        "reported_usage_records": len(records),
        "provider_counter_totals": totals,
        "counter_semantics": "Raw reported counters; cached/reasoning counters are not added again to input/output totals. Missing fields remain null; not an invoice.",
        "reported_models": sorted(
            {item["reported_model"] for item in metadata if item.get("reported_model")}
        ),
        "responses_without_model_id": sum(not item.get("reported_model") for item in metadata),
        "real_bill": None,
        "price_source": None,
        "failed_request_usage": "unknown; successful responses do not account for failed provider requests",
    }


def application_resources(row):
    sessions = [row["lead"], *[c["result"] for c in row["children"]]]
    attempts = [item for s in sessions for item in s["model_inputs"]]
    metadata = [i["response_metadata"] for i in attempts if i["response_received"]]
    tools = [e for s in sessions for e in s["events"] if e["type"] == "tool"]
    signatures = [(e["call"]["name"], e["call"]["arguments_json"]) for e in tools]
    reads = [
        key
        for key in signatures
        if key[0] in {"read_file", "search_knowledge", "mcp__docs__search"}
    ]
    return {
        "model_request_attempts": len(attempts),
        "model_requests_without_received_response": sum(
            not i["response_received"] for i in attempts
        ),
        "application_model": usage_ledger(metadata),
        "support_model": usage_ledger([c.get("model", c) for c in row["support_calls"]]),
        "tool_calls": len(tools),
        "repeated_read_signatures_beyond_first": len(reads) - len(set(reads)),
        "read_repeat_limit": "Literal same-argument repeats only; necessity requires task context and source version.",
        "wall_elapsed_seconds": row["wall_elapsed_seconds"],
        "tool_elapsed_sum_seconds": sum(e["elapsed_seconds"] for e in tools),
        "background_elapsed_sum_seconds": sum(
            j["elapsed_seconds"] for s in sessions for j in s["background_jobs"]
        ),
        "latency_limit": "Overlapping durations must not be summed into end-to-end wall latency.",
    }
