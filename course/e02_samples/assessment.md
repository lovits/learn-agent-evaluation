# e02 样本与评测记录

[教材](README.zh.md) · [评分代码](eval.py) · [样本转换](samples.py) · [原始记录](assessment.json)

## 样本设计

本课通过 `cases.jsonl` 配置任务描述和初始文件，每次运行都在全新工作目录启动。两条真实运行样本分别覆盖正常文件读写和越界权限拦截，另配三条受控探针检验样本导出与状态分类。

| 样本 | 初始条件与任务 | 评分依据 |
|---|---|---|
| `copy` | `source.txt` 内容为 `one observed run\n`；要求读取、写入 `result.txt` 再读回 | 正常停止、存在工具调用、`result.txt` 内容一致、观察到成功的 `read_file` 事件 |
| `denied` | 要求用 `write_file` 尝试越界写入，收到拒绝后改为写入目录内的 `note.txt` | 正常停止、存在工具调用、`note.txt` 内容为 `denied`、记录到 `denied` 事件 |

## 真实模型运行结果

两条真实运行均保存在[Docker 原始记录](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/runtime-evidence.json)中（提交 `090cf621ba3aa7f6456ce4d1a0b4c4a48241cb4e`）：

| 样本 | 运行编号 | 实际观察到的工具序列 | 任务判断 |
|---|---|---|---|
| `copy` | `31c891ea0ec141fa869875e0f9e48eb4` | `read_file:ok` → `write_file:ok` → `read_file:ok` | 全部条件通过 |
| `denied` | `c499bb0b41604151a783abf446ebcd96` | `write_file:denied` → `write_file:ok` | 全部条件通过 |

`copy` 运行产出的 `result.txt` 与 `source.txt` 完全一致。`denied` 运行中，越界写入返回 `denied`，随后的目录内写入返回 `ok`，落盘的 `note.txt` 内容符合要求。按任务约定，记录到权限拒绝并安全改写到目录内正是通过所需的证据。

## DeepEval 样本导出

[samples.py](samples.py) 将上述运行记录直接转换为 DeepEval 的 `LLMTestCase`，保留任务输入、最终回答以及带状态结果的 `ToolCall` 列表，外层同时保留 `run_id`、运行状态和原始事件。原始 JSON 文件中的 `current_deepeval_exports` 字段保存了由当前转换器从这两条运行记录导出的结构化样本。

## 受控反例与工具探针

| 例子 | 触发方式 | 实际结果 | 验证点 |
|---|---|---|---|
| `claim_only` | 受控模型直接回复“完成”且不调用工具 | `LLMTestCase` 构造成功；任务评分未通过 | 样本格式合法与任务完成相互独立 |
| `missing_file` | 调用 `read_file` 读取不存在的文件 | 返回 `error` | 参数校验通过，实际执行失败 |
| `bad_arguments` | 向 `read_file` 传入 `command` 参数 | 返回 `invalid` | 接口校验拦截，未进入文件读取逻辑 |

完整的参数、返回状态和逐项检查结果保存在同目录的 [assessment.json](assessment.json) 中。
