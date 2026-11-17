# e14 源码导读：先确认标签与评分单位

[教材](README.zh.md) · [裁判和统计](eval.py) · [固定运行入口](code.py)

## 固定的是候选回答，不是新生成答案

`cases.jsonl` 保存问题、当前参考、提供资料、候选回答与课程参考标签。这里没有重新调用 Agent 生成答案；--judge 才实际调用 DeepEval 裁判，默认运行只是明确标记的构造分数聚合练习。

reference_label 与 label_reason 由课程作者构造，不是独立人工标注。human_label 全部为空；unlabeled 还故意不提供课程参考标签，用于说明未标注不能被偷偷算对。标注处理示例中的两份标签和仲裁同样是构造布尔例子，没有虚构两名真人。

`reconcile` 只在两份标签一致时采用共同结果；有分歧时需显式仲裁，否则保留 None。真实人工流程还应保存各自理由、证据与仲裁者。两个人一致也可能沿用了同一错误标准，不能把一致自动当成真值。

## 逐行统计，不独立删除两边

`summarize` 先保留有课程参考标签的行，再筛选评分成功的行，最后对同一行中的 reference_label、passed 计数。

- TP：参考接受，裁判接受。
- FP：参考拒绝，裁判却接受，即误接收。
- TN：参考拒绝，裁判也拒绝。
- FN：参考接受，裁判却拒绝，即误拒绝。

一致率分母是实际进入比较的行数；误接收率分母为参考拒绝行 FP+TN，误拒绝率分母为参考接受行 FN+TP。空分母保持 None，不填成完美或零表现。

同时保留参考标签覆盖率、人工标签覆盖率、所有行评分覆盖率与已标注行评测覆盖率。参考标签缺失和模型评分失败不是同一种缺失。评分失败不能当成拒绝标签，否则会悄悄改变混淆矩阵。

## DeepEval：步骤、量表和阈值

