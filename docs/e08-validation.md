# 第8课验收

## 代码与真实实验

本课只增加独立数据构建与审核，不增加目标Agent能力。DeepEval原生Synthesizer实际生成单跳、多跳各一条；Ragas原生TestsetGenerator基于规则构造的原生KnowledgeGraph，实际调用两类Specific场景生成器。没有默认embedding/NER transforms调用。

Docker原生生成入口成功退出。16份生成响应、8份参考审核响应均保留prompt和原始响应；没有运行目标Agent。4条原生题、3条明确编写种子、2条注入反例合计9条；重复与错误参考被隔离，7条待人工审核。人工通过数为0，Agent准确率为空。5/1/1题族划分只演示公开课用材料隔离。

断网verifier实际运行14项数据合同检查并全部通过。[固定原始报告](../lessons/e08_datasets/example_report.json)、[验收报告](../lessons/e08_datasets/grade_report.json)、[源文件与镜像证据](../lessons/e08_datasets/runtime_evidence.json)分别保存，具体判断见[实验解释](../lessons/e08_datasets/run_summary.md)。

## 教材与来源

正文按问题、解决方案、工作原理、相对上一课的变更、试一下、接下来组织；正文只摘关键代码，完整代码另存。源码导读保留两个框架实际调用边界、schema适配、质量重试、图谱与persona、候选转换、审核和去重口径。只对本课相关文档与源码建立阅读清单，不声称已经读完两框架全部文档。

PocketFlow实际生成与完整正文humanizer审校记录见[生成凭证](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/e08-provenance.json)。一张关键数据管线图有可编辑draw.io源和已检查PNG，预览来源见[图记录](../references/e08-diagram.json)。

## 发布核验

本地87项测试通过，Docker断网87项测试通过，均有1条既有DeepEval DAG弃用提示；自有代码Ruff通过。阅读器/lesson8实测HTTP 200，一张PNG通过图片入口正常返回，整站页面与本地链接检查通过。第一次构建遇到上游镜像TLS超时，重试成功；第一次链接检查发现生成凭证链接未在阅读器开放范围，已改为GitHub源链接并通过复查。

原生生成阶段、独立验收阶段和教材/阅读器阶段的镜像快照分别记录，不能把最后镜像当作早先生成的环境。原生生成源文件哈希与固定报告仍和实测记录一致。GitHub CI以对应提交的检查结果为准；飞书文档创建后回读核对代码、标题与图片，元数据保存在references/feishu-e08.json。
