# e14 源码导读：先确认标签与评分单位

[教材](README.zh.md) · [裁判和统计](eval.py) · [固定运行入口](code.py)

## 冻结候选与标注仲裁

`cases.jsonl` 保存题目、当前参考规范、检索资料、候选回答以及 `reference_label`。运行 [code.py](code.py) 时不会重新调用 Agent 生成回答：默认模式使用每行自带的 `fixture_score` 演示聚合统计，加上 `--judge` 后才调用 DeepEval `GEval` 裁判。

数据集里同时保留了 `reference_label` 和 `human_label` 两个字段。`reference_label` 与 `label_reason` 记录课程参考判断，`human_label` 留空以备接入人工复核；`unlabeled` 样本有意将参考标签设为空，用来验证统计代码会把它排除在一致率分母之外。

`reconcile` 实现双人标注合并逻辑：两份布尔标签一致时采用共同结果，出现分歧时取显式传入的 `adjudicated`，未仲裁则保持 `None`。在生产标注流程中，还需要把两位标注员的理由、依据和仲裁者信息一并落盘，并定期抽查双方是否共同遵循了最新标准。

## 按行对齐的统计实现

`summarize` 先过滤出具备布尔 `reference_label` 的样本，再从中筛选评分状态为 `ok` 的行，最后按同一行的 `reference_label` 与 `passed` 累计四个计数：

- TP：参考接受，裁判接受。
- FP：参考拒绝，裁判接受（误接收）。
- TN：参考拒绝，裁判拒绝。
- FN：参考接受，裁判拒绝（误拒绝）。

三项指标使用各自对应的分母：一致率除以有效比较行数；误接收率除以参考拒绝行数 `FP + TN`；误拒绝率除以参考接受行数 `FN + TP`。当分母为 0 时，`ratio` 辅助函数直接返回 `None`。

汇总字典同时输出 `reference_label_coverage`、`human_label_coverage`、`scoring_coverage` 和 `evaluation_coverage`。把“缺少标签”和“裁判调用报错”分开统计，可以防止接口失败被悄悄折算成拒绝样本而扭曲混淆矩阵。

## DeepEval：步骤、量表与阈值

本课对应 DeepEval 固定提交 [34db63d](https://github.com/confident-ai/deepeval/tree/34db63dd005ebc9a905c8ef4741ae0687c93c14c)，核心概念参考 [G-Eval 文档](https://deepeval.com/docs/metrics-llm-evals)。

沿 [g_eval.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/g_eval/g_eval.py) 追踪调用路径：

1. `evaluation_params` 控制哪些样本字段进入裁判提示词。本课显式传入 `INPUT`、`ACTUAL_OUTPUT`、`EXPECTED_OUTPUT` 与 `RETRIEVAL_CONTEXT`，`reference_label` 不放入样本。
2. `_generate_evaluation_steps` 在调用方已经提供 `evaluation_steps` 时直接返回，不再用模型自动生成步骤。本课两套配置都固定了步骤列表，保证每条样本使用同一套判据。
3. `rubric` 定义原始分值区间。在非 strict 模式下，`measure` 按 `(原始分 - 下界) / 范围跨度` 做线性归一化。
4. `threshold` 决定最终的 `passed` 布尔值。原配置采用 0 至 2 量表，部分正确得 0.5，在 `threshold=1.0` 下仍判为拒绝；因此比较版本时必须同时看原始分与通过状态。

原配置复用第 9 课的 `task_metric`。修订配置 `revised_metric` 把“与当前规范矛盾、未通过检查即发布、跳过失败项”放在最前面作为硬失败条件，随后说明证据不足时的合理保留，并改用 0/1 二元量表和开发集示例。

本课使用的 `JudgeModel` 走结构化 JSON 评分路径，外层沿用第 4 课的 `score` 包装函数检查分值范围、捕获异常并保留原始 `reason`。

## 开发集示例与题族隔离

`development_examples` 只选取 `split == "dev"` 且带有布尔 `reference_label` 的 `Atlas` 样本，连同 `label_reason` 序列化后追加到 `evaluation_steps` 末尾。`Boreal` 与 `Cedar` 题族全部留出，同题的语言和篇幅变体随题族一起归属留出集。

[code.py](code.py) 在运行初期计算开发集与留出集的题族交集，一旦发现跨集合题族就抛出 `ValueError`。这种硬校验能拦住同一道题的不同改写版本同时出现在示例和验证集中。

## 形式变体与位置对照

长短变体和中英变体围绕同一参考事实构造，用来检查裁判是否会因为篇幅或语言切换而跨过通过阈值。分析差异前需要先确认候选回答没有引入额外错误，把事实差异和形式偏差区分开。

位置对照由 `pair_metric` 执行，输入是同一对一好一坏候选拼接成的 `Candidate A` 与 `Candidate B`。`GEval` 返回 `1` 表示 A 更好，`0` 表示 B 更好。主程序交换 A/B 顺序跑两轮，并把每轮分数映射回候选 ID 后再对比胜者，非 `0`/`1` 或异常结果记为 `None`。

查看 DeepEval 原生的 [arena_g_eval/utils.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/arena_g_eval/utils.py) 可以发现，Arena 模式会在内部对候选名称做匿名映射和随机打乱。因此只交换传入列表的顺序，无法保证底层模型恰好看到严格对调的 A/B 位置。本课通过显式拼装 `Candidate A` 和 `Candidate B` 文本实现受控对调，避免随机化掩盖位置效应。关于位置偏差与篇幅偏差的系统讨论可参考论文 [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685)。

## 结合前课分歧检查评分单位

[casebook.json](casebook.json) 绑定了第 12、13 课原始记录的 SHA-256 哈希，摘录任务说明、工具事件、规则检查结果和原裁判理由：

- 第 12 课中，代码行为满足了程序契约，但最终回复遗漏了题目要求的说明义务，此时语义扣分反映的是另一层要求。
- 第 13 课中，磁盘文件已经正确写入，但纯文本会话指标读不到工具执行结果，因此低会话分不能推翻文件交付事实。

保留这些原样案例，是为了提醒我们在修改裁判提示词之前，先核对评分单位和输入证据范围是否选对。

参考资料：[DeepEval 文档整理](https://my.feishu.cn/docx/Ve2RdP0tyoPsumxuhnxcvsXuneD)。
