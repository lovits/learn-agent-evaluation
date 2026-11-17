# 第16课验收记录

验收对象是综合编程 Agent、状态与评分链，范围以冻结协议和 [17项能力契约](../references/e16-capability-contracts.json) 为准。正式发布的 GitHub、飞书与 CI 回读结果在最终交付清单中补齐。

| 要求 | 已取得的实际证据 |
|---|---|
| 六部分正文与六步关键代码 | [正文](../lessons/e16_regression/README.zh.md)，代码外2245个汉字；短片段标明节选并链接完整入口 |
| PocketFlow实际组织 | 固定原版四节点，生成模型实际请求一次；[输入哈希与节点](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/e16-provenance.json) |
| humanizer全篇审校 | 六节、六步，共12单元；66个代码/行内代码/链接目标按顺序不变；[审校记录](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/e16-humanizer.json) |
| 真实组合任务 | Docker实际33次模型响应、八阶段、28条原生trace，首轮失败另存 |
| 独立业务与原生状态 | 断网验收两个API的44条输入、原测试、调用关系与实际状态，[结果](../integrated_agent/evidence/composed-evaluation.json)通过 |
| 错误与边界 | 两个新工作区各3次真实响应，实际工具拒绝与文件保持分别验收通过 |
| 17项机制 | 原生控制检查实际文件、Git、锁、进程与线程；供应商请求数0；与真实组合证据分别记录 |
| 双框架原生评分 | 两轮共20次真实裁判响应、0评分错误；工具规则比较0裁判请求；保存每条声明与verdict |
| 工作流恢复 | 真实并行两检查后注入中断，换进程命中两条日志，仅新增一次验证；损坏日志控制另存 |
| bad case进入回归 | 实际缺测试上下文的旧评审持续拦截，采样漏命令修订前后均保留 |
| 结构图 | 当前图与实际接线对应，15节点/16边，PNG已目视检查，原生draw.io XML保留 |
| 练习与答案分开 | [12道练习](../lessons/e16_regression/exercises.md)与[参考答案](../lessons/e16_regression/solutions.md) |

## 实际 Docker 入口

组合任务使用 [scenario.py](../integrated_agent/scenario.py)，真实模型由宿主已登录 Codex 提供；容器只执行课程项目工具。知识目录只读挂载，工作区和原始报告持久化。模型登录凭据与独立答案没有进入应用容器。

验收使用 `integrated_agent.verify --profile composed`，在断网容器中只读挂载工作区。状态合同与业务合同分开；失败、未评分与未知模型版本保持各自状态。模型版本与费用没有提供，报告留空。

应用镜像为 `sha256:cd69385a64289e9fe7d0b44e8a3d7111e873c55574a0c54ee3801044209d3bc0`；第一轮评分镜像为 `sha256:b6a2bdc5dd6a0b7e7afae063e1759cc88e323a04195ce7a2ca8018994020a92b`；第二轮评分镜像为 `sha256:7c3dbf9d84011808d0da21ed9d3ad4f23b3d1c83d9047b58561f1a459081813b`。每次对应代码/输入哈希已先冻结，后来文档发布使用新的构建，不把历史镜像说成当前最终镜像。

## 失败记录怎样处理

首次组合实验保留退出码137、started报告与精确源码；原容器自动移除，无法回查 OOMKilled，根因只记录为源码分析与回归支持的假设。修正观测范围后使用新目录、新协议重新执行，旧记录未覆盖。

并发实验实际复现绑定覆盖认领；修复适配器事务后，同一实验重测通过。局部测试中的格式断言和异步日志读取问题也保留私有执行日志，没有将它们算作供应商失败。首轮采样省略工具参数，已保存原评分并冻结修订版重评；不宣称这是留出集提升。

## 范围限制

这是一套可复核的教学项目。39次本轮应用/支持响应、20次裁判响应和有限业务输入，不能证明一般任务可靠性或裁判普遍准确。队友评审内容还需要具体语义复核，完成状态与上下文资格不能自动通过它。

原生 TodoWrite、schema、cron加载、Goal恢复、MCP stand-in 和进程组边界详见 [能力说明](../integrated_agent/capabilities.md)。这些能力的存在与已测分支分别列出，没有把源文件原样加载解释为逐版本、逐平台全面等价。
