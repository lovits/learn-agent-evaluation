# 第5课实测结果

以下保留首次制作时的历史实验及后续注明的修订；本轮教材重写没有重新执行这些模型实验。

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

## 只改变裁判输入封装的补测

保留同一份真实回答，将原始id以前缀形式与正文一起传入裁判，保留original_text/original_sha256，并为派生输入另算哈希。追加5次真实请求，DeepEval默认为1、同verdict惩罚仍为0，Ragas为1；DeepEval的truths抽取没有保留来源路径。不是知识库改版，也没有新Agent执行。[补测报告](source_prefixed_report.json)与主实验分开保存。

复跑：`docker compose run --rm -T --entrypoint python course tools/e05_sources.py`，先完成主实验。两轮成功评测合计39次模型请求，初次连接失败0次。评测封装应保留回答中引用的来源身份，不能只传正文后把分数下降全归因于Agent。
