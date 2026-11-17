# 第11课：任务完成，先检查，再允许结束

## 问题

`shipping.py` 中有一个运费函数：1000克收费600分，之后每开始额外1000克增加200分。因此1001克已经进入下一档，应该收费800分。

初始实现却把1001克算成600分：

```python
def shipping_fee(weight_grams, expedited=False):
    extra = max(0, (weight_grams - 1000) // 1000)
    return 600 + extra * 200 + (300 if expedited else 0)
```

合同还要求：重量必须是精确的 `int`，且在1到5000之间，不能把 `bool` 当整数；`expedited` 必须是精确的 `bool`；类型错误先抛 `TypeError`，重量越界再抛 `ValueError`；加急增加300分；原测试文件必须保留。知识库可以挂载给模型查询。

修完公式后，还得回答一个问题：什么时候可以结束任务？模型可能回答“已完成”，但文件根本没改；也可能只让三个公开例子通过，却遗漏类型和边界；甚至可能删除测试，使测试命令收集到零个用例后仍正常退出。

循环需要先审查这个停止候选，再决定是否接受模型的完成声明。

## 解决方案

本课保留已有结构：第4课的真实 Agent 循环、第2课的文件工具与权限，以及第10课的动态工具池和宿主模型桥。模型仍然输出动作 JSON，文件和 Bash 工具在 Docker 中执行。

最小增量放在 `run_case` 外层：Agent 每次停止后，先检查三个公开例子以及测试文件是否原样保留。通过后，状态只写成 `ready_for_external_verification`，表示公开条件已经满足，下一步还要交给独立验收。

公开检查失败时，状态为 `blocked`。真实检查反馈会追加到 `history`，然后沿用同一个工具池继续下一段循环。最多审查3轮，每段最多12个模型步骤。检查异常记为 `review_error`，耗尽轮数记为 `limit`，都不能伪装成完成。

Agent 产物冻结后，独立 Docker 验收器再检查其他输入。保留题不会回流给 Agent。本课还预先声明了一个明确冲突：若约束同时要求保留公开测试和删除全部测试，直接返回 `impossible`，模型调用次数为0。这个分支只识别事先声明的字段冲突；其他自然语言目标还需要另外判断。

完整模块可分别阅读 [code.py](code.py)、[verify.py](verify.py)、[runner.py](runner.py)、[metrics.py](metrics.py) 和 [eval.py](eval.py)。

## 工作原理

Agent 先给出停止候选，公开审查决定是否续轮。产物确定后，独立验收结果再交给规则指标与语义裁判。

**第1步：把内部循环的结束当作停止候选**

`run_case` 仍创建 `ToolPool`，并调用原来的 `agent_loop`。模型只能选择动作；文件读取、修改和命令执行由工具完成。

```python
for _ in range(max_turns):
    result = agent_loop(
        task, workspace, model=model, max_steps=12,
        tool_dispatch=pool.dispatch
    )
    history.extend([
        {"role": "user", "content": task},
        *recorded_messages(result["events"]),
    ])
# 省略：停止审查与续轮
```

这里的 `result["status"] == "finished"` 只说明模型这一轮没有继续请求工具。此时才开始核对文件是否满足合同。完整接入位置见 [code.py](code.py)。

**第2步：公开审查读取真实文件并运行函数**

`probe` 直接读取 `shipping.py` 和 `test_shipping.py`。它计算文件哈希，再启动受限子进程执行输入用例。

```python
source = source_path.read_text()
protected = workspace / "test_shipping.py"
retained = protected.is_file() and digest(
    protected.read_text()
) == digest(case["files"]["test_shipping.py"])
child = subprocess.run(
    [sys.executable, "-I", "-S", str(HERE / "runner.py")],
    input=json.dumps({"source": source, "cases": checks}),
    text=True, capture_output=True, timeout=4, check=False,
)
# 省略：解析结果并生成检查项
```

执行结果同时比较返回值和精确类型；预期异常则比较异常类。公开阶段检查1000、2000和1001克，独立阶段另有20个保留输入，共23个行为输入。报告还保存源码哈希、源码是否改变和测试文件是否保留，便于追查修改。验收只覆盖预先声明的纯Python子集和有限输入，不能证明任意程序对所有输入都正确。执行范围与资源限制见 [runner.py](runner.py)，完整机制见 [源码导读](source_walkthrough.md)。

