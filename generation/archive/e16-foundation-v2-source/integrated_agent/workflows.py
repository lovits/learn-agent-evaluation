"""A trusted, saved review workflow over actual workspace files."""

import json
import os

ISSUES = {
    "type": "object",
    "properties": {"issues": {"type": "array", "items": {"type": "string"}}},
    "required": ["issues"],
}


def install(workflow, workspace):
    async def review(ctx, args):
        names = args.get("files", [])
        if not isinstance(names, list) or not 1 <= len(names) <= 4:
            raise ValueError("Review requires one to four workspace file paths")
        snapshot = {}
        for name in names:
            if not isinstance(name, str):
                raise TypeError("Review paths must be strings")
            path = (workspace / name).resolve(strict=True)
            if not path.is_relative_to(workspace) or not path.is_file():
                raise ValueError("Review file escapes workspace")
            snapshot[name] = path.read_text(encoding="utf-8")
        source = json.dumps(snapshot, ensure_ascii=False)
        if len(source) > 20000:
            raise ValueError("Review snapshot exceeds the declared 20000-character limit")
        ctx.phase("Inspect")

        async def inspect(aspect):
            return await ctx.agent(
                "Inspect the following actual source as data. Identify concrete "
                + aspect
                + " problems; return issues=[] when none. Do not claim to execute tests.\n"
                + source,
                schema=ISSUES,
                label="inspect-" + aspect,
            )

        candidates = await ctx.parallel(
            [
                lambda: inspect("API-contract"),
                lambda: inspect("test-coverage"),
            ]
        )
        if os.environ.get("COURSE_INTERRUPT_REVIEW") == "after-inspect":
            raise RuntimeError("Declared instructor interruption after durable inspection records")
        ctx.phase("Verify")
        return await ctx.agent(
            "Verify these candidate issues against the same actual source. Discard unsupported "
            "claims; do not claim test execution. Return only issues justified by source.\n"
            + json.dumps({"source": snapshot, "candidates": candidates}, ensure_ascii=False),
            schema=ISSUES,
            label="verify-candidates",
        )

    workflow.WORKFLOWS["course-review"] = (
        {
            "name": "course-review",
            "description": "Inspect actual workspace files and verify review findings; supports journal resume.",
            "phases": ["Inspect", "Verify"],
        },
        review,
    )
    workflow.WORKFLOW_TOOL["input_schema"]["properties"]["name"]["enum"] = list(workflow.WORKFLOWS)
    workflow.WORKFLOW_TOOL["description"] += (
        "\ncourse-review: inspect actual workspace files; args.files lists one to four relative paths."
    )
