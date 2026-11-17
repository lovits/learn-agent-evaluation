# 17项机制的验收范围

编号采用固定版本 Learn Claude Code 的 s01–s17。前14项在原生 s15 中集成；课程加载 s15，再接入原生记忆、workflow 和 Goal。下表逐项写明检查动作和证据。模块存在与检查通过分别记录。

| 上游机制 | 检查什么 | 证据位置 |
|---|---|---|
| s01 Agent Loop | 真实工具结果回填后继续请求，没工具时返回 | 基础任务与组合任务；`test_real_file_and_shell_execution...` |
| s02 Tool Use | 具名工具、参数、未知工具与响应结构；实际文件和 Shell | `tests/test_integrated_runtime.py` |
| s03 Permission | 未预授权命令与越界路径在执行前拒绝 | 两次真实拒绝任务；权限单测 |
| s04 Hooks | 首次拒绝停止后续 pre hook，允许调用才执行 post hook | `test_s04_hooks_stop...` |
| s05 TodoWrite | 非法状态不覆盖原清单；原生 JSON/字面量兼容 | 同上；真实修复计划 |
| s06 Subagent | 独立历史、不继承主会话秘密、权限保留、仅返回摘要 | `test_s06_one_shot...`；组合任务 |
| s07 Skill Loading | 目录只给摘要，正文按需加载，外部符号链接排除 | `test_s07_skill...`；真实 repair 加载 |
| s08 Context Compact | 大输出落盘、未读结果保留、归档与调用配对、摘要不授权；重试与截断分支 | `test_s08_*`；真实手动 compact |
| s09 Memory | 持久/当前任务过滤、去重、磁盘重读、合并失败回滚 | `test_s09_*`；真实记忆记录 |
| s10 Task System | 依赖、环、owner；两进程竞争只能一人认领；绑定不能覆盖认领 | `test_s10_*`；实际文件锁 |
| s11 Background | 真命令退出码、一次通知、SIGTERM 清理原进程组 | `test_s11_*`；组合任务实际后台测试 |
| s12 Cron Scheduler | 真实时钟唤醒与写文件；持久交付重载、去重恢复和确认 | `test_s12_*`；组合任务一次性调度 |
| s13 Agent Teams | 同一队友 WORK/IDLE/再认领；任务版本审批；伪造消息拒绝；实际 worktree 租约与保留分支 | `test_s13_*`；组合任务评审与关机 |
| s14 MCP Plugin | 下一轮发现工具；宿主授权；名字冲突/长度；参数不能替换绑定客户端 | `test_s14_*`；挂载知识库查询 |
| s15 Integrated Harness | 同一入口组合；真实 trace 导出；独立状态合同；观测不展开 Runtime 对象 | `test_s15_*`；正常、错误、边界实验 |
| s16 Workflow Runtime | schema 一次重试与计费、零预算不请求、并行失败等待成功分支、journal 中断续跑 | `test_s16_*`、跨进程真实恢复实验 |
| s17 Goal Loop | 后台 defer；严格布尔；异常、续轮上限、恢复、成功与 impossible | `test_s17_*`；真实公开目标审查 |

完整测试节点在 [机器清单](../references/e16-capability-contracts.json)。控制实验明确使用模型夹具，供应商请求数为0；磁盘、Git、进程、线程、锁与时钟仍真实执行。真实模型组合任务与这组控制共同提供证据，两者计数分别保存。

## 一个在并发实验中发现的问题

原生 `create_worktree` 先读取待领取 Task，再执行 Git，最后保存带 worktree 的 Task。它只持有进程内锁；另一个进程可以在 Git 期间领取任务并写入 owner。绑定方随后保存旧对象，把这次认领覆盖回 `pending`。

失败实验先在真实 `git worktree add` 前暂停绑定，让另一个 Python 进程完成认领，再继续绑定。原始结果确实丢失 owner，保留在失败日志中。课程适配器现在把整个绑定操作放进原生 `task_store_lock`，与认领使用同一把跨进程锁。修复后的同一个实验检查到锁已持有、owner 保留，领取者 cwd 指向绑定目录。代价是 Git 创建期间其他任务写操作等待这把锁，适用于本课程的小任务板。

## 保留的边界

原生 TodoWrite 接受空清单和多个进行中项目；第13课的严格教学实现与它不同。释放 assignment 后 plan gate 会回到 `not_required`，因此下一项任务要重新声明审批要求。

原生 workflow 的 `SimpleJsonSchema` 只实现一个小子集，`integer` 分支也接受浮点数；它不能当作完整 JSON Schema 校验器。原生 durable cron 加载器遇到损坏内容会吞掉异常，不能承诺损坏恢复。原生 GoalController 可以从事件恢复条件，当前 CLI 不提供跨进程恢复整个会话。

本机模型桥不强制供应商 `max_tokens`，也没有 logprobs，所以截断、429/529 和上下文超长分支使用明确的协议夹具。模型版本与费用未知，报告保留为空。MCP 使用上游的进程内 stand-in：docs 读取真实挂载文件，deploy 示例仍模拟。工作目录和进程组分别提供 working copy 隔离与生命周期清理，不构成通用的恶意代码隔离保证。