**第3步：公开失败就带着真实反馈继续**

`GoalState.review` 把检查结果转换为明确状态。只有公开检查已评分且全部通过，才允许进入外部验收。

```python
def review(self, evidence, max_turns):
    self.reviews += 1
    if evidence["status"] == "impossible":
        self.status = "impossible"
    elif evidence["status"] != "scored":
        self.status = "review_error"
    elif evidence["passed"]:
        self.status = "ready_for_external_verification"
    elif self.reviews >= max_turns:
        self.status = "limit"
    else:
        self.status = "blocked"
# 省略：返回状态
```

若1001克仍返回600，状态就是 `blocked`。下一段循环能看到原任务、此前模型消息、工具结果和本次公开反馈，并继续使用已经发现的工具池。这个接入点来自 Learn Claude Code s17 的停止审查。它的会话恢复、后台延迟和通用目标判断，留到后续集成时再接入。

**第4步：用外部事实生成规则分数**

独立验收完成后，可信结果通过 `metadata` 交给 `ExternalCompletionMetric`。证据结构由严格的 Pydantic 模型验证，不接受字符串形式的真假值。

```python
class ExternalCompletionMetric(BaseMetric):
    def __init__(self):
        self.threshold, self.async_mode = 1.0, False

    def measure(self, test_case, **kwargs):
        self.score, self.error, self.reason = None, None, None
        data = (test_case.metadata or {})["external_evidence"]
        self.score = evidence_score(data)
        return self.score
# 省略：错误记录、异步入口和名称
```

所有必需检查为真时得1；只要一个为假就得0。空检查、结构错误、执行器不适用或验收异常都记为 `unscored`，分数是 `null`，而不是0。对应的 `RagasExternalCompletion` 提供 `ascore` 和同步 `score`。这些规则指标不请求模型，本轮同步与异步结果一致。

**第5步：再让原生语义指标判断轨迹**

规则检查回答“文件是否真的合格”，语义指标则判断“给定轨迹看起来是否完成目标”。本课实际调用 DeepEval 的 `TaskCompletionMetric`：

```python
sample = LLMTestCase(
    input=REFERENCE,
    actual_output="\n".join(
        m.pretty_repr() for m in messages
    ),
)
metric = TaskCompletionMetric(
    task=REFERENCE, model=deep_judge,
    eval_mode="llm", async_mode=False, threshold=1,
)
value = metric.measure(sample, _show_indicator=False)
```

DeepEval 先抽取 `TaskAndOutcome`，再生成带浮点结论的 `TaskCompletionVerdict`。官方推荐完整轨迹；本课固定源码走兼容的 `input` 与 `actual_output` 分支，输入是序列化的对话和外部检查。原生 SDK 轨迹采集尚未接入。

Ragas 的 `AgentGoalAccuracyWithReference` 使用给定参考目标，`WithoutReference` 使用裁判推断的目标。二者先生成 `WorkflowOutput(user_goal, end_state)`，再用 `CompareOutcomeOutput` 返回字符串 `"0"` 或 `"1"`。本轮 `MetricResult.reason` 为 `None`，实际解释保存在捕获的第二阶段结构化结果里。提示词、异步路径和校验细节见 [源码导读](source_walkthrough.md)。

**第6步：组合分数保留必需检查的失败**

组合函数取两种分数的较小值。缺少任一有效分数时，结果保持未评分。

```python
def composite(rule_score, judge_score):
    if any(s is None for s in (rule_score, judge_score)):
        return {"status": "unscored", "score": None}
    if any(
        not math.isfinite(s) or not 0 <= s <= 1
        for s in (rule_score, judge_score)
    ):
        raise ValueError("Scores must be finite and within [0, 1]")
    return {"status": "scored", "score": min(rule_score, judge_score)}
```

