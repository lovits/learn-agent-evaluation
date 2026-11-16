# s07 Faithfulness：固定样章任务

只写这一课的中文 Markdown 样章。读者会 Python、了解 RAG / Agent。
课程风格参考 Learn Claude Code 的“问题→最小机制→工作原理→试一下→接下来”；
不复述整个仓库目录。标题可为“s07 Faithfulness — 回答真的被证据支持吗”。

本课要让读者能：区分支持/未支持/矛盾；手算两个框架的口径；
跟踪真实源码；运行 Docker 实验；解释空声明和信息缺失的边界。

必须包含下列内容：
1. 具体问题：知识库说未拆封商品30天可退、原路退款，但没说运费。回答额外承诺免费退货是否忠实？
2. 先讲测量对象：回答的 claims 对给定 retrieved context。参考答案不是必需字段；
   不代表现实事实正确、检索完整、回答相关或有用。忠于错误文档也可能得到高分。
3. 管线：收集question/answer/retrieved_contexts → 拆claims → 根据证据判断 → 聚合与解释。
4. 三类声明：supported；unsupported（上下文未支持也未直接矛盾）；contradicted。
5. 版本限定：DeepEval commit 34db63dd005ebc9a905c8ef4741ae0687c93c14c 的 llm模式：
   truths/claims并行抽取，然后生成verdicts。默认 (yes+borderline)/N；
   penalize_ambiguous_claims=True时只yes通过；这不同于strict_mode的阈值钳制。
   idk为历史verdict别名，不是助手给用户的“我不知道”。无verdict默认empty_score=1。
6. Ragas commit 8c63f10d500c44efbf24fdb9e2920de2104c321c 的collections Faithfulness：
   从response拆statements，再根据合并的contexts作NLI；直接支持为1，否则0；
   空statements/verdicts为NaN；空response/input/context会先校验失败。
7. 同一组固定人类verdict [yes,borderline,no] 算出 DeepEval默认2/3、惩罚歧义1/3；
   对应Ragas固定[1,0,0]为1/3。模型运行时不保证会拆出同样claims，不能据此声称模型优劣。
8. 讲清这是“真实SDK+人工固定模型输出”的replay，不是自造简化框架，也不是模型效果实测。
   Live才会调用裁判；本轮没有API Key时不能伪称已经做过真实裁判实测。
   回放标注与知识库SHA绑定；文件变化必须拒绝旧回放，不能照搬旧分数。
9. 五组实际fixtures：supported、unsupported、contradicted、mixed、no_claims；
   最后一组DeepEval原始1与Ragas原始NaN要显示，NaN输出JSON null而不当0分。
10. 最小代码取实际code.py/runner/judges的片段；不要发明函数/API。
    可引用独立完整代码文件，不把所有实现压成一个不完整代码块。
11. 源码分析依照提供的snapshots，至少讲DeepEval._calculate_score→score_qag_verdicts、
    Ragas.ascore→_create_statements/_create_verdicts→_compute_score；
    每项包含真实文件和固定commit链接。不要声称两个框架公式永远相同。
12. Docker命令必须准确：
    docker compose up --build -d
    浏览器 http://localhost:8765
    docker compose exec course python s07_faithfulness/code.py
    docker compose run --rm course replay --sample mixed
    docker compose run --rm course search "退款"
    课程结果挂载 ./runs:/data/runs，知识库默认 ./knowledge_base:/data/knowledge:ro。
    自定义知识库通过 .env 的KNOWLEDGE_DIR切换，宿主目录必须先存在。
13. 至少四个练习：手算/改变歧义策略/修改证据/空声明；
    每题写可检查的结果与不应推导的结论，参考答案链接到exercises.md/solutions.md。
14. 结尾列验收：会区分三类claim、说明版本和模式、重放并找到逐样本记录、
    解释为什么1分不保证高质量；接下一课答案正确性/相关性。

额外要求：
- 不输出不存在的图像链接，不依赖Mermaid渲染、远端图片或前端CDN。
- 不使用机器上的绝对路径；仓库内链接以s07目录为基准。
- 不把后续23课写成已经完成；本次仅s07样章项目可运行。
- 不编造模型评测分数、费用、命令执行结果或源码行号。
- 公式和固定verdict的结果可以确定；其余写明是预期现象或待校准。
