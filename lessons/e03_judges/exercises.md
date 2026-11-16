# 第3课练习

1. 预期四种工具、实际只有read_file与bash时，手算precision、recall与F1。再重复一次read_file，集合分数会变吗？
2. 比较正确JSON与中文同义回答。分别说明精确匹配、JSON合同和语义分数在回答哪个问题。
3. false_completion的回答字符串正确，为什么state_contract仍为0？真实项目里的artifact_verified应从哪里来？
4. 把语义标准改成“必须有效JSON”，预测paraphrase的分数变化，再实际运行并保留新报告。
5. 给裁判输入一次无效JSON，检查score=null/error和非零退出，不能把它算入低质量回答的0分。
6. 把DAG的叶子分数改成10和3，解释固定映射与模型随机判断的区别。设计三位人工标注者校准阈值的流程。
