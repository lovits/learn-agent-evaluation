# e09 源码导读：运行编排与比较规则

[教材](README.zh.md) · [运行](code.py) · [统计](statistics.py) · [分析](eval.py)

## 变化只发生在检索分发处

`limited_dispatch` 检查固定查询，在相同文档副本上以 `limit=k` 搜索，其余请求仍交给前课。`execute_trial` 运行真实 Agent，然后读取 `answer.json`，保留逐条判定。

manifest 保存实际源码、任务和文档哈希。开发阶段 `choose` 只读取开发结果，冻结后才能进入 holdout。课程公开任务用于理解协议，正式比较还要另备代表性任务。

## DeepEval：把配置与输出关联

[参数优化指南](https://deepeval.com/guides/guides-optimizing-hyperparameters) · [evaluate.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/evaluate/evaluate.py)

批量入口校验输入、按配置选择同步或异步执行，再把 `hyperparameters` 关联到运行。它不会自动检查两个实验的样本配对，也不会替调用者计算统计区间。

本课使用 `LLMTestCase.metadata` 保存版本和运行信息，文件合同给出规则分。源码阅读中的批量入口与本课的直接调用应按接口区分。

## Ragas：按完成顺序收集结果

[实验概念](https://docs.ragas.io/en/stable/concepts/experimentation/) · [experiment.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/experiment.py)

`@experiment` 返回 `ExperimentWrapper`；`arun` 为数据行创建任务，通过 `asyncio.as_completed` 收集结果。因此每行必须有 `case_id/k/repeat`，不能依靠列表位置配对。

固定实现可能警告后跳过异常行或 None 返回值。本课检查运行结果完整性，遗漏时停止比较，避免分母缩小。

[Dataset](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/dataset.py) 和 [InMemoryBackend](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/backends/inmemory.py)负责数据载体。内存后端的保存不等于跨进程文件持久化，JSON 写入由本课另行完成。

## 配对差值怎样形成

`paired_rows` 先检查两个版本的重复编号相同且没有重复，再求任务内部均值，最后计算候选减基线。`summarize` 保留逐题差值、分层和代价。

一次执行中的业务字节数与统计样本量没有关系。同题重复也不能当成多个独立用户需求。

## 为什么按题族重采样

`family_bootstrap` 使用标准库实现 percentile 方法，先求族均值，再抽族。题族只有一个时返回空区间；族数量少时，区间只描述已有材料，无法保证未知任务的表现。

它与[配对 bootstrap](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html)使用同一索引保持配对的思想一致，但没有调用 SciPy，也不是 BCa。族大小不同时，应先明确按族还是按题加权。

`repeat_judge` 对固定回答重复评分，不参与版本选择。应用与裁判的延迟、请求和 usage 也分别记账。
