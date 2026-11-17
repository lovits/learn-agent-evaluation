# e03 样本与评测记录

[教材](README.zh.md) · [题目](cases.jsonl) · [数据检查](eval.py) · [原始记录](assessment.json)

## 资料与种子题

`knowledge_base/course/upload.md` 是构造的教学资料，只给出上传请求头、最大大小和超限状态。它不代表真实生产 API。本课不发送上传请求，观察的是 Agent 读取文件与回答问题的过程。

种子候选覆盖正常、错误前提、边界和缺证据，并专门放入重复、未审核、参考错误、缺引文和来源变更的例子。`origin=constructed_teaching_case` 与真实模型生成的 `live_model_candidate` 分开记录。

## 模型生成与审核

Docker 中实际执行了候选生成，运行编号为 `604338d8a76b406a92f64caa9059b750`。模型产生三道候选：认证头、恰好等于大小上限、超限响应与发送前检查。原始返回与模型传输信息保留在 JSON，三条原始审核状态均为 `pending`。

随后由课程编写助手逐项对照原文核对参考，并规范题意键。这是 AI 辅助的教材审核演示，不是独立人工标签；真实业务应由掌握业务标准的人复核。

| 候选 | 审核与题意归属 | 数据整理结果 |
|---|---|---|
| generated-0 | 原文支持请求头，题意归入 token-header | 与 auth-header 重复，未再加入 |
| generated-1 | 恰好 1048576 字节没有超过上限，归入 at-limit | 加入 upload-size 留出题族 |
| generated-2 | 原文支持 HTTP 413 和发送前检查，归入 over-limit | 与既有超限题重复，未再加入 |

原始模型题意、审核后的题意和审核理由都保留，便于区分模型建议与整理后的标签。

## 数据整理结果

| 候选 | 实际判断 | 说明 |
|---|---|---|
| auth-header、auth-misplaced | 接受，开发集 | 同族、不同题意 |
| size-limit、size-overflow | 接受，留出集 | 大小规则和超限行为保持同侧 |
| billing-unknown | 接受，开发集 | 参考限定为所给资料没有说明 |
| auth-paraphrase | duplicate_intent | 字面不同，题意键相同 |
| pending、bad-reference | not_approved | 尚未审核或明确拒绝 |
| missing-quote | missing_evidence | 即使批准标记存在，程序仍检查引文 |
| stale-source | source_changed | 审核时的资料哈希已经不符 |

合并种子与已审核模型候选后，13 条候选形成 6 条样本，开发集和留出集各 3 条。题号、题意键唯一，两侧题族不相交，四类任务均有覆盖。逐项 audit、两个真实 `EvaluationDataset` 的 Golden 导出见 JSON。

这些检查只能说明这份教学数据符合当前结构约束，不能证明参考全都正确，也不能证明它代表真实用户分布。

## 复用 Agent 的真实运行

Docker 中执行 `auth-header`，运行编号为 `c2d4a4a765774873a3d26a02ef7a073a`。Agent 实际调用 `read_file("upload.md")`，工具返回文件内容，随后回答 token 应放在 `X-Project-Token` 头中，循环正常停止。

导出的 DeepEval 样本保留了真实工具参数、结果和最终回答，`expected_output` 另取自题目中的参考。JSON 中还保存资料哈希与数据划分。

本课没有运行答案质量指标，`answer_quality_score` 为 `null`。不能将一次样本构造成功或一次正常停止解释为 Agent 的准确率。

## 软件检查覆盖什么

检查包含：资料变更后重新审核、越界资料路径拒绝、待审核候选排除、同意改写去重，以及人为把同族题分到两侧后能发现泄漏。软件检查使用受控数据，不冒充真实模型结果。
