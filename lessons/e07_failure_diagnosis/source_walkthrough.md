# 第7课源码导读

正文按Learn Claude Code的问题、方案、分步实现和动手观察组织；这里保留框架内部调用链供继续阅读。版本与前六课一致，避免把升级带来的变化混进故障实验。

## 先看本课究竟改了哪里

[上游写作方式与实读章节](../../references/e07-teaching-pattern.md)说明实际参考的s01、s02、s07、s08。上游s02用dispatch map替换硬编码工具执行，本课借用“只改接入点”的思路：第4课循环只多一个默认等于原dispatch的tool_dispatch参数，并把执行工具的一行改为调用它。原来的判停、权限回调、事件、工具结果回填保持原路径。

本课[code.py](code.py)中的fault_dispatch只截获search_knowledge，其他工具仍交第4课dispatch，再沿第2课的权限分发执行。它校验固定query，调用既有search_knowledge，保存before后才过滤或追加after。drop_doc在临时资料副本中先移除文档；drop_hit只从返回命中移除文档。旧规范与噪声是明确标注的合成返回文档，不谎称它们本就在挂载目录。资料副本位于独立临时目录，原知识库只读挂载，运行后核对原文哈希。

模型入口仍在宿主机，tools/model_bridge.py只增加e07分支和布尔faulty_generation。正常组与e04使用同一指令；bad_prompt才追加有意错误的旧限额指令。原始指令可在仓库核对，不把手改的回答冒充模型生成。六组都真实执行读写文件的Agent循环；评分程序只读取这些已保存记录。

inspect_artifact独立读取文件，先校验JSON结构与类型，再逐业务字段对照课程合成v1合同。null表示缺信息，不当运行异常。diagnose先排查产物错误、可用资料缺口、实际返回缺口，再看字段是否匹配；它依据观察记录而非case.id给结论。generation_mismatch_requires_review只定位到需要继续查的阶段，不声称自动证明原因。

## DeepEval ContextualRelevancyMetric

[文档](https://deepeval.com/docs/metrics-contextual-relevancy)、[RAG分阶段评测指南](https://deepeval.com/guides/guides-rag-evaluation)与[固定源码](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/contextual_relevancy/contextual_relevancy.py)。版本4.3.4，提交34db63dd005ebc9a905c8ef4741ae0687c93c14c。

当前文档列input、actual_output和retrieval_context；这个固定实现的_required_params实际仅为INPUT与RETRIEVAL_CONTEXT。评分主体以问题和检索上下文生成裁决，不对回答正确性作判断。本课仍传实际产物的业务字段投影，避免把文档示例字段与算法实际比较对象混淆。

measure先prepare_measure，再沿同步分支为各个context生成ContextualRelevancyVerdicts；其中每项有statement、yes/no verdict与可选reason。_calculate_score展平全部context的verdicts，经共享score_qag_verdicts计算yes占有效声明的比例，empty_score=0。它不是按文档数简单平均，也不读取reference来判断应有文档是否漏检。长文档拆出较多声明时会贡献较多分母。

异步a_measure会并发为上下文生成裁决，再聚合；本课同步、eval_mode="llm"、include_reason=False，省去最终总结，但逐声明理由保留。不比较hybrid/system_one的不同算法。相关性高只能说明拿到的内容大多切题，不能证明拿全、版本正确或模型采用正确。

## Ragas NoiseSensitivity：先建三张支持关系表

[文档](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/noise_sensitivity/)、[固定实现](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/noise_sensitivity/metric.py)、[prompt与schema](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/noise_sensitivity/util.py)。版本0.4.4，提交8c63f10d500c44efbf24fdb9e2920de2104c321c。

ascore需要user_input、response、reference、retrieved_contexts，任一缺失会在入口报错。先调用StatementGeneratorPrompt分别拆reference与回答，再对每个context调用StatementFaithfulnessPrompt，分别判断它能支持哪些reference声明、哪些回答声明；最后用reference核对回答声明。

StatementGeneratorOutput保存statements列表；StatementFaithfulnessOutput保存每条statement、reason和整数verdict。该固定实现把非零verdict转为1，再转布尔数组，schema的int本身不把它严格限为0/1；报告保留原始输出供检查。三张表为：

- retrieved2ground_truth：reference声明×context。
- retrieved2answer：回答声明×context。
- ground_truth2answer：1×回答声明。

参考支持至少一条reference声明的context被归为relevant，其他归为irrelevant。这里的“相关”是按reference事实支持关系分组，不等于DeepEval按问题判断的话题相关。旧规范可能谈同一API却不支持任何当前参考事实；一篇混合文档只要支持一条参考事实，整篇就进入relevant组。

## 分数怎样聚合

_compute_score先对ground_truth2answer取反，得到回答中的错误掩码。relevant模式找出由relevant组任一context支持的回答声明，再与错误掩码相交，最后对全部回答声明取均值。

irrelevant模式同样找支持关系，但明确排除也被relevant组支持的声明，保证两组不重复计。分母仍是全部回答声明，而非错误声明数；值越低越好。错误若没有得到任何检索context支持，就不会计入任一组，所以NoiseSensitivity为0不能证明回答正确。

本课AuditedNoise仅在_compute_score处记录原生已经生成的矩阵，仍调用super实现。原生ascore跑relevant；切换mode后对同组矩阵再调原生聚合得到irrelevant，不再请求模型。这是相同裁决下的两个口径，避免把重新抽取带来的随机差异误当模式差异。CapturingJudge复用第5课，只保存schema输出，不替换SDK提示词。

测试里的三声明、两context矩阵是明确构造的手算夹具：第一条回答正确，第二条错误且两组都支持，第三条错误且仅irrelevant组支持。两种模式均为1/3；第二条不会在irrelevant重复计。这个正分演示不冒充真实Agent成绩。

空声明或异常矩阵的归约边界在该固定版本没有完整业务语义保护，可能得到NaN或归约异常。eval.py将非有限值保存为null、undefined_nan，异常保存error并使进程非零退出；有效0分不当错误。本课不替上游静默填造裁决。

## 指标和阶段证据怎样合用

[eval.py](eval.py)对实际upload_notes.json中的三个业务字段做显式文字投影，来源数组与Agent最后一句完成回执不在这两个SDK的评分范围。原始文件、最终回答、tool events仍完整保留，不能把投影分数说成整个回答或全部任务成功。

同一固定任务、query、参考版本和模型入口分别执行六个干预；每组新建工作目录和消息历史。文档与检索干预都留before/after；生成开关不改变检索。模型采样仍不保证相同，单次小型开发实验支持排查与提出假设，不支持严密的普遍因果结论或稳定性保证。下一步怎么改要由实际证据决定，不是看到低分就先改prompt。

## 初次评分与输入修正

初版reference未明确POST /upload，但声明生成时结合了问题，得到带端点的声明；最后NLI只看到reference，出现“端点未说明”的不支持裁决，基线NoiseSensitivity relevant因此为1。初版把JSON null直接写为None，模型也可能将它解释为系统根本没有设置，而非本次检索未知。

保留[初次评分](initial_evaluation.json)与[当时评分源码](https://github.com/lovits/learn-agent-evaluation/blob/main/lessons/e07_failure_diagnosis/initial_eval.py.txt)，后者哈希与初次报告核对一致。修正版reference逐句写明接口，投影把null明确表达成检索证据范围内未知；原始六组Agent记录、资料和产物没有修改，也没有重跑Agent。这是两项评分输入修正，不声称只改变一个因素的效果估计；主实验六组仍按同一修订协议再评。不为追求预设分数继续改SDK提示词或裁决。
