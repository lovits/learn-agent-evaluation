# e10 样本与评测记录

[教材](README.zh.md) · [控制条件](cases.jsonl) · [完整记录](assessment.json)

## 固定对象与改动范围

本课复用第 9 课真实运行记录中的首条检索查询与最后一次生成输入。所有重放条件均在首条消息末尾附加相同的资料策略：只按当前提供的资料回答，缺证据时不猜测；发生冲突时以 `atlas/release.md` 为主规范，其余旧备忘不得覆盖它。重放阶段传入 `tools={}`，禁止模型再调搜索工具。

七组条件（`baseline`、`source_missing`、`retrieval_miss`、`assembly_drop`、`stale_source`、`noise`、`conflict`）在内存快照、检索筛选或上下文组装层各改动一处，挂载在磁盘上的原始知识库文档保持不变。

## Docker 中的阶段计算

阶段检查运行编号为 `aacb5927dd774becaefc9f36484945b4`，在 Docker 中执行 TinyRAG 检索、`first_gap` 定位与 `noise_fraction` 计算，无模型请求：

| 条件 | `first_evidence_gap` | 可观察阶段证据 |
|---|---|---|
| `baseline` | `None` | 参考版本发布规范进入 `selected` 与最终上下文 |
| `source_missing` | `source_missing` | 内存资料清单已移除 `atlas/release.md` |
| `retrieval_miss` | `retrieval_output` | 原生候选 `native_hits` 含有规范，过滤后的 `retrieved` 没有 |
| `assembly_drop` | `context_assembly` | `retrieved` 含有规范，截取过滤后的 `selected` 没有 |
| `stale_source` | `source_version` | 路径不变，内存快照命令改为 `unittest`，哈希与参考不同 |
| `noise` | `None` | 正确规范保留，另追加无关天气备忘 |
| `conflict` | `None` | 正确规范保留，另追加内容相反的旧归档备忘 |

返回 `None` 仅表示来源、哈希、检索输出和组装传递这四步均包含目标文档；出现 `source_version` 时需要结合版本变更审核具体内容差异。

## 真实回放与 DeepEval 评测

有效重放与评测运行编号为 `d152ed2599f24ae98a94fa45efe55fac`。Docker 中实际完成 7 次生成模型调用与 28 次 DeepEval 裁判请求（每组 3 次 `FaithfulnessMetric` 调用和 1 次 `GEval` 调用），所有生成原文、抽取事实、逐条裁决和评分理由均完整保存在 [assessment.json](assessment.json) 中：

| 条件 | 默认 `FaithfulnessMetric` | `support_score` | `GEval` 任务质量 | 实际回答行为 |
|---|---:|---:|---:|---|
| `baseline` | 1 | 0.75 | 1 | 正确说明命令、发布条件和失败处理 |
| `source_missing` | 1 | 0 | 1 | 说明缺少 `atlas/release.md`，保留结论且未猜测 |
| `retrieval_miss` | 1 | 1/3 | 1 | 说明检索结果不足并请求补充发布规范 |
| `assembly_drop` | 1 | 2/7 | 1 | 依据仅有的日志资料说明无法确定发布规范 |
| `stale_source` | 1 | 0.75 | 0.5 | 沿旧快照给出 `python -m unittest`，其余发布条件仍正确 |
| `noise` | 1 | 0.75 | 1 | 忽略天气备忘，按规范完整回答 |
| `conflict` | 1 | 0.714 | 1 | 按主规范选择 `pytest`，明确排除旧备忘 |

`source_missing`、`retrieval_miss` 与 `assembly_drop` 虽然缺少发布规范，但模型均按要求明确保留结论，因此在 `GEval` 任务质量上获得 `1`。与之对照，`stale_source` 中模型根据过期快照在根目录给出 `python -m unittest`，同时答出了全通过门槛与失败先修复规则，因此 `FaithfulnessMetric` 为 `1` 而 `GEval` 为 `0.5`，反映出忠于过期文档不代表符合当前规范。

默认 `FaithfulnessMetric` 把 `borderline` 计入通过项，因此七组全为 `1`。查看只统计 `yes` 的 `support_score` 可以看到明细差异：拒答条件下关于“资料未提供规范”或“未执行测试”的声明常落入 `borderline`，因而 `source_missing` 的 `support_score` 为 `0`，`conflict` 为 `5/7`（约 `0.714`）。

## 裁判校准观察点

在 `stale_source` 条件中，`GEval` 理由准确指出了 `python -m unittest` 与当前参考 `python -m pytest -q` 不一致，最终按“部分发布信息正确”给到 `0.5` 分；而当前 `Rubric` 第 0 档同时列出了 `contradictory`。这一结果把“忠于过期上下文但与当前参考矛盾时究竟应落 0 档还是部分正确档”的量表分歧暴露了出来，记录已保留供第 14 课裁判校准使用。

## 噪声比例计算

`assessment.json` 中 `stage_experiment.noise_math` 记录了 `noise_fraction` 在教学向量 `correct=[True, False, False]`、`relevant_support=[True, True, False]`、`irrelevant_support=[False, True, True]` 上的计算结果：共 3 条声明，第 2 条有误且两类资料均支持，计入 `relevant`；第 3 条有误且仅得无关资料支持，计入 `irrelevant`，两者均以全部 3 条陈述作分母，结果均为 `1/3`。这一算式独立展示错误陈述的归因与排他分母结构，未对七组重放回答做自动噪声掩码标注。

## 软件检查与评估边界

配套单元测试与运行时校验确认以下行为：

- `first_gap` 能够准确区分 `source_missing`、`source_version`、`retrieval_output` 与 `context_assembly` 四类缺口；`prepare()` 中 `noise` 不改变 `knowledge_version`，而 `retrieval_miss` 保留原始 `native_hits`。
- `noise_fraction` 严格执行全部陈述作分母、无关方向排除 `relevant_support`、空列表返回 `None` 以及数组长度不一致抛错。
- `replay` 不修改原始冻结轨迹、以 `tools={}` 禁用新工具调用并从实际 `model_input` 恢复 `retrieval_context`；真实重放运行核对了七组上下文一致、无新工具调用且磁盘原始知识库哈希未变。

本课仅针对单一公开任务并在每个条件执行一次重放。当前测试中天气噪声与冲突备忘未导致掉分，具体业务场景下的抗噪能力与稳定性需在多样本、多轮对比中进一步测定。
