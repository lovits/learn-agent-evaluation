# e12: 任务完成度：说完成了，交付完成了吗？

[e11](../e11_tool_quality/README.zh.md) → `e12` → [e13](../e13_conversation/README.zh.md) → … → e16

> *“模型写完文件并回复‘已完成’，只能说明循环停了下来；任务是否交付，要靠独立检查产物行为和约束条件来确认。”*
>
> **评测层：任务完成度。** 用独立探针 `inspect_delivery` 和自定义 `DeliveryContract`（继承 `BaseMetric`）核验代码行为、副作用与不可篡改文件，再用 `TaskCompletionMetric` 补充语义目标与说明义务的判断。

## 问题

Agent 接到一个修复任务：修改 `billing.py` 里的 `total_cents(items)`，按每项 `unit_cents` 乘 `quantity` 求和，空订单返回 `0`，支持数量为 `0`，不得修改传入列表或字典，不得改动 `policy.txt`，完成后说明修复了什么。运行结束时，Agent 写了文件，最后回复“已完成。”

写入成功只说明工具没有报错，还不能保证金额计算正确。即使当前算对了金额，函数也可能用 `items.pop()` 清空了调用方的列表，或者顺手改写了不允许修改的 `policy.txt`。第 11 课的工具调用匹配能核对过程动作，而用户最终收到的是磁盘上的代码与文件状态，两者必须分别核验。

## 解决方案

继续复用第 11 课的 `run_case` 执行循环与具名文件工具，运行 [cases.jsonl](cases.jsonl) 中八组构造决策（加 `--live` 时再补充真实模型修复任务）。Agent 退出循环后，评分端由独立进程读取工作区里的 `billing.py` 和 `policy.txt`，实际运行四组订单输入并核对保护条件。

