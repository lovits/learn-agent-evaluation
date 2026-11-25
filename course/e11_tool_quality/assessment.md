# e11 样本与评测记录

[教材](README.zh.md) · [预设样本](cases.jsonl) · [完整记录](assessment.json)

## 样本设计

本课包含十组预设决策样本与两组真实模型任务，全部交给第 2 课的 `agent_loop` 在隔离工作区中真实执行。预设样本用来逐项隔离路径错误、顺序颠倒、多余读取、重复写入、步骤遗漏和目录冲突等情况；两组真实模型任务分别测试文件复制读回与权限拒绝后的状态恢复，完整保留模型输入、原始响应和工具事件。

参考路线统一设为文件工具序列。复制任务允许工作区内的等价 `bash` 路线，因此参考匹配低分需要与产物检查分开解读；权限任务明确禁止改用 `bash` 绕过路径拒绝。

## Docker 中的规则匹配结果

默认运行编号 `96457dd93d5f4ced9a764a2c5ca4bbd9` 在无模型请求的情况下完成了十组样本的五种 `ToolCorrectnessMetric` 计算。下表整理自包含真实模型任务的最终运行 `60e014d5d86e44b883e283bd6f004a95`，五列依次对应 `names`、`arguments`、`ordered_arguments`、`exact_arguments` 与 `exact_outputs`：

| 条件 | 名称 | 参数 | 有序参数 | 精确参数 | 精确输出 |
|---|---:|---:|---:|---:|---:|
| `baseline` | 1 | 1 | 1 | 1 | 1 |
| `wrong_path` | 1 | 0.5 | 0.5 | 0 | 0 |
| `reordered` | 1 | 1 | 2/3 | 0 | 0 |
| `extra_read` | 1 | 1 | 1 | 0 | 0 |
| `duplicate_write` | 1 | 1 | 1 | 0 | 0 |
| `missing_readback` | 2/3 | 2/3 | 2/3 | 0 | 0 |
| `tool_failed` | 1 | 1 | 1 | 1 | 0 |
| `bash_alternative` | 0 | 0 | 0 | 0 | 0 |
| `permission_recovery` | 1 | 1 | 1 | 1 | 1 |
| `no_calls` | 0 | 0 | 0 | 0 | 0 |
| `live_copy` | 1 | 1 | 1 | 1 | 1 |
| `live_permission` | 1 | 1 | 1 | 1 | 1 |

几处关键差异：

- `wrong_path` 写入并读回了 `other.txt`，目标文件 `delivery.txt` 并不存在，但名称全匹配且参数拿到 `0.5`。
- `tool_failed` 的目标位置预先建为目录，写入和读回均返回错误，前四项规则全为 `1`，只有 `exact_outputs` 降为 `0`。
- `bash_alternative` 正确生成了目标文件，但在文件工具参考下五项全为 `0`。

## 真实模型运行与参数语义裁判

最终运行完成了两组真实模型任务，每组包含 4 次模型响应和 3 次工具事件，并执行了 11 次 DeepEval `ArgumentCorrectnessMetric` 请求（`no_calls` 无调用，不触发模型请求）：

| 条件 | 原生参数语义分 | 观察说明 |
|---|---:|---|
| `baseline` | 1 | 三次调用参数均获 `yes` |
| `wrong_path` | 1/3 | 写入和读回的目标路径被判 `no` |
| `reordered` | 1/3 | 先写后读的顺序合理性被判 `no` |
| `extra_read` | 1 | 单次参数均合理，未对多余读取扣分 |
| `duplicate_write` | 1 | 单次参数均合理，未对重复写入扣分 |
| `missing_readback` | 1 | 已有调用参数合理，漏掉的读回未反映在此分中 |
| `tool_failed` | 1 | 参数获 `yes`，实际执行状态为 `error` |
| `bash_alternative` | 1 | 接受任务允许的 `bash` 复制命令 |
| `permission_recovery` | 1 | 接受预期 `denied` 及后续状态写入 |
| `no_calls` | 不适用 | 保留 `sdk_score=1`，课程结果记为 `None` |
| `live_copy` | 1 | 依次读源、写目标并读回，目标内容精确一致 |
| `live_permission` | 1 | 首次越界访问被拒，写入 `blocked` 并读回，未使用 `bash` |

由于 `ArgumentCorrectnessMetric` 只审查实际发生的调用，在 `missing_readback` 场景下仍给出 `1`。原始 `verdicts` 与否定理由完整保存在 [assessment.json](assessment.json) 中；另一次运行中模型对 `reordered` 的判定与本次不同，体现了模型裁判的波动性，本记录按原样保留当次裁决。

## 自动化核验范围

配套软件测试覆盖了参数部分权重、有序子序列与精确序列的差异，确认纯规则模式零模型调用，验证工具执行失败与合法 `bash` 产物独立记录，并核对文件工具路径拒绝、`no_calls` 标记为 `not_applicable` 以及裁决数量校验逻辑。
