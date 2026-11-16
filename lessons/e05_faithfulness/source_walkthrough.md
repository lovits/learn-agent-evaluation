# 第5课源码导读

本课只新增独立评测，Agent继续复用第4课。七条评测中五条是受控回答，一条改证据版本，一条使用第4课真实Agent的原始产物与当次search_knowledge返回的文档快照。重新调用裁判，不重新执行Agent；也不重新检索今天的知识库来替代旧证据。

## 输入与证据身份

Faithfulness检查回答相对给定证据的支持程度，不等于外部事实正确、切题、完整或任务完成。NLI可从蕴含、矛盾、信息不足理解，但两个SDK实际输出不一定是这三个标签。cases.jsonl的annotation是教学标注，不传给裁判充当答案。

[code.py](code.py)提供固定verdict的手算，以及按文档id/sha256组成的evidence_key。这里使用可信加载器产生的哈希元数据，不做防篡改证明。即使文件路径相同，内容哈希改变就拒绝复用旧标注；证据顺序也是身份的一部分。本课修改限额时同步计算文本新哈希，保留两个版本。

## DeepEval 4.3.4

固定提交34db63dd005ebc9a905c8ef4741ae0687c93c14c。[官方说明](https://deepeval.com/docs/metrics-faithfulness)与[faithfulness.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/faithfulness/faithfulness.py)可沿以下调用链读：

1. prepare_measure校验INPUT、ACTUAL_OUTPUT和RETRIEVAL_CONTEXT，不需要expected_output。
2. _generate_truths从检索材料抽取truths；_generate_claims从回答抽取claims。truths本身是模型整理结果，不是外部真值。抽取漏项会影响下一步判定。
3. _generate_verdicts把claims与truths交给模板，经结构化schema得到yes/no/borderline及reason。无claims时直接返回空列表。
4. _calculate_score调用[score_qag_verdicts](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/utils/qag.py)。默认passing为yes、borderline；penalize_ambiguous_claims=True时只计yes。分母为有效verdict数，空列表默认返回1；未知裁决可能在上游被归一化或丢弃，不能假定verdict数必然等于最初claim数。

本课不另调用模型来比较penalize开关，直接对同一组实际verdict重聚合。示例yes/borderline/no默认2/3，开启惩罚1/3。阈值0.7只是教学配置，strict_mode=False；strict_mode=True还会把低于阈值的分数压成0，不能混为同一参数。

同步measure依次抽取truths、claims、判定；异步a_measure会并发抽取前两项。实验使用同步入口、include_reason=False，省略额外总结调用，逐条reason仍保留。空声明1分只反映这个公式的空集约定，不代表回答完成任务。

## Ragas 0.4.4 collections

固定提交8c63f10d500c44efbf24fdb9e2920de2104c321c。[官方说明](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/)与[metric.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/faithfulness/metric.py)中：

- ascore先检查response、user_input、retrieved_contexts非空。
- _create_statements通过StatementGeneratorPrompt，用问题和回答生成原子statements。没有statements时返回MetricResult(value=NaN)。空字符串response则在更早阶段抛ValueError，二者不同。
- _create_verdicts拼接检索上下文，通过NLIStatementPrompt逐条给statement、reason与0/1 verdict。
- _compute_score计算支持数/判定数，空判定也返回NaN。它不沿用DeepEval默认borderline计通过的口径，也没有本课所谓三元标签输出。

CapturingJudge继承第4课ModernJudge，只记录SDK实际schema结果，不替换prompt或修改verdict。报告保留statements和NLI两阶段结构，便于和DeepEval的claims、truths、verdicts对照。Ragas实际拆出的声明数量可能与DeepEval不同，不能仅比较最终分数就断言谁更准。

## 正常零分、未定义和错误

JSON不能保存标准NaN。本课将原生NaN保存为score=null、status=undefined_nan，passed=null；调用失败则status=error并保存异常，进程非零退出；有效0分仍是正常评分。不能把这三种情况平均成一个0。控制样本“Thanks!”只意图没有事实，仍以模型实际拆解结果为准。

[eval.py](eval.py)保存原始prompt、返回文本、模型usage、阶段结果与证据哈希。未返回的确切型号和费用不编造。所有判断由真实裁判模型产生；手算函数只用于解释固定verdict，不能冒充SDK实测。

## 证据改版与真实产物再评

旧证据限额1048576，回答2097152应与旧证据冲突；新证据改成2097152后同一回答可获支持。这不说明服务端真实配置已经改变，新版本是受控实验材料。评价实际正确性还需要独立配置或reference，下一课继续处理。

对真实Agent只使用其原始upload_notes.txt内容及当次命中快照。原轨迹、source_run_id和源报告哈希保留；不把它算成新Agent运行。Faithfulness得分与第4课文件验收结果分别呈现。
