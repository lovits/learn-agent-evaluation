# 第7课实测记录

## 先沿三层证据排查

六组都在Docker中真实运行Agent循环，使用相同任务、固定有效query和课程合成v1合同。每组新建工作目录，读取挂载知识库的两份课用资料并在临时副本上做实验；原始挂载文档哈希未改变。生成故障由宿主机指令开关引入，不手改模型产物。

| 组 | 可用资料有limits | 检索before有limits | 交给模型after有limits | 实际max_bytes | 观察性定位 |
|---|---|---|---|---|---|
| baseline | 有 | 有 | 有 | 1048576 | no_observed_task_failure |
| drop_doc | 无 | 无 | 无 | None | knowledge_gap |
| drop_hit | 有 | 有 | 无 | None | retrieval_gap |
| add_old | 有 | 有 | 有 | 1048576 | no_observed_task_failure |
| add_noise | 有 | 有 | 有 | 1048576 | no_observed_task_failure |
| bad_prompt | 有 | 有 | 有 | 524288 | generation_mismatch_requires_review |

drop_doc与drop_hit都诚实填写了null。它们造成相同的末端缺项，但可用资料与检索before不同，故不能只看答案猜故障。add_old和add_noise本次没有观察到业务字段错误，不能写成噪声必然导致失败，也不证明永远免疫。bad_prompt资料齐全却写524288，说明需要排查生成指令与采用标准。

Agent共25次真实模型请求、19次工具请求，其中18次ok、1次error。drop_hit尝试换query，被固定查询检查拒绝；之后按现有证据写null。这个拒绝留在events中，不伪装成所有工具调用成功，也不计成SDK评分错误。六组均正常结束并写出有效JSON，只有三组的全部业务字段符合完整合同；“运行完成”不等于“内容全部正确”。

## 两轮裁判分别保留

初轮reference没有明确端点，声明抽取结合问题添加POST /upload，末次NLI却只看到reference，因端点缺失把正确基线判成不支持。初轮还将null直接投影为None，可能被解释为系统没有限制。原始初轮结果与当时评分源码已保存，源码哈希核对一致。

修订协议补全reference中的端点，并把null明确表达成“本次检索证据未知”。没有修改Agent产物、轨迹、原始资料或六组故障；仅重新评分。这同时修正了两处输入表达，不当成单因素性能改进估计。

| 组 | 上下文相关性v2 | Noise relevant v2 | 同矩阵irrelevant v2 |
|---|---:|---:|---:|
| baseline | 1 | 0 | 0 |
| drop_doc | 1 | 0.8 | 0 |
| drop_hit | 1 | 0.8 | 0 |
| add_old | 0.7143 | 0 | 0 |
| add_noise | 0.7143 | 0 | 0 |
| bad_prompt | 1 | 0 | 0 |

上下文相关性越高越好，NoiseSensitivity越低越好；分母和任务含义不同，不直接平均。bad_prompt的两个Noise模式为0，但文件限额仍错：该错误没有被任一原始context支持，因此指标没有把它算成从这些context引入的噪声。缺项和未知声明还需结合实际矩阵与业务字段核对。

初轮54次、修订轮54次真实裁判请求，两轮SDK运行错误均0；教材生成另计。irrelevant对同组原生矩阵重聚合，没有额外模型请求。两个SDK评分对象仅是文件中三个业务字段的显式文字投影，不评价sources与最后回执，不扩大成整体Agent成功率。

## 可核对材料

[真实Agent记录](agent_report.json)、[初轮评分](initial_evaluation.json)、[初轮实现](https://github.com/lovits/learn-agent-evaluation/blob/main/lessons/e07_failure_diagnosis/initial_eval.py.txt)、[修订评分](example_report.json)、[源码导读](source_walkthrough.md)。真实轨迹、文件原文、有效和被拒绝的query、支持关系矩阵、原始prompt/响应与usage均保留。模型确切标识未报告时不补造。

tests/test_e07.py中的三声明矩阵是构造手算夹具，两个模式各1/3，用于说明重叠排除与分母，不冒充真实Agent实测。模型采样没有固定种子，单次小型开发实验用于排查与提出假设，不能证明普遍因果或稳定可靠性。
