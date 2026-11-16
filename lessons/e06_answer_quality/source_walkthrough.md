# 第6课源码导读

本课固定 DeepEval 4.3.4（34db63dd005ebc9a905c8ef4741ae0687c93c14c）与 Ragas 0.4.4（8c63f10d500c44efbf24fdb9e2920de2104c321c）。在线文档用于理解概念，复现以这两个提交为准。下文公式来自所链源码，不能把同名指标视为同一种实现。

## DeepEval：答案相关性

[官方文档](https://deepeval.com/docs/metrics-answer-relevancy)；[固定源码](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/answer_relevancy/answer_relevancy.py)。

`AnswerRelevancyMetric` 的 `_required_params` 仅有 INPUT 和 ACTUAL_OUTPUT，不要求 reference 或检索证据。`prepare_measure` 后，`measure` 在同步分支调用 `_generate_statements`，再调用 `_generate_verdicts`，最后 `_calculate_score`。本课显式指定 `eval_mode="llm"`，不把 hybrid、system_one 的结果混进同一对照。

声明抽取经 `Statements.statements` schema，相关性裁决经 `AnswerRelevancyVerdict`，允许 yes/no/borderline，带可选 reason。`_calculate_score` 调共享 `score_qag_verdicts`，yes、borderline 均计通过，空 verdict 默认1；strict_mode 还会改变阈值和低分处理。本课不启用 strict_mode，且只记录原始分数，不拿默认阈值宣布业务通过。

`include_reason=False` 省略最后的总结理由请求，逐声明 verdict 仍保留。异步 `a_measure` 依次 await 抽取、裁决和总结；后一阶段依赖前一阶段，不会让依赖消失。模型提出了一条切题但错误的限额时，该指标并没有独立 reference 来核实数字。

## DeepEval：业务正确性与拒答

[正确性指南](https://deepeval.com/guides/guides-answer-correctness-metric)建议以 GEval 定义应用自己的正确性。本课复用第3课的 GEval 与模型适配器，不另造一个名为“官方 AnswerCorrectnessMetric”的类。

`eval.py` 的 STEPS 明确内容正确、所问事项覆盖、切题和拒答政策。`expected_output` 同时携带版本化 reference、answerable 与 policy；`evaluation_params` 为 INPUT、ACTUAL_OUTPUT、EXPECTED_OUTPUT。这些是评分器可用的标准，不是被测回答自报的事实。GEval 的 schema、评分归一化和调用细节沿用[第3课源码导读](../e03_judges/source_walkthrough.md)。本机适配没有 token 级 logprobs，不能声称复现了有 logprobs 时的加权校准。

拒答合同区分“给定证据内答不出”和“世界上不存在答案”。缺少 retry 配置时接受说明缺口、请求补充资料；没有写重试次数不表示0次。已给出完整上传设置时，无理由拒答要扣分。此 GEval 分数是对这些标准的模型判断，仍需人工检查 reason；它不独立核实工具或文件产物。

## Ragas：FactualCorrectness 的两个方向

[官方概念](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/factual_correctness/)；[固定实现](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/factual_correctness/metric.py)。

`ascore(response, reference)` 先拒绝空 response/reference。`_decompose_and_verify_claims(response, reference)` 用 ClaimDecompositionPrompt 拆回答，再由 NLIStatementPrompt 判断每条能否由 reference 推出。mode 非 precision 时，交换两个文本再执行一次。本课 `atomicity="high"`、`coverage="high"`，使抽取尽量细致；模型实际产出的声明仍可能不同，不能强行等同人工预设。

其计数是：TP=正向支持数，FP=正向不支持数，FN=反向不支持数。precision=TP/(TP+FP+1e-8)，recall=TP/(TP+FN+1e-8)，f1 调 fbeta_score，最后四舍五入为两位。源码中的 recall 沿用正向 TP，**并非始终等于反向支持数/反向声明数**。两个方向的粒度不同就会出现差异。例如正向 [1,1,1]、反向 [1,0] 时，其 recall 为3/(3+1)=0.75，反向覆盖率则为1/2。

`CapturingJudge` 复用第5课，只记录 schema 原始结果。`eval.py` 按 ClaimDecompositionOutput 与 NLIStatementOutput 的实际阶段顺序对齐方向，即使某方向为空、跳过NLI也不把后一方向误认成前一方向。主实验只真正运行 f1；precision/recall 是对同组实际裁决的手算重聚合，不冒充三次独立原生运行。断网测试另用固定裁决检查原生三种 mode。

空拆解或空NLI生成空布尔数组；全空计数经该实现得到0。输入空字符串报错与拆不出声明不是同一个阶段。

## Ragas：AnswerCorrectness 的分类与混合

[官方文档](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/answer_correctness/)；[固定实现](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/answer_correctness/metric.py)；[prompt/schema](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/answer_correctness/util.py)。

`ascore(user_input,response,reference)` 分别调用 StatementGeneratorPrompt 抽两个文本的声明，再以 CorrectnessClassifierPrompt 输出 ClassificationWithReason，其中 TP/FP/FN 是带 statement/reason 的列表。`_compute_f1_score` 统计这些列表长度，计算 F-beta；这不是把 FactualCorrectness 的两次NLI结果直接拿来用。任意一侧没有声明时，固定版本直接设 factuality_score=1，未进入分类器。此边界由原生断网测试验证，不能把这项默认值理解为拒答合格。

默认 weights=[0.75,0.25]，组合事实分与 embedding 余弦相似度，权重用 np.average 归一化，不强制总和恰好1。相似度权重大于0又没有 embeddings，构造时就报错。`_calculate_similarity` 异步嵌入回答和 reference，零向量返回0；它没有把语义相似度变成逻辑蕴含。

本课实测显式使用 weights=[1.0,0.0]，跳过 embedding；报告名为 RagasAnswerCorrectnessFactualOnly。默认混合公式另用人工指定事实分0.5、人工相似度0.8手算，得到0.575，模式标成 constructed。没有真实 embedding 服务，绝不把这个数写成默认 AnswerCorrectness 的实测成绩。

## Response Relevancy 与语义相似度

[Ragas Response Relevancy 文档](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/answer_relevance/)的概念在该固定 collections API 中对应 [AnswerRelevancy](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/answer_relevancy/metric.py)。它从回答反推 strictness 个问题，嵌入原问题与生成问题，取余弦均值；只要生成问题非空才保留它与 noncommittal 标志。没有有效问题直接0；这个版本用 np.all(noncommittal_flags)，全部不作实质回答才将均值乘0，不应照搬旧实现的任一标志规则。它与 DeepEval 逐声明切题比例不同。

[SemanticSimilarity 文档](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/semantic_similarity/)与[固定源码](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/_semantic_similarity.py)则直接比较回答和 reference 的嵌入，没有反推问题、声明分类或NLI。该类将空字符串替换为空格，直接归一化；零向量没有与 AnswerCorrectness 相同的显式保护。余弦本身可以为负，不能仅凭接口简介把所有嵌入分数都假定在[0,1]。

本课没有声称实跑这两个 embedding 指标。`code.cosine` 的人工二维向量用于解释点积/范数，不模拟语义编码器；零向量显式报错是教学函数自己的边界约定。改变一个数字或否定词后句子仍可能在语义空间很近，事实判定需要别的证据。

## 版本、标注与运行状态

`reference.json` 是课程合成系统的验收夹具，v2的2MiB限额是受控设定，不是生产服务器事实。参考答案、answerable和policy一起哈希，`source_reference_sha256` 保存整份夹具身份。reference不能由被测回答反向补写；v1真实记录按v1标准再评，受控stale_v1样本则用于模拟当前v2任务却只查到旧资料。

cases.jsonl 的 teaching_expectation 不传给裁判；SDK仅收到它们各自需要的字段。off_topic中的健康接口事实存在于独立合成配置，却未写进上传问答的reference，借此说明“参考不支持”不能自动升级为“外部事实虚假”。实验失败是status=error、score=null，进程非零退出；有效0分正常保留。原始prompt、返回、阶段输出、usage和实现哈希可在报告核对。
