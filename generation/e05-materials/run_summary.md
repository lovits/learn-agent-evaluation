# 第5课实测结果

七条样本真实调用两个原生SDK，共34次裁判请求，0个运行错误。五条受控回答、一条证据改版、一条第4课真实Agent原始产物再评。没有新增Agent运行。

| 样本 | DeepEval默认 | 同verdict惩罚borderline | Ragas | 状态 |
|---|---|---|---|---|
| supported | 1.0 | 1.0 | 1.0 | scored |
| unmentioned | 1.0 | 0.0 | 0.0 | scored |
| contradiction | 0.0 | 0.0 | 0.0 | scored |
| mixed | 0.6666666666666666 | 0.3333333333333333 | 0.3333333333333333 | scored |
| no_claim | 1 | 1 | 0.0 | scored |
| evidence_v2 | 1.0 | 1.0 | 1.0 | scored |
| recorded_agent | 1.0 | 0.0 | 0.5714285714285714 | scored |

默认阈值0.7是教学设置，不要求所有样本通过。borderline重聚合未新增模型调用；两个框架可能生成不同声明集合，不能把最终高分直接当准确率。

证据改版时同ID新sha256导致旧标注被拒用。原始文档、证据键、claim/truths/NLI结果、prompt和模型响应都保存在[完整报告](example_report.json)。第4课真实记录以源run_id和源报告哈希标识，不改写原始回答。

初次模型入口未启动，14项连接错误、0次真实模型请求，保留[初始失败记录](initial_connection_failure.json)。启动入口后才完成34次真实请求；生成教材的调用另记。score=null且undefined_nan表示原生未定义，status=error才是运行失败。
