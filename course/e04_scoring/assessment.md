# e04 样本与评测记录

[教材](README.zh.md) · [教学回答](cases.jsonl) · [评分实现](eval.py) · [完整记录](assessment.json)

## 样本设计

本课沿用第 3 课的 `knowledge_base/course/upload.md` 作为测试资料，任务要求 Agent 读取上传规则后返回包含 `required_header`、`max_bytes` 和 `explanation` 的 JSON 对象。

[cases.jsonl](cases.jsonl) 收录了五条教学对照回答（均标记为 `constructed_teaching_answer`），分别对应等价改写、漏项、矛盾声明、答非所问和纯文本输出五种边界场景，用于观察规则检查与语义裁判在判分上的分工。另外运行了一次真实 Agent 任务，并将所有样本结果记录在 [assessment.json](assessment.json) 中。

## 对照样本与真实裁判结果

在 Docker 环境中对五条对照样本执行评分（运行编号 `dea7034d37c9444589be03e531a932c6`），`UploadContract` 与 DeepEval `GEval` 均完成调用并分别保存分项得分：

| 样本编号 | 规则分 | `GEval` 归一化分 | 裁判判定理由摘要 |
|---|---:|---:|---|
| `paraphrase` | `1` | `1` | 同义表达同时覆盖 `1 MiB` 超限返回 `413` 与发送前检查大小 |
| `omission` | `1` | `0.5` | 只说到发送前检查文件大小，遗漏超限返回 `HTTP 413` |
| `contradiction` | `1` | `0` | 声称超限仍返回 `200` 且不必检查，与参考直接矛盾 |
| `irrelevant` | `1` | `0` | 只说明文档位于 `upload.md`，未覆盖两项必需说明 |
| `plain-text` | `0` | `1` | 语义覆盖两项要求，但未使用合规 JSON 格式输出 |

五次裁判请求均正常返回，原始提示词哈希、模型输出文本、耗时、token `usage` 以及逐条理由均完整留存在 [assessment.json](assessment.json) 中。

## 真实 Agent 运行

在 Docker 中同步运行了一次完整 Agent 任务（运行编号 `9d73b411ab7b4ea1848adfc3a397e90d`）。Agent 实际调用 `read_file("upload.md")` 读入上传规范后以 `finished` 状态退出，返回如下 JSON：

```json
{"required_header":"X-Project-Token","max_bytes":1048576,"explanation":"超出最大文件大小会返回 HTTP 413；发送前应检查文件大小。"}
```

这次运行的 `UploadContract` 规则分与 `GEval` 语义分均为 `1.0`，裁判在理由中确认两条语义要求均已覆盖。Agent 与模型裁判分别在独立上下文中运行，且记录同时保留了资料 SHA-256、工具调用参数与返回输出，方便后续逐项复核。

## 零分、未定义与故障探针

Docker 中另外执行了一组受控软件探针（运行编号 `cebc28fdd326433d9ae1421da6a40905`），用于检验异常与空集合分母的处理：

- 传输故障注入：让传输层主动抛出 `OSError` 时，`score` 返回 `status="error"`，并将 `score` 与 `passed` 保持为 `None`，与真实答错得到的 `0.0` 分彻底隔离。
- 空集合分母：`set_scores` 在预测为空、参考含一项时返回 `precision=None`、`recall=0.0`、`f1=0.0`；两侧都为空时三项均返回 `None`。

## 软件检查覆盖项

配套单元测试（[test_scoring.py](../../tests/test_scoring.py)）覆盖以下边界行为：

- `UploadContract` 对“字段合规但解释错误”的样本给 `1.0`，对字符串类型的 `"1048576"` 给 `0.0`，对非法 JSON 返回 `status="ok"` 与 `0.0` 分。
- 裁判传输抛出 `OSError`、返回空文本或无效 JSON schema 时，`score` 统一返回 `status="error"` 且 `score=None`。
- `set_scores` 自动对输入列表去重，并在预测为空或两边均为空时按约定返回 `None` 与 `0.0`。
