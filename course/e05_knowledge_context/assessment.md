# e05 样本与评测记录

[教材](README.zh.md) · [任务](cases.jsonl) · [固定查询实验](experiment.py) · [完整记录](assessment.json)

## 资料与任务

知识库目录 `knowledge_base/atlas/` 包含三份 Atlas 项目规范文档：发布要求、认证说明和日志保留策略。任务要求 Agent 先检索知识库，把规范中要求的测试命令写入工作区的 `check.txt`，再读回文件并说明发布条件。题目参考绑定了发布规范的路径与内容哈希，用于校验资料版本是否一致。

## 两次真实 Agent 运行

两次运行均在 Docker 隔离环境中执行，接入真实模型、原生 TinyRAG 检索和已有文件工具。完整对话消息、成功调用的模型输入、候选列表、选中片段、工具参数及 DeepEval 样本均保存在 [assessment.json](assessment.json) 中。

| 运行编号 | 参数与资料 | 观察到的行为 |
|---|---|---|
| `e482c43222e54cd4861b0227c9b13cac` | 原挂载，`k=3`，`context_limit=1` | 两次搜索后命中发布规范，写入并读回 `python -m pytest -q` |
| `b89516d0244046469378d036fe429fbc` | 替换挂载，`k=1`，`context_limit=1` | 三次搜索后命中新规范，写入并读回 `python -m pytest -q tests/unit` |

两次运行都正常结束，五项数据对应检查全部通过。原挂载运行的 `reference_status` 为 `current`；替换挂载修改了发布规范后，`reference_status` 变为 `source_changed_or_missing`，样本里的 `context` 和 `expected_output` 自动置空，`retrieval_context` 则照常保留。

从轨迹可以看到，两次运行第一轮都先命中了日志说明，随后 Agent 改写查询才拿到发布规范。日志文档里出现了“发布前检查命令”等词面匹配项，但并未给出具体命令，直观反映出纯词面检索的局限。此外，原运行最终历史保留了两次搜索累积的 2 条片段，替换运行保留了 3 条，印证了单次回填上限不会清空历史消息。

因为两次运行同时改动了挂载资料和 `k`，比较参数影响需要看下面固定变量的独立实验。

## 固定查询比较

[experiment.py](experiment.py) 在 Docker 中执行（运行编号 `1f358423948643cf89aa1871fdbb1e13`），固定文档与查询“Atlas 补丁发布前的检查要求 测试命令 发布条件”，直接运行原生 TinyRAG，排除模型改写查询的干扰。

| `k` | `context_limit` | 返回候选 | 选中片段 |
|---:|---:|---|---|
| 1 | 1 | `logs` | `logs` |
| 3 | 1 | `logs`、`release`、`auth` | `logs` |
| 3 | 2 | `logs`、`release`、`auth` | `logs`、`release` |

片段完整编号为 `atlas/文件名.md#0`。将 `k` 从 1 扩大到 3 后，`release` 进入了候选列表；但 `context_limit=1` 时仍只会回填排在第一位的 `logs`，直到把 `context_limit` 提高到 2，`release` 才真正被选中。

## 挂载隔离与边界验证

在 Docker 容器内尝试向 `/data/knowledge` 写入会返回 `errno=30`（EROFS），`/proc/self/mountinfo` 也显示该挂载点带有 `ro` 标记，原知识文件保持不变；与此同时，两次 Agent 都在各自独立的工作目录中顺利创建并读回了 `check.txt`。替换资料时使用另一份只读挂载目录，新旧运行的知识版本号、文档哈希与片段在 JSON 中各自留存，互不覆盖。

配套的自动化软件检查还验证了多项边界场景：未选中的候选不会进入模型输入；磁盘中途变动不会改写已读入内存的文本；资料变更后新运行自动撤下过期参考；触达步数上限时，第八次搜索的工具返回留在日志中，只有前七次进入后续模型调用。检查同时覆盖了文件工具路径权限、字符偏移与重叠窗口、同文异源区分、空语料和零匹配查询。
