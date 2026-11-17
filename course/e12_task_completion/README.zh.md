# e12: 说完成了，交付完成了吗？

[e11](../e11_tool_quality/README.zh.md) → `e12` → [e13](../../docs/curriculum.md#13-会话上下文与约束保持) → … → e16

> 从用户收到的结果，定义任务是否完成。

## 问题

Agent 要修复一个金额函数：每项单价乘数量，再求和。它写了文件，最后回复“已完成。”

但写入成功还不能说明金额算对。即使算对，也可能顺手清空输入列表，或者改了不允许修改的策略文件。第11课的调用匹配，只解释工具用得怎样；还需要检查实际交付。

## 解决方案

Agent 继续使用已有循环和工具。运行结束后，评分端读取文件，调用函数检查业务行为，再核对保护条件。

![完成声明、工具轨迹与实际产物分别保留](https://lovits.github.io/learn-agent-evaluation/diagrams/e12-delivery-flow.png)

可执行的条件交给自定义 DeepEval 指标，Task Completion 补充语义判断。两种结果各自保留。

![独立业务条件与语义完成度分别判断](https://lovits.github.io/learn-agent-evaluation/diagrams/e12-completion-flow.png)

## 工作原理

### 先把“修好”说具体

本课使用一个构造的订单任务。初始代码漏乘数量：

```python
def total_cents(items):
    return sum(item["unit_cents"] for item in items)
```

用户要求：金额以整数分计算，单价乘数量再求和；空订单返回0，允许零数量，不修改传入列表或字典，并保留 policy.txt。

一种正确写法是：

```python
def total_cents(items):
    return sum(item["unit_cents"] * item["quantity"] for item in items)
```

也可以用显式循环。只要任务没有限定实现，便不该用源码字符串相等来判断成功。

### 沿实际产物检查行为

[运行入口](code.py) 复用已有 run_case。构造条件都回复“已完成。”，但实际写入不同程序；`--live` 则由真实模型决定怎样修复。

```python
run = run_case(case, live=live)
evidence = inspect_delivery(workspace, case["files"]["policy.txt"])
```

[inspect_delivery](eval.py) 在独立子进程加载工作区的 billing.py。检查程序由评分端提供，不接受 Agent 自报的“检查通过”。

四组输入覆盖空订单、数量大于1的多项订单、另一组金额和零数量。例如这组构造输入的期望结果可以直接手算：

```text
200分 × 3 + 50分 × 1 = 650分
```

只检查这一组，永远返回650的程序也能通过。加入不同输入，才会暴露这种硬编码。

### 返回值正确，还要看副作用

下面的函数能够算出金额，却会清空调用方的列表：

```python
while items:
    item = items.pop()
    total += item["unit_cents"] * item["quantity"]
```

因此每组检查都保存调用前的副本，再检查返回值和输入：

```python
before = copy.deepcopy(items)
actual = module.total_cents(items)
checks[f"value_{index}"] = type(actual) is int and actual == expected
checks[f"input_unchanged_{index}"] = items == before
```

“金额正确”和“输入未变”是两个必要条件。漏掉后者，就会把破坏数据的实现收进去。

### 保护条件不能靠其他得分补偿

policy.txt 的参考内容来自任务夹具。检查器对比原始内容与实际文件的哈希，并核对检查前后是否保持一致。

金额算对、策略被改，仍然没有按要求交付。这些可执行条件组成程序契约，应取逻辑与：

```python
self.score = float(all(evidence["checks"].values()))
```

[DeliveryContract](eval.py) 继承 DeepEval BaseMetric，设置 score、reason、success。它没有把通过项目除以总项目；保护条件失败，不能用其他项目通过来补分。

这份程序契约检查行为与文件，用户要求的“说明修复内容”另由语义裁判核对。程序契约通过，不表示完整任务的每个要求都已覆盖。

检查成功且发现失败项，结果是有效0分。检查器没有产生有效证据，则保留评分错误和空分数。候选程序的语法错误可以被明确观察到，属于交付失败；它与检查系统自身损坏不同。

### Task Completion 判断它看到的结果

TaskCompletionMetric 在 LLM 模式下先抽取任务结果，再判断与目标的对齐程度：

```python
metric = TaskCompletionMetric(
    task=run["task"], model=model,
    eval_mode="llm", async_mode=False, threshold=1.0,
)
```

显式 task 固定比较目标。裁判仍需从输入中抽取 outcome，它不会自己打开工作区检查程序。

因此本课另组装一份评分样本：

```python
sample.actual_output = json.dumps({
    "agent_final_answer": run["final_answer"],
    "independent_observation": evidence,
}, ensure_ascii=False)
```

原始完成声明不变，独立观察明确标注来源，工具调用照常保留。这个复合 actual_output 是评测者提供的证据，不是 Agent 多说了一段话。

本课直接使用固定版本 measure 保留的无 trace 兼容路径。官方推荐完整 tracing；这里保存的 ToolCall 列表不等于 SDK 的 span 树，迁移方式与限制见[源码导读](source_walkthrough.md)。

语义分表示裁判理解的目标对齐程度，不是业务条件通过率。它可以帮助解释复杂自然语言目标；明确的保护条件失败，仍由程序契约判定，不能与语义高分平均后当作成功。

### 有参考与无参考，差别在目标从哪里来

Ragas AgentGoalAccuracyWithReference 从对话推断 end_state，再与给定 reference 比较；WithoutReference 还从对话推断 user_goal，再比较推断的目标与结果。两者最终给出二元判断，本课只读其原理与源码。

参考可以固定目标，却不能自动补齐实际状态。如果只有“已经下单”的回复、没有订单回执，裁判看到的仍是声明。业务能读取真实状态时，应把相应证据接进来。

### 通过检查的范围有多大

四组输入只能说明这四组情况。策略哈希一致，只说明观察时点字节一致，不能证明过程中没有改动后又恢复。更严格的行为要求需要更多输入、性质检查或完整写入审计。

检查器虽然另起进程并设置超时，仍在同一个教学容器中；它不构成恶意代码沙箱或防篡改证明。

## 本课变化

Agent 循环和工具不增加能力。只增加一个小金额任务、独立产物观察、全条件业务指标，以及原生 Task Completion 对照。完成声明、工具轨迹与评分证据分别保存。

## 试一下

```sh
python -m course.e12_task_completion.code
```

1. 比较 correct 与 claim_only：回复相同，为什么交付不同？
2. 看 hardcoded、mutates_input、policy_changed，分别指出失败的必要条件。
3. 对照 equivalent_loop 与求和写法，解释为何不比较完整源码。
4. 加 `--live --judge`，先读独立观察，再看裁判抽出的 outcome 是否遗漏条件。

[源码导读](source_walkthrough.md) · [练习](exercises.md) · [参考解释](solutions.md) · [样本与评测记录](assessment.md)

## 接下来

目标固定时，可以明确检查交付。用户下一轮改了要求，哪些旧约束仍然有效？下一课把任务放进会话，追踪当前目标与模型实际看到的上下文。