本轮就发生了一次裁判误判。`early_claim_only` 只有业务请求和实际的“已完成”回答，DeepEval 给出1，还在抽取结果中补出了未被证实的类型修复、边界处理和独立检查通过；Ragas 两种指标均为0。加入同一时刻真实的公开失败结果后，文件与 Agent 都没有重跑，DeepEval 变为0.2，Ragas 仍为0。这只是评分输入增加了证据，不能说 Agent 变好了。

讲师构造的“只修公开例子”状态通过三个公开用例，却在完整检查中失败；DeepEval 为0.35，Ragas 为0。此时 `min(0, 0.35) = 0`，规则失败不会被语义裁判的部分分抬高。更多结果见 [运行摘要](run_summary.md)。

本轮运行了2次模型 Agent，共12个模型响应、15个工具请求。正常路径1轮通过；另一条路径明确注入“先假报完成”的故障，首轮0个工具请求，随后修复，共2轮。它不能被解释为模型的自然故障率。两次最终产物均通过3个公开与20个保留输入，并保留测试。

另外，6个讲师构造状态分别检查了只改说明、删除测试、假报成功、只修公开例子、重复多加费用和使用不支持的 `import`。最后一种为未评分，不是0。4种评分投影实际产生24次裁判请求、12个指标结果、0个错误；精确模型标识和费用未提供。新增冲突预检后来在 Docker 单独执行，原有两次 Agent 轨迹和裁判记录仍按原运行保存。

## 相对上一课的变更

| 能力 | 上一课已有 | 本课新增 |
|---|---|---|
| Agent 执行 | 文件工具、权限、真实循环 | 保持不变 |
| 工具接入 | 动态工具池、宿主模型桥 | 续轮沿用同一工具池 |
| 停止条件 | 模型结束当前循环 | 公开规则审查停止候选 |
| 最终证据 | 工具调用与局部结果 | 独立业务验收与测试保护 |
| 评分 | 工具层指标 | 外部规则、原生语义指标与组合分数 |
| 冲突 | 未处理本课合同冲突 | 声明式冲突直接记为不可完成 |

工具调用成功率很高，只能说明工具层运行顺利。整项任务完成还要求业务行为、异常类型、边界条件和受保护文件同时满足。两种结论不能互相替代。

## 试一下

先在宿主机分别启动模型桥和裁判桥，凭据不要放进容器：

```bash
python3 tools/model_bridge.py
```

另开一个终端启动裁判桥：

```bash
python3 tools/judge_bridge.py
```

两项服务端口分别是8766和8768。然后构建镜像并运行 Agent：

```bash
docker compose build
docker compose run --rm -T --entrypoint python course \
  -m lessons.e11_task_completion.code
```

接着运行断网的独立验收器：

```bash
docker compose --profile verify run --rm -T \
  --entrypoint python verifier \
  -m lessons.e11_task_completion.eval
```

最后读取已经完成的验收报告，运行语义裁判；这一步不会再次执行工作目录中的文件：

```bash
docker compose run --rm -T --entrypoint python course \
  -m lessons.e11_task_completion.eval --judge
```

三步依次覆盖 `runs/e11-agents.json`、`runs/e11-evaluation.json` 和 `runs/e11-judges.json`，需要保留旧结果时应先另存。私有规则位于 `evaluation_private/e11.json`，构建镜像时被排除，只读挂载给验收器。

阅读页面可以这样启动：

```bash
docker compose up -d
```

浏览器访问 `http://localhost:8765/lesson11`。运行后试着从记录中回答三个问题：

1. 初始实现为什么让1001克失败？
2. 删除测试后，即使函数行为正确，为什么整项任务仍不能通过？
3. 只给评分输入补充检查证据，为什么不能称为 Agent 变好了？

练习见 [exercises.md](exercises.md)，参考答案见 [solutions.md](solutions.md)。验收说明与生成记录分别见 [e11-validation.md](../../docs/e11-validation.md) 和 [e11-README.md](../../generation/e11-README.md)。

## 接下来

续轮会保留任务、工具结果和失败原因，对话也会越来越长。第12课将进入多轮、上下文压缩和持久记忆：当会话继续时，哪些合同、失败证据和不可违反的约束必须保留下来，不能在压缩中丢失。
