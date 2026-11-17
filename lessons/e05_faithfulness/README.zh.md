# e05: Faithfulness — 每条声明都能找到依据吗

[课程](../../README.md) · [上一课](../e04_retrieval/README.zh.md) · [下一课](../e06_answer_quality/README.zh.md) · [源码导读](source_walkthrough.md)

> 忠实度检查回答能否从给定证据推出。

## 文档没有写重试次数

上传规范写了认证头、大小上限和413状态码。回答却补了一句：

> 上传失败后会自动重试三次。

这句话听起来合理，但“三次”从哪里来？

Faithfulness 关心回答与本次证据的关系。即使这句话碰巧符合真实系统，给定材料也没有支持它。相反，回答照抄一份过期文档，可以很忠实，却不符合当前系统。

本课不增加 Agent 工具，只在已有回答与检索快照之间接入评分。

## 先拆成能单独判断的声明

把一段回答拆开：

```text
认证头是 X-Project-Token。
最大文件为 2097152 字节。
失败后自动重试三次。
```

旧证据写的上限是1048576字节，因此三句话分别是：有支持、与证据矛盾、证据未说明。

自然语言推断，也就是 NLI，可以帮助理解这几种关系。未提及不等于明确否定；拆句也影响分数，一句复合话拆成几项，分母就会变化。

## DeepEval 先整理证据，再判断回答

[`eval.py`](eval.py) 构造原生样本：

```python
sample = LLMTestCase(
    input=case["question"],
    actual_output=case["response"],
    retrieval_context=[d["text"] for d in case["documents"]],
)
```

`FaithfulnessMetric` 内部走这条路径：

```text
检索上下文 → truths
回答       → claims
truths + claims → yes / borderline / no → 分数
```

`truths` 是模型从证据整理出的内容，也可能遗漏信息。遇到奇怪分数，要同时检查拆出的 claims 和整理后的 truths。

固定版本默认让 `yes` 与 `borderline` 通过；开启 `penalize_ambiguous_claims` 后只接受 `yes`。

假设裁决为 `[yes, borderline, no]`，默认分数是2/3，惩罚含糊项后为1/3。这是同一组裁决的两种聚合方式。

## Ragas 先生成声明，再做二元支持判断

Ragas collections 的调用是：

```python
metric = Faithfulness(llm=judge)
value = asyncio.run(metric.ascore(
    user_input=case["question"],
    response=case["response"],
    retrieved_contexts=[d["text"] for d in case["documents"]],
)).value
```

内部先生成原子 statements，再让 NLI 判断每项能否由上下文支持，最后计算：

```text
支持的声明数 / 全部判定声明数
```

若三条判定是 `[1, 0, 0]`，结果就是1/3。它没有沿用 DeepEval 默认把 borderline 计入通过的规则。

两个框架还可能拆出不同数量的声明。比较分数前，先确认它们各自数了什么。

## 没有声明时怎么办

“谢谢”可能没有需要核实的事实。固定版本的 DeepEval 对空裁决默认返回1；Ragas 对无声明或无裁决可返回 NaN，空字符串又可能更早触发输入错误。

这些值反映聚合约定。回答有没有完成用户要求，要用其他指标判断。评分代码把未定义结果保存为 `null`，并与请求失败、有效0分分开。

## 证据也属于样本

回答必须与当次检索结果一起保存，不能在评价旧回答时悄悄换成今天的知识库。

[`evidence_key`](code.py) 用文档 ID、哈希和顺序标识证据。内容变化后，旧标注不能直接复用：

```python
def require_same_evidence(old_key, documents):
    if old_key != evidence_key(documents):
        raise ValueError(
            "Evidence changed; old annotations must not be reused"
        )
```

同一句“上限2097152字节”，在旧资料下是矛盾，在新资料下可能有支持。回答没有变化，评价条件已经变了。

## 试一下

给相同回答分别配上1048576与2097152字节的证据，观察逐声明裁决。

再对同一组 DeepEval 裁决切换含糊项惩罚。分数变了以后，分别说明：哪次变化来自证据，哪次来自聚合政策？

[证据与聚合](code.py) · [原生指标调用](eval.py) · [练习](exercises.md) · [参考答案](solutions.md)

## 接下来

每句都有证据，仍可能只回答了用户问题的一小部分。下一课把切题、正确、完整与拒答放在各自的位置。
