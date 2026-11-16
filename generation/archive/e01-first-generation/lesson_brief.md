# 第1课教材生成要求

为《从Learn Claude Code编程Agent学评测》生成e01完整中文教材。读者会Python，理解RAG/Agent。
当前课只介绍最小agent_loop与Bash，不加入文件专用工具、检索、记忆、计划、任务系统、子Agent或协作。

目标：能分清模型决策、容器工具执行与独立验收；运行真实任务，解释模型停止不等于任务通过。
材料中包含真实code.py、eval.py、4条公开任务、实际example_report、源码导读与练习答案。
所有运行数字、model_requests、Bash次数和通过情况只能从实际报告读取。不得编造准确率或费用。

按Learn Claude Code方式写：具体问题→最小解决机制→逐步代码解释→与起点的变化→评测合同→运行实验→
结果解释→DeepEval/Ragas依据与源码阅读→练习验收→下一课。正文重点解释核心循环与run_bash，
模型传输、CLI与报告保存作为运行配套说明，不能隐藏提前实现的复杂Agent。

必须说明：
- 原版s01是Anthropic tool_use/tool_result，本课为复用本机登录，以JSON tool_calls/answer传输模型动作。
- Codex CLI仅作为模型入口，自身工具关闭，练习目录不在宿主机模型进程中；实际命令由Docker内课程循环执行。
- 第一课的评分是程序断言；DeepEval/Ragas的样本、运行与结果组织作方法依据，框架适配后续逐步引入。
- 每次任务独立workspace；verifier独立容器无网络、workspace只读，私有标准不挂载到Agent且不进入其镜像。
- finished是模型停止，passed是验收；command_error任务是观察原始错误，工具非零退出与任务通过可以共存。
- hello任务明确限定一条print语句，AST合同不是任意代码功能证明；最终解释语义不评分。
- 预设模型只用于单元测试，合成假报成功用于测试验收器；不要把它们计入真实模型表现。
- CLI如果不返回确切model ID就保留null，不把默认选择描述为固定型号；token usage不等于已知费用。

实际启动命令：
宿主机保持 python3 tools/model_bridge.py 运行；另一终端 docker compose up --build -d。
真实任务：docker compose run --rm -T course run --case create_and_run
独立验收：docker compose --profile verify run --rm -T verifier verify --run-id 实际run_id
批量实验：python3 tools/run_e01.py
阅读入口：http://localhost:8765/lesson。

链接只指向已给材料中的真实代码/资料，cases.jsonl可链接；私有criteria路径用行内代码，不做网页链接。
不要写指向尚未创建的未来课文件的链接；来源引用固定commit链接。
使用普通Markdown、表格、短Python/命令片段；不要使用图片、Mermaid或需要插件的LaTex。
练习与答案独立文件已有内容，正文可概括并链接。末尾给明确学习验收清单和下一课预告。
仅输出当前课Markdown，不输出隐藏思维或项目已全部完成的宣称。
