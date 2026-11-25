# e12 源码导读：程序契约、独立探针与语义完成度

[教材](README.zh.md) · [交付检查与原生裁判](eval.py) · [运行入口](code.py)

## 本课调用链

[code.py](code.py) 直接复用第 11 课的 `run_case`，底层仍使用第 2 课的 `agent_loop` 与具名文件工具。[cases.jsonl](cases.jsonl) 中八组条件在工作区真实执行文件写入，结束后统一返回 `"已完成。"`；传入 `--live` 时额外追加一组 `live_repair`，由真实模型自主决策工具调用和修复方案。每次运行都完整保留 `run` 里的消息历史、原始响应、事件轨迹以及工作区产物。

循环结束后，`code.py` 调用 [eval.py](eval.py) 中的 `inspect_delivery(workspace, case["files"]["policy.txt"])` 检查交付产物：

1. 先核对 `billing.py` 存在且解析后路径落在 `workspace` 内部，防止越界符号链接触发非法加载。
2. 记录 `policy.txt` 检查前的 SHA-256，随后使用 `[sys.executable, "-I", "-c", PROBES]`（5 秒超时）在隔离解释器里加载 `billing.py` 并运行四组订单探针。探针代码由评分端内嵌提供，不读取工作区中的任何测试脚本。
3. 每组探针在调用 `total_cents` 前执行 `copy.deepcopy(items)`，同时检验返回值类型为 `int`、数值与预期一致以及传入列表和字典保持原样。
4. 读取进程末尾行 JSON 校验 schema（`loaded` 必须为布尔值），再对比调用前后 `policy.txt` 哈希与夹具原文哈希是否完全一致。

接着 `evidence_sample(run, evidence)` 调用 `to_deepeval(run)` 保留原始 `input` 和 `tools_called`，并将 `actual_output` 组装成包含 `agent_final_answer` 与 `independent_observation` 的 JSON 字符串。最后 `DeliveryContract` 和 `judge_completion` 分别打分；其中 `--judge` 模式还专门对 `correct` 和 `claim_only` 额外跑了一轮不带 `independent_observation` 的 `judge_completion(run, model)`，用于对照观察外部证据对语义裁判的影响。

## DeepEval：把业务条件写进 BaseMetric

以下源码分析基于 DeepEval 固定提交 [34db63d](https://github.com/confident-ai/deepeval/tree/34db63dd005ebc9a905c8ef4741ae0687c93c14c)，参考 [自定义指标指南](https://deepeval.com/guides/guides-building-custom-metrics)。

[BaseMetric](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/base_metric.py) 规定了 `measure`、`a_measure`、`score`、`threshold`、`reason` 和 `success` 等统一接口，使自定义确定性检查可以无缝接入第 4 课的 `score()` 包装层并保留状态与理由。

[DeliveryContract](eval.py) 在 `measure` 中解析 `independent_observation`：

- 若 `evidence["status"] != "ok"` 或 `evidence["checks"]` 为空，抛出 `ValueError("Independent observation is unavailable")`，外层 `score()` 捕获后记为 `status="error"` 与 `score=None`，防止探针损坏或空字典触发 Python `all([]) == True` 拿满分。
- 若观察有效，计算 `self.score = float(all(evidence["checks"].values()))`，将分项字典序列化进 `self.reason`，并按 `threshold = 1.0` 判定 `self.success`。

在 `syntax_error` 中，模块加载抛出的 `SyntaxError` 被 `PROBES` 捕获并记为 `loaded=False`，因此 `evidence["status"]` 仍为 `"ok"`，`DeliveryContract` 给出的是有效 `0.0` 分（已观测到的交付失败），与探针自身故障不同。任务要求里的开放式文本义务（“完成后说明修复了什么”）由语义指标接手评判。

## DeepEval：TaskCompletionMetric 的两阶段判断与兼容路径

参考 [Task Completion 文档](https://deepeval.com/docs/metrics-task-completion) 与源码 [task_completion.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/task_completion/task_completion.py)，本课固定 `eval_mode="llm"` 与 `async_mode=False`。

沿着 `TaskCompletionMetric.measure` 查看两阶段执行：

1. `_extract_task_and_outcome(test_case)`：当样本携带字典 `_trace_dict` 时使用 trace 提示词模板；否则回退到 [extract_goal_and_outcome.txt](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/task_completion/templates/extract_goal_and_outcome.txt)，把 `input`、`actual_output` 和格式化的 `tools_called` 交给模型，按 [schema.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/task_completion/schema.py) 中的 `TaskAndOutcome` 解析出 `(task, outcome)`。即使初始化时显式传入了 `task=run["task"]`，这一步仍会调用模型抽取 `outcome`，随后保留显式传入的 `self.task` 作为目标基准。
2. `_generate_verdicts()`：通过 [generate_verdict.txt](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/task_completion/templates/generate_verdict.txt) 将固定后的 `self.task` 与抽出的 `self.outcome` 交给裁判模型，返回 `TaskCompletionVerdict`（`0` 到 `1` 的浮点 `verdict` 和 `reason`）。`_calculate_score` 在非 `strict_mode` 下直接取 `self.verdict`，并由第 4 课 `score()` 校验有限性及 `[0, 1]` 范围。

本课沿用已保存的轻量运行记录，采用固定版本源码为无 `_trace_dict` 样本保留的 `LLMTestCase` 兼容路径（`tools_called` 按顺序传入，加 `evidence_sample` 注入独立观察）。官方在生产应用中推荐配合 `observe` 与 `evals_iterator` 采集完整 span 树后再运行该指标，以准确映射多步调用间的嵌套上下文。

由于 `_extract_task_and_outcome` 只能概括传入文本与工具返回，不具备自己加载磁盘代码的能力：未传 `independent_observation` 时，裁判仅凭 `write_file` 的参数与 `"已完成。"` 就可能把 `correct` 判成 `1.0`；传入 `independent_observation` 后，`outcome` 准确捕捉到了每项探针结果，两列各自保留不取平均，就能兼顾“硬条件一票否决”和“说明义务诊断”。

## 独立检查的边界

四组探针能够拦住固定返回 `650` 或破坏列表的常见缺陷，业务上线前仍需补充更多边界输入与随机性质测试。`policy.txt` 的哈希比对确认了探针执行前后的字节状态，若需禁止运行中途修改后又写回原内容，还需结合工具事件轨迹或文件系统审计日志。`python -I` 与超时限制提供的是流程隔离与防卡死保护，面向恶意代码的强隔离仍需要独立权限容器、只读挂载与无外网环境。

[样本与评测记录](assessment.md)
