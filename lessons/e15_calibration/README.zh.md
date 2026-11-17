# 第15课：裁判校准，分数对了，标准也对了吗

## 问题

第14课的产物通过了检查，效率裁判却给了低分。先看裁判收到什么、按什么标准判断，再决定要改哪段代码：它可能漏读证据，也可能把额外检查当成了浪费。

例如，独立检查记录是“预期值为 9，检查未通过”，Agent 报告也写“值为 9，检查未通过”。这份报告与记录相符，应判为 `pass`。业务问题仍未修好，任务完成门禁依旧不能通过。

本课沿用已有 Agent、工具和只读知识库，把评测对象换成裁判。16条标量记录由讲师构造，没有新增16次 Agent 执行。所有记录的 `human_reviewed` 都是 `false`；标签依据下文的两项事实合同，尚未人工审核，因此这里只计算与合同标签的一致率。

## 解决方案

先把样本按家族隔离成训练集、开发集和留出集，数量分别为4、4、8。同一任务的正确版、错误版、长篇版和英文版必须留在同一集合，避免裁判在开发阶段看过几乎相同的事实。

两版 G-Eval 标准只在开发集比较。v1只要求报告“有用、可信”，故意留下歧义；v2明确要求核对预期值和独立验证状态，接受诚实报告失败，并忽略篇幅、语言与作者身份。候选必须完成全部开发样本评分，选择时先减少误放行，再比较一致率；同分按预定规则选择v2。

选定版本先写入报告，之后才用留出样本调用裁判。即使留出结果不理想，也要保留，不能回头修改标准。作者知道样本如何构造，因此这里不宣称双盲。

## 工作原理

**第1步：构造并校验合同记录**

[`make_cases` 与 `validate_cases`](code.py)创建记录，并检查同一家族是否跨集合。下面是[完整代码](code.py)中的节选，其他校验已省略：

```python
# 节选：code.py，省略重复ID等检查
previous = splits.setdefault(row["family"], row["split"])
if previous != row["split"]:
    raise ValueError("Family leakage across splits")
expected = (
    reported["value"] == evidence["expected_value"]
    and reported["verification_passed"] == evidence["verification_passed"]
)
if row["label"] != ("pass" if expected else "fail"):
    raise ValueError("Label contradicts contract")
```

输入是一组带 `family`、`split`、证据和标签的记录，输出是校验后的记录；接入点在评测入口读取 `cases.jsonl` 后。若家族泄漏，开发集可能提前见到留出事实；若标签违反合同，后续一致率再高也没有意义。校验后的样本仍保留未审核标记。

**第2步：让 G-Eval 按固定步骤评分**

[`score`](eval.py)把必要证据放进 `INPUT`，把报告放进 `ACTUAL_OUTPUT`。以下为节选，异常保留逻辑已省略：

```python
# 节选：eval.py，省略结果整理
judge = GEval(
    name="Completion report accuracy",
    evaluation_steps=STEPS[version],
    evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
    model=DeepJudge(transport),
    async_mode=False,
    threshold=0.7,
)
```

输入是一条报告及v1或v2标准，输出为0到1的连续分数；达到0.7才映射成 `pass`。开发评分和选定后的留出评分都走这里。步骤若没有区分报告准确与修复完成，裁判就可能拒绝一份诚实说明失败的报告。

自定义后端不支持原始概率接口时，DeepEval 会回退到结构化 schema 路径，细节见[源码导读](source_walkthrough.md)。这里不能声称 Codex 适配器做了概率加权。

**第3步：先冻结选择，再评价留出集**

[`select_version`](code.py)只接收开发结果，并拒绝未完整评分的候选：

```python
# 节选：code.py，省略辅助函数
eligible = [
    v for v in STEPS
    if dev[v] and alignment(dev[v])["unscored"] == 0
]
if not eligible:
    raise ValueError("No fully scored development candidate; do not open holdout")
return max(eligible, key=rank)
```

输入是两版完整的开发集预测，输出为选定版本。接入点位于留出评分之前；[`eval.py`](eval.py)会先调用 `atomic_save` 保存版本、阈值和开发结果，再读取留出集。顺序颠倒就会把留出集变成调参集，结果不再是独立验证。

本次两版都判断正确，按预定同分规则选择v2。v2把判断依据写得更明确，这次实验没有测出准确率提升。

**第4步：用原生少样本对齐检查判分**

Ragas 的 `DiscreteMetric.align`把训练示例加入提示，不会训练模型权重：

```python
# 节选：eval.py，省略数据集构造
judge = metric()
judge.align(
    ragas_dataset(train, "training"),
    embedding_model=None,
    max_similar_examples=4,
)
result = judge.validate_alignment(llm, ragas_dataset(holdout, "heldout"))
```

输入是4条训练记录和留出数据，输出是逐条预测、agreement 与 Cohen’s κ。它接在原始标准评分之后，用来比较对齐前后判分。

