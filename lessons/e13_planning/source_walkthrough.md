# e13 源码导读：计划怎样对应到执行

[教材](README.zh.md) · [运行时](code.py) · [任务状态](state.py) · [角色工具](tools.py)

## 从声明到认领

参考 [s05 清单](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s05_todo_write/code.py)、[s10 任务](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s10_task_system/code.py)、[s06 子 Agent](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s06_subagent/code.py)与 [s13 团队](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s13_agent_teams/code.py)。具体目录以固定版本为准。

本课先验证整份 todo，再替换；任务先建节点再加依赖；`claim` 在同一把 RLock 中检查依赖和 owner。锁保护同一进程共享实例，不提供跨进程分布式认领。

状态以临时文件加 replace 写入。`task_complete` 先运行分配组件的公开行为检查，失败保持进行中；局部通过仍标明整体尚未评估。外部检查还会重放任务事件，防止只看一张全部完成的任务表。

## 上下文与文件分别限制

`run_child` 新建消息，`PlanningPool` 约束可改文件。子任务没有递归委派工具，结果进入 `MessageBus`，由父循环单一消费者读取。

文件哈希守卫拒绝过期修改；它没有接管 Lead 的任意 Bash，也不替代操作系统隔离。邮箱摘要是声明，文件与测试才提供行为证据。

## 原生 trace 的真实父子关系

[Plan Quality 文档](https://deepeval.com/docs/metrics-plan-quality) · [Plan Adherence 文档](https://deepeval.com/docs/metrics-plan-adherence)

`@observe` 在执行时建立 agent/llm/tool 层级，`update_current_span` 写入角色与实际参数。结束后导出原生 Trace，再通过 SDK `create_nested_spans_dict` 与 `serialize_to_json` 转成评分结构。

投影可省去重复请求历史，但原始模型输入仍保存。固定版本低层 `measure` 的 `_trace_dict` 绑定属于内部适配；官方 observe/dataset 流程通常自动处理它，升级时应重新核对。

## DeepEval 的两条计划指标

[PlanQuality 实现](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/plan_quality/plan_quality.py) · [PlanAdherence 实现](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/metrics/plan_adherence/plan_adherence.py)

```text
任务抽取 → AgentPlan 抽取
               ├─ task + plan → 质量分
               └─ task + plan + execution → 遵从分
```

质量关注覆盖、必要性与顺序；遵从只关注是否照计划执行。多次计划更新可能被抽取器混合，因此保留原清单及每次 `AgentPlan`。

没有计划时原生默认1，需单列缺少计划。评分 schema 是 float，外层仍检查有限值与范围。同步与异步入口的依赖顺序相同，不等于采集隐藏思维过程。

## Ragas 用 rubric 定义等级

[通用指标说明](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/general_purpose/) · [DomainSpecificRubrics](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/metrics/collections/domain_specific_rubrics/metric.py)

本课分别定义质量与遵从的1至5级标准。`RubricScorePrompt` 接收相应证据，返回整数 score 与 feedback，再进入 `MetricResult`。

质量看首次计划，遵从再加入执行记录。Ragas 的最低档1与 DeepEval 空计划默认1含义相反，必须连同量尺和缺失依据一起解释。

## 整体结果从文件取证

`verify.py` 分别检查核心与入口，把唯一允许的导入绑定到实际核心，再运行行为合同；还核对签名、测试保护、文件范围与依赖认领。

组件完成不代表入口正确。子会话失败后重试，要保留早先错误，再检查最终交接与产物；状态标签不能替代这些证据。
