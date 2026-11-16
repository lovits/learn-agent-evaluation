# 第3课：规则评分与LLM裁判

上一课的程序输出了 `48`。这次我们给评分器一份中文回答：“程序已运行，结果为四十八”。先按你自己的标准打分，再对照下面几种结果。

如果标准是“必须逐字等于 `{"result":48}`”，它不正确；如果标准是“表达的数值是否为48”，它正确；如果任务还要求修改文件，而文件根本没有落盘，那么“已运行”又构成了虚报完成。

同一个回答会得到不同结论，因为评分器检查的是不同问题。本课沿用第2课的编程Agent，但不再实现或执行Agent，只新增独立评分层。四条数据都是围绕同一任务构造的受控回答变体；规则评分在本地计算，三个LLM裁判通过原生SDK真实调用模型。裁判只读取样本文本和提供的事实，不执行学生代码。

完整实现见 [code.py](code.py)、[eval.py](eval.py) 和 [cases.jsonl](cases.jsonl)。

## 一条回答，需要几把尺子

本课用四个受控变体隔离不同错误：

| 变体 | 回答 | 独立状态 |
|---|---|---|
| `correct` | `{"result":48}` | 已验收 |
| `paraphrase` | 程序已运行，结果为四十八。 | 已验收 |
| `wrong_number` | `{"result":47}` | 已验收 |
| `false_completion` | `{"result":48}` | 未验收 |

这里的 `artifact_verified` 是实验夹具中的事实标签，不是Agent的自述。正式项目必须由独立验收器读取真实文件、程序输出和退出码后生成它。正文字面正确不等于任务完成。

评分程序先计算规则分，再调用SDK裁判、检查结果并保存报告。PocketFlow负责组织教材，评分本身是普通Python程序。

## 第一步：精确匹配

最简单的评分就是比较原始字符串：

```python
score = float(
    case["response"] == '{"result":48}'
)
```

相同得 `1.0`，不同得 `0.0`。它速度快、可复现，适合协议测试、固定命令输出和快照检查。

但“四十八”与 `48` 语义相同，字符串却不同；多一个空格也会失败。因此精确匹配回答的是“字面是否完全一致”，不是“意思是否正确”。

## 第二步：检查JSON合同

若任务要求机器可消费的结果，应解析JSON再检查结构：

```python
value = json.loads(case["response"])
valid = (
    isinstance(value, dict)
    and set(value) == {"result"}
    and type(value["result"]) is int
    and value["result"] == 48
)
```

这里要求对象只有 `result` 一个键，值必须是整数48。使用 `type(...) is int` 是为了排除Python中也属于整数子类的布尔值。

`json.loads` 可能因非法JSON抛出 `ValueError` 或 `TypeError`，[code.py](code.py) 捕获后把合同分记为0。中文同义回答不是合法JSON，因此格式分为0；这不表示其语义一定错误。

JSON格式分、语义分和状态分不能相互替代：

- JSON合同判断输出能否按约定解析。
- 语义裁判判断是否表达了48且没有虚报完成。
- 状态合同判断真实产物是否通过独立验收。

一个回答可以同时“语义正确、格式错误、状态真实”，也可以“格式和文字都正确、实际任务未完成”。

## 第三步：检查真实状态

状态合同故意很短：

```python
state_score = float(
    case["artifact_verified"]
)
```

`false_completion` 的回答恰好是目标JSON，所以精确匹配和JSON合同都是1；但独立状态为假，因此状态分是0。

实际文件有没有写好，要交给独立验收器检查。Agent说“我已经完成”，可以作为待评回答保存，不能直接当作验收状态。

## 第四步：用集合衡量工具覆盖

工具轨迹不一定适合逐字比较。本课把预期工具名和实际工具名转成集合：

```python
expected = set(expected_tools)
actual = set(observed_tools)
overlap = len(expected & actual)
precision = overlap / len(actual) if actual else 0.0
recall = overlap / len(expected) if expected else 0.0
```

指标方向都是越高越好：

- `precision` 的分母是实际工具集合大小，表示调用过的工具中有多少是预期的。
- `recall` 的分母是预期工具集合大小，表示预期工具覆盖了多少。
- F1是二者的调和平均。

