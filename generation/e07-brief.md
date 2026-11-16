# 第7课：按Learn Claude Code的正文方式编写

本轮用户再次强调正文必须像Learn Claude Code一样带读知识点与代码。优先遵守references/e07-teaching-pattern.md中的实际阅读分析。不要延续上一课先列术语、再报分数的长篇介绍。写约2500至3500中文字的中文动手课程，标题《第7课：RAG故障定位，只改一个位置》。语气平实自然，代码紧接解释；公式服务问题，不做指标百科。

一级正文顺序固定：问题、解决方案、工作原理、相对第6课的变更、试一下、接下来。工作原理下分5至6个小步骤，每步放一段约5至15行、对应真实源码的短片段，先说这一段为何需要，再讲输入、输出和接入位置。不要在开头粘完整Agent，不凭空创造函数或把示意代码冒充完整可运行入口。可从完整函数摘片段，但说明省略日志；完整code.py和eval.py链接必须提供。不要Mermaid、图片占位、装饰性标语或大量加粗。

问题：同样漏了最大上传字节数，可能资料里就没有，也可能检索丢了，还可能模型拿到资料却写错。仅看一个答案分数无法区分。从这个具体场景进入。

解决方案：固定任务与query，在文档副本、返回命中、生成指令三个位置一次改变一处。六组baseline、drop_doc、drop_hit、add_old、add_noise、bad_prompt。实验记录expected_observation是人工预期，不能当实测结论。真实结果只按run_summary写。

工作原理需要逐段带读：
1. 固定EXPECTED（三个业务字段，synthetic v1：X-Project-Token、1048576、413）与固定QUERY。任务要求写upload_notes.json，信息缺失填null，不猜。读者已学过工具和检索，本课只加故障位置，不加新工具。
2. 临时资料副本中drop_doc先移除limits。原始只读挂载不改；运行后核对原文哈希。拿不到与取不到不同。
3. fault_dispatch先保存检索before，再按case过滤drop_hit或追加虚拟旧文档/无关文档，最后把after作为真正tool_result交模型。其余工具交原dispatch，固定query校验避免另一变量悄悄变化。
4. 复用e04 agent_loop，只增加默认等于原dispatch的tool_dispatch参数；工具执行那一行改为调用它。调用模型、权限、工具结果回填、判停维持原流程。生成faulty_generation只改变宿主机生成指令，不能手改生成答案；模型入口源码有明确错误兼容限额524288的指令。
5. inspect_artifact独立读实际文件，校验JSON类型并比较三个字段。null是缺信息。diagnose按实际available IDs、after IDs、字段匹配定位，而不是按case.id分配预设根因。generation_mismatch_requires_review仍需复核，不说自动证明因果。
6. 最后才引入辅助评分：DeepEval ContextualRelevancy高不代表找全或用对；NoiseSensitivity低为好，按reference支持关系归relevant/irrelevant，不是话题相似。错误没被任一context支持时两个模式都可能0。正文用少量说明配真实例子；详细prompt/schema/矩阵/聚合链接source_walkthrough。可以给测试夹具两组分数1/3的手算，但明确构造演示，不冒充Agent成绩。

评分投影：两个SDK只评价实际文件的三个业务字段文字投影，不评价sources或最后完成回执；原始轨迹与文件保留。本课重新真实执行六组Agent，不是回放旧回答。原生NoiseSensitivity运行relevant，irrelevant对同组矩阵重聚合，不多调用模型。

相对第6课用简短变更表：reference、工具/权限/循环保留；原来构造回答/旧产物再评，现在真实干预并重跑；仅增加故障开关、阶段快照和噪声指标。模型抽样未固定，不能因单次噪声未生效就说永远免疫，也不能用一次失败证明普遍因果。

试一下命令：宿主机python3 tools/model_bridge.py（8766）和python3 tools/judge_bridge.py（8768）保持运行，已有登录凭据不入容器；另开终端docker compose build，然后docker compose run --rm -T --entrypoint python course -m lessons.e07_failure_diagnosis.code，再运行docker compose run --rm -T --entrypoint python course -m lessons.e07_failure_diagnosis.eval。命令分别写runs/e07-agents.json与runs/e07-evaluation.json，重跑覆盖，先另存。阅读docker compose up -d，http://localhost:8765/lesson7。

给3个试验观察题，指向available_documents、retrievals.before/after、artifact、events，能在实际报告中找到差异。不要把请求数和测试数当正文主线，完整实验与验收留链接。最后自然过渡第8课评测数据集：把有证据的bad case保存为明确任务和标准，而非只存低分。

初次评分存在输入表达问题，已单列保存：reference漏写POST /upload，声明生成结合问题后带端点，而最后NLI只看reference，基线NoiseSensitivity relevant竟为1。另把null直接写None会被解释为系统没有限制。修订协议补端点并把null明确为检索范围未知；只重新评分，没有改或重跑Agent。这段在正文最多一小段提醒“评分输入也会出问题”，详细过程与两轮数值留run_summary/source_walkthrough，不要抢走三层故障定位主线。

版本语境必须交代：本课固定回到第4课挂载资料的合成v1上传合同（1MiB）。第6课的v2（2MiB）是另一个受控版本，不拿它给本课v1文档判错。保留的是版本化reference方法，不是说第6课与本课的参考文本完全相同。
