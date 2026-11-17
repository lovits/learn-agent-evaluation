# e14 源码导读：异步状态怎样成为评测证据

[教材](README.zh.md) · [运行时](code.py) · [后台](background.py) · [调度](scheduler.py)

## 后台生命周期

上游 [s11](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s11_background_tasks/code.py) 由显式 `run_in_background=True` 启动后台路径。本课采用单独工具，先检查权限和命令，再启动线程与真实进程。

`BackgroundManager` 保存 running、completed/error/timeout，收集完成队列只通知一次。输出截断需要标记，关闭时清理进程组并等待线程。进程组管理不等于完整隔离，也不能在进程崩溃后复活原进程。

initial/final 源码哈希与当前文件一致，才支持本次执行对应当前代码的有限判断。测试期间仍应避免并发修改被测源码。

## 调度的持久状态

上游 [s12](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s12_cron_scheduler/code.py) 与本课 [cron.py](cron.py) 使用五段 cron。日期与星期同时受限时采用或语义，其他字段继续匹配。

`poll` 持久化 pending 与分钟标记，`take` 提供待交付，失败时 `restore`，收到响应后 `acknowledge`。写盘先临时文件再 replace，失败回滚状态；损坏记录可见报错。

重复交付窗口与停机错过分钟不同：本课恢复 pending，但不补发停机期间每一分钟。受控时钟只用于明确推进场景。

## DeepEval StepEfficiency

[文档](https://deepeval.com/docs/metrics-step-efficiency) · [实现](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/step_efficiency/step_efficiency.py)

LLM 路径为 `prepare_measure → 提取 Task → 效率 prompt → EfficiencyVerdict(score,reason)`，没有按固定工具次数公式计算。strict mode 再按阈值处理，外层校验有限分。

模板明确排除正确性与完整性。必须另行检查结果。原始 span 的全量返回与模型实际收到的预览也要区分，否则恢复上下文会被误当浪费。

## Ragas 重试的层次

[RunConfig 说明](https://docs.ragas.io/en/stable/howtos/customizations/run_config/) · [实现](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/run_config.py)

固定 `add_retry/add_async_retry` 通过 tenacity 的 `stop_after_attempt(max_retries)` 限制总尝试次数，包含第一次。装饰器没有读取 timeout 来中断函数；超时要由实际客户端或执行器处理。

本地 seed 也不保证外部模型确定。现代 collections 的自定义传输需按自己真实实现的重试与超时解释。

## 费用从 usage 计算

[费用说明](https://docs.ragas.io/en/stable/howtos/customizations/metrics/_cost/) · [cost.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/cost.py)

解析器把模型返回转成 `TokenUsage`，回调按模型聚合，再乘调用者提供的输入与输出单价。多模型价格覆盖、缺失 usage 和空记录都需处理。

`resources.py` 分开记录应用、支持与裁判调用。缓存输入不再次叠加，工具时间之和不当成墙钟，缺价格不写0费用。

## 最后检查状态闭合

`eval.py` 读实际文件、原生后台记录和调度收据，核对正常停止、通知送达、到期后的实际执行及当前哈希。清理仍在工作的进程，只能结束资源，不能把提前停止改成任务成功。
