# 第1课源码导读：模型、执行与验收

## 从原版循环到本课

上游依据：[Learn Claude Code s01](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s01_agent_loop/code.py)。
原版agent_loop把消息发给模型，提取tool_use，执行run_bash，把tool_result追加到历史；没有工具调用就返回。

本课[code.py](code.py)保持这一结构，只提供Bash。模型传输改为本机Codex的结构化JSON响应：
`tool_calls`为空时停止；非空时逐个执行command。它支持一轮多个Bash调用，结果按顺序返回。
这是一份课程改编的最小Harness，不将官方Claude Code或Codex产品本身当成被测执行器。

## 三个角色

- 模型：给出下一步Bash命令或最终回答。本机登录桥只处理模型请求，Codex自身工具被关闭。
- Agent循环：在Docker练习目录执行真实Bash，再把stdout、stderr和exit_code给模型。
- 验收器：Agent结束后，单独容器读取真实文件和记录，用任务合同判定通过与否。

模型桥不接触练习目录，登录凭据留在宿主机。每次模型请求记录耗时、CLI选择方式、可获得的token usage和工具审计。
若CLI未回传确切模型ID，reported_model保持null，不编造型号或费用。

## 关键函数

`call_model`只负责HTTP传输和动作结构检查；`run_bash`只负责命令执行；`agent_loop`组织消息、工具结果与停止。
`prepare_workspace`为每条任务建立独立目录，避免上次运行的文件让下一次误通过。
模型错误和步数上限单独标记，不当作任务成功。

原版Bash的教学阻断词保留。超时时本课终止命令进程组，并分开保存stdout/stderr/退出码；
输出截断会标记truncated。它们是使实验可观察、可结束的基础处理，完整权限机制留到第2课。

## 验收代码怎样工作

[eval.py](eval.py)只读工作目录，不执行模型生成的程序，也不调用模型。
它检查模型是否停止、是否真正调用Bash，以及具体任务所需的成功输出、失败输出、文件哈希或Python AST。
hello任务明确要求一条print语句，因此AST合同接受引号和注释变化，但不接受额外语句。
这是固定教学任务的验收，不是任意Python程序的功能等价证明。

验收标准文件在evaluation_private/e01.json，只挂载到独立verifier容器。
Agent容器没有这份文件；工作目录在验收容器只读，验收结果写入runs。
`finished`只表示模型没有继续调用工具；`passed`才是独立验收是否通过。
command_error任务的目标是如实观察原脚本失败，所以工具非零退出与任务通过可以同时成立。
本课不评分最终中文解释的语义质量；该维度在后续裁判与答案质量课程展开。

## DeepEval与Ragas在这一课的依据

先区分预期任务与实际运行，再评分和保存，是两框架共同的实验组织思路。
本课用程序断言确定文件与命令事实；后续课程再逐步引入框架样本适配和模型裁判。

- [DeepEval dataset实现](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/dataset/dataset.py)：数据、goldens与运行结果的角色。
- [DeepEval evaluation实现](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/evaluate/evaluate.py)：评测执行与结果组织。
- [Ragas experiment实现](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/experiment.py)：应用运行、逐样本评价与实验记录。

## 本课边界

没有专用文件工具、知识检索、记忆、计划、任务图、子Agent或团队。
知识库挂载已准备，但第1课不检索它。共享模块只处理记录与阅读，不藏入后续Agent能力。

## Bash与消息的细节

run_bash以cwd=workspace启动/bin/bash，分开保存stdout、stderr、exit_code与status；超时会终止命令进程组，输出截断会标记truncated。教学阻断词表不是完整安全体系。每条任务的新workspace用于避免遗留文件误通过，不等于内核级隔离。

模型动作结构经过call_model检查：answer为字符串、tool_calls为列表，每个command非空。agent_loop用max_steps限制循环，空tool_calls返回finished，用完预算返回step_limit，模型传输或结构错误另记model_error。工具失败的stderr/退出码照常回填，模型可以继续观察；预算耗尽和传输失败不按通过处理。

私有合同只给verifier，不能为提高分数而看结果后倒推标准。successful_stdout_contains必须对应成功工具输出；error_contains必须对应非零退出和stderr；file_sha256检查不可修改脚本；python_ast用ast.dump对照明确的单语句要求，接受引号、注释和空白变化，拒绝额外语句。它不证明任意程序功能等价，输出检查也不是完整防投机证明。

本课保留DeepEval的数据集/运行组织与Ragas实验代码作为方法依据，使用的是确定性程序断言，没有调用它们的LLM裁判。原始运行的具体证据见[实验记录](run_summary.md)，不把文档更新当成重新运行。

## 读图时对应哪些代码

正文图1只展开正常回路：messages → call_model → 空调用判停或run_bash → 把结果回填messages。异常和预算分支由文字及完整代码解释。图2对应tools/run_e01.py先启动Agent、再启动独立verifier；eval.py的evaluate汇集checks，check_rule读取工具记录或文件内容。

图中的代码名都对应实际实现。两张图有[执行循环源文件](https://github.com/lovits/learn-agent-evaluation/blob/main/lessons/e01_agent_baseline/images/agent-loop.drawio)和[评测结构源文件](https://github.com/lovits/learn-agent-evaluation/blob/main/lessons/e01_agent_baseline/images/evaluation-path.drawio)，可在draw.io编辑。图示只讲本课关键边界，没有加入RAG、文件专用工具或后续Agent机制。
