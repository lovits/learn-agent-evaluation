# e03 样本与评测记录

[教材](README.zh.md) · [题目](cases.jsonl) · [数据检查](eval.py) · [原始记录](assessment.json)

## 资料与种子题

本课使用 `knowledge_base/course/upload.md` 作为资料源，内容涵盖上传请求头、文件大小上限和超限返回状态码，供 Agent 读取并回答问题。

种子候选覆盖正常、错误前提、边界和缺证据四类题型，同时包含重复题意、未审核、参考错误、缺少引文和来源变更等过滤用例。数据中通过 `origin=constructed_teaching_case` 和 `live_model_candidate` 区分手工种子与模型生成的候选。

## 模型生成与审核

在 Docker 环境中执行候选生成，运行编号为 `604338d8a76b406a92f64caa9059b750`。模型生成了三条候选（认证头、恰好等于大小上限、超限响应与发送前检查），初始审核状态均为 `pending`，原始返回内容保存在 JSON 记录中。

随后逐条对照原文核对参考答案并规范题意键，整理结果如下：

| 候选 | 审核与题意归属 | 数据整理结果 |
|---|---|---|
| `generated-0` | 原文支持请求头，题意归入 `token-header` | 与 `auth-header` 重复，记为 `duplicate_intent` |
| `generated-1` | 恰好 `1048576` 字节未超限，归入 `at-limit` | 纳入 `upload-size` 留出题族 |
| `generated-2` | 原文支持 HTTP 413 与发送前检查，归入 `over-limit` | 与既有超限题重复，记为 `duplicate_intent` |

记录中同时保留了模型原始建议的题意、审核后的题意和审核理由，方便追溯每次归类决策。

## 数据整理结果

| 候选 | 整理结果 | 说明 |
|---|---|---|
| `auth-header`、`auth-misplaced` | 接受，开发集 | 同属认证题族，题意不同 |
| `size-limit`、`size-overflow` | 接受，留出集 | 大小上限与超限行为保持同侧 |
| `billing-unknown` | 接受，开发集 | 参考限定为所给资料未提及 |
| `auth-paraphrase` | `duplicate_intent` | 字面不同，题意键相同 |
| `pending`、`bad-reference` | `not_approved` | 待审核或已拒绝 |
| `missing-quote` | `missing_evidence` | 即使有批准标记，缺少原文引文仍被拦截 |
| `stale-source` | `source_changed` | 审核时记录的资料哈希与当前版本不符 |

合并种子题与审核通过的模型候选后，13 条候选最终整理为 6 条有效样本，开发集和留出集各占 3 条。题号唯一、题意键唯一、两侧题族完全不相交，四类题型全部覆盖。逐条审计日志和两个 `EvaluationDataset` 的 `Golden` 导出保存在 JSON 中。

## 复用 Agent 的真实运行

在 Docker 环境中执行 `auth-header` 任务，运行编号为 `c2d4a4a765774873a3d26a02ef7a073a`。Agent 调用 `read_file("upload.md")` 获取原文内容，随后回答 token 应放在 `X-Project-Token` 请求头中，循环正常停止。

导出的 DeepEval `LLMTestCase` 完整保留了工具调用参数、返回结果和实际回答，`expected_output` 独立取自审核后的参考，元数据中附带资料哈希和数据集划分。由于本课尚未接入答案评分指标，`answer_quality_score` 字段记录为 `null`。

## 自动化检查覆盖项

本课配套检查覆盖五类关键边界：资料更新后触发 `source_changed`、越界资料路径被拒绝、待审核候选被排除、同义改写按题意键去重，以及人为将同族题目拆到两侧时检出题族泄漏。完整结构化记录见 [assessment.json](assessment.json)。
