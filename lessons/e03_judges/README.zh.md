# e03: 评分标准 — 同一个 48，为什么分数不同

[课程](../../README.md) · [上一课](../e02_tools_traces/README.zh.md) · [下一课](../e04_retrieval/README.zh.md) · [源码导读](source_walkthrough.md)

> 先确定在判断什么，再选择评分器。

## 字面不同，含义相同

Agent 修改程序以后，可能返回：

```text
{"result":48}
```

也可能返回：

```text
程序输出为四十八。
```

如果接口只接受 JSON，第二句不合格；如果只问输出是多少，两句都表达了正确数字。还有第三种情况：回答写了48，程序却根本没改。

格式、含义和实际完成状态，要各自有标准。本课保持 Agent 不变，只增加评分层。

## 能直接判的条件，先写规则

[`rules`](code.py) 先比较原始字符串，再解析 JSON：

```python
value = json.loads(case["response"])
valid = (
    isinstance(value, dict)
    and set(value) == {"result"}
    and type(value["result"]) is int
    and value["result"] == 48
)
```

这里判断的是整个输出合同：对象只有 `result`，类型是整数，值是48。用 `type(...) is int` 可以排除布尔值。

程序还单列 `state_contract`，读取独立检查给出的状态。教学样本通过构造这个字段制造差异；实际项目中，它必须由文件和执行检查产生。

## 比较集合，要先看分母

预期工具为四种，实际只使用其中两种。精确率回答“用了的有多少合适”，召回率回答“该用的覆盖多少”：

```python
overlap = len(expected & actual)
precision = overlap / len(actual) if actual else 0.0
recall = overlap / len(expected) if expected else 0.0
f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
```

在这个手算例子中，precision 为1，recall 为1/2，F1 为2/3。

`set_f1` 先去重，因而忽略顺序、参数和重复次数。它只适合解释覆盖。后面的工具课会把这些条件分别加回来。

## 理解含义时，把标准交给模型

LLM 裁判需要一份 rubric，也就是明确的评分依据。本课要求它判断：回答是否表达输出为48，是否符合独立状态，并忽略 JSON 格式。

DeepEval 的 G-Eval 接受显式评分步骤：

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

`evaluation_params` 决定裁判能看见哪些字段。`evaluation_steps` 决定按什么标准看；`threshold` 决定分数达到多少才接受。

例如“不能虚报完成”可能被理解为只禁止出现“完成”二字。若业务要求独立检查失败时一律不能通过，就应把这条写清楚。标准中的歧义会成为评分中的歧义。

## 三种裁判怎样组织判断

| 方式 | 判断过程 | 输出含义 |
|---|---|---|
| G-Eval | 按步骤给出评分与理由 | 归一化后的等级分 |
| DeepEval DAG | 判断节点选择分支，落到分值叶子 | 由路径决定的分数 |
| Ragas AspectCritic | 按 `definition` 判断是否满足 | 二元裁决 |

DAG 的分值映射由程序固定，判断节点仍可使用模型。把判断接成图，并不会消除模型的不确定性。

本课的 G-Eval 适配器没有 token 级概率，因此走结构化评分路径。AspectCritic 使用固定版本的旧接口，`strictness=1`。它们的具体调用链见[源码导读](source_walkthrough.md)。

## 0 分和没有分数

裁判正常返回“不满足”，是有效的0分。请求失败或结果无法解析，则没有形成裁决：

```python
except Exception as error:
    scores[type(metric).__name__] = {
        "score": None,
        "error": str(error),
    }
```

统计时要同时保留未评分项。把它们删掉，会让结果看起来比实际更可靠。

## 试一下

比较“中文四十八”“JSON里的47”和“文件未修改但回答48”。先写出每种标准应当关注的事实，再运行相应评分器。

试着改一句 rubric：从“不要虚报完成”改成“独立检查未通过时必须失败”。哪些回答的判定会受影响？

[规则评分](code.py) · [裁判入口](eval.py) · [练习](exercises.md) · [参考答案](solutions.md)

## 接下来

自然语言评分已经能接上。下一课让 Agent 读取项目知识库，先评价它拿到的资料是否相关、是否完整，以及顺序是否合理。
