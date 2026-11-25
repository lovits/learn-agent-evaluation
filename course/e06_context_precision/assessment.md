# e06 样本与评测记录

[教材](README.zh.md) · [标签与判据](cases.jsonl) · [实现](eval.py) · [完整记录](assessment.json)

## 数据与控制条件

本课沿用第 5 课的 Atlas 知识库文档（`atlas/release.md`、`atlas/auth.md`、`atlas/logs.md`），固定检索查询为“Atlas 补丁发布前的检查要求 测试命令 发布条件”。原生 TinyRAG 检索返回 `logs`、`release`、`auth` 三条候选，原始文档与片段哈希完整保留在 [assessment.json](assessment.json) 中。

在 [cases.jsonl](cases.jsonl) 中，对照参考答案将提供测试命令与发布条件的 `atlas/release.md#0` 标为 `1`，将仅描述日志期限或认证请求头的 `atlas/logs.md#0` 与 `atlas/auth.md#0` 标为 `0`。随后基于这同一批候选构造有用项前移、有用项后移和末尾追加构造天气文本三组控制条件，用来在相同片段集合上隔离观察排序与尾部噪声对各项指标的影响。

## 固定标签的 Docker 实验

运行编号为 `ad253f7c73054fb58d5f28e729ff2189`，在 Docker 中运行原生 TinyRAG 与 `ranking` 聚合函数，不发起裁判模型请求：

| 条件 | 标签顺序 | 普通精度 | 列表 AP | RR | NDCG |
|---|---|---:|---:|---:|---:|
| `original`（原序） | `0,1,0` | `1/3` | `0.5` | `0.5` | 约 `0.6309` |
| `useful_first`（有用项前移） | `1,0,0` | `1/3` | `1` | `1` | `1` |
| `useful_last`（有用项后移） | `0,0,1` | `1/3` | `1/3` | `1/3` | `0.5` |
| `trailing_noise`（前移后加尾部噪声） | `1,0,0,0` | `1/4` | `1` | `1` | `1` |

三组重排的相关项总数相同，因此普通精度同为 `1/3`，只有 `list_ap`、`rr` 和 `ndcg` 随着位置变化而拉开差距；末尾追加天气噪声让普通精度跌至 `1/4`，而 `list_ap`、`rr` 与 `ndcg` 仍维持 `1`。

## DeepEval 原生评分

运行编号为 `c675aad87cd140e6af3aaa0112643740`，在 Docker 中带 `--judge` 参数实际发起了五次模型请求：对 `original` 和 `useful_first` 各调用一次 `ContextualPrecisionMetric`，以及对 `original` 的三个片段各调用一次 `ContextualRelevancyMetric`。由于关闭了 `include_reason`，SDK 跳过了生成总分解释的请求，但每条裁决仍保留各自理由或陈述内容。

| 指标与条件 | 实际裁决 | 实际分数 |
|---|---|---:|
| `ContextualPrecisionMetric`，`original` | `no`、`yes`、`no` | `0.5` |
| `ContextualPrecisionMetric`，`useful_first` | `yes`、`no`、`no` | `1` |
| `ContextualRelevancyMetric`，`original` | 共 `9` 条陈述，其中 `4` 条 `yes` | `4/9`，约 `0.4444` |

这次原生运行中，两次 `ContextualPrecisionMetric` 给出的逐片段裁决与预设标签完全一致；由于 LLM 裁判每次调用独立作答，后续复跑或切换模型时仍应以当次留存的原生 `verdicts` 为准。

`ContextualRelevancyMetric` 把日志文档和认证文档里的背景陈述（例如“日志保留 14 天”“使用 `X-Atlas-Token` 传递令牌”）判为无关，但把“日志保留时间不决定检查命令”与“`X-Atlas-Token` 请求头不用于决定能否发布”判为相关，加上 `release.md` 贡献的 `2` 条相关陈述，合计 `4/9`。它度量的单位是陈述而非整段文档，因此不能把 `0.4444` 解释为“44% 的文档有用”，也不能直接拿它和 `0.5` 比较数值高低。

两次指标调用仅面向检索上下文，样本中的 `actual_output` 保持为空。

## 软件检查覆盖项

配套单元测试（[test_context_precision.py](../../tests/test_context_precision.py)）验证了以下边界行为：

- 相同相关数量在不同位置下的 `precision`、`list_ap`、`rr` 与 `ndcg` 计算结果，以及 `trailing_noise`、多相关项 `[1,0,1]`、空列表返回 `None`、全 `0` 返回 `0` 和非法标签拦截。
- 在 `actual_output=None` 的样本上运行 `judge_precision` 与 `judge_relevancy`，确认两者分别输出片段级与陈述级裁决且统计单位相互独立。
- 当裁判返回裁决条数少于字符串上下文片段数时，`judge_precision` 将结果记为对齐错误（`status="error"`，`score=None`），不把缺失条目默认记为 `no`。

阅读本课实验分数时，应同时对照相关性判据、模型逐条裁决以及各自的分母定义，避免把单条检索样例的排序分或默认阈值当成全局检索结论。
