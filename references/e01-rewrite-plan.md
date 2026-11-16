# 第1课改写与配图依据

以固定Learn Claude Code s01的中文正文和Agent Loop图为主要参考，沿用第7课已经确认的语气与组织：问题、解决方案、工作原理、相对一次模型问答的变更、试一下、接下来。每段先说明困惑或作用，再紧接5至12行真实代码片段。用“我们先把消息存下来”“命令真正执行在这里”这样的直接带读句，不写验收汇报或指标百科。

原版有Agent Loop图，本课也在方案处给图，但内容反映本项目的实际边界：本机Codex只是模型入口，Docker中的code.py执行Bash；独立eval.py检查文件与记录。图1讲执行回路，图2讲评测代码结构。H按Harness（执行框架）理解，属于Agent系统中的执行层，与模型分开。

两张图的图片路径固定：images/agent-loop.png、images/evaluation-path.png。正文使用普通Markdown图片，紧挨相关知识/代码，可用点击图片查看原尺寸的链接。不要Mermaid源码、图片占位或编造不存在的图片。只画关键节点，不画完整项目/未来机制。PNG与可编辑draw.io源文件均在images目录；本机没有draw.io Desktop，使用同一图数据生成PNG预览，不冒称其桌面导出。

建议主线：用户让模型创建并运行hello.py；模型回复完成不足以验收；加入最小循环与Bash，再独立验收。工作原理依次讲messages、model调用、tool_calls判停、run_bash、结果回填、evaluate/check_rule。图1放在方案处，图2放在引入验收器时。保留max_steps、step_limit和command_error特殊目标，但细节链接源码导读。

内容边界：原执行代码、公开任务、初始真实example_report不改。本次只重写教材和配图，不新增真实模型运行或把历史4/4说成本次成绩。首次生成稿与凭证已归档，旧发布稿可通过Git历史查阅。实现、样本、历史报告哈希将在交付时核对。

上游：[s01正文](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s01_agent_loop/README.zh.md)、[s01图片](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s01_agent_loop/images/agent-loop.svg)。
