# 第2课编写任务

读者已完成第1课，会Python，想学会评测编程Agent。严格围绕e02工具、权限、轨迹和统一评测样本，保留第1课。参照Learn Claude Code每次只加一个机制的组织方式，把合并课拆成小节：文件工具分发；执行前权限；hook记录和父子span；框架字段映射与SDK校验；Docker实验与练习。

材料包含本课完整代码、样本适配、独立验收器、五条真实任务和实际运行摘要、源码导读与练习。使用这些材料组织一课中文教材，约3500至5500中文字，紧扣实际代码，不虚构运行成绩。教材先讲一个需要修改calculate.py并运行的具体问题，解释Bash为什么还要有具名工具，再引入需要观察的权限分支与轨迹。正文给少量必要代码片段并链接完整文件，不能提前引入未来Agent代码。

语气面向一位坐在旁边练习的Python学习者，具体、耐心、自然。用真实任务的路径、输出、报错解释概念。不要“深入探讨”“至关重要”“赋能”，不加夸张评价；不要每节都用三项排比、反问开场或一句口号收尾。不编造亲身经历。保留事实、术语、命令、字段与链接。

必须讲清：
- 第1课复用哪些函数；本课五种工具与必需参数；edit只换第一处；glob最多200项；参数缺失在执行前返回invalid_arguments。
- 参数校验、权限allow/deny/approval_required、执行error与timeout的差别。批量批准固定拒绝，不弹确认。目录外文件直接拒绝；规则只是教学策略，不能保证隔离任意Bash。列清与原版s02-s04的改编差异。
- Agent根、model-N、model-N:tool-i和run_id的关系；重复工具名不足以关联返回；Pre/Post记录连拒绝与参数错误也覆盖；trace_errors能识别缺失、错位和hook缺口，但不是防篡改证明。
- DeepEval四个基础字段与tools_called；Ragas对应字段及Human/AI/Tool多轮消息；单轮与多轮视图的区别；None不等于空列表，工具输出不伪装成检索证据。单轮结束条件与任务通过条件分开。
- 本课实际构造DeepEval LLMTestCase、ConversationalTestCase与Ragas SingleTurnSample、MultiTurnSample，导出JSON后恢复对象。DeepEval当前before validator要求嵌套ToolCall实例，恢复时先建ToolCall。Ragas ToolCall没有本课所需call_id，把关联ID放消息metadata并保留原始轨迹；不能假定后续指标读取metadata。
- SDK构造成功不代表任何指标都可用。只运行确定性文件/输出/轨迹合同，不声称运行了G-Eval、Faithfulness或工具质量分数；最终回答语义与工具路径最优性未评分。本课不新增裁判调用，没有裁判prompt/verdict聚合或异步评分。
- 源码导读给出固定版本文件和函数，说明DeepEval Tracing父子节点与Ragas消息校验。不能宣称本课已接入原生云端tracing。
- 数据集共开发5条、校准2条、留出2条，后两类有完整任务和验收标准但未执行且不进入Agent镜像；仅开发五条进入本次通过率。不得把故障注入当自然模型失误。
- Docker容器执行工具，宿主机Codex只返回动作；独立verifier断网、工作目录只读、标准私有挂载；知识库本课仍不检索。凭据不入容器。

运行命令原样使用：
```sh
python3 tools/model_bridge.py
```
另开终端：
```sh
docker compose up --build -d
docker compose run --rm -T course run-e02 --case edit_and_run
docker compose --profile verify run --rm -T verifier verify-e02 --run-id 实际run_id
python3 tools/run_e02.py
```

任务运行后用实际run_id，重跑默认不覆盖固定示例。列五条任务的实测结果，明确expected错误实验成功指观察到错误和文件保持，不能笼统把error算运行失败。

评分口径：每个任务必须finished、轨迹内部一致、指定工具状态满足、指定文件或stdout/exit_code满足、四种SDK样本可以构造并恢复；任一检查失败该任务不通过。分母是五条实际开发任务。练习至少覆盖重复工具、拒绝/错误分类、错位轨迹、SDK重载、失败编辑、数据划分。结尾衔接第3课规则评分和LLM裁判。

链接完整源码、源码导读、练习、参考答案、run_summary.md、example_report.json和dataset_manifest.json（均在本课目录）。官方说明与固定版本源码URL见source_walkthrough.md，不引用无法确认的函数或代码行。
