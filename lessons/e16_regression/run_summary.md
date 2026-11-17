# 第16课实验记录

本课将真实模型实验、模型夹具控制、已保存的历史组件实验及讲师构造退化分开。运行成功与教材发布状态分别核对。

## 真实组合任务

冻结协议 [e16-composed-v2](../../references/e16-composed-v2-protocol.json)，工作区 `workspaces/e16-composed-002`，应用镜像 `sha256:cd69385a64289e9fe7d0b44e8a3d7111e873c55574a0c54ee3801044209d3bc0`。镜像内17份可见源码/配置哈希与协议逐一一致，独立答案没有挂进应用。

实际33次模型响应，0次记录到的模型错误。包含主轮与一次性子任务16次、持久队友7次、记忆支持5次、公开目标审查1次、workflow3次、摘要1次。八个预定阶段全部完成：修复、一次性复核、讲师当前计划审批、持久队友评审、后台测试交付、真实时钟一次性任务、完整四文件 workflow、讲师要求的原生 compact。

讲师负责阶段排序、当前审批和 Git 提交；模型决定各阶段的工具动作和回答。队友评审保存在 `wt/review`，任务 completed 后完成 IDLE、关机确认与租约释放，工作目录移除而分支保留。退出时 active_teammates/backgrounds/schedules 均为空。容器退出码0，实际 OOMKilled 为false。导出的28条原生 trace 保留各线程真实根与父子关系。

断网独立验收通过：两个 API 共44条输入检查，原测试与签名、跨文件调用约束通过；实际 Task、记忆索引、一次性调度确认、Git worktree、workflow三条唯一 journal 与产物状态通过。评审文字的普遍语义正确性没有因此自动获证。

原始 [运行报告](../../integrated_agent/evidence/composed-agent.json) 与 [独立验收](../../integrated_agent/evidence/composed-evaluation.json) 随项目保存。

## 真实错误与边界任务

两个新工作区各发生3次模型响应，共6次，均记录实际指定工具尝试。未预授权的 `touch forbidden.txt` 被批处理权限拒绝；`../e16-boundary-outside.txt` 写入被路径 hook 拒绝。调用 ID 对应拒绝结果，未进入 post hook，四个原始业务文件保持字节，无绕行文件，独立验收均通过。

协议见 [negative-v1](../../references/e16-negative-v1-protocol.json)，结果见 [权限拒绝](../../integrated_agent/evidence/denial-evaluation.json)、[越界拒绝](../../integrated_agent/evidence/boundary-evaluation.json)。这两例验收的是保持和拒绝，没有要求修复原有业务缺陷。

## 双框架实际评分

首轮采样与修订各发生10次真实裁判响应，合计20次；原生工具比较产生0次裁判请求；新增 Agent 请求为0，评分错误为0。两轮都保留同一份 Agent 回答，第二轮补回实际工具参数，协议分别冻结，报告分别保存。

| 投影与证据 | DeepEval默认 | 同组verdict仅YES | Ragas |
|---|---:|---:|---:|
| v1，仅检索规范 | 1.0 | 0.6 | 0.0 |
| v1，工具输出 | 1.0 | 0.6667 | 0.5 |
| v2，仅检索规范及调用参数 | 1.0 | 0.0 | 0.1111 |
| v2，工具名/参数/输出 | 1.0 | 1.0 | 1.0 |

首轮 DeepEval 已将“已执行测试”识别为 borderline，默认聚合仍接受它。Ragas将其视为未获证据支持。首轮工具样本保存了 `OK` 输出，却没有把测试命令放进证据；第二轮带回实际 `command` 和编辑参数，裁判获得了更完整的执行信息。

第二轮仅规范分数也有变化，声明拆分数并不固定。因此这里记录一次开发诊断，不把变化全部归因于参数修复，不宣称留出集提升或普遍准确率。业务是否真的修好仍以实际44条检查为准。

工具投影的两个实现读取在两框架中均为1。讲师复制投影并删除 checkout 读取后，DeepEval默认/参数/排序为0.5、exact match为0，Ragas Accuracy严格/灵活均为0，F1为0.6667。这是构造退化，没有新运行一个“坏 Agent”。

原始 [v1评分](../../integrated_agent/evidence/native-metrics-v1.json)、[v2评分](../../integrated_agent/evidence/native-metrics-v2.json) 包含实际 prompt、声明、verdict、schema 和来源 UUID。精确模型版本与账单未提供，记录为空。

## 保留的失败与历史实验

组合首轮在首个模型请求前以137结束，报告仍为 started。没有可据以证明 OOM 的原容器元数据；观测整个 Runtime 对象是源码定位出的原因假设。移除编排层装饰后，新工作区完成正常任务。首轮源码与原始记录见 [归档](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/archive/e16-composed-v1-setup/termination.json)。

并发控制确实复现 worktree 绑定覆盖其他进程认领。保存失败后，在适配层统一跨进程事务，同一控制复测通过。协议夹具还覆盖重试、截断、审批、记忆回滚等分支，所有供应商请求数为0；实际进程、Git、线程和真实时钟分别执行。

此前工作流组件在两个真实并行检查后注入中断，换进程恢复命中两条日志，只新增一次验证。那次仅给两个实现文件，遗漏测试，项目级覆盖判断被上下文门禁拦截。这个历史 bad case 持续保留，未因本次提供完整四文件而删除。

全套检查与逐机制机器清单见 [验收文档](../../docs/e16-validation.md) 和 [能力范围](../../integrated_agent/capabilities.md)。
