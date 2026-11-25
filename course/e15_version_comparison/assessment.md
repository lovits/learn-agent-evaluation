# e15 样本与评测记录

[教材](README.zh.md) · [样本](cases.jsonl) · [完整记录](assessment.json)

## 样本设计

[cases.jsonl](cases.jsonl) 包含三个构造教学任务：跨文档发布与认证（`Atlas`）、跨文档上传认证与容量上限（`Upload`），以及当前生效规范识别（`Shipping` v3）。每道题都在 `sources` 字段绑定全部相关文档的 SHA-256 哈希；知识库以只读方式挂载，Agent 提示仅包含问题本身，参考答案只留给评分端使用。

每题跑两个版本（`baseline` 的 `context_limit=1`，`candidate` 的 `context_limit=3`）、各重复两次，共 12 行运行结果和 6 个预期配对。检索候选数固定为 `k=3`，第一步 `search_knowledge` 查询词由实验固定并交由 TinyRAG 实际执行，后续回复在默认模式下取 `fixture_answers`，在 `--live --judge` 模式下由真实模型续跑生成。

## 构造聚合示例与真实模型运行

两份运行记录分别验证了聚合算法与真实模型续跑效果：

| 运行模式 | 运行文件 | 内容说明 |
|---|---|---|
| 默认 Docker | `e15-suite-4d2c90f473214fbe93ada3f9390b4969` | 真实 TinyRAG 检索，配合预设回答与 `fixture_scores` 演示聚合 |
| `--live --judge` Docker | `e15-suite-c056915bad4a46138ccf0e9e838fac5e` | 真实 TinyRAG 检索，配合 12 次模型续跑与 12 次原生 `GEval` 裁判 |

在默认构造模式下，`Atlas`、`Upload` 与 `Shipping` 的题族差值分别为 `+0.5`、`+0.5` 与 `-1`，题族等权均值 `family_weighted_delta` 为 `0.0`，95% 百分位重采样区间为 `[-1, 0.5]`。其中 `Shipping` 的候选回答是刻意设计的退化示例，用来展示单题回退怎样被总均值掩盖。

在 `--live --judge` 真实运行中，6 个预期配对全部有效（`pair_coverage=1.0`），无评分报错，单次检索协议全部通过：

| 题族 | `baseline` 两次得分 | `candidate` 两次得分 | 同题平均差值 |
|---|---|---|---|
| `Atlas` | `0.5`、`0.5` | `1.0`、`1.0` | `+0.5` |
| `Upload` | `0.5`、`0.5` | `1.0`、`1.0` | `+0.5` |
| `Shipping` | `1.0`、`1.0` | `1.0`、`1.0` | `0.0` |

真实运行下的题族等权差值为 `1/3`（`0.3333`），近似 95% 百分位重采样区间为 `[0.0, 0.5]`，`regressions` 为空。从模型回答可以看到，在 `Atlas` 与 `Upload` 上，`context_limit=1` 时确实缺少认证或另一份文档的内容；扩到 3 条后模型补齐了全部要求；`Shipping` 两侧都识别出了当前 v3 规范。因为只有三个构造题族且重采样区间下界触及 `0`，扩大适用范围前还需要补充更多独立题族并复核裁判表现。

## 调用次数、耗时与费用记录

[assessment.json](assessment.json) 的 `runtime_by_version` 汇总了 `--live --judge` 模式下两个版本的 Agent 运行开销：

| 版本 | 平均质量分 | 平均 Agent 耗时（秒） | 真实模型请求数 | 总输入 token | 总输出 token | 美元费用 |
|---|---:|---:|---:|---:|---:|---|
| `baseline` | `0.6667` | `6.5285` | `6` | `93316` | `563` | `null` |
| `candidate` | `1.0` | `6.259` | `6` | `94582` | `449` | `null` |

受控首步检索不计入模型请求数，两个版本各有 6 次真实模型调用，共 12 次；12 次裁判调用的耗时与完整 `usage` 单独保存在每行的 `judge_calls` 中，与 Agent 耗时分开统计。总输入 token 包含传输层完整提示词与缓存部分；`reported_model` 均为空值，桥接层只记录了相同的默认选择器而未锁定模型快照；美元单价与费用保留 `null`（未知）。由于单次耗时受冷启动、缓存和服务端负载影响较大，这里的耗时仅作为小样本工程开销记录。

## 软件检查与日志记录

Docker 环境中同步运行了 50 项软件检查（包括 [test_version_comparison.py](../../tests/test_version_comparison.py)），验证了错位配对防护、缺评分归入 `missing_pairs`、重复键报错、题族等权、受控首步排除统计以及未知价格返回 `None` 的逻辑。最初未覆盖 Docker 仅接受 `serve` 的默认 entrypoint 时，失败日志保留在 `runs/e15-default.log` 与 `runs/e15-native.log`；指定入口命令重新运行后产出了上述两份完整结果记录。
