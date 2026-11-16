# 第7课：试着自己定位

1. 不看case.id，只看available_documents、retrievals.before/after和artifact，区分drop_doc与drop_hit。写出支撑判断的ID或原文，不凭最终低分猜。
2. 保留三层日志，将add_old与baseline对照。如果业务字段仍然正确，应该把它记为“注入失败”还是“本次未观察到任务失败”？还缺什么证据才能推断稳定性？
3. 固定同一组NoiseSensitivity矩阵，手算relevant与irrelevant。第二条错误声明同时得到两类上下文支持时，为什么不能在irrelevant里重复计？
4. 解释“相关上下文”：DeepEval按问题判断切题，NoiseSensitivity按是否支持至少一条reference声明归组，它们可以不同吗？
5. 上下文相关性为1、NoiseSensitivity为0，但文件限额错误，能宣布任务通过吗？从bad_prompt的真实轨迹找证据；若该次未出错，也保留实际结果。
6. 给一条bad case写四行：观察到什么、依据什么、目前假设什么、下一次只改变什么。不要把评分相关性当严格因果证明。