`embedding_model=None` 走原生“最近四个示例”回退，对齐阶段产生0次模型请求；它不是向量检索，也不是权重训练。固定源码中还存在旧 embedding wrapper 接口不匹配、参考值与预测值分别过滤 `None` 可能错位，以及κ依赖额外 `scikit-learn` 的风险。若忽略这些边界，可能把错配记录算成一致。

**第5步：适配中文提示，保留审核状态**

`ReportPrompt`提供两个非空示例，并用数字0/1作为标签，避免翻译固定枚举：

```python
# 节选：eval.py，省略异常保存
prompt = ReportPrompt(train)
adapted = asyncio.run(
    prompt.adapt("chinese", llm, adapt_instruction=True)
)
```

原提示与两个示例一起交给翻译接口，得到中文副本。随后，两版提示评价同四条正确、错误样本。检查时既要看数字、布尔值与 schema，也要看否定词，以及“诚实报告失败仍可准确”这一条是否保留。

`language` 字段变化不能证明翻译成功。原生实现遇到空示例会提前返回，连指令也不翻译；即使结构和数值未变，也不足以证明语义无漂移。本次只能记录助手核对结果，人工语义复核仍为 `false`。

**第6步：按内容回映偏差测试**

[`alignment` 与 `equivalent_pairs`](code.py)统计误放行、误拒绝、覆盖率和成对翻转。κ分母退化时返回 `None`，表示此时无法计算：

```python
# 节选：code.py，省略计数过程
agreement = (counts["true_pass"] + counts["true_fail"]) / n if n else None
kappa = None
if n:
    gold_pass = sum(g == "pass" for g, _ in pairs) / n
    pred_pass = sum(p == "pass" for _, p in pairs) / n
    chance = gold_pass * pred_pass + (1 - gold_pass) * (1 - pred_pass)
    if not math.isclose(chance, 1):
        kappa = (agreement - chance) / (1 - chance)
```

输入是按唯一ID配对的参考标签和预测，输出包括覆盖率、混淆计数、κ及分歧ID。A/B实验还会交换答案顺序，再把字母映射回 `correct` 或 `incorrect` 内容。原序的A与反序的B可能指向同一份报告，只比较字母会把它们误算成分歧。

误放行是把错误报告判为通过，误拒绝则是拒绝准确报告。请求超时或结果格式错误另计为未评分，并留在总样本数里，因此还要一起看覆盖率。不能只删掉失败调用，再公布剩余样本的高一致率。

一致率只数判得相同的比例；κ还考虑双方类别分布带来的偶然一致。若样本几乎全为通过，裁判一直答通过也可能显得不错，所以要把类别计数与逐条分歧一起保存。

测试覆盖长篇、中英改写和作者身份线索。来源声明未经证实，精确裁判模型也未知，所以不能证明真实自偏好。交换顺序后选择一致，不代表选择正确；小样本没有翻转，也不能证明裁判普遍无偏。

更完整的 SDK 调用链、回退路径与固定源码链接见[source_walkthrough.md](source_walkthrough.md)。

## 相对上一课的变更

| 项目 | 第14课 | 本课 |
|---|---|---|
| 被测对象 | Agent产物与效率 | 评测裁判 |
| Agent与工具 | 执行任务 | 保持不变 |
| 输入 | Agent运行结果 | 讲师构造的固定报告与合同 |
| 选择依据 | 任务目标 | 开发集误放行与一致率 |
| 最终检查 | 产物是否达标 | 冻结标准在留出集上的表现 |

本课没有加入新的 Agent 能力。正式运行结果见[run_summary.md](run_summary.md)：开发集同分后选择v2，留出评分、原生对齐、中文提示和正反序实验均已完成。精确裁判模型与费用未知，因此记录为 `null`，不能用框架示意数字代替本课测量。

练习共12题，见[exercises.md](exercises.md)，完成后再看独立的[solutions.md](solutions.md)。验收依据见[第15课验收文档](../../docs/e15-validation.md)，生成与审校记录见[第15课说明](../../generation/e15-README.md)。

## 试一下

Docker 环境和只读知识库沿用现有 `compose`。先在宿主机的独立终端启动裁判桥，凭据不要放进容器：

```bash
python3 tools/judge_bridge.py
```

随后构建课程镜像，构建成功后再执行真实评测：

```bash
docker compose build course
docker compose run --rm -T --entrypoint python course \
  -m lessons.e15_calibration.eval
```

若 `runs/e15-calibration.json` 已存在，程序会拒绝覆盖。先归档旧报告，并明确声明这是一次新实验；不要因为结果不理想而反复重跑挑选结果。

离线检查可以在 Docker 中执行：

```bash
docker compose run --rm -T --entrypoint python course \
  -m pytest tests/test_e15.py -q
```

这些测试由 fixture 控制，不会调用供应商。然后打开 <http://localhost:8765/lesson15>，重点观察三件事：诚实报告失败为何仍可判为准确、原生对齐前后如何判分、A/B字母如何回映到真实内容。

## 接下来

第16课将已有机制接成一个完整项目，加入工作流日志与续跑、目标循环，并逐项核对17项能力。独立验收与持续集成也会接进同一条运行链；完整集成仍待下一课实际验证。
