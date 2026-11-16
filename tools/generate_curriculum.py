"""Run original PocketFlow planning nodes, then draft a grounded course design."""

import argparse
import json
import sys
import time
import types

from model_backend import PROJECT, VENDOR, codex_completion, sha


def main():
    import yaml
    from pocketflow import Flow, Node

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--resume", action="store_true", help="复用中断前保存且prompt完全相同的真实节点响应"
    )
    args = parser.parse_args()
    inputs = PROJECT / "generation/curriculum_inputs"
    output = PROJECT / "generation/output/curriculum_v2"
    private = PROJECT / "generation/private/curriculum_v2"
    output.mkdir(parents=True, exist_ok=True)
    private.mkdir(parents=True, exist_ok=True)
    contracts = json.loads((inputs / "lesson-contracts.json").read_text())
    brief = (PROJECT / "generation/curriculum_brief.md").read_text()
    calls = []
    previous = (
        json.loads((output / "model-calls.json").read_text())
        if args.resume and (output / "model-calls.json").exists()
        else []
    )

    def call_llm(prompt, use_cache=False):
        started = time.monotonic()
        full = brief + "\n\n遵守当前节点的输出协议，不要执行工具。\n\n" + prompt
        index = len(calls) + 1
        saved_prompt = private / f"prompt-{index}.txt"
        saved_reply = private / f"response-{index}.md"
        reused = bool(
            args.resume
            and index <= len(previous)
            and saved_prompt.exists()
            and saved_reply.exists()
            and saved_prompt.read_text() == full
            and sha(saved_reply.read_text()) == previous[index - 1]["response_sha256"]
        )
        result = saved_reply.read_text() if reused else codex_completion(full)
        (private / f"prompt-{index}.txt").write_text(full, encoding="utf-8")
        (private / f"response-{index}.md").write_text(result, encoding="utf-8")
        calls.append(
            {
                "prompt_sha256": sha(full),
                "response_sha256": sha(result),
                "elapsed_seconds": previous[index - 1]["elapsed_seconds"]
                if reused
                else round(time.monotonic() - started, 2),
                "reused_from_checkpoint": reused,
            }
        )
        (output / "model-calls.json").write_text(
            json.dumps(calls, ensure_ascii=False, indent=2) + "\n"
        )
        print(f"Model call {index} finished in {calls[-1]['elapsed_seconds']}s", flush=True)
        if index <= 3 and "```yaml" not in result:
            # Upstream nodes require fenced YAML; preserve the model's raw response above.
            yaml.safe_load(result)
            return "```yaml\n" + result.strip() + "\n```"
        return result

    bridge = types.ModuleType("utils.call_llm")
    bridge.call_llm = call_llm
    sys.modules["utils.call_llm"] = bridge
    sys.path.insert(0, str(VENDOR))
    from nodes import AnalyzeRelationships, FetchRepo, IdentifyAbstractions, OrderChapters

    class WriteCurriculumPlan(Node):
        def prep(self, shared):
            if len(shared["abstractions"]) != 16:
                raise ValueError("课程主题必须恰好16项，未以手写输出冒充生成结果。")
            if sorted(shared["chapter_order"]) != list(range(16)):
                raise ValueError("课程排序必须完整且无重复。")
            participants = {
                i for r in shared["relationships"]["details"] for i in (r["from"], r["to"])
            }
            if participants != set(range(16)):
                raise ValueError("每一课必须有先修或评测数据关系。")
            state = {k: shared[k] for k in ("abstractions", "relationships", "chapter_order")}
            (output / "planning-state.json").write_text(
                json.dumps(state, ensure_ascii=False, indent=2) + "\n"
            )
            facts = "\n\n".join(
                (inputs / name).read_text()
                for name in (
                    "teaching-method.md",
                    "evaluation-landscape.md",
                    "agent-capabilities.json",
                )
            )
            return (
                json.dumps(contracts, ensure_ascii=False)
                + "\n\n"
                + facts
                + "\n\n"
                + json.dumps(state, ensure_ascii=False)
            )

        def exec(self, context):
            return call_llm(
                "请输出最终中文课程设计Markdown，不要外层代码围栏。先讲原项目学习方式，再讲两框架评测与数据能力，"
                "再按e01到e16给出16个逐课卡片，每课使用独立二级标题，并列：评测对象、知识点、Agent代码增量、实验、验收、来源。"
                "最后写分阶段制作计划、每课文件结构、24到16映射、功能保留与未实现状态。控制在10000中文字以内。"
                "仅生成计划，不声称实验已执行。源码引用使用给出的固定提交GitHub地址；不得虚构来源、分数或功能。\n\n"
                + context
            )

        def post(self, shared, prep_res, exec_res):
            (output / "curriculum-draft.md").write_text(exec_res.rstrip() + "\n", encoding="utf-8")

    shared = {
        "repo_url": None,
        "local_dir": str(inputs),
        "project_name": contracts["title"],
        "github_token": None,
        "language": "Chinese",
        "use_cache": False,
        "max_abstraction_num": 16,
        "max_file_size": 100000,
        "include_patterns": {"*.md", "*.json", "*.py", "LICENSE"},
        "exclude_patterns": {"original-24.json", "__pycache__"},
    }
    fetch = FetchRepo()
    identify = IdentifyAbstractions(max_retries=1)
    analyze = AnalyzeRelationships(max_retries=1)
    order = OrderChapters(max_retries=1)
    write = WriteCurriculumPlan(max_retries=1)
    fetch >> identify >> analyze >> order >> write
    Flow(start=fetch).run(shared)
    provenance = {
        "generator": "The-Pocket/PocketFlow-Tutorial-Codebase-Knowledge",
        "upstream_commit": "05b24cbbb0fe409c5e23c9791f0342f07524ffdc",
        "backend": "local authenticated Codex CLI",
        "actual_model_calls": len(calls),
        "new_model_calls_in_this_attempt": sum(not c["reused_from_checkpoint"] for c in calls),
        "transport_normalization": "Valid bare YAML is wrapped in YAML fences for original node parsers; raw model replies are preserved.",
        "calls": calls,
        "nodes_run": [
            "FetchRepo",
            "IdentifyAbstractions",
            "AnalyzeRelationships",
            "OrderChapters",
            "WriteCurriculumPlan (course adapter)",
        ],
        "not_run": ["WriteChapters", "CombineTutorial"],
        "reason": "This request is course planning, not generation of all sixteen chapters.",
        "input_manifest": [
            {"path": str((inputs / name).relative_to(PROJECT)), "sha256": sha(content)}
            for name, content in shared["files"]
        ],
        "brief_sha256": sha(brief),
        "draft_sha256": sha((output / "curriculum-draft.md").read_text()),
        "implementation_status": "curriculum planning only; current lesson status is tracked in curriculum.json",
    }
    (output / "provenance.json").write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n"
    )
    print(f"PocketFlow curriculum finished: {len(calls)} model calls; {output}", flush=True)


if __name__ == "__main__":
    main()