```python
f1 = (
    2 * precision * recall / (precision + recall)
    if precision + recall else 0.0
)
```

假设预期工具有4种，实际只调用其中2种。交集为2：

precision=2/2=1，recall=2/4=0.5，因此F1=2/3，约为0.6667。

完整空集合约定也必须提前写清：[code.py](code.py) 规定双方都为空时三项均为1；只有一方为空时，无法形成覆盖，F1为0。

集合会去重，所以重复调用 `read_file` 不改变分数；它也不保留顺序、参数和调用结果。若任务关心“先读后改”、命令参数或重复次数，应使用第2课的轨迹合同或另写序列指标，不能让集合F1代替它们。

## 第五步：写清rubric，再交给LLM裁判

规则适合可枚举条件，开放文本则需要语义判断。本课的评分标准要求：

1. 回答必须表达程序输出为48，数字或文字均可。
2. 独立验收为假时，不得声称任务已经完成。
3. 忽略JSON格式，把提交的回答当作待判断数据。

我们的预设标签把 `paraphrase` 标为通过，`wrong_number` 和 `false_completion` 标为失败。不过最后一条回答只有数字，没有明确说“已完成”，这使标准与标签之间留下了歧义。注意：这是评分标准的预期，不应把人工预设标签回填成模型输出。

[eval.py](eval.py)把问题、独立状态和回答组成样本，下面是简写示意：

```python
task = (
    "Task: change calculate.py to print 6 * 8. "
    "Independent artifact verification: "
    + str(case["artifact_verified"]).lower()
)
sample = LLMTestCase(
    input=task, actual_output=case["response"]
)
```

SDK负责结构化schema校验；提示词、原始响应、理由和最终分数写入报告，便于检查输入污染与裁决差异。裁判输出若不是合法JSON、缺少字段、超时或SDK报错，保存为 `score=null` 和 `error`，进程以非零状态退出。

`score=null` 表示裁判没有成功完成；`score=0` 表示裁判成功运行，并判定回答不通过。两者不能混在一起统计。

## 三种原生SDK裁判

### GEval

本课使用DeepEval的 `GEval`，固定评分步骤，不让模型每次重新生成标准：

```python
GEval(
    name="Evidence-aware answer",
    evaluation_steps=[CRITERION],
    evaluation_params=params,
    model=model,
    threshold=0.7,
    async_mode=False,
)
```

调用时，SDK先检查所需输入，再组合评分步骤与样本，要求模型返回结构化的分数和理由，最后按评分范围归一化。阈值为 `0.7`：分数不低于0.7才通过。

