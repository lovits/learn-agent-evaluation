# 第1课改写要求：像Learn Claude Code一样带读

本次只改写e01教材，代码、四条公开任务、原始真实example_report不变。原稿和首次生成凭证已归档。不制造本次新实测，数字若出现必须说明来自历史记录。读者会Python，第一次系统学习Agent评测。

按references/e01-rewrite-plan.md的写作、组织和配图方式。标题《第1课：一个循环、一个Bash，再加独立验收》。一级正文顺序固定：问题、解决方案、工作原理、相对一次模型问答的变更、试一下、接下来。不要22节指标清单、学习验收汇报或先大段术语解释。讲解要像同事带着写：遇到什么困难，先加哪几行，为什么加，结果怎样回到下一步。正文约2500至3500中文字，重点清楚，不堆完整代码。

问题：用户要创建只有一条print("Hello, World!")的hello.py并运行。模型只回复完成，文件和运行未必存在。先让动作真实发生，再独立检查它。

解决方案紧挨图1，使用精确Markdown图片路径：
![Agent执行循环](images/agent-loop.png)
可将图片包在同路径链接内供放大。两张PNG已真实制作，不是占位。图2在工作原理引入验收器时插入：
![独立验收代码结构](images/evaluation-path.png)
两图只解释关键部分：图1模型/宿主机与Docker中Harness分开，call_model → tool_calls判停 → run_bash → messages回填；图2tools/run_e01.py启动Agent后，再启动eval.py的evaluate/check_rule，读取events和只读workspace，按私有标准给passed。H按Harness执行框架理解，属于Agent系统，不是模型本身。不要再造一张大全景或引用不存在图片。

工作原理分6至7个短步骤，每步给约5至12行来自实际code.py或eval.py的教学片段，并说明函数内部摘录/省略日志与异常记录，不能把删节片段当独立完整程序，也不编造不在源码里的函数。完整代码分别链接。
1. messages只放用户任务；解释它是模型可见历史。
2. model(messages)取reply，追加assistant消息；原版s01为Anthropic tool_use/tool_result，本课为复用本机登录，用JSON tool_calls/answer传动作。Codex CLI自身工具关闭、只生成动作，实际Bash在Docker运行。
3. tool_calls为空返回finished；这只是判停。原版while True，本课for range(max_steps)加预算，耗尽step_limit，模型传输错model_error，细节留源码导读。
4. run_bash(command,workspace)执行真实命令。cwd=workspace是关键，保存stdout、stderr、exit_code、status。命令超时/截断/阻断词表的实现细节可链接附页，不在主文贴完整Popen配置。
5. 收集results并追加role=tool消息，下一轮模型读到真结果。events另存过程。新workspace避免上次遗留文件误通过，不声称内核级隔离。
6. 转到图2，独立验收器看文件/轨迹。evaluate先检查finished和有Bash，再按任务逐条check_rule，最后all(checks)得到passed。hello同时核实成功输出与单条print的AST要求。AST接受引号、注释和普通空白变化，不是任意代码语义证明；自动合同也不是通用防投机执行证明。私有标准只给verifier，workspace只读、无网络，不调用模型，不重跑生成程序。

用一小段讲command_error：任务是观察原脚本错误而非修复，所以工具非零退出与任务passed可共存。预设模型只用于单元测试，合成假完成只用于测试验收器，不算真实模型表现。code.py/eval.py本课没有DeepEval/Ragas原生裁判调用，两框架仅作为样本、运行与结果组织的依据，来源在source_walkthrough.md，不把程序断言冒充SDK指标。

历史example_report只在需要时给一个具体例子或链接。不要把4/4、8次、4条命令当教材主线；这些是首次保存的报告，不是本次文档改写新跑。真实结果不编造。最终解释的语义、通用编码能力、未返回的确切模型ID和未知费用不在评分范围。

试一下：宿主机终端保持python3 tools/model_bridge.py运行；另一个终端docker compose up --build -d。
单任务：docker compose run --rm -T course run --case create_and_run
独立验收：docker compose --profile verify run --rm -T verifier verify --run-id 实际run_id（明确用刚返回的32位编号替换占位词）。报告e01-实际run_id.json与grade-e01-实际run_id.json分别看。
批量：python3 tools/run_e01.py（不加--publish-example，保留教材固定报告）。本地阅读http://localhost:8765/lesson。
给三个具体观察点：一次动作何时变成真实命令；真实stdout/stderr如何回到模型；finished与passed来自哪个函数。链接exercises.md、solutions.md、source_walkthrough.md、example_report.json；不要提前粘集成Agent或未来机制。

接下来只自然提出第2课问题：现在读写文件都要拼Bash，接下来把意图变成具名工具，再讲权限和轨迹。语气直接、具体、少机械总结，图片、文字和代码相邻。
