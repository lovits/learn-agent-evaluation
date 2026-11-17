# e11: 任务完成度 — 谁来确认代码修好了

[课程](../../README.md) · [上一课](../e10_tool_evaluation/README.zh.md) · [下一课](../e12_conversation/README.zh.md) · [源码导读](source_walkthrough.md)

> 完成声明要回到目标状态上检查。

## 公开例子都通过，为什么还不够

运费规则是前1000克600分，之后每开始1000克增加200分。初始代码：

```python
extra = max(0, (weight_grams - 1000) // 1000)
```

1001克被整除成0个额外档位，费用仍为600，正确应为800。

任务还要求重量与加急参数的类型正确、边界合理、原测试保留。只修几个例子，或者删除测试后报告成功，都没有满足完整要求。

## 在循环停止处加一次检查

模型不再调用工具时，外层先读取文件，运行公开行为检查。通过以后只进入 `ready_for_external_verification`；失败则带反馈继续同一任务。

```text
模型停止 → 公开检查
             ├─ 失败：反馈 → 继续循环
             └─ 通过：冻结产物 → 独立检查
```

[`GoalState.review`](code.py) 只根据检查结果更新状态：

```python
elif evidence["status"] != "scored":
    self.status = "review_error"
elif evidence["passed"]:
    self.status = "ready_for_external_verification"
elif self.reviews >= max_turns:
    self.status = "limit"
else:
    self.status = "blocked"
```

公开检查可以帮助修复；独立保留条件用于后续评价，不回流给本次修复。预算耗尽和检查异常也各自保留状态。

## 检查行为，同时保护要求

[`probe`](verify.py) 读取实际源码，交给受限执行器运行输入，比较返回值、精确类型与异常类型。原测试则按内容哈希检查。

行为正确但测试被删除，仍违反用户要求。反过来，测试文件保留也不保证函数正确。所有必需条件都要检查。

执行器只支持事先声明的纯 Python 子集与有限输入。超出适用范围时记为未评分，不能塞成普通0分。

## 把外部事实写成指标

DeepEval 自定义指标继承 `BaseMetric`：

```python
class ExternalCompletionMetric(BaseMetric):
    def __init__(self):
        self.threshold, self.async_mode = 1.0, False

    def measure(self, test_case, **kwargs):
        self.score, self.error, self.reason = None, None, None
        data = (test_case.metadata or {})["external_evidence"]
        self.score = evidence_score(data)
        return self.score
```

片段省略错误记录和异步入口，完整实现见 [`metrics.py`](metrics.py)。`evidence_score` 校验非空布尔检查，全部为真得1，任一为假得0。

Ragas 的自定义类覆盖 `ascore`，返回 `MetricResult`。框架提供接口，业务代码定义事实来源与判分规则。

## 语义完成度看到了什么

DeepEval `TaskCompletionMetric` 从轨迹抽取任务与结果，再判断目标是否完成。Ragas `AgentGoalAccuracy` 先抽取目标和终态，再用给定目标或推断目标比较。

这些指标帮助理解轨迹，但它们无法凭一句“修好了”直接读取真实文件。外部检查结果作为评分证据加入时，也应明确时间与来源。

本课将规则与裁判保留为两项，组合政策取较小值：

```python
return {"status": "scored", "score": min(rule_score, judge_score)}
```

缺少任一有效分则保持未评分。必需业务条件已经失败时，语义高分不能将它抵消。

## 试一下

准备三种代码状态：修好公式但漏类型检查、公式正确却删掉测试、满足行为与保护要求。分别说明外部规则和语义裁判应接收什么证据。

再看一条只有“完成了”的回答：在没有文件证据前，你最多能确定什么？

[停止审查](code.py) · [行为检查](verify.py) · [自定义指标](metrics.py) · [练习](exercises.md) · [参考答案](solutions.md)

## 接下来

反馈不断接回对话，消息会越来越长。下一课检查压缩与记忆以后，跨轮要求是否仍然有效。
