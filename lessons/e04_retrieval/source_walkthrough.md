# 第4课源码导读

这一课把项目资料接到编程Agent上。只增加search_knowledge；第2课的五种工具与权限继续复用，循环、父子span和hook在本课保留可读快照。没有向量库、重排模型、记忆或新Agent协作。

## 挂载与按需加载

[code.py](code.py)调用公共eval_course.knowledge.search：catalog从KNOWLEDGE_DIR读取Markdown/text，terms把英文分词、中文取相邻双字，按查询词交集数降序、路径升序打破平局，只返回前三篇。每篇文件就是一个证据单元，id用相对路径，sha256标识内容版本。路径解析拒绝越出目录的链接。每次查询重新读文件，所以换挂载或修改文本后不必重建镜像；这不是语义检索或通用中文分词。

源头是固定Learn Claude Code提交448c75bb596917ad196cc1fb7558f459c5c50fdd的[SkillLoader](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s07_skill_loading/code.py)。scan扫描*/SKILL.md、解析frontmatter并构建目录；catalog给摘要，load按名字返回全文。这里借用“需要时再把内容给模型”的组织方式，改成项目文档搜索。没有移植skill frontmatter、工具注册或执行指令。模型看到搜索结果，检索器在磁盘上仍须读取候选文件，二者要区分。

知识库只读挂载，工作目录可写，runs保存轨迹。独立verify.py断网读取真实upload_notes.txt，检查三个事实和来源路径，以及检索与工具轨迹。它不执行生成代码。这个教学镜像同时提供教材和例题答案，不能当严格防作弊的盲测环境。

## ID口径与排序口径

[eval.py](eval.py)的ranking先按ID保留第一次出现，避免重复命中虚增召回。precision的分母为去重后的返回数；recall的分母为标注相关ID数。

ap_retrieved把每个相关位置的P@i相加，再除以本次返回中相关项数，模拟本课两个框架Context Precision的聚合形式。ap_reference改用全部标注相关ID数，漏检会被扣分。两者不要同名。MRR只看首个相关项；二元NDCG使用1/log2(rank+1)折扣，理想排序长度取min(返回数,相关总数)。它们的目标不同。

两篇必要资料中只返回认证文档，ID precision=1、recall=0.5、ap_retrieved=1、ap_reference=0.5。把噪声从末尾移到开头时，precision/recall不变，ap_retrieved从1降到7/12，约0.5833。返回空集且已有非空标注时，这些规则分数约定为0；标注集合本身为空时抛错，不能把未知参考当满分。

## DeepEval：先判有用性，再聚合

固定提交34db63dd005ebc9a905c8ef4741ae0687c93c14c（4.3.4）。

- [Contextual Precision文档](https://deepeval.com/docs/metrics-contextual-precision)与[源码](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/contextual_precision/contextual_precision.py)：prepare_measure校验input、expected_output、retrieval_context；_generate_verdicts经模板和结构化schema对每个节点给yes/no和理由，_calculate_score对相关位置的累计precision求均值，分母为本次相关节点数，不是库中全部相关资料数。没有相关节点则0。
- [Contextual Recall文档](https://deepeval.com/docs/metrics-contextual-recall)与[源码](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/contextual_recall/contextual_recall.py)：同样依赖expected_output。模型判断参考答案的声明能否从检索资料归因，再按yes比例评分。因此分母是声明，而非文档。认证一条、限额一条、413一条，对应三条声明；只有认证时可能得到1/3，而ID召回是1/2。
- [Contextual Relevancy源码](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/contextual_relevancy/contextual_relevancy.py)：仅需input与retrieval_context，不要求参考答案。逐文档提取声明并判断与问题相关性，_calculate_score展平verdicts_list后求相关声明比例。它不是文档集合precision。precision/recall对象用verdicts，relevancy对象用嵌套verdicts_list；本课曾在保存时混用字段，已保留初次失败报告并修正。

measure和a_measure分别提供同步、异步入口。实验用同步DeepEval接口，每个情景独立实例；include_reason=False省去额外总结请求，逐项verdict理由仍保存。阈值0.7是教学约定，不是官方推荐的业务门槛。

## Ragas collections：参考答案与参考无关口径

固定提交8c63f10d500c44efbf24fdb9e2920de2104c321c（0.4.4）。

- [Context Precision文档](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_precision/)与[collections实现](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/context_precision/metric.py)：ContextPrecisionWithReference.ascore逐个把question、reference、context交给prompt和结构化ContextPrecisionOutput，收集0/1；_calculate_average_precision采用相关位置precision的和，分母cumsum+1e-10，因此接近1可能显示0.99999999995。
- 同文件ContextPrecisionWithoutReference把response替代reference，并非完全脱离答案的纯检索相关性。如果回答遗漏了事实，用回答反查上下文可能掩盖问题。本课实测WithReference；WithoutReference做源码对照，不声称已跑其模型实验。
- [Context Recall文档](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_recall/)与[collections实现](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/context_recall/metric.py)：ascore要求非空问题、reference和retrieved_contexts，把contexts合并后生成classifications，分数为attributed声明数/总声明数；无classifications返回NaN。本课有限数校验将非有限结果记为未评分，不保存成正常0分。

本课ModernJudge继承InstructorBaseRagasLLM，agenerate调用宿主机传输后按response_model校验JSON。没有把第3课legacy BaseRagasLLM直接塞进collections；接口与返回MetricResult.value均按固定版本执行。

## 实验边界与失败记录

一条真实Agent任务检验挂载、检索动作、产物与引用。good/late/missing/empty则是同一问题的受控检索扰动，不冒充四次Agent自然检索结果。原生SDK对前三种情景实测，empty只跑规则，明确记录skip，避免掩盖collections Recall拒绝空输入的差异。

参考不完整时，召回可能虚高。本课把标注缩成只有认证文档，返回认证会得ID recall=1，但依然答不出限额和413。评价reference的完整性，需要独立人工检查。

首次Agent入口误带第2课故障注入提示，产生无关Bash动作并被拒绝；清理提示后重跑。初次轨迹与提示、初次SDK保存错误均单独保留。正常报告与这些失败记录分开，不用人工标签覆盖模型verdict。score=null和error表示运行失败；score=0才是有效评分的不通过。
