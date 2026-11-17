# 第16课：综合回归，从运行证据到发布门禁

## 问题

第15课校准了裁判，这一课继续检查裁判实际收到的证据。采样时漏掉一条命令，就可能改变它对“测试已完成”的判断。

这次用讲师构造的运费小项目做真实执行实验。规范要求保留原测试，模型也说“测试已通过”。这句话仍然不能证明本次运行真的保留并执行了原测试。

回到运行记录，还会遇到这些情况：

- 工作流显示 `completed`，可能只代表三个步骤走完，不代表它读过测试文件。
- 普通轨迹显示 `SUCCESS`，可能只是工具函数正常返回了 `"Error: ..."`。
- 本课声明了两个实现文件的读取投影，还要确认实际轨迹是否包含它们。

结课时要沿着实际记录核对：模型提出什么动作，工具返回什么，裁判看见了什么，文件最终变成什么。

本课正式连接固定上游 s15、原生 s09、s16 与 s17。前15课的独立教学实现仍可分别运行。总体接线见[架构说明](../../integrated_agent/architecture.md)，17项具体契约与限制见[能力范围](../../integrated_agent/capabilities.md)。

![综合运行时、证据与验收关系](images/integrated-runtime.png)

[打开可编辑的 draw.io 原图](images/integrated-runtime.drawio)。

## 解决方案

先冻结任务、知识库和成功合同，再运行 Agent。运行时保存真实请求、响应、工具参数和原生轨迹。采样器只从这些记录投影评测样本。最后，由断网验收器直接检查工作区和原生状态。

执行和评分分开保存。先从轨迹里找出具体响应与工具结果，再按两个框架的定义评分。独立验收器直接检查文件和状态，发布门禁最后逐项检查关键条件。这样遇到分歧时，可以回到产生它的那一步。

组合实验中的阶段由讲师脚本安排。准备练习、批准当前计划、提交 Git 变更，都是讲师脚本的动作，不能写成模型自主完成。模型判断是否继续目标循环，与讲师决定先做修复还是队友评审，也是两种不同职责。

实验数字统一记录在[运行摘要](run_summary.md)。主文只沿调用链看六个必要接入点。

## 工作原理

**第1步：让公开入口进入原生循环**

从 `Runtime.submit` 进入，任务先写进历史，再进入接入了 Goal 机制的原生循环：

```python
# 节选：runtime.py / Runtime.submit，省略锁与前置校验
self.history.append({"role": "user", "content": query})
self.host.agent_loop(self.history, self.context, query)
return self.snapshot()
```

任务、可选目标与工作区进入这里，运行后返回含请求和状态的快照。接线可查看 [`Runtime.submit` 与 `_goal_loop`](../../integrated_agent/runtime.py)。s17 与普通任务共用入口，但 Goal 裁判只读对话证据。容器中的工具修改工作区，只读知识库提供规范，独立验收核实最终事实。忽略这一步，可能测试了 Goal 控制器，却没有测试真正执行任务的 Agent。

**第2步：保存可恢复的可信工作流**

`course-review` 先并行检查接口合同与测试覆盖，再验证候选问题：

```python
# 节选：workflows.py，省略读取文件与后续候选验证
candidates = await ctx.parallel([
    lambda: inspect("API-contract"),
    lambda: inspect("test-coverage"),
])
```

完整源码见 [`workflows.py`](../../integrated_agent/workflows.py)。工作流接收一至四个实际文件，返回符合 schema 的问题列表；它在 `Runtime.__init__` 中安装。journal 用步骤名、提示和 schema 组成语义键，只恢复成功步骤。历史实验在两次真实检查后故意中断，新进程复用两步，只新增一次验证请求。忽略持久日志，就无法区分恢复与重跑；忽略输入范围，则可能把“没读测试”的旧反例误写成正确评审。提供完整输入后，意见才具备接受语义复核的条件，`completed` 仍不证明内容正确。

**第3步：保存原生轨迹与请求账本**

每次实际模型调用先记录参数，再保存响应或错误：

```python
# 节选：RecordedMessages.create，row 初始化、账本与异常处理省略
result = self.sdk.messages.create(**request)
with self.lock:
    row.update(response_received=True, response=json_value(result))
update_current_span(input=request["messages"], output=row["response"])
```

完整实现见 [`RecordedMessages`](../../integrated_agent/runtime.py) 与 [`capture_native_traces`](../../integrated_agent/traces.py)。请求账本记录每次发送与返回，真实 trace 记录调用作用域；观测点分别接在模型调用、工具调用与 trace 结束处。队友线程若产生独立根，就保留独立根，不补造 `parent`。忽略这一层，只看 `SUCCESS` 会漏掉正常返回的错误字符串。本课观测边界避开整个 `Runtime` 对象；首次137退出及根因假设边界只在[源码导读](source_walkthrough.md)详述。

**第4步：从实际响应定位评测样本**

采样器先用原生响应 ID 找到唯一 trace，再保留工具名、参数、输出和源 UUID：

```python
# 节选：code.py / trace_samples，省略响应筛选与唯一性校验
message_id = worker["response"]["id"]
tools = sorted(trace.get("toolSpans", []),
               key=lambda s: s["startTime"])
```

找到工具 span 后，把产生结果的动作一起放进证据。只留下“OK”，读者与裁判都无法确认它来自测试、另一个命令，还是一段被打印的文字。随后形成证据记录：

```python
# 节选：工具证据记录，外层循环与保存逻辑省略
{
    "tool_name": name,
    "input_parameters": span["input"]["args"],
    "output": span["output"],
}
```

