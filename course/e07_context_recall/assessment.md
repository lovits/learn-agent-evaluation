# e07 样本与评测记录

[教材](README.zh.md) · [参考事实](cases.jsonl) · [完整记录](assessment.json)

## 样本与控制条件

本课沿用 Atlas 发布规范（`atlas/release.md`）与审计日志规范（`atlas/logs.md`）。[cases.jsonl](cases.jsonl) 针对同时询问测试命令、发布条件和日志期限的问题，列出三条带来源映射的参考事实与对应文档哈希。

在 TinyRAG 返回的 `logs`、`release`、`auth` 候选基础上，[prepare](code.py) 选出两份必要文档构造三组控制条件：`complete` 保留完整两份文档和三条事实；`missing_logs` 主动移出 `atlas/logs.md` 而保持参考不变；`incomplete_reference` 继续使用缺日志上下文，同时从参考中删掉 `log_days`，用于观察参考缩水如何掩盖召回缺口。两份短文档各自只占一个完整片段，因此本课实验可以安全按文档路径做事实映射。

## Docker 中的覆盖计算

运行编号为 `b54b378d84cc417fbe63a434bede8078`，在 Docker 中执行原生 TinyRAG 检索与 `summarize` 集合计算，不发起模型裁判请求：

| 条件 | 必要文档数 | 必要事实数 | 文档精度 | 文档召回 | 事实召回 |
|---|---:|---:|---:|---:|---:|
| `complete` | `2` | `3` | `1` | `1` | `1` |
| `missing_logs` | `2` | `3` | `1` | `1/2` | `2/3` |
| `incomplete_reference` | `1` | `2` | `1` | `1` | `1` |

`missing_logs` 的 `missing` 字段明确输出遗漏事实 `"Atlas 审计日志保留 14 天。"`，而它的文档精度依然是 `1`。`incomplete_reference` 与 `missing_logs` 使用完全相同的上下文，仅因参考缩水，文档召回和事实召回都升至 `1`。

## DeepEval 原生归因

运行编号为 `103e25bec4ae4891b77a351090462444`，在 Docker 中带 `--judge` 参数发起三次实际裁判请求（每组条件一次）。由于设置 `include_reason=False`，省去了额外的总分解释请求，逐条裁决的归因理由仍完整保存在 [assessment.json](assessment.json) 中：

| 条件 | 实际裁决 | Contextual Recall |
|---|---|---:|
| `complete` | `yes`、`yes`、`yes` | `1` |
| `missing_logs` | `yes`、`yes`、`no` | `2/3` |
| `incomplete_reference` | `yes`、`yes` | `1` |

查看逐条 `reason` 可以确认对应关系：`complete` 的三条裁决分别定位到发布规范中的命令、发布门禁以及日志文档的 14 天期限；`missing_logs` 的第三条明确指出上下文节点未提及审计日志或“保留 14 天”；`incomplete_reference` 中裁判只核对两条发布要求，因此两项都判 `yes`。由于原生 `VerdictWithExpectedOutput` 把整段参考附在每条结果上，以上对应关系均通过逐条阅读 `reason` 文本核对确认。

三组条件在 SDK 中的 `passed` 均为 `true`，这是因为 `ContextualRecallMetric` 默认阈值为 `0.5`，`2/3` 同样超过默认门槛。实际工程中是否允许漏掉一条必要依据，仍应按业务要求重新设定阈值。三组调用仅面向检索上下文与参考事实的覆盖关系，`actual_output` 保持为空。

## 软件检查覆盖项

配套单元测试（[test_context_recall.py](../../tests/test_context_recall.py)）验证了以下边界行为：

- `summarize` 在 `missing_logs` 下分别算出 `document_recall=0.5`、`fact_recall=2/3` 与 `precision=1.0`，并正确列出缺失事实；缩短参考后 `fact_recall` 变为 `1.0`。
- `coverage` 对重复命中自动去重，对空必要集返回 `None`，对有要求但无命中返回 `0.0`。
- `judge_recall` 在 `actual_output=None` 下正常计算原生归因比例，同时把空白参考与裁判返回空 `verdicts` 列表统一拦截为 `status="error"` 并置空分数。

阅读召回指标时，需要把来源文档哈希、参考事实清单的完整性以及当前选用的统计单位（文档、预设事实或模型拆句）一并纳入核对范围。
