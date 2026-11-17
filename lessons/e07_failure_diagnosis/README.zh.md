# e07: 失败定位 — 错误最先出现在哪里

[课程](../../README.md) · [上一课](../e06_answer_quality/README.zh.md) · [下一课](../e08_datasets/README.zh.md) · [源码导读](source_walkthrough.md)

> 最终答案指出症状，阶段证据缩小排查范围。

## 同一个 null，三种来路

Agent 要把上传规范写成 `upload_notes.json`，其中 `max_bytes` 却是 `null`。

可能是知识库没有限额说明，也可能是文档存在但没有检索出来，还可能是模型收到资料后遗漏了它。只看最终分数，无法区分。

本课继续使用合成 v1 的1048576字节上限，保持问题和查询不变，每次只改变一个位置。

## 把改动放在链路上

| 位置 | 控制方式 | 要观察什么 |
|---|---|---|
| 资料源 | 从临时资料副本移除限额文档 | 是否本来就缺资料 |
| 检索返回 | 隐去命中、加入旧规范或噪声 | 模型实际收到什么 |
| 生成入口 | 加入错误的旧限额指令 | 证据完整时仍会怎样输出 |

这里的故障开关是有意设置的，不代表模型自然发生这些错误的比例。

原知识库保持只读。资料缺口只在临时副本里制造，避免一次练习影响后续课程。

## 只替换工具执行的位置

前面的循环已经接收 `tool_dispatch`。本课通过这个参数接入 `fault_dispatch`，其他工具继续走原实现。

检索时，先保存正常命中，再应用干预：

```python
hits = search_knowledge(QUERY, root=corpus)
before = json.loads(json.dumps(hits))
if case_id == "drop_hit":
    hits = [d for d in hits if d["id"] != "e04/limits.md"]
if case_id in ("add_old", "add_noise"):
    hits = [*hits, extra_document(case_id)]
retrievals.append({"query": QUERY, "before": before, "after": hits})
```

`before` 说明检索器原本找到了什么；`after` 才是交给模型的内容。`drop_doc` 则更早发生，在检索开始前就从资料副本移走文件。

这样，“资料没有”和“没有返回”就留下了不同证据。

## 从实际文件往回查

[`inspect_artifact`](code.py) 重新读取文件，校验 JSON 结构，再比对认证头、上限和状态码。`null` 表示给定证据范围内未知，不表示系统没有限制。

诊断按观察值逐层判断：

```python
if artifact["status"] != "valid":
    return "artifact_error"
if not REQUIRED <= set(available_ids):
    return "knowledge_gap"
if not REQUIRED <= set(returned_ids):
    return "retrieval_gap"
if all(artifact["field_matches"].values()):
    return "no_observed_task_failure"
return "generation_mismatch_requires_review"
```

诊断函数不根据故障组名字猜答案。证据完整而产物不匹配时，它只把范围缩到生成及执行阶段，仍要继续检查指令与动作。

## 噪声指标补充了什么

DeepEval 的 Contextual Relevancy 问“返回内容有多少切题”。旧上传规范可能很切题，但已经过期。

Ragas 的 NoiseSensitivity 按事实支持关系划分上下文：能支持至少一条 reference 声明的为 relevant，其他为 irrelevant，再检查错误回答声明被哪组支持。

```text
噪声敏感度 = 被指定上下文组支持的错误回答声明数 / 全部回答声明数
```

它越低越好。如果错误是模型自己编出的，任何上下文都不支持，这个分数也可能为0。因此仍需答案正确性与阶段证据一起判断。

无关模式会排除同时被相关组支持的声明，避免两组重复计数。具体支持矩阵放在源码导读。

## 评分输入也会制造错误

参考答案若没有写明端点，裁判可能把带端点的正确声明判成不受支持。把 JSON 的 `null` 写成“系统没有配置”，又会改变原来的未知含义。

给裁判的文本投影要忠实表达原文件。修改评分输入以后，分数变化只说明评价条件变了，不能据此判断 Agent 改进。

## 试一下

对照 `drop_doc` 与 `drop_hit` 的可用文档、`before` 和 `after`。哪一步最早缺少限额？

再给模型完整证据但加入错误指令。沿实际文件和工具事件说明你已经知道什么，以及还需要查什么。

[故障接入](code.py) · [评分与诊断](eval.py) · [练习](exercises.md) · [参考答案](solutions.md)

## 接下来

定位出的失败值得保留下来。下一课把问题、证据与成功条件整理成可反复使用的评测数据。
