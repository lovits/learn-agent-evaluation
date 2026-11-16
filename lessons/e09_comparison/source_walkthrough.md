# 第9课源码导读：同一任务，两个版本

本课复用第4课已经可运行的循环、权限和文件工具，只在检索分发处改变返回数量。数据是明确编写的公开合成任务，没有将第8课尚待人工审核的原生候选直接升级为正式测试集。

## 文档与固定实现

[DeepEval改进教程](https://deepeval.com/tutorials/rag-qa-agent/improvement)把检索配置和生成提示词作为可迭代因素；[参数优化指南](https://deepeval.com/guides/guides-optimizing-hyperparameters)说明将输出与配置关联。本课固定其他代码与合同，仅比较k=1和k=2。任务成功由实际文件检查给出，相关性分数不能代替它。

固定DeepEval提交`34db63dd005ebc9a905c8ef4741ae0687c93c14c`的[evaluate](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/evaluate/evaluate.py)先校验输入，再按AsyncConfig选择异步或同步执行，最后把hyperparameters处理到test_run。在线示例有使用单数hyperparameter的片段，固定实现签名为复数hyperparameters；实际调用应以使用版本为准。这个元数据功能不会自动保证样本配对，也不会自动给出bootstrap区间。

本课实际使用原生LLMTestCase保存文件文本、参考、检索上下文和metadata，再保留完整原生序列化结果；没有调用DeepEval.evaluate，也没有把本课规则成绩写成DeepEval原生语义指标分数。早期预运行把metadata误写成additional_metadata，字段被忽略；已停止该未完成运行，修正后再进行正式实验，并增加经过真实循环的适配测试。

[Ragas实验概念](https://docs.ragas.io/en/stable/concepts/experimentation/)介绍数据、应用与评分的组合。本课实际运行固定提交`8c63f10d500c44efbf24fdb9e2920de2104c321c`的[experiment装饰器](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/experiment.py)，不手写一个同名仿制器。

## 原生实验编排并不等于统计比较

experiment返回ExperimentWrapper；__call__按函数类型调用，arun对每行创建任务并按asyncio.as_completed收集结果。结果到达顺序不能当作原数据行顺序，必须保存case_id、k和repeat后再配对。

固定实现对单项异常打印警告并继续，返回None的行也不会加入结果。若直接对剩余行求均值，失败任务可能悄悄从分母消失。本课每次原生arun只运行一行，并检查结果恰好一行；遗漏立即中止不完整比较。每完成一条就另外保存partial报告，以免进程中断后只剩最后一个均值。

使用原生[Dataset](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/dataset.py)和[InMemoryBackend](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/backends/inmemory.py)。DataTable.save根据类型调用save_experiment；本课选择内存后端，保存是深复制到该实例内，不会自动生成CSV。本课自己的JSON写入才负责跨进程持久化。教程中使用的文件后端示例不能直接套作本课实际行为。

## 控制什么，记录什么

两个版本的query、任务、初始文件、知识库文本、模型入口、提示词、最大循环步数和判分函数相同；变化只有search的limit。每个任务、每个版本真实执行两次，顺序为1→2、2→1，以分散固定先后顺序的影响。模型抽样种子未固定，不能说已经消除随机性；宿主机负载也会影响耗时。

开发任务使用上传接口族，留出任务使用另一套明确编写的归档接口族。两个题族不跨集。每族都有单跳限额题和需要认证、限额、超限状态的组合题。它们在仓库公开，所以只是协议演示，不能当作生产盲测或代表性用户样本。

开发阶段结束后choose只读取开发结果：任务成功率差至少0.1，且已观察分层没有退化时选择k=2，否则保留k=1。相等时偏向基线。决定连同代码、数据、文档哈希一起保存；holdout入口先比对manifest，发生变化就拒绝沿用旧决定。留出结果不会再次进入choose。

## 从重复到配对差值

先在同一个case_id和k内部求两次任务成功的均值，再计算candidate-baseline。一次执行的业务数值1048576不是这里的统计样本数；一个任务多跑几次，也不会自动变成多个独立任务。

paired_rows要求两个版本的重复编号相同，并拒绝重复编号。summarize保留逐题差值、单跳/多跳分层、失败率，以及耗时和应用请求数差值。总体均值可能掩盖一种任务的退化，因此choose先检查分层，而不仅比较总分。

## 区间的重采样单位

[配对bootstrap说明](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html)中，配对样本使用相同的重采样索引。本课用少量标准库代码展开percentile方法：先对每族的任务差值求平均，再对族有放回抽样，保存2.5%与97.5%位置。它没有调用SciPy，也不是BCa算法。本课每族题数相同，族均值再平均与逐题均值一致；题数不等时须先约定权重，不能把这个区间随意配给另一个按题加权的均值。

同族题可能共享文档、参考模板和失败原因，因此不能把它们全当独立行重采样。每个单独split只有一个族，本课返回空区间并解释原因；合并也只有两个公开合成族，区间仅示范方法。重采样2000次增加的是数值模拟精度，不增加真实样本量。区间包含0时证据不足以排除无变化；不含0也不能补救选择偏差或不具代表性的数据。95%是适当条件下重复抽样程序的覆盖目标，不是给当前固定区间分配真值概率；本课小型合成样本也不提供经校准的覆盖保证。

## 实际状态、裁判重复与成本

inspect从真实answer.json核对键、字段值及类型、来源ID；独立verifier在Agent结束后只读重查文件，并比对原记录。完成回执不能替代文件事实。passed还要求循环正常结束；文件检查通过与循环停止分别保留。

可选的repeat_judge只对两个固定输出各评分两次；prompt、实际响应与分歧保留，不重新运行Agent，不进入版本选择，也不生成独立人工标签。重复裁判与重复应用回答是两种不同不确定性。两次恰好一致不能证明裁判可靠；更完整校准在第15课。

应用事件保存宿主机返回的每次usage；统计页从这些原始字段汇总已报告输入、输出与缓存输入计数，报告中的token_count为空表示runner未预先聚合。不能把缓存计数再简单叠加成输入总数，也不能从这些计数推定实际费用。型号和单价不明确时费用保留未知。裁判调用、应用调用和教材生成分别记账；耗时是真实墙钟时间，比较时需考虑模型和系统负载。

完整入口见[运行代码](code.py)、[配对统计](statistics.py)、[分析与独立验收](eval.py)。实际结果与局限见[运行摘要](run_summary.md)。
