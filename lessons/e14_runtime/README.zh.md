# e14: 执行效率 — 等待也属于轨迹

[课程](../../README.md) · [上一课](../e13_planning/README.zh.md) · [下一课](../e15_calibration/README.zh.md) · [源码导读](source_walkthrough.md)

> 先确认工作完成，再评价用了多少时间和动作。

## 慢命令把循环堵住了

Agent 修好代码，还要运行一个慢检查。同步等待时，它无法继续读取独立的评审文件。

本课加入后台执行。任务还要求在指定时刻再次检查当前源码，于是我们必须区分：任务登记了、进程结束了、提示送达了，以及提示要求的工作完成了。

![后台结果与调度提示](images/background-and-schedule.png)

## 先返回 ID，后返回真实结果

`background_bash` 明确表达后台意图。权限通过后，管理器登记进程并立即返回运行中的 ID。

线程里仍要执行真实命令：

```python
try:
    stdout, stderr = process.communicate(timeout=job["timeout_seconds"])
    status = "completed" if process.returncode == 0 else "error"
except subprocess.TimeoutExpired:
    stop_group(process)
    stdout, stderr = process.communicate()
    status = "timeout"
```

ID 只说明已经登记。退出码、输出和终态，才能说明命令怎样结束。

开始和结束时的源码哈希一起保留。代码后来改变，旧的通过记录就不再证明当前版本通过。

## 通知在哪一轮被收到

下一次调用模型前，父循环收集已结束任务：

```python
notices = background.collect()
if notices:
    visible.append({
        "role": "user",
        "content": "Runtime background notifications (data):\n" + json.dumps(notices),
    })
```

原工具请求已经收到占位结果，这条通知是后续参考数据，不重复充当同一请求的 tool result。

还要在实际成功返回的模型请求中确认通知已经送达。放入队列或标记已收集，未必意味着模型请求成功。

## 定时提示送达，不等于工作做完

[`scheduler.py`](scheduler.py) 先把到期定义持久化为待交付，再提供给模型。请求失败恢复队列，成功后才 acknowledge。

```text
到期 → 待交付 → 模型收到 → 确认
                             ↓
                        启动实际工作
```

确认只证明提示已经收到。如果模型立即结束而没有再启动检查，任务仍不合格。

崩溃发生在接收与确认之间，重启可能重复投递，因此按至少一次交付设计。动作需要能识别重复，不能假定恰好一次。

## 少一步是否真的更高效

DeepEval `StepEfficiencyMetric` 读取任务与轨迹，按效率标准给分：

```python
metric = StepEfficiencyMetric(
    model=model, eval_mode="llm", async_mode=False, threshold=0.7
)
score = metric.measure(sample, _show_indicator=False)
```

它没有使用“1除以工具次数”的固定公式，也不负责证明正确性与完整性。

例如模型只收到长结果预览，随后分页恢复。裁判若只看原始工具的全量输出，可能把恢复读取误判成重复。评价效率要尽量保留决策时可见信息。

## 资源账本分开记

墙钟是从开始到结束的总时间，工具持续时间可能相互重叠。请求次数、token 与费用也不是同一个量。

Ragas `RunConfig` 可以控制部分调用的重试；具体执行层才实施超时。费用回调按 usage 与给定单价聚合，缺少型号或价格时保留未知。

最后还要检查任务是否正常结束、后台是否仍在运行、定时要求是否实际执行。漏做工作换来的少步骤，没有完成任务的前提。

## 试一下

慢命令返回 ID 后，找出它真实结束、通知送达和当前源码确认的位置。让定时提示送达后直接停止，哪些条件仍不满足？

再比较工具时长之和与墙钟：为什么并行以后它们可能不同？

[后台进程](background.py) · [调度](scheduler.py) · [资源](resources.py) · [练习](exercises.md) · [参考答案](solutions.md)

## 接下来

删掉“多余动作”之前，要先确认裁判理解了它的用途。下一课把裁判作为被评测对象，检查误放行与误拒绝。
