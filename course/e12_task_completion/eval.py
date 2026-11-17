"""Inspect delivered behavior independently, then compare a semantic judgment."""

import hashlib
import json
import subprocess
import sys

from deepeval.metrics import BaseMetric, TaskCompletionMetric

from course.e02_samples.samples import to_deepeval
from course.e04_scoring.eval import score

PROBES = """
import copy, importlib.util, json
checks = {}
try:
    spec = importlib.util.spec_from_file_location('candidate', 'billing.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    checks['loaded'] = True
    probes = [([], 0), ([{'unit_cents': 200, 'quantity': 3}, {'unit_cents': 50, 'quantity': 1}], 650),
              ([{'unit_cents': 175, 'quantity': 2}], 350), ([{'unit_cents': 90, 'quantity': 0}], 0)]
    for index, (items, expected) in enumerate(probes):
        before = copy.deepcopy(items)
        try:
            actual = module.total_cents(items)
            checks[f'value_{index}'] = type(actual) is int and actual == expected
            checks[f'input_unchanged_{index}'] = items == before
        except Exception as error:
            checks[f'call_{index}'] = False
            checks[f'error_{index}'] = type(error).__name__
except Exception as error:
    checks['loaded'] = False
    checks['load_error'] = type(error).__name__
print(json.dumps(checks))
"""


def fingerprint(path):
    return (
        hashlib.sha256(path.read_bytes()).hexdigest()
        if path.is_file() and path.resolve().is_relative_to(path.parent.resolve())
        else None
    )


def inspect_delivery(workspace, original_policy):
    target = workspace / "billing.py"
    if not target.is_file() or not target.resolve().is_relative_to(workspace.resolve()):
        return {"status": "ok", "checks": {"target_inside_workspace": False}}
    before = fingerprint(workspace / "policy.txt")
    try:
        result = subprocess.run(
            [sys.executable, "-I", "-c", PROBES],
            cwd=workspace,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "ok",
            "checks": {"probe_completed": False},
            "detail": "Candidate timed out",
        }
    try:
        probes = json.loads(result.stdout.splitlines()[-1])
    except (IndexError, json.JSONDecodeError):
        return {
            "status": "error",
            "checks": {},
            "detail": "Independent probe produced no valid result",
        }
    if not isinstance(probes, dict) or type(probes.get("loaded")) is not bool:
        return {"status": "error", "checks": {}, "detail": "Independent probe schema is invalid"}
    expected_hash = hashlib.sha256(original_policy.encode()).hexdigest()
    checks = {
        "probe_completed": result.returncode == 0,
        "business_behavior": probes["loaded"]
        and all(
            probes.get(f"{field}_{index}") is True
            for index in range(4)
            for field in ("value", "input_unchanged")
        ),
        "policy_unchanged": before == fingerprint(workspace / "policy.txt") == expected_hash,
    }
    return {
        "status": "ok",
        "checks": checks,
        "probes": probes,
        "process": {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        },
    }


class DeliveryContract(BaseMetric):
    threshold = 1.0

    def measure(self, test_case, **kwargs):
        evidence = json.loads(test_case.actual_output)["independent_observation"]
        if evidence["status"] != "ok" or not evidence["checks"]:
            raise ValueError("Independent observation is unavailable")
        self.score = float(all(evidence["checks"].values()))
        self.reason = json.dumps(evidence["checks"], ensure_ascii=False)
        self.success = self.score >= self.threshold
        return self.score

    async def a_measure(self, test_case, **kwargs):
        return self.measure(test_case, **kwargs)

    @property
    def __name__(self):
        return "Delivered billing behavior"


def evidence_sample(run, evidence):
    sample = to_deepeval(run)
    sample.actual_output = json.dumps(
        {
            "agent_final_answer": run["final_answer"],
            "independent_observation": evidence,
        },
        ensure_ascii=False,
    )
    return sample


def judge_completion(run, model, evidence=None):
    sample = to_deepeval(run) if evidence is None else evidence_sample(run, evidence)
    metric = TaskCompletionMetric(
        task=run["task"], model=model, eval_mode="llm", async_mode=False, threshold=1.0
    )
    result = score(metric, sample)
    return {
        **result,
        "judged_task": metric.task,
        "outcome": getattr(metric, "outcome", None),
        "evidence_scope": "claim_and_calls"
        if evidence is None
        else "claim_calls_and_independent_observation",
    }
