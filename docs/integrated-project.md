# 完整项目：给编程 Agent 留下一条可核对的评测链

项目入口是[第 16 课](../course/e16_regression/README.zh.md)及对应的 [code.py](../course/e16_regression/code.py)。综合项目直接由前 15 课搭好的模块组装而成，每个模块仍然可以回到各自课次单独查阅和运行。

## Agent 怎样工作

用户提交修复任务后，Agent 在循环里选择具名工具：文件读写工具被限制在隔离工作区内，Bash 负责执行命令，TinyRAG 的 `search_knowledge` 查询只读挂载的知识库。工具返回值写回 `messages` 供模型继续决策，直到模型停止调用工具或达到运行边界。

在实测模式（`--live --judge`）下，包括首步查询、读取源码、写回修复和验证在内的每一步都由模型自主决策；默认离线模式则使用预设决策配合真实工具执行，专门用来验证接口接线和门禁逻辑。模型传输层只输出结构化动作建议，实际执行和路径权限边界由课程 Harness 统一控制。

## 评测怎样工作

| 阶段 | 保留什么 | 判断依据 | 对应课程 |
|---|---|---|---|
| 定义成功 | 任务目标、参考标准、业务条件 | 明确需要交付的结果 | 1 |
| 保存运行 | 输入、回答、动作、返回与产物 | 完整轨迹与 DeepEval `LLMTestCase` | 2 |
| 准备数据 | 来源哈希、审核记录、去重与划分 | 参考独立于模型实际输出 | 3 |
| 选择评分 | 规则契约、量表、阈值与错误状态 | 可直接核对的条件优先写规则 | 4 |
| 接入知识 | 文档哈希、分块、候选与实际上下文 | TinyRAG 命中结果与最终模型输入 | 5 |
| 检索与上下文 | 相关性、排序位置与事实覆盖 | 精度、排序与召回各自的口径与分母 | 6 至 7 |
| 评价回答 | 声明、证据支持、正确性与完整性 | 忠实度、切题性与任务标准 | 8 至 9 |
| 定位失败 | 分层对照快照与受控反例 | 资料、检索、组装与生成的各自边界 | 10 |
| 评价行动 | 工具名、参数、顺序与业务产物 | 工具匹配高分和最终交付分别核对 | 11 至 12 |
| 多轮与裁判 | 有效约束、参考标签与位置偏差 | 模型实际可见上下文与校准后裁判 | 13 至 14 |
| 比较与回归 | 同题差值、重采样波动、成本与待复核队列 | 固定判据与分项硬门禁 | 15 至 16 |

综合评测按任务需求组合指标。在账单修复项目里，`evaluate_run` 串联了运行与工具轨迹检查、独立行为与哈希契约（`DeliveryContract`）、显式 `GEval` 完成度量表以及 `ContextualRecallMetric` 召回检查，其余专门指标保留在各自课次按需调用。

## 目录结构

```text
course/e16_regression/
  code.py                 串联 Agent 运行、版本指令与逐条评分
  eval.py                 独立行为检查、显式量表、门禁与失败候选收集
  cases.jsonl             公开回归任务、初始文件与知识来源哈希
  failure_origin.json     从第 12 课复核引入的历史反例与原始分数
  observed_failure.json   实测中断样本（HTTP 502）与可用性阻塞记录
  README.zh.md            主教材
  source_walkthrough.md   调用链、Learn Claude Code 与 DeepEval 源码导读
  exercises.md            动手练习
  solutions.md            练习参考解释
  assessment.md / .json   样本设计、实验数据与自动化检查留档
  images/                 两张 SVG 流程图及对应源图与 PNG 导出
eval_course/              模型桥接、TinyRAG 检索、运行记录与本地阅读器
knowledge_base/           只读挂载的课程知识库文档
runs/ / workspaces/       实际运行记录与工作区文件
```

[Docker 配置](https://github.com/lovits/learn-agent-evaluation/blob/main/compose.yaml) 将知识库以只读方式挂载进容器，并为 `runs/` 和 `workspaces/` 提供独立的可写目录。[固定版本](https://github.com/lovits/learn-agent-evaluation/blob/main/references/versions.json) 与 `uv.lock` 锁定了上游代码提交和依赖版本；模型响应保留接口返回的模型选择方式和 token 用量，接口未提供的固定快照与价格字段保持为空。

## 一次改动怎样过门禁

先把复核确认过的失败场景连同明确判据加入公开回归集。每次评估改动时，基线与候选两个版本从完全相同的初始文件在隔离工作区里分别执行，由 `inspect_delivery` 独立核对工作区代码与保护文件，再交给统一口径的 DeepEval 语义指标打分。

只要候选版本在任意一道回归题上触发关键失败，门禁就会返回 `reject`；只要存在模型报错或评分接口异常导致裁决缺失，门禁就会返回 `blocked` 阻塞流程。只有指定范围内的题目全部通过且修复了基线失败时，门禁才给出 `accept_in_scope`。

离线自动化流程验证真实工具运行、数据接线和门禁分支逻辑，实测模型和原生裁判结果则完整记录在各课 `assessment.md` 与 `assessment.json` 中。未通过的运行会自动进入 `failure_candidates` 等待人工复核；若要将局部回归结论推广到更广泛的生产流量，还需要在独立留出题族和多次重复运行中继续验证。

[完整大纲](curriculum.md) · [课程要求](course-requirements.md) · [制作规范](course-specification.md)
