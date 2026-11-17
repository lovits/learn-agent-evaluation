# e08 样本与评测记录

[教材](README.zh.md) · [样本](cases.jsonl) · [完整记录](assessment.json)

## 评分对象与来源

frozen_agent 复用第 5 课真实运行 `e482c43222e54cd4861b0227c9b13cac` 的任务、最终回答和实际知识库上下文。原文件 SHA-256 写在样本中，变化时停止评分。本课没有再次运行 Agent 生成回答。

另外三组为构造条件：unmentioned 加入资料没有的 GitLab 托管声明；contradicted 将日志期限说成 30 天，与原始 14 天矛盾；changed_evidence 保持后一组回答不变，将教学日志资料改为 30 天。替换片段编号为 constructed/logs-30-days，未修改原始知识库，不冒充真实检索结果。

教学声明与标签由课程编写助手给出，用于展开聚合，不是独立人工金标准，也不要求原生提取器一定拆成同样数量。

## Docker 中的固定标签计算

运行编号 `a04925731eec4e1389ec374239f08ca6`，没有裁判请求。

| 构造条件 | 教学标签 | 默认比例 | 明确支持比例 |
|---|---|---:|---:|
| unmentioned | yes、yes、borderline | 1 | 2/3 |
| contradicted | yes、yes、no | 2/3 | 2/3 |
| changed_evidence | yes、yes、yes | 1 | 1 |

frozen_agent 未预设教学标签；它的声明数量与关系由原生执行后逐项阅读。

## DeepEval 原生执行

运行编号 `589609fbb5a14e539c99942ab39352ac`，Docker 中实际发出 12 次裁判请求。每组分别抽取 truths、claims，再判 verdicts；include_reason=False 跳过额外总分解释。

| 条件 | 实际声明数 | 实际裁决 | 原生默认分数 | 同裁决的明确支持比例 |
|---|---:|---|---:|---:|
| frozen_agent | 6 | borderline、yes、yes、borderline、borderline、borderline | 1 | 1/3 |
| unmentioned | 3 | yes、yes、borderline | 1 | 2/3 |
| contradicted | 3 | yes、yes、no | 2/3 | 2/3 |
| changed_evidence | 3 | yes、yes、yes | 1 | 1 |

三组构造条件与本次教学标签一致。GitLab 声明因资料未说明托管平台判 borderline；30 天因与 14 天直接矛盾判 no；换成 30 天证据后，期限声明判 yes。不能将此解释成模型纠正了原始规范。

support_score 从这同一批原生 verdicts 计算，只统计 yes，没有再次调用裁判，也没有执行 Ragas。四组 passed 均为 true，沿用的是 DeepEval 默认 0.5 阈值及默认聚合；它不表示所有声明明确有据，更不表示完整完成任务。

## 真实回答中的边界

frozen_agent 的两个 yes 对应发布前命令及通过条件、失败先修复要求。其余四项需要分开解释：

- “check.txt 包含命令”没有知识库证据。第五课实际 write_file/read_file 轨迹能够核对文件内容；本课只传知识资料，不能据此宣布文件没写成。
- “测试和实际发布均未执行”属于执行轨迹声明，知识库规范本身不能证明是否做过。
- 两条带来源编号的声明被判 borderline，因为裁判收到的 truths 未保留 atlas/release.md#0 与 atlas/logs.md#0。原始 retrieval_context 实际含有这些编号。这里是中间抽取损失影响了引用判定，不能直接归咎于 Agent 引用了不存在的资料。

因此，这次明确支持比例 1/3 不宜作为该 Agent 总体质量结论。应先划清知识与执行证据范围，再检查 truths 是否保留了判定所需信息。原始上下文、抽取内容、声明和理由均已保存，未为了得到更好分数而重写记录。

## 软件检查与解释范围

构造软件检查验证：同一标签的默认与明确支持聚合、未知标签拒绝、空分母、原生默认 borderline 通过、空声明的 sdk_score=1 与课程 not_applicable 区分，以及裁决数量不足时记 error/None。这些模拟响应不冒充实际模型调用。

数量对齐不保证语义对齐；抽取器可能漏声明、丢条件或丢来源。真实裁决仍需对照回答与证据审核。无声明时，不给忠实度有效分数，但是否合理拒答、是否完成任务需另评。

这里只有一条公开真实回答及三个教学对照，不能推断业务分布上的幻觉率。所有结果都依赖指定上下文、提取过程和聚合口径。
