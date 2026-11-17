"""Capture real native DeepEval traces locally, including separately rooted threads.

The pinned runtime evicts completed traces outside evaluation. This scoped host
adapter observes end_trace; it preserves the original lifecycle and restores it.
It does not invent parent links or convert audit rows into synthetic spans.
"""

import threading
from contextlib import contextmanager

from deepeval.tracing.tracing import trace_manager

_capture_lock = threading.Lock()


@contextmanager
def capture_native_traces():
    if not _capture_lock.acquire(blocking=False):
        raise RuntimeError("Native trace capture is already active in this process")
    records, lock = [], threading.Lock()
    original = trace_manager.end_trace

    def end_trace(trace_uuid):
        trace = trace_manager.get_trace_by_uuid(trace_uuid)
        original(trace_uuid)
        if trace is not None:
            record = trace_manager.create_trace_api(trace).model_dump(
                mode="json", by_alias=True, exclude_none=True
            )
            with lock:
                records.append(record)

    trace_manager.end_trace = end_trace
    try:
        yield records
    finally:
        trace_manager.end_trace = original
        _capture_lock.release()