![完成声明、工具轨迹与实际产物分别保留](https://lovits.github.io/learn-agent-evaluation/diagrams/e12-delivery-flow.svg?v=9e0dcb543d86)

能写成确定性规则的行为与约束交给继承 `BaseMetric` 的自定义指标 `DeliveryContract`，包含开放式说明义务的整任务对齐度则交给 DeepEval 原生的 `TaskCompletionMetric`。两项结果分别落盘，不取平均。

![独立业务条件与语义完成度分别判断](https://lovits.github.io/learn-agent-evaluation/diagrams/e12-completion-flow.svg?v=526a1d6a53fe)

## 工作原理

### 把“修好”拆成可验证的行为与约束

初始的 `billing.py` 漏乘了数量：

```python
def total_cents(items):
    return sum(item["unit_cents"] for item in items)
```

一种简洁的修复写法是补上乘法：

```python
def total_cents(items):
    return sum(item["unit_cents"] * item["quantity"] for item in items)
```

用显式 `for` 循环累加 `row["quantity"] * row["unit_cents"]` 同样符合要求。只要任务没有限定实现语法，评分就不应该比较源码字符串是否相等，而应当从实际运行行为和约束出发。

### 用独立探针检查返回值与输入副作用

在 [code.py](code.py) 中，八组构造条件统一回复“已完成。”，各自通过真实工具往隔离工作区写入不同程序：

```python
run = run_case(case, live=live)
evidence = inspect_delivery(workspace, case["files"]["policy.txt"])
```

[inspect_delivery](eval.py) 先检查 `billing.py` 确实是落在工作区内部的常规文件（拦截缺失文件或越界符号链接），再用独立子进程（`python -I`，5 秒超时）执行评分端自带的 `PROBES` 脚本加载模块，不信任工作区里任何自报检查。四组探针分别覆盖空订单、含数量大于 `1` 的多商品订单（`200 * 3 + 50 * 1 = 650`）、另一组单品订单（`175 * 2 = 350`）以及零数量订单（`90 * 0 = 0`）。加入不同金额的输入，可以直接暴露只针对演示样例返回 `650` 的硬编码实现。

此外，有些实现虽然算出正确总额，却会顺手破坏调用方数据，例如：

```python
while items:
    item = items.pop()
    total += item["unit_cents"] * item["quantity"]
```

因此每轮探针调用前都会深拷贝输入，再同时核对返回值类型、金额与输入不变性：

```python
before = copy.deepcopy(items)
actual = module.total_cents(items)
checks[f"value_{index}"] = type(actual) is int and actual == expected
checks[f"input_unchanged_{index}"] = items == before
```

只有类型是 `int`、数值相等且传入数据原封不动，这一组探针才记为通过。

### 用 DeliveryContract 把保护条件写成逻辑与

任务同时要求不得修改 `policy.txt`。`inspect_delivery` 将夹具提供的原始策略文本哈希、调用探针前的磁盘哈希以及调用探针后的磁盘哈希三者比对，确保 `policy_unchanged` 成立。

在业务交付中，功能做对却破坏了保护文件，或者算对金额却篡改了输入，都属于未完成交付。为此，[DeliveryContract](eval.py) 继承 DeepEval 的 `BaseMetric`，把所有可执行检查项作逻辑与：

```python
self.score = float(all(evidence["checks"].values()))
```

`policy_changed` 算对了所有订单金额，但因为改写了 `policy.txt` 依然得 `0.0` 分，避免“金额得分高”掩盖违背硬约束。这里还要区分两种零分与评分错误：`syntax_error` 样本加载报错（`loaded=False`）或候选执行超时（`probe_completed=False`），均属于明确观察到的交付失败，记为有效 `0.0` 分；若探针本身没有输出有效 JSON 或结构校验失败，`inspect_delivery` 返回 `status="error"`，`DeliveryContract` 随之抛出异常，由 `score()` 记为 `status="error"` 与 `score=None`，不让检查故障冒充业务分数。`DeliveryContract` 只负责代码行为与保护文件，任务要求中的“完成后说明修复了什么”留给语义指标核对。

### 用 TaskCompletionMetric 对比有无独立观察

[judge_completion](eval.py) 调用 DeepEval 原生的 `TaskCompletionMetric` 评估任务目标对齐度：

```python
metric = TaskCompletionMetric(
    task=run["task"], model=model,
    eval_mode="llm", async_mode=False, threshold=1.0,
)
```

在 `llm` 模式下，指标分两步执行：先从输入、输出与工具调用记录抽取 `task` 和 `outcome`（显式传入 `task=run["task"]` 后，比较目标锁定为原始任务，不会随模型猜测漂移），再由裁判对比 `task` 与抽出的 `outcome`，打出 `0` 到 `1` 的对齐分。

裁判默认看不到磁盘文件里的代码运行结果，因此 [evidence_sample](eval.py) 把独立观察一并装进 `actual_output`：

```python
sample.actual_output = json.dumps({
    "agent_final_answer": run["final_answer"],
    "independent_observation": evidence,
}, ensure_ascii=False)
```

这样既原样保留了模型回复的 `"已完成。"` 和真实 `tools_called`，又把客观探针证据送进了裁判视野。对比就能看出差异：`claim_only` 在没有独立观察时得 `0.0`，`correct` 在没有独立观察时仅凭回复和工具写入就拿了 `1.0`；加上 `independent_observation` 后，`correct` 与 `equivalent_loop` 因回复只有 `"已完成。"` 缺少修复说明各得 `0.95`，而 `mutates_input`（`0.55`）与 `policy_changed`（`0.65`）虽然拿到中间分，理由里都清楚指出了对应违约项。语义分适合衡量说明义务等开放要求，明确违反硬约束的交付仍由 `DeliveryContract` 一票否决。

本课为复用已落盘的 `ToolCall` 记录，直接走固定版本 `TaskCompletionMetric` 对无 `_trace_dict` 样本保留的兼容路径；迁移到全链路线上追踪时，应按 DeepEval 官方推荐通过 `observe` 收集完整的 span 树。

### 独立检查的范围与隔离边界

四组探针验证了这四组边界输入下的行为，要覆盖更复杂的订单分布仍需扩充输入族或性质测试；`policy.txt` 的哈希一致只能说明观察时点的文件字节与基准相同，无法排除执行中途修改后又恢复的情况，严格禁止写入的过程审计仍要核对工具事件或文件系统日志。

此外，虽然探针另起 `python -I` 子进程并设了 5 秒超时，它依然运行在同一个教学容器内，生产环境评测不可信代码需要权限隔离的只读沙箱与网络屏蔽。

## 本课组件

| 组件 | 位置 | 作用 |
|---|---|---|
| `run_case` | [code.py](code.py) / [e11](../e11_tool_quality/code.py) | 准备隔离工作区，真实执行八组构造决策或 `--live` 模型修复 |
| `inspect_delivery` | [eval.py](eval.py) | 在 `python -I` 子进程运行四组探针并校验 `policy.txt` 哈希 |
| `DeliveryContract` | [eval.py](eval.py) | 继承 DeepEval `BaseMetric`，对可执行行为与保护条件取逻辑与 |
| `evidence_sample` | [eval.py](eval.py) | 将 `agent_final_answer` 与 `independent_observation` 拼装为评分样本 |
| `judge_completion` | [eval.py](eval.py) | 运行 `TaskCompletionMetric`，对比有无独立观察下的语义完成度 |

## 试一下

运行本课脚本，在隔离工作区执行八组交付条件并查看 `DeliveryContract` 结果：

```sh
python -m course.e12_task_completion.code
```

动手验证四个问题：

1. 对比 `correct` 与 `claim_only`：最终回复完全相同，为什么磁盘证据与交付分数完全相反？
2. 查看 `hardcoded`、`mutates_input`、`policy_changed`，分别指出它们违背了哪一条必要条件。
3. 对比 `equivalent_loop` 与 `correct`，解释为什么不应该直接比较源码字符串。
4. 加上 `--live --judge` 运行真实修复与裁判对比，先看 `independent_observation`，再核对 `TaskCompletionMetric` 抽出的 `outcome` 与 `reason`。

[源码导读](source_walkthrough.md) · [练习](exercises.md) · [参考解释](solutions.md) · [样本与评测记录](assessment.md)

## 接下来

这一课把任务描述固定在单轮输入里。在真实多轮对话中，用户往往在后面推翻前面的部分要求、保留另一些旧约束，甚至对历史做摘要压缩。下一课 `e13` 把任务放进多轮会话，追踪当前有效约束以及每次模型调用实际看到的上下文。
