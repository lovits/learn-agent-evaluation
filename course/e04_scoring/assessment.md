# e04 样本与评测记录

[教材](README.zh.md) · [教学回答](cases.jsonl) · [评分实现](eval.py) · [完整记录](assessment.json)

## 数据从哪里来

继续使用第 3 课的 `knowledge_base/course/upload.md`。它是构造的上传规则，不代表真实生产接口。本课任务要求 Agent 读文件，返回请求头、最大字节数和解释，不实际发送上传请求。

`cases.jsonl` 中五段回答由课程作者构造，均标为 `constructed_teaching_answer`，用于观察评分器边界。对它们的裁判调用是真实模型调用；这些回答本身不冒充 Agent 运行结果。

## Docker 中的实际评分

构造回答运行编号 `dea7034d37c9444589be03e531a932c6`。规则用原生 DeepEval 自定义指标，语义分使用原生 G-Eval；没有第二套 Ragas 评分。

| 构造回答 | 规则分 | G-Eval 归一化分 | 原因 |
|---|---:|---:|---|
| paraphrase | 1 | 1 | 同义表达覆盖超限响应和发送前检查 |
| omission | 1 | 0.5 | 只写发送前检查，遗漏超限响应 |
| contradiction | 1 | 0 | 解释声称返回 200 且不必检查，与参考矛盾 |
| irrelevant | 1 | 0 | 只指出文档位置，没有覆盖要求 |
| plain-text | 0 | 1 | 含义完整，但没有按要求返回 JSON 对象 |

五次裁判均成功完成，原始 JSON、usage、耗时与逐项理由见完整记录。两项分数分别保存，没有计算综合平均分。这组构造回答用于解释机制，不能拿其平均值当 Agent 的业务准确率。

## 真实 Agent 运行

另在 Docker 中执行一次真实 Agent 任务，运行编号 `9d73b411ab7b4ea1848adfc3a397e90d`。Agent 实际调用 `read_file("upload.md")`，收到资料后返回：

```json
{"required_header":"X-Project-Token","max_bytes":1048576,"explanation":"超出最大文件大小会返回 HTTP 413；发送前应检查文件大小。"}
```

循环状态为 `finished`；规则分和 G-Eval 分均为 1，裁判指出解释覆盖两个要求。记录包含真实工具参数、输出、最终回答、资料哈希及模型返回。一次成功不能推断其他任务也会成功。

Agent 与裁判复用本机 Codex 登录，运行上下文分离；本课没有声称使用不同模型或获得独立人工金标准。评分理由仍需核对。

## 零分、未定义和故障探针

Docker 还执行了受控软件探针 `cebc28fdd326433d9ae1421da6a40905`：主动让传输函数抛出 `OSError`，没有向模型发送请求。结果为 `status=error`，`score`、`passed` 均为空，原因说明是人为注入的故障。

同一记录保存空集合计算：预测为空、参考含一项时 precision 为空、recall 与 F1 为零；两侧都为空时三项均为空。它们与上表中真实完成裁决的零分分别记录。

软件检查另外覆盖：错误解释不能靠结构检查发现、整数不能由字符串替代、无效 JSON 是有效规则零分、传输与 schema 错误不能写成零分，以及集合重复项和空分母。软件检查不替代裁判校准。
