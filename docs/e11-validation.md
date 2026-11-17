# 第11课验收

任务、停止和评分分别验收。两次真实模型Agent在Docker修复运费函数，一次普通运行，一次明确控制首轮只声明完成。后者首轮0工具且被公开审查拦截，续轮后修复。两次最终23个行为输入检查通过，原测试哈希保留。实际工作目录文件与记录artifacts一致；这项发布前核验不冒充已经在旧镜像执行的新增逻辑。

六个讲师构造状态在独立临时目录实际验收；五个业务/文件合同失败，不适用import变体记unscored/null。原生DeepEval自定义measure/a_measure和Ragas ascore/score在七个有效状态上结果一致，共28分、0次模型请求。声明式retain/delete约束冲突另在Docker运行，impossible、0次模型请求；不声称有通用自然语言目标求解器。

原生TaskCompletion、AgentGoalAccuracyWithReference和WithoutReference在四个明确投影实际运行，24次模型请求、12结果、0指标错误。缺证据时DeepEval抽取补出未经观察的事实并给1，原始误判保留；追加真实公开失败后给0.2。规则0使组合仍0。评分输入变化不算Agent改进。DeepEval走固定源码兼容measure路径，未冒充官方原生trace采集。

源码固定版本和哈希、prompt/schema、抽取/判断、返回对象、同步/异步与适用范围均在[源码导读](../lessons/e11_task_completion/source_walkthrough.md)。[原始报告](../lessons/e11_task_completion/example_report.json)、[验收分数](../lessons/e11_task_completion/grade_report.json)、[裁判结果](../lessons/e11_task_completion/judge_report.json)、[冲突预检](../lessons/e11_task_completion/conflict_report.json)、[分阶段镜像](../lessons/e11_task_completion/runtime_evidence.json)分别保存。

正文沿Learn Claude Code的六部分和六步关键代码组织，PocketFlow四节点实际运行一次生成，humanizer完整审校12个正文单元，78个受保护片段不变。练习和答案分开。代码只增加本课所需停止审查、独立验收与业务指标，复用已介绍的循环与工具。

全库Ruff通过，本地与Docker断网各122项测试通过，保留1条既有DeepEval DAG弃用提示。Docker阅读器本课七条路由与首页状态实测HTTP 200；全站本地链接检查通过。机器记录保存于同目录e11-validation.json。GitHub发布提交和飞书回读分别在发布后记录。
