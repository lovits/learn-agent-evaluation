# Chapter 1: 规则评分与LLM裁判

## 问题

第2课的编程 Agent 修改了 `calculate.py`，目标是让程序输出 `6 * 8` 的结果。现在假设我们收到两个回答：

```text
{"result":48}
```

```text
程序已运行，结果为四十八。
```

它们都表达了48，但算不算同样正确？

这取决于我们正在检查什么。若接口要求精确返回 `{"result":48}`，第二个回答不合格；若只检查语义，它又是正确的。更麻烦的是，即使回答写着48，也不能证明文件确实修改成功，更不能证明程序真正运行过。

因此，本课不再实现或执行新的 Agent，只在第2课之外增加独立评分层。PocketFlow负责组织本课的代码、四条受控回答、固定实验报告、源码导读和练习。四条数据是人为控制差异的回答变体，不是四次新 Agent 运行；三个裁判则通过原生 SDK 发起过真实模型调用。

我们要分别回答四类问题：

- 格式是否符合接口合同；
- 回答在语义上是否表达了48；
- 独立验收是否确认任务完成；
- 实际工具集合与预期集合有多接近。

这些维度不能相互替代。合法 JSON 不保证数字正确，语义正确不保证格式正确，正文字面正确也不证明任务完成。工具集合相同，更不代表调用顺序、参数和结果都正确。

## 解决方案

本课采用“先确定性规则，后模型裁判”的顺序。

确定性规则适合边界清晰的问题：字符串是否完全相同、JSON是否满足合同、独立状态是否为真、工具集合有多少重合。它们运行稳定、成本低，而且容易定位失败原因。

语义判断则交给带评分标准的 LLM 裁判。本课的标准要求：

1. 回答必须表达程序输出为48，数字或中文均可；
2. 独立验收为假时，不得虚报完成；
3. 语义评分忽略JSON格式。

第三条是刻意设计的：JSON格式由规则评分负责，语义裁判只判断含义。否则一个指标同时混入格式、数字和完成状态，得到低分时便很难知道错在哪里。

四条受控回答位于 [cases.jsonl](cases.jsonl)：

| 变体 | 回答特征 | 独立状态 |
|---|---|---:|
| `correct` | 正确JSON与48 | 真 |
| `paraphrase` | 中文表达“四十八” | 真 |
| `wrong_number` | 合法结构但数字为47 | 真 |
| `false_completion` | 文本为正确JSON | 假 |

这里的 `artifact_verified` 是夹具事实，只为制造可控差异。正式项目必须由独立验收器根据文件内容、程序输出和退出码产生，不能从 Agent 的自述中提取。

完整确定性规则见 [code.py](code.py)，三个原生裁判及报告生成见 [eval.py](eval.py)。更深的提示词、结构化结果、聚合方式及同步与异步调用链，集中在 [源码导读](source_walkthrough.md)。

## 工作原理

以下片段均来自本课真实代码，但省略了上下文或部分参数，不能单独作为运行入口。短片段的完整版本在 [eval.py](eval.py) 和 [tools/refine_e03.py](../../tools/refine_e03.py)。

**第1步：先用精确匹配建立最严格的基线**

```python
"exact_match": float(
    case["response"] == '{"result":48}'
),
```

输入是原始回答字符串，输出只能是 `1.0` 或 `0.0`。`correct` 得1分，而中文同义回答得0分，因为空格、文字和标点都会影响字符串比较。

精确匹配适合固定协议、快照或标准答案，不适合判断自然语言含义。它告诉我们“字面是否完全一致”，没有声称自己理解语义。

**第2步：再检查JSON合同，而不是只看能否解析**

```python
value = json.loads(case["response"])
valid = (
    isinstance(value, dict)
    and set(value) == {"result"}
    and type(value["result"]) is int
    and value["result"] == 48
)
```

输入仍是回答字符串。输出是合同是否通过：顶层必须是字典，只能有 `result` 键，其值必须是整数48。这里用 `type(...) is int`，因此不会把 Python 中可当作整数使用的布尔值误收为答案。

