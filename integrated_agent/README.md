# 综合编程 Agent 与独立评测项目

固定版本的上游集成核心已经接入，真实组合任务、错误与边界实验通过了对应独立验收。[第16课](../lessons/e16_regression/README.zh.md)沿六步解释接线、采样与回归，[总体架构](architecture.md)展开完整调用链，[17项能力说明](capabilities.md)逐项区分真实任务、夹具控制和保留的限制。

## 代码从哪里来

`vendor/learn_claude_code/` 保留原样的 s09记忆、s15集成、s16工作流、s17目标循环四个模块和MIT声明。[来源与文件哈希](https://github.com/lovits/learn-agent-evaluation/blob/main/vendor/learn_claude_code/provenance.json)对应commit `448c75bb596917ad196cc1fb7558f459c5c50fdd`。原始集成结构见[上游源码](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s15_integrated_harness/code.py)。

课程适配集中在以下文件，前15课的Agent实现保留独立入口。

| 文件 | 职责 |
|---|---|
| [runtime.py](runtime.py) | 加载原生机制，记录真正发送的模型输入与响应，把公开目标审查放在返回边界 |
| [transport.py](transport.py) | 让宿主Codex响应进入原生Messages协议；宿主执行模型，容器执行项目工具 |
| [workflows.py](workflows.py) | 注册可信的审查脚本，执行并行检查、记录journal，再验证候选意见 |
| [workflow_demo.py](workflow_demo.py) | 独立运行、中断和跨进程恢复工作流组件 |
| [verify.py](verify.py)、[state.py](state.py)、[negative.py](negative.py) | 断网读取实际工作区，分别检查基础/组合任务的业务、原生状态与实际拒绝行为 |
| [gates.py](gates.py) | 已知测试文件没有进入审查输入时，阻止把覆盖意见当成合格评审 |
| [scenario.py](scenario.py) | 讲师声明阶段的组合实验，串起主轮、子任务、持久队友、后台、真实调度与工作流 |
| [traces.py](traces.py) | 保存真实原生trace，保留同步父子关系与队友线程独立根 |

MCP沿用上游的进程内工具适配方式。docs工具已经改为读取真实挂载目录，返回文档和哈希；上游deploy示例仍是模拟工具，没有实际部署服务。

## 运行一个任务

先在宿主机的独立终端启动模型桥：

```bash
python3 tools/integrated_bridge.py
```

在项目根目录构建环境，并准备一个新的练习工作区。以下代码只复制公开练习文件；目录已存在时会停止：

```bash
docker compose build course
python3 - <<'PY'
import json
from pathlib import Path
case = json.loads(Path('integrated_agent/cases/foundation.json').read_text())
workspace = Path('workspaces/my-project')
workspace.mkdir()
for name, text in case['files'].items():
    (workspace / name).write_text(text)
PY
```

Agent先读规范，再修改实现。下面只预授权实际回归所用的一条命令：

```bash
docker compose --profile capstone run --rm -T agent \
  'Load repair skill, write todos, connect docs, read shipping v3, repair both APIs, preserve original tests and actually run python3 -m unittest -q.' \
  --workspace /data/workspaces/my-project \
  --report /data/runs/my-project.json \
  --approve-command 'python3 -m unittest -q' \
  --goal 'Both APIs follow the mounted contract, original tests are preserved, and the actual unittest command has passed.'
```

报告拒绝覆盖已有文件。`returned` 只表示Agent已返回，独立验收仍是另外一步：

```bash
docker compose --profile verify run --rm -T --entrypoint python verifier \
  -m integrated_agent.verify --workspace /data/workspaces/my-project \
  --criteria /verification/e16-foundation.json \
  --report /data/runs/my-project-evaluation.json
```

这份验收条件适用于公开的v3基础练习。应用容器不挂载答案，验收容器断网并只读挂载工作区；基础profile接受业务四文件与经过格式、索引核对的原生记忆记录。自己的项目需要自己的业务与状态合同。

完整组合实验使用全新目录，讲师脚本安排阶段，模型产生实际响应和工具动作。先完成上面的构建，再执行：

```bash
docker compose --profile capstone run --rm -T --entrypoint python agent \
  -m integrated_agent.scenario --workspace /data/workspaces/my-capstone \
  --report /data/runs/my-capstone.json
docker compose --profile verify run --rm -T --entrypoint python verifier \
  -m integrated_agent.verify --profile composed \
  --workspace /data/workspaces/my-capstone \
  --criteria /verification/e16-foundation.json \
  --report /data/runs/my-capstone-evaluation.json
```

组合验收另外核对实际任务、已释放worktree、保留评审分支、记忆索引、定时交付和workflow日志。阶段排序、当前审批、Git提交归讲师脚本；评审内容的语义正确性仍需按具体发现复核。双框架评分命令见[第16课](../lessons/e16_regression/README.zh.md)。

## 挂载与模型边界

`agent`服务默认把 `knowledge_base/e16/` 只读挂到 `/data/knowledge`，工作区和报告分别持久化到宿主的 `workspaces/`、`runs/`。可用 `INTEGRATED_KNOWLEDGE_DIR` 指定自己的知识目录。

模型登录留在宿主。容器中的 `course-local-codex` 是接口别名，不能当成供应商模型版本；精确版本与实际账单未知。桥接只支持非流式请求，不硬性实施供应商的 `max_tokens` 参数，也不提供logprobs。截断、重试和上下文错误分支已用明确的协议夹具验证，供应商请求数为0。

一个Runtime对应一个工作区和一个进程。任务、记忆和工作流日志落盘；队友线程本身不跨进程存活。批处理只接受逐条预授权的Shell命令，异步轮仍遵守上游的交互权限限制。公开目标裁判只读取对话证据，最终业务门禁由外部验收器负责。

## 已实际得到的证据

基础任务使用9次工作模型响应、1次记忆支持响应和1次公开目标审查，修改了两处实现，实际执行五个原测试。断网独立检查覆盖两个API的44条输入，两份测试保持原字节，两条原生记忆通过格式和索引检查。见[原始运行](evidence/foundation-agent.json)、[独立结果](evidence/foundation-evaluation.json)与[冻结协议](../references/e16-foundation-v2-protocol.json)。

首次连接失败和旧验收口径失败均保留，分别是适配器空鉴权值错误、旧验收器未包含原生记忆状态合同。两条记忆保留原样，修正状态合同后，仅重新执行独立验收。

工作流先真实并行请求两个检查，讲师在日志写入后注入中断。新进程用同一run ID恢复，两个检查命中缓存，只新请求一次验证。见[中断报告](evidence/workflow-interrupted.json)、[恢复报告](evidence/workflow-resumed.json)、[journal](evidence/workflow.journal.jsonl)与[协议](../references/e16-workflow-component-protocol.json)。

这次审查只看了两个实现文件，没有看到项目中的两个测试文件。工作流虽然完成，部分“没有测试”的项目级判断仍证据不足，见[门禁结果](evidence/context-gate.json)。这个真实bad case已经进入CI，完整上下文只能使意见具备接受语义复核的条件，不能自动证明意见正确。

本轮[组合任务](evidence/composed-agent.json)实际33次响应、28条原生trace，业务44输入与完整状态[独立通过](evidence/composed-evaluation.json)。[命令拒绝](evidence/denial-evaluation.json)和[越界拒绝](evidence/boundary-evaluation.json)各有真实模型尝试及文件保持证据。两轮实际评分共20次裁判响应，修订只补采样中的工具参数，原Agent不重跑；[前后结果](../lessons/e16_regression/run_summary.md)完整保留。

[第16课验收](../docs/e16-validation.md)与[能力范围](capabilities.md)列出每项适用条件。工作目录、进程组、最小schema和课程里的有限业务输入均有明确边界，不扩展成一般可靠性或通用安全承诺。
