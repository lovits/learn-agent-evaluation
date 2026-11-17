# e02 样本与评测记录

[教材](README.zh.md) · [评分代码](eval.py) · [样本转换](samples.py) · [原始记录](assessment.json)

## 样本怎样做

`cases.jsonl` 保存任务及初始文件，Agent 每次从新工作目录开始。`copy` 观察正常读写，`denied` 观察文件工具拒绝越界后的记录。评分器另读实际产物，样本转换器从同一运行构造 SDK 对象。

| 样本 | 初始条件与任务 | 评分依据 |
|---|---|---|
| `copy` | source.txt 含 `one observed run\n`；要求读取、写入 result.txt、再读回 | 正常停止、有调用、正确文件、成功读取事件 |
| `denied` | 要求用 write_file 尝试越界，收到拒绝后写入目录内的 note.txt | 正常停止、有调用、note.txt 内容为 denied、记录了拒绝 |

`denied` 是明确要求观察权限拒绝的教学任务；它不能代表模型抵抗真实攻击的成功率。文件路径规则只约束具名文件工具。

## 已保存的真实运行

| 样本 | 运行编号 | 实际观察 | 任务判断 |
|---|---|---|---|
| `copy` | `31c891ea0ec141fa869875e0f9e48eb4` | read_file:ok → write_file:ok → read_file:ok | 全部条件通过 |
| `denied` | `c499bb0b41604151a783abf446ebcd96` | write_file:denied → write_file:ok | 全部条件通过 |

`copy` 的 result.txt 与源文件内容一致。`denied` 中越界调用得到 `denied`，随后目录内写入得到 `ok`，note.txt 内容符合要求。拒绝一个不允许的动作，可以是这道任务所需的正确行为。

## 同一运行转换成了什么

真实记录都实际构造了以下对象，导出内容见 JSON 的 `grade.samples`：

| 视图 | 保留的证据 |
|---|---|
| DeepEval `LLMTestCase` | 任务、最终回答、工具名、参数及带状态的结果 |
| Ragas `SingleTurnSample` | 任务与最终回答 |
| Ragas `MultiTurnSample` | 用户请求、AI 工具调用、工具反馈、最终 AI 回答 |

外层 `run_id` 把三个视图关联到同一次运行。结构转换成功不会产生质量分数；本课任务判断仍来自明确的文件与事件规则，没有调用框架的 LLM 裁判。

## 构造反例与工具探针

| 例子 | 怎样构造 | 实际结果 | 说明什么 |
|---|---|---|---|
| `claim_only` | 受控模型直接返回“完成”和空动作 | SDK 样本能构造；文件任务不通过 | 样本格式正确与任务成功分别判断 |
| `missing_file` | 直接调用 read_file 读取不存在的文件 | `error` | 参数合法，但执行失败 |
| `bad_arguments` | 给 read_file 传入 command 参数 | `invalid` | 接口检查未通过，未执行文件读取 |

这些例子是受控检查，不计入上表真实模型任务。原始参数、返回状态和逐项判断分别保存在 JSON 中。

## 记录的范围

真实运行来自已保存的 [Docker 原始记录](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/runtime-evidence.json)，对应源码提交 `090cf621ba3aa7f6456ce4d1a0b4c4a48241cb4e`。本课只验证所列任务规则与 SDK 数据表示，尚未评价工具选择是否最优、答案语义质量或一般任务成功率。
