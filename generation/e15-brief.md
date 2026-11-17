# 第15课制作约束：裁判校准

为会Python、了解RAG与Agent的中文读者写本课。按Learn Claude Code六部分：问题、解决方案、工作原理、相对上一课的变更、试一下、接下来。正文2000–3500中文字符（代码除外），自然、直接、像带读真实代码；不写生成工具的过程。工作原理六个加粗步骤，每步给真实短代码，解释输入、输出、接入点和出错的后果。代码片段须标明节选/省略，链接完整code.py/eval.py，不能写伪入口。不要整篇堆数字或自夸“体系化”。不复制上游原文。

问题承接14课：产物通过、效率裁判却低分，裁判是否读对证据？本课保持被测Agent及工具不变，固定讲师构造的报告与合同，评测裁判本身。构造16条标量记录，不是16次Agent运行。报告准确不等于修复完成：失败记录被诚实报告，也可报告准确。human_reviewed始终false，不可冒充人工金标准/人类一致率。

解决方案按样本家族划分train/dev/holdout=4/4/8。两版G-Eval只在dev比较，候选须完整评分，优先少误放行、再比较agreement，同分按预定规则选v2；选择先持久化，之后留出评分。作者知道构造方法，不宣称双盲。演示v2明确预期值、独立验证状态、诚实失败、篇幅语言与身份无关；v1故意欠明确。冻结标准后不能根据留出结果继续改。

六步：
1. 读取make_cases/validate_cases，讲家族隔离、明确合同和未审核标签。短代码只取真实family leakage或label校验，不造字段。
2. GEval真实evaluation_steps/evaluation_params/model/threshold/async_mode配置。连续0–1阈值0.7、schema/logprob自定义后端回退另读源码。不能声称自定义Codex适配器用了概率加权。
3. select_version与先atomic_save后holdout评分，讲开发选择/留出验证，结果不理想保留。
4. 原生DiscreteMetric.align + validate_alignment。None embedding是原生最近四示例回退，0次对齐模型请求，不是向量检索或权重训练。源码导读保留旧embedding wrapper接口不匹配、原生分别过滤None风险、额外scikit-learn依赖。
5. 原生ReportPrompt.adapt("chinese", llm, adapt_instruction=True)，2个非空示例，数字0/1标签避免翻译枚举。原提示/中文提示同schema、同四个正确/错误样本比较；language字段变化不能证明翻译成功，空示例分支不翻译指令。结构与数值保留不足以证明语义无漂移，人工复核仍待进行。
6. alignment/equivalent_pairs和A/B反序映射，讲误放行、误拒绝、覆盖率、κ退化null；长篇、中英改写、作者身份线索。来源声明未经证实，精确裁判模型未知，不能证明真实自偏好。交换顺序一致不等于选择正确。小样本未出现翻转不能证明普遍无偏。

源码分析和文档链接另放source_walkthrough.md，练习12题/独立solutions.md，实测看run_summary.md，验收看../../docs/e15-validation.md，生成审校见../../generation/e15-README.md。正文可以放简短流程文字或表格，不必画复杂图；本课变化集中在裁判，前14课的Agent不改。

试一下：Docker环境与只读知识库沿用既有compose。宿主独立终端启动python3 tools/judge_bridge.py，凭据不入容器；docker compose build course成功后再docker compose run --rm -T --entrypoint python course -m lessons.e15_calibration.eval。已有runs/e15-calibration.json会拒绝覆盖，另存旧报告再明确新实验。离线检查可在Docker运行python -m pytest tests/test_e15.py -q；这是fixture控制，不是供应商调用。阅读http://localhost:8765/lesson15。提示读者观察“诚实失败的报告”“原生对齐前后判分”“A/B回映内容”三个现象。精确模型与费用未知写null。

接下来第16课，把课程机制整合、工作流journal与续跑、目标循环、17项能力核对、独立验收和CI串起来。不能提前宣称完整集成已完成。正文只讲当前课，不引入新Agent能力。

正式结果由run_summary最终实测补充；若仍在运行，禁止提前宣称全部完成。不要把论文或框架文档的示意数字抄成本课测量。
