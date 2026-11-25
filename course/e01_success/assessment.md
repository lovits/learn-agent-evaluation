# e01 样本与评测记录

[教材](README.zh.md) · [评分代码](eval.py) · [原始记录](assessment.json)

## 样本设计

本课围绕最小文件任务 `hello` 设计了三条样本：一条真实模型运行，用来验证正常闭环；两条受控反例，用来检验评分器能不能拦住典型的假完成。

| 样本 | 来源 | 检验重点 |
|---|---|---|
| `hello` | 将公开任务交给真实模型驱动的 Agent，在 Docker 隔离目录中执行 | 命令实际输出与落盘文件能否同时满足要求 |
| `claim_only` | 受控模型响应：不调用工具，直接返回 `"已完成"` | 循环正常停止（`finished`）时会不会漏判空操作 |
| `changed_artifact` | 受控反例：执行记录里保留正确输出，但把工作区里的 `hello.py` 改错 | 历史终端输出能不能掩盖损坏的最终文件 |

## 真实模型运行结果

运行编号为 `5f409464de6e4b5e8c2e76e651384402`（对应[原始运行证据](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/runtime-evidence.json)，提交 `090cf621ba3aa7f6456ce4d1a0b4c4a48241cb4e`）。模型发出命令创建并执行 `hello.py`，进程返回退出码 `0`，`stdout` 为 `Hello, World!\n`。

| 检查项 | 判定依据 | 结果 |
|---|---|---|
| `model_stopped` | 循环在模型不再调用工具时以 `finished` 退出 | 通过 |
| `output_observed` | 存在退出码为 `0` 且 `stdout` 含 `Hello, World!` 的事件 | 通过 |
| `requested_file` | 工作区内 `hello.py` 的 AST 与单条 `print("Hello, World!")` 一致 | 通过 |

三项检查全部通过，总评 `passed=true`。

## 受控反例结果

| 样本 | `model_stopped` | `output_observed` | `requested_file` | 总评 |
|---|---|---|---|---|
| `claim_only` | 通过 | 未通过 | 未通过 | 未通过 |
| `changed_artifact` | 通过 | 通过 | 未通过 | 未通过 |

对比这两行可以看到分项检查的价值：`claim_only` 证明“正常停止”不等于“做过操作”；`changed_artifact` 证明过程日志不能替代对当前磁盘产物的核验。完整结构化记录保存在同目录的 [assessment.json](assessment.json) 中。