固定提交 [34db63d](https://github.com/confident-ai/deepeval/tree/34db63dd005ebc9a905c8ef4741ae0687c93c14c)，概念见 [G-Eval](https://deepeval.com/docs/metrics-llm-evals)。

沿 [g_eval.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/g_eval/g_eval.py) 看：

1. evaluation_params 决定哪些样本字段进入评价。本课显式提供问题、候选、当前参考与可见资料；参考标签不塞进待评分样本。
2. `_generate_evaluation_steps` 有现成步骤就直接返回；未提供时才根据 criteria 生成。本课两个版本均固定步骤，避免每行再生成一套判据。
3. rubric 决定原始分数范围。非 strict 模式下，measure 按 `(原分数 - 下界) / 范围跨度` 归一化；它不是将分数解释成正确概率。
4. threshold 决定 passed。原版0—2量表中的部分正确0.5，在阈值1下仍是拒绝；不能看到原始分下降就宣布误判率下降。

原版复用第9课 task_metric。修订版把当前规范冲突、绕过门槛和跳过失败列为优先拒绝条件，再解释证据不足时的合理保留。它同时改为二元量表并附开发示例，因此是整个裁判配置的比较，不能把变化单独归因于某一行提示词。

本课 JudgeModel 不提供 log probabilities，沿用原始结构化分数路径；没有声称实际使用了加权 token 概率。第4课包装继续检查有限范围与评分错误，原始理由保留。

## Few-shot 只能从开发材料选

`development_examples` 只选择 split=dev 且有参考标签的 Atlas 样本，连同其判据写入 evaluation_steps。Boreal、Cedar 题族留出，语言与篇幅变体随原题族一起划分；程序拒绝题族跨集合。

这是显式的少量示例，不是 G-Eval 自动替我们寻找了正确示例。示例本身也来自课程构造参考，不能写成“已经人工校准”。本次看真实结果前固定修订配置，没有再依据留出分数调整规则。

题族分开仍不等于真正独立的外部测试：这些项目任务共享同一发布模板，只有两个留出题族。多个等价回答也不等于多个独立任务。因此本课只能演示组织与诊断方法，不能证明广泛泛化。

## 位置、篇幅与语言各自怎么观察

篇幅与语言变体保持同一参考含义，比较它们是否跨越接受阈值。措辞等价需要先核对；如果长答案多了错误，差异就不能简单归为篇幅偏差。

位置例子使用同一对候选，显式构造 Candidate A、Candidate B，再交换文本位置。pair_metric 仍由 DeepEval GEval 执行，1表示A更好、0表示B更好。映射回候选ID后再比较，不能把两次原始0/1不同误当成判断翻转。

这份受控比较只有一好一坏，不适用于平局或模棱两可的任意回答；非0/1结果保留为未决。它不是 ArenaGEval 的通用胜率。

阅读原生 [arena_g_eval/utils.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/arena_g_eval/utils.py) 可以看到匿名映射与展示顺序都会随机化。因此仅调换传给 Arena 的列表，并不能保证模型恰好看到一次严格的位置对调。本课用明确候选文本控制这个小例子的呈现，不改写上游随机化实现。

一次顺序对照同时受模型波动影响；没有观察到翻转不证明不存在位置偏差。相关研究见 [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685)。论文指出位置和篇幅等偏差，不意味着本课已经对这些偏差测得稳定发生率。

## Ragas：align 改了什么

固定提交 [8c63f10](https://github.com/vibrantlabsai/ragas/tree/8c63f10d500c44efbf24fdb9e2920de2104c321c)，参考 [Align an LLM as a Judge](https://docs.ragas.io/en/stable/howtos/applications/align-llm-as-judge/)。本课不实际执行 Ragas。

指南将固定回答交给裁判，再与专家 target 对照、分析分歧。专家标签的来源是该指南的数据集说明，不是本课构造标签的来源。

[metrics/base.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/base.py) 的 SimpleBaseMetric.align 将训练行的输入与指标输出放入 DynamicFewShotPrompt。它做的是推理时示例检索，不等于更新了基础模型权重。

[dynamic_few_shot.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/prompt/dynamic_few_shot.py) 的 format 按当前输入、数量限制与相似度阈值选择示例。没有 embedding 时会使用最近示例；“动态选择”不是永远具有语义相关性保证。

同一固定版本还保留 MetricWithLLM.train 的 instruction / demonstration 优化路径。它使用不同提示接口，不能把所有同名 align、train 与 collections 的模型适配混为一套 API。

validate_alignment 中可看到 gold 与 pred 各自过滤 None 后再 zip 的实现。若缺失位置不同，就有错位比较的风险。课程统计直接按样本行对齐，并另外报告缺失，避免拿删除后的数组位置当成样本身份。

## Ragas：翻译示例不保证跨语言公平

参考 [语言适配](https://docs.ragas.io/en/stable/howtos/customizations/metrics/metrics_language_adaptation/)。

固定版本 [pydantic_prompt.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/prompt/pydantic_prompt.py) 的 adapt 提取并翻译示例字符串，复制提示对象并更新语言。默认不翻译 instruction，设置 adapt_instruction=True 才另作翻译。翻译后仍需检查术语、否定与判据是否保留，并用目标语言的独立样本验证。

较新 collections 使用 [prompt/metrics/base_prompt.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/prompt/metrics/base_prompt.py) 接口，文档示例与遗留 PydanticPrompt 应分别追踪。不能只改 language 字段就宣布偏差消除。本课中英候选对照只是一组观察，没有执行翻译适配或第二套评分。

## 把前课分歧作为案例，不擅自改分

[casebook.json](casebook.json) 绑定第12、13课原始记录的文件哈希，摘取任务、真实工具事件、独立条件和原裁判理由。

第12课程序行为通过，但用户还有说明义务；程序契约与语义分的差异未必是裁判错误。第13课文件已写，语言层会话样本却没有工具证据；不能凭低会话分宣布文件未交付。

这两类分歧先要明确评分单位与证据范围，再由独立标注者判断。案例没有被本课发布规范裁判重新打分，也没有被偷偷补写一句完成声明。它们用于说明：发现分歧后，先修标准、证据或指标选择，不能只追求更高一致率。

原始资料：[DeepEval docs](https://my.feishu.cn/docx/Ve2RdP0tyoPsumxuhnxcvsXuneD)、[Ragas docs](https://my.feishu.cn/docx/SOHsdGTt0ojxXoxVwbjcBzCYntg)。本课核对固定步骤、量表、专家对照与语言适配相关内容。
