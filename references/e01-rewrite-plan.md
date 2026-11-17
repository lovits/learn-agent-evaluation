# 第1课内容与改造依据

核心问题是“模型停下了，任务就完成了吗？”。从创建并运行 hello.py 开始，沿任务、模型动作、真实 Bash、结果回填和独立评分讲解。课堂只出现最小循环与 Bash，任务规则读实际文件和执行事件。

对照 Learn Claude Code 固定版本的 [s01 正文](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s01_agent_loop/README.zh.md)和 [s01 循环](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s01_agent_loop/code.py)，教材以问题、解决方案、工作原理、变更内容和试一试衔接。完整函数放代码文件，讲解只取关键片段。

`code.py` 保留最小循环与运行入口；`eval_course/runtime.py` 收拢已有的模型传输、Bash 和初始目录处理；`eval.py` 保留独立规则评分。图中的函数调用关系继续适用，辅助函数完整位置以源码导读为准。两张现有结构图只服务于当前执行和评分链。

公开任务保持四种目标：创建并运行、列文件、运行已有程序、观察错误。任务难度不以引入更多模块增加。本次会重新运行模型驱动的 Docker 任务；既有证据保留来源，不将构造反例当作真实模型表现。

第2课继续回答一次运行怎样形成可追溯的评测样本。具名工具和必要权限到那一课再加入。
