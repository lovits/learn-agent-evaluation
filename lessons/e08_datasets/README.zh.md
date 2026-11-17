# e08: 评测数据集 — 一道题要带哪些东西

[课程](../../README.md) · [上一课](../e07_failure_diagnosis/README.zh.md) · [下一课](../e09_comparison/README.zh.md) · [源码导读](source_walkthrough.md)

> 保存任务、参考和来源，下次才能评价同一个问题。

## 只有问题列表还不够

上一课发现 Agent 漏写上传限额。把“上传上限是多少”存下来，过几天再问一次，未必能重现原问题：文档可能已改版，问题可能不再要求同一版本。

一条评测数据需要把任务与当时的成功条件绑在一起。生成器可以帮我们扩充问题，但生成的参考也需要检查。

## 先定义候选

本课的候选保存这些信息：

| 字段 | 用处 |
|---|---|
| `question / reference` | 要问什么、依据什么判断 |
| `evidence` | 文档 ID 与内容哈希 |
| `family / query_type` | 属于哪类任务、单跳还是多跳 |
| `answerable` | 指定证据内能否回答 |
| `origin / review_status` | 从哪里产生、审核到哪一步 |
| `actual_output` | 被测 Agent 真正运行后的输出 |

准备题目时，`actual_output=None`。参考答案不能复制成实际输出。编程题还要保存文件与行为合同，例如修改后的输出应为48。

![数据从候选进入审核与划分](images/dataset-pipeline.png)

## DeepEval 从上下文生成 Golden

[`code.py`](code.py) 把已经选好的文档交给原生 Synthesizer：

```python
goldens = synthesizer.generate_goldens_from_contexts(
    contexts=[[d["text"] for d in docs]],
    max_goldens_per_context=1,
    include_expected_output=True,
    source_files=[[d["id"] for d in docs]],
    context_chunk_source_files=[[d["id"] for d in docs]],
    _send_data=False,
)
```

先生成问题，再经过质量反馈、重写与演化，最后生成参考。Reasoning 可以增加推理要求，Multi-context 可以让问题利用多份上下文。

质量分不是最终通行证。固定版本在重试用完后仍可能保留低分输入，后续演化又会改变题目，因此最后还要审核。

## Ragas 先构图，再生成场景

两份规范都谈 `POST /upload`，可以用这个共同实体建立关系：

```text
认证文档 ── POST /upload ── 限额文档
```

本课用规则提取真实共同端点，构造原生 `KnowledgeGraph`。没有共同端点就停止，不凭空造关系。

`TestsetGenerator` 再依据 persona、节点和关系组织 scenario，生成问题与参考。persona 在这里是编写的 Python 开发者角色。

单跳只依赖一份资料，多跳需要跨来源组合。把两篇文档放进输入，并不保证生成的问题真正依赖两篇，所以还要问：去掉其中一篇，它是否仍能回答？

## 参考也要评分

生成之后，另一次审核检查 reference 是否受给定证据支持，以及多跳题是否确实需要多来源。

这还是模型判断。自动通过后，候选保持 `pending_human`，等待人工确认。对于“会重试几次”这类不可回答题，参考应说明未知，不能猜数字。

本课从预构建图进入生成器，没有运行向量化的默认构图流程；源码导读会区分两条路径。

## 去重和划分一起考虑

[`dataset.py`](dataset.py) 先归一化问题，再检查重复：

```python
cluster = clusters[question_key(row["question"])]
duplicate_of = cluster[0]["id"] if cluster[0]["id"] != row["id"] else None
if len({r["family"] for r in cluster}) > 1:
    errors.append("cross_family_duplicate")
elif duplicate_of:
    errors.append("duplicate_question")
```

词面归一化能发现大小写或标点变化，语义改写仍需复核。同一任务的不同版本应留在同一题族，再按题族划分开发、校准和留出集，避免近似题跨集。

来源哈希变化时，参考也要重新检查。课程里的公开样例适合练习划分方法，正式留出集还需要未参与开发的任务。

## 试一下

从认证与限额两份资料写一道单跳题、一道确实需要两份资料的题，以及一道证据不足的题。给每题补上 reference、来源和可回答性。

再为其中一道改写措辞：它应作为独立题，还是同一题族的变体？为什么？

[生成入口](code.py) · [数据审核](dataset.py) · [练习](exercises.md) · [参考答案](solutions.md)

## 接下来

任务与标准保存好以后，就可以反复用于两个版本。下一课先把同一任务配对，再讨论平均分与不确定性。
