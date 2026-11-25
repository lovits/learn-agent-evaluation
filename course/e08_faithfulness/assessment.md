# e08 样本与评测记录

[教材](README.zh.md) · [样本](cases.jsonl) · [完整记录](assessment.json)

## 样本设计

本课包含一条冻结的真实 Agent 回答和三组受控对照样本：

- `frozen_agent`：复用第 5 课真实运行 `e482c43222e54cd4861b0227c9b13cac` 的任务、最终回答与实际知识库上下文，样本内记录了原文件 SHA-256 以便校验一致性。
- `unmentioned`：在回答中加入资料未提及的 GitLab 托管声明，检验无依据信息的裁决方式。
- `contradicted`：将日志保留期限写成 30 天，与原始 14 天资料直接矛盾。
- `changed_evidence`：保持上一组回答不变，在内存中将教学日志上下文的 14 天改为 30 天，并将片段编号标为 `constructed/logs-30-days`，检验忠实度随上下文的变化。

## Docker 中的固定标签计算

运行编号为 `a04925731eec4e1389ec374239f08ca6`，无裁判模型请求，仅验证固定标签在两种口径下的聚合结果：

| 样本条件 | 教学标签 | 默认比例 | 明确支持比例 |
|---|---|---:|---:|
| `unmentioned` | `yes`、`yes`、`borderline` | 1 | 2/3 |
| `contradicted` | `yes`、`yes`、`no` | 2/3 | 2/3 |
| `changed_evidence` | `yes`、`yes`、`yes` | 1 | 1 |

`frozen_agent` 未预设教学标签，其声明拆解与逐条裁决完全由 DeepEval 原生执行后逐项核对。

## DeepEval 原生执行

运行编号为 `589609fbb5a14e539c99942ab39352ac`，Docker 环境中实际发出 12 次裁判请求。每组样本依次抽取 `truths`、`claims` 并判定 `verdicts`，关闭 `include_reason` 以跳过额外的总分解释请求。

| 样本条件 | 实际声明数 | 实际裁决 | 原生默认分数 | 明确支持比例 |
|---|---:|---|---:|---:|
| `frozen_agent` | 6 | `borderline`、`yes`、`yes`、`borderline`、`borderline`、`borderline` | 1 | 1/3 |
| `unmentioned` | 3 | `yes`、`yes`、`borderline` | 1 | 2/3 |
| `contradicted` | 3 | `yes`、`yes`、`no` | 2/3 | 2/3 |
| `changed_evidence` | 3 | `yes`、`yes`、`yes` | 1 | 1 |

三组对照样本的原生裁决与教学标签完全一致：GitLab 托管声明因资料未提及判为 `borderline`；30 天期限与 14 天直接冲突判为 `no`；上下文换成 30 天后，同一条期限声明转为 `yes`。

`support_score` 直接基于同一批原生 `verdicts` 统计 `yes` 比例，无需再次调用裁判。四组样本的 `passed` 均为 `true`，这是因为 DeepEval 默认阈值为 `0.5` 且默认聚合允许 `borderline` 通过。

## 真实回答中的证据边界

在 `frozen_agent` 抽出的 6 条声明中，两条 `yes` 对应发布前命令、通过条件以及失败先修复的要求，其余四条 `borderline` 来自两类原因：

- 工具执行声明：“`check.txt` 包含命令”以及“测试和实际发布均未执行”描述的是工具操作与执行状态，知识库规范里找不到这类记录，需要回到第 5 课的 `write_file`/`read_file` 轨迹与工作区文件核对。
- 中间抽取损失：两条附带来源编号的声明被判为 `borderline`，原因是裁判收到的 `truths` 在抽取时丢掉了 `atlas/release.md#0` 与 `atlas/logs.md#0` 编号，而原始 `retrieval_context` 里实际包含这些编号。

因此，读懂 `frozen_agent` 的 `1/3` 明确支持比例时，需要先分清知识类声明与执行类声明的证据范围，再检查 `truths` 是否完整保留了判定所需信息。原始上下文、中间抽取结果、声明与理由均原样保存在 [assessment.json](assessment.json) 中。

## 软件检查覆盖项

配套单元测试覆盖以下边界行为：同一批标签在默认与严格口径下的聚合计算、非法标签拦截、空列表返回 `None`、原生默认允许 `borderline` 通过、空声明场景下保留 `sdk_score=1` 同时对外标记 `not_applicable`，以及裁决数与声明数不匹配时标记 `error` 并置空分数。