中文同义回答无法解析成JSON，所以格式分为0，但它仍可能得到语义分。反过来，`{"result":47}` 具有JSON外形，却因数值错误而不通过合同。格式分和语义分回答的是不同问题。

**第3步：把真实状态留给独立验收**

```python
"state_contract": float(
    case["artifact_verified"]
),
```

输入是夹具提供的独立状态，输出同样是0或1。`false_completion` 的回答恰好是 `{"result":48}`，所以精确匹配和JSON合同都得1；但其状态分是0，因为验收事实表明产物没有完成。

这正是“回答正确”和“任务完成”的区别。任何正文，无论写得多肯定，都不能替代对真实文件和运行结果的检查。本课没有执行学生代码；裁判只看到样本文本以及明确提供的独立事实。

**第4步：用集合的精确率、召回率和F1检查工具覆盖**

```python
overlap = len(expected & actual)
precision = overlap / len(actual) if actual else 0.0
recall = overlap / len(expected) if expected else 0.0
f1 = 2 * precision * recall / (precision + recall)
```

假设预期工具为四种，实际只出现 `read_file` 和 `bash`。交集为2，实际集合大小为2，预期集合大小为4：

\[
精确率=2/2=1,\quad 召回率=2/4=1/2
\]

\[
F1=\frac{2\times1\times1/2}{1+1/2}=2/3
\]

精确率的分母是实际集合大小，回答“实际使用的工具中有多少是预期的”；召回率的分母是预期集合大小，回答“预期工具覆盖了多少”。F1是二者的调和平均，越接近1越好。

`set_f1` 会先转成集合，因此不保留重复次数、顺序和参数。重复一次 `read_file` 不会改变分数。若两边都为空，本课约定三项均为1；只有一边为空时得0。它适合粗略覆盖率，不能替代第2课的轨迹合同。

**第5步：用同一评分标准接入三种原生裁判**

```python
CRITERION = (
    "The response must correctly communicate that the program "
    "output is 48 (words or digits acceptable). "
    "It must not claim completion when the independent artifact "
    "verification in user_input is false. "
    "Ignore JSON formatting for this semantic criterion."
)
```

输入包括任务、独立验收状态和回答；输出是裁判生成的结构化裁决。代码分别调用 DeepEval 的 `GEval`、`DAGMetric`，以及 Ragas 的 `AspectCritic`，而不是自行仿写它们的评分流程。

GEval将分数归一化到0至1，本课阈值为0.7。自定义模型没有提供 `logprobs`，所以不能声称使用了概率加权。

DAG只有一个模型判断节点：真分支进入10分叶子，假分支进入0分叶子，再归一化到1或0，阈值同样为0.7。叶子映射由程序固定，但模型节点仍可能随机波动。

Ragas的结果是二元值，1表示通过。本课固定版本使用旧接口，`strictness=1`；不能仅凭 `strictness` 属性，就把当前实现解释成多次独立投票。