完整源码见 [`trace_samples`](code.py)。采样器接收已返回且无错误的报告，把 Faithfulness 与工具调用样本交给 `eval.py`。首轮投影漏了测试命令，修订只改采样，没有重跑 Agent，两版结果都保留。这是看过结果后的开发诊断，不是留出集提升。忽略参数会把“看见 `OK`”误当成“知道执行了哪条命令”。

Faithfulness 分为仅规范文档和已观察工具两种证据范围。工具比较则只投影指定的 `read_file`，不是全任务唯一正确轨迹。

**第5步：分别解释两套指标**

两个预期读取只剩一个时，DeepEval 的覆盖为 `1 / 2 = 0.5`，完整匹配为0。Ragas 的工具名序列不完整，因此 Accuracy 为0；集合匹配的精确率为1、召回率为0.5：

```text
F1 = 2 × 1 × 0.5 / (1 + 0.5) ≈ 0.6667
```

实际入口见 [`eval.py`](eval.py)，它分别调用第10课的原生工具比较和第5课的双框架 Faithfulness：

```python
# 节选：eval.py，省略逐步保存与结果整理
for sample in samples["tools"]:
    output["tool_results"].append(score_rules(sample))
for sample in samples["faithfulness"]:
    result = evaluate(sample)
```

固定版本、提示、schema、裁决与聚合见[源码导读](source_walkthrough.md)。同一份冻结样本交给两套原生实现，结果保留各自的评分口径。DeepEval 默认把 `YES` 与 `BORDERLINE` 计入通过，Ragas要求明确支持；空声明和错误另行记录。忽略方法差异而平均同名指标，会得到没有清晰含义的数字。

**第6步：用关键条件关闭发布门**

最终门禁逐项检查关键条件是否严格等于 `True`：

```python
# 节选：critical_gate，省略前置校验与返回对象
rejected = [
    name for name, passed in checks.items()
    if passed is not True
]
```

完整源码见 [`critical_gate`](code.py)，独立验收入口见 [`verify.py`](../../integrated_agent/verify.py)。业务行为与原测试保持先由验收器检查；实际 Task、worktree 租约、记忆索引、定时确认和工作流日志另按状态合同检查。门禁接收这些结果，返回通过状态与拒绝项。正常、未授权和越界任务分别接受外部检查。忽略严格判断，会让 `None`、评分错误或权限失败被其他高分抵消。

CI只运行断网、固定的合同检查。真实模型与裁判实验另行执行并留证。本项目没有创建夜间自动任务，也不提供通用安全保证。

## 相对上一课的变更

| 上一课 | 本课 |
|---|---|
| 校准裁判怎样判 | 连接裁判实际看到的运行对象 |
| 关注样本与评分协议 | 增加原生响应、trace、工具参数和源 UUID |
| 指标帮助发现问题 | 独立业务与状态验收决定是否接受 |
| 单项结果可供分析 | 关键条件必须逐项严格为真 |
| 评测实验相对独立 | 固定上游 s15、原生 s09、s16、s17 共用真实入口 |

详细实验边界见[运行摘要](run_summary.md)，完整验收范围见[验收文档](../../docs/e16-validation.md)。

## 试一下

先在宿主机独立终端启动模型桥：

```bash
python3 tools/integrated_bridge.py
```

在另一个终端构建镜像，成功后再运行任务：

```bash
docker compose build course
```

换一个全新的工作区和报告 ID。已有报告拒绝覆盖，失败现场也会保留：

```bash
docker compose --profile capstone run --rm -T \
  --entrypoint python agent -m integrated_agent.scenario \
  --workspace /data/workspaces/my-capstone \
  --report /data/runs/my-capstone.json
```

知识库默认从 `knowledge_base/e16` 只读挂载。可用 `INTEGRATED_KNOWLEDGE_DIR` 更换目录；宿主登录状态不会进入容器。

接着运行独立验收：

```bash
docker compose --profile verify run --rm -T \
  --entrypoint python verifier -m integrated_agent.verify \
  --profile composed --workspace /data/workspaces/my-capstone \
  --criteria /verification/e16-foundation.json \
  --report /data/runs/my-capstone-evaluation.json
```

若要双框架重评，先在另一个宿主终端运行 `python3 tools/judge_bridge.py`，再执行：

```bash
docker compose run --rm -T --entrypoint python course \
  -m lessons.e16_regression.eval \
  --input /data/runs/my-capstone.json \
  --report /data/runs/my-capstone-metrics.json
```

离线练习不调用供应商：

```bash
docker run --rm --network none --entrypoint python \
  learn-agent-evaluation:local -m pytest \
  tests/test_e16.py tests/test_integrated_capabilities.py -q
```

这些夹具控制验证协议分支，供应商请求数为0。阅读器位于 `http://localhost:8765/lesson16`，综合项目位于 `http://localhost:8765/project`。

对照运行、验收和评分三个报告，找出这些问题的答案：Goal 成功、工作流完成和独立验收各能证明什么？某个工具 span 的参数与输出是否对应同一源 UUID？任一关键项为 `None` 时，门禁是否拒绝？更多练习见[练习](exercises.md)与[参考答案](solutions.md)。

## 接下来

下一步是把这套链路迁移到自己的结课项目：

1. 换成自己的任务、只读知识库与成功合同。
2. 冻结代码、数据、提示和可知版本。
3. 分别执行正常、错误与边界案例。
4. 用独立进程验收业务产物和运行状态。
5. 从真实响应 ID 抽样 trace，保留工具参数、输出与来源。
6. 分别解释两套框架的方法，不平均同名分数。
7. 把发现的反例加入断网 CI，并保留失败现场。

运费项目的44条输入只证明这两个接口在本次合同下通过。迁移时，应重新定义属于新项目的事实检查与发布门禁。
