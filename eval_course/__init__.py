"""Runnable lessons for RAG and agent evaluation."""

import os

# Set SDK opt-outs before any submodule imports those SDKs.
os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")
os.environ.setdefault("RAGAS_DO_NOT_TRACK", "true")