三种裁判的机制和刻度不同，不能用“谁的数值更高”判断谁更好。固定版本、原生调用路径和官方资料见 [源码导读](source_walkthrough.md)，其中链接了 [DeepEval LLM评测说明](https://deepeval.com/docs/metrics-llm-evals)、[DeepEval DAG说明](https://deepeval.com/docs/metrics-dag)及 [Ragas AspectCritic说明](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/aspect_critic/)。

**第6步：把裁判失败与裁判不通过分开**

```python
except Exception as error:
    scores[type(metric).__name__] = {
        "score": None,
        "error": str(error),
    }
```

`score=0` 表示裁判成功运行，并判断回答不满足标准；`score=null` 表示裁判调用、解析或 SDK 执行失败，没有形成有效裁决。二者不能一起算作低质量回答。

四条样本的历史真实运行共发起12次模型请求，指标运行错误为0：

| 变体 | 精确匹配 | JSON | 状态 | F1 | GEval | DAG | AspectCritic |
|---|---:|---:|---:|---:|---:|---:|---:|
| `correct` | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 1 |
| `paraphrase` | 0.0 | 0.0 | 1.0 | 0.6667 | 1.0 | 1.0 | 1 |
| `wrong_number` | 0.0 | 0.0 | 1.0 | 1.0 | 0.0 | 0.0 | 0 |
| `false_completion` | 1.0 | 1.0 | 0.0 | 0.0 | 1.0 | 1.0 | 1 |

`wrong_number` 的工具F1为1，却不代表回答正确；`false_completion` 的格式与语义字面看似正确，也不代表产物完成。这再次说明各维度不可替代。

v1中三个裁判都放过了 `false_completion`。原因不是简单的“模型犯错”：旧标准说“不得声称完成”，而该回答只有一个JSON数字，未显式声称完成，人工预设标签与评分标准存在歧义。

v2将标准修订为：独立验收为假时，即使数字正确且没有显式完成声明，也必须失败。随后只对这条开发样本重新评分，三个裁判都得到0，新增3次真实请求。v1和v2都是已经保存的历史真实裁判记录，但v2不是新的四样本实验，也不是独立留出测试。本轮教材重写没有重跑裁判或Agent，固定报告没有修改。完整数字与修订边界见 [运行摘要](run_summary.md)。

## 相对上一课的变更

| 第2课 | 第3课 |
|---|---|
| Agent调用工具并修改程序 | Agent保持不变，不新增执行 |
| 关注工具权限、轨迹与产物 | 独立评价回答、状态和工具覆盖 |
| 执行过程产生事实 | 评分层读取回答及已提供的事实 |
| 判断任务能否完成 | 判断不同维度是否满足合同 |

本课的裁判桥只提供模型输出，工具处于关闭状态。Docker中的裁判不会执行学生代码，也不会把模型自述当作验收结果。运行时只挂载既有知识库、`runs` 和工作区，不向容器导出宿主机凭据。

固定报告 [example_report.json](example_report.json) 是随教材保存的实测证据，包含提示词、原始响应和分数。报告没有返回确切模型编号，费用也未测量，因此都保持未知，不作猜测。

一次四样本运行只能演示差异，不能证明裁判可靠。正式使用前，应由人工标注者校准评分标准和阈值，冻结配置后再评估独立留出集。开发样本上的修订结果不能冒充泛化能力。

## 试一下

先在宿主机启动裁判桥：

```bash
python3 tools/judge_bridge.py
```

在另一个终端构建并运行原生评测：

```bash
docker compose build
docker compose run --rm -T --entrypoint python course -m lessons.e03_judges.eval
```

默认报告写入 `runs/e03-latest.json`。同名文件会被覆盖；若要比较历史运行，请在重跑前复制旧文件。需要复现v2开发样本修订时运行：

```bash
docker compose run --rm -T --entrypoint python course tools/refine_e03.py
```

该命令写入 `runs/e03-refined.json`，同样要留意覆盖。运行后可以观察：

1. `paraphrase` 为什么JSON为0，而三个语义裁判均通过？
2. `wrong_number` 为什么工具F1为1，却不能据此判定答案正确？
3. 报告中若出现 `score: null`，它与 `score: 0` 在统计时应如何处理？

本课有六道配套题，涉及F1手算、格式与语义的边界、独立状态、标准版本、错误记录和人工校准。请先完成 [练习](exercises.md)，再查看 [参考答案](solutions.md)。

## 接下来

我们已经把“回答是否正确”拆成了可解释的规则评分、独立状态和LLM裁判，也看到了一个更现实的问题：裁判拿到的事实从哪里来？

本课的任务和状态都很短，可以直接放进评分输入。第4课将进入检索评测：当依据分散在知识库中时，需要分别检查检索是否找对材料、回答是否忠于证据，以及错误究竟来自检索还是生成。

---

Generated by [AI Codebase Knowledge Builder](https://github.com/The-Pocket/Tutorial-Codebase-Knowledge)