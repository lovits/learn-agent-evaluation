# s07 参考答案

## 1. mixed 的手算

三条预设声明：yes、borderline、no。DeepEval 默认通过前两条，2/3；
开启惩罚歧义后只通过 yes，1/3。Ragas 的预设 verdict 为1、0、0，1/3。
这些数字证明聚合契约，不证明真实模型的拆分/判断也一定如此。

## 2. 歧义策略与 strict_mode

惩罚歧义决定分子；strict_mode 对最终分数施加全通过门槛，SDK 会将阈值设为1。
本课第二列只启用了 penalize_ambiguous_claims，没有开启 strict_mode。

## 3. 新证据

知识库变动后旧 fixture 的 hash 校验失败，replay 应明确报错。这避免“证据已经变了，
裁判还在背旧答案”。Live 使用当前文本：若能从新规则推断运费声明，应判 supported，
但实际结果须检查抽取、verdict 和理由。不得只更新 hash、沿用旧教学判定。

## 4. 空声明

DeepEval 聚合的 empty_score 默认为1；Ragas 对空 statements/verdicts 返回NaN，
项目将其序列化为null并记录未评分原因。没有事实声明的回答可能仍然答非所问，
要另测 relevancy、completeness 或适当拒答。回放结果不是模型对“你好！”的真实判断。

## 5. 错误知识库

Faithfulness只检查回答与给定上下文之间的支持关系。若上下文本身错误，忠实回答
也可能高分；要用可信业务规则、人工 reference、版本/时效检查等独立证据检查正确性。