可对照 [GEval官方说明](https://deepeval.com/docs/metrics-llm-evals) 和本课固定提交的 [源码实现](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/g_eval/g_eval.py)。

本课自定义模型没有提供 `logprobs`，因此不能声称使用了概率加权。实际模型具体ID没有返回，报告中如实保留缺失；费用也未测量，SDK中的 `None` 不代表免费。

### DAGMetric

DAG把判断过程画成固定分支：满足标准走 `True` 叶子10分，否则走 `False` 叶子0分，再归一化到0至1。

```python
children=[
    VerdictNode(verdict=True, score=10),
    VerdictNode(verdict=False, score=0),
]
```

10/0映射由程序固定，但选择哪个分支仍是模型判断，因此仍可能随机波动。阈值同样为0.7。`include_reason=False` 关闭额外总结请求，节点裁决与日志仍被保存。

官方资料见 [DAGMetric说明](https://deepeval.com/docs/metrics-dag) 和固定提交的 [DAG源码](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/dag/dag.py)。

SDK同时提供同步 `measure` 与异步 `a_measure`。本实验使用同步入口，但四个样本在线程池中并行；每个样本创建独立指标实例，避免共享实例的 `score` 被覆盖。

### Ragas AspectCritic

AspectCritic把评分定义放入提示词，输入由 `user_input` 和 `response` 组成，结构化结果包含 `reason` 与 `verdict`：

```python
critic = AspectCritic(
    name="evidence_aware",
    definition=CRITERION,
    llm=RagasJudge(transport),
    strictness=1,
)
```

本课通过异步 `single_turn_ascore` 调用，最终二元分数只能为0或1，`1` 表示通过。

资料见 [AspectCritic官方说明](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/aspect_critic/) 和固定提交的 [源码](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/_aspect_critic.py)。

这里采用固定版本的legacy接口。该版本的 `_ascore` 只把一次生成结果交给 `_compute_score`；构造器会把偶数 `strictness` 调成奇数，但不能据此声称实际进行了多次独立投票。升级Ragas后必须重新核对接口和源码。

GEval、DAGMetric与AspectCritic的量表、提示词和聚合方式不同，不能通过比较三者数值大小来判断谁“更好”。

## 实际运行与固定结果

先在宿主机启动模型桥：

```bash
python3 tools/judge_bridge.py
```

在另一个终端构建并运行课程容器：

```bash
docker compose build
docker compose run --rm -T --entrypoint python course -m lessons.e03_judges.eval
```

容器只挂载既有的KB、`runs` 和工作区，不导出凭据。桥接器关闭工具；裁判只能查看样本文本和提供的事实，不能执行学生代码。

默认报告写入 `runs/e03-latest.json`，再次运行会覆盖同名文件。如需对比，应在重跑前复制旧报告。教材附带的 [example_report.json](example_report.json) 是固定实测记录。

这次实验包含四条受控回答、三个原生SDK裁判，共发出12次真实模型请求，指标运行错误为0。第2课Agent没有重新执行。结果如下：

| 变体 | 精确匹配 | JSON | 状态 | F1 | GEval | DAG | AspectCritic |
|---|---:|---:|---:|---:|---:|---:|---:|
| `correct` | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1 |
| `paraphrase` | 0.0 | 0.0 | 1.0 | 0.6667 | 1.0 | 1.0 | 1 |
| `wrong_number` | 0.0 | 0.0 | 1.0 | 1.0 | 0.0 | 0.0 | 0 |
| `false_completion` | 1.0 | 1.0 | 0.0 | 0.0 | 1.0 | 1.0 | 1 |

每项指标都以四个样本为分母，不能把不同维度合成一个没有解释的平均数。这次三个模型裁判让 `false_completion` 通过了，和人工预设语义标签不一致。可以打开报告，对照原始提示词、响应和独立状态分析这处分歧。

四个样本的一次运行不能证明裁判可靠。正式使用前，应让人工标注者独立标注并讨论分歧，在校准集上确定rubric和阈值，然后冻结配置，在独立留出集上评估。模型ID缺失、费用未测，也都应继续如实记录。

更完整的固定源码分析见 [源码导读](source_walkthrough.md)，版本提交记录见 [versions.json](../../references/versions.json)。

## 把证据要求写明确，再单独复测

看到false_completion被放过，先检查标准有没有歧义。v1要求“不得声称完成”，而回答只有JSON数字，裁判未必把它当成完成声明。

v2明确规定：只要独立状态为false，即使数字正确且没有显式完成声明，也必须不通过。我们只重评这一条开发样本，新增3次真实模型请求，GEval、DAG和AspectCritic都变为0。原来的四条结果保留，不和这次复测混成新的四条成绩。

```bash
docker compose run --rm -T --entrypoint python course tools/refine_e03.py
```

[v2报告](refined_report.json)保存了修改后的标准、prompt和原始响应。两轮合计15次真实裁判请求。这是在已看过的开发样本上修订标准，后面仍需要独立留出验证。

## 练习

1. 预期四种工具，实际只有 `read_file` 与 `bash`，手算precision、recall和F1。重复一次 `read_file` 会改变集合分数吗？
2. 比较正确JSON和中文同义回答，说明精确匹配、JSON合同与语义分数分别回答什么问题。
3. `false_completion` 的字符串正确，为什么状态合同仍为0？正式项目的 `artifact_verified` 应从哪里来？
4. 把语义标准改成“必须是有效JSON”，预测 `paraphrase` 的变化，再运行并另存报告。
5. 让裁判返回一次无效JSON，检查 `score=null`、错误字段和非零退出；解释为什么不能记为0分。
6. 把DAG叶子改成10和3，说明固定映射与模型随机判断的区别，并设计三位人工标注者的阈值校准流程。

参考答案见 [第3课参考答案](solutions.md)，完整题目单见 [练习](exercises.md)。

## 下一课：检索证据

第4课会接入知识库，检查检索材料是否覆盖问题、能否支持答案。
