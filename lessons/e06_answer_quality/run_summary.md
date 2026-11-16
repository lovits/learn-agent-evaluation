# 第6课实测摘要

以下保留首次制作时的历史实验及后续注明的修订；本轮教材重写没有重新执行这些模型实验。

数字用于检查原理，本课不做框架排名。八条回答是明确标注的构造教学样例，第九条是第4课真实Agent的原始记录；以下分数均来自Docker里的原生SDK实际调用，没有新增Agent执行。

| 样本 | DeepEval相关性 | Ragas事实F1 | Ragas正确性[1,0] | GEval业务政策 |
|---|---:|---:|---:|---:|
| complete_v2 | 1 | 1 | 1 | 1 |
| relevant_wrong | 1 | 0.57 | 0.6667 | 0.7 |
| partial | 1 | 0 | 0.5 | 0.4 |
| off_topic | 0 | 0 | 0 | 0 |
| stale_v1 | 1 | 0.67 | 0.3333 | 0.7 |
| appropriate_refusal | 1 | 1 | 1 | 1 |
| invented_retry | 1 | 0 | 0 | 0 |
| unnecessary_refusal | 0 | 0 | 0 | 0 |
| recorded_v1 | 1 | 0.73 | 1 | 1 |

## 从分歧回到原理

- relevant_wrong相关性为1，却报错限额。FactualCorrectness为0.57而AnswerCorrectness事实版为2/3，两者拆解和计数不同。前者反向把“超过2097152即413”也判为未覆盖，因为回答错误地把限额放到4194304。
- partial的人工设计是“认证正确但缺两项”，不能把这个预期伪装成实测P=1。FactualCorrectness原生F1实际为0：reference首句只写Use the X-Project-Token header，没有说authentication，正向NLI因此把“用于认证”判为0。AnswerCorrectness生成reference声明时还拿到问题，补出了认证语境，得到TP=1、FN=2、F1=0.5。GEval说明缺限额与状态码，得0.4。
- off_topic的健康接口事实在合成v2_config中为真，但没有回答上传问题，也没有被任务reference覆盖。FP表示相对reference不支持，不能自动宣称外部虚假。
- stale_v1相对当次旧文档的DeepEval Faithfulness实测1，相对当前合成v2 reference的事实F1为0.67。当前任务取错版本与当年任务答对要分开。
- appropriate_refusal与invented_retry的相关性均为1，业务政策分别为1与0。相关性不足以决定拒答是否合理；unnecessary_refusal在可回答合同下得0。
- recorded_v1保留当时的v1标准。FactualCorrectness把来源路径拆为独立声明而参考未列路径，得0.73；AnswerCorrectness把来源与内容合为复合声明并接受，得1。两个拆解不是同一分母，不能据此宣布哪个更准。

## 只澄清reference的一句补测

同一partial回答，只将首句改为“For authentication, use the X-Project-Token header.”。原始主报告不改写。独立补测原生FactualCorrectness F1从0到0.5，实际4次请求；其余条件保持不变。它展示参考措辞与输入语境的影响，单次对照不证明普遍稳定性。

[原始主报告](example_report.json)、[补测报告](reference_repair_report.json)、[补测脚本](../../tools/e06_reference_repair.py)保留逐阶段结果及请求。先跑主实验，再在Docker执行 `python tools/e06_reference_repair.py`。

## 模式与验收

主实验93次、补测4次真实裁判请求，最终指标运行错误0。教材生成另计。DeepEval相关性显式llm模式；Ragas FactualCorrectness原生仅f1，P/R对同组裁决重聚合；AnswerCorrectness真实运行权重[1,0]，没有embedding模型调用。

人工计数TP=1、FP=0、FN=2得到F1=0.5、F2=5/13；人工向量余弦0.8，预设事实分0.5和相似度0.8默认混合0.575。这些在报告calculation_demo内标成constructed，不是embedding实测。Response Relevancy和SemanticSimilarity保留原理与源码分析，未运行它们的embedding链路。

本地与Docker断网65项测试通过，覆盖原生边界、三种FactualCorrectness模式及计数口径。SDK已有第3课DAG弃用提示另计，不影响本课运行。
