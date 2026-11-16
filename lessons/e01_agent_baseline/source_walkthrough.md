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
