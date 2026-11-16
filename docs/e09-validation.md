# 第9课验收

## 实际实验

开发、留出各8次正式Agent运行，2族×2任务×2版本×2重复，全部通过原生Ragas experiment/arun调度。64次应用模型响应保留原始usage、轨迹和真实文件；DeepEval原生LLMTestCase逐条保留metadata。只改变检索limit，模型抽样种子未固定。

开发阶段冻结k=2，随后才打开另一题族；留出没有用于再调参。单跳限额题两版本均通过，组合题由0变1。每split一个族不提供区间，合并两族仅作percentile方法演示；公开合成任务与零宽区间不能支持总体性能承诺。完整原始记录、逐题差值和局限见[实验解释](../lessons/e09_comparison/run_summary.md)。

4次重复裁判只重评2个固定输出，与应用运行和教材生成分开。自动标签未冒充人工标签，精确型号与费用未知时保持空。应用已有usage按原字段汇总，缓存输入不重复相加。

## 独立验收与反例

断网verifier实际重读16份产物，12项实验合同检查通过。[分析报告](../lessons/e09_comparison/analysis_report.json)记录配对矩阵、原生字段、split、来源哈希、实际文件与冻结决定。控制实验改错原生metadata会失败，删除配对行会被拒绝；10个新增测试覆盖配对缺失/重复、分层退化、族重采样、类型、异常遗漏、检索参数、实际循环字段适配和usage缺失。

初次预运行的字段错误已明确排除并保留局限；正式运行代码哈希与报告核对一致。[运行证据](../lessons/e09_comparison/runtime_evidence.json)区分应用与分析阶段。

## 教材与发布

PocketFlow实际读取本课白名单材料并生成正文，humanizer全文审校保护代码、命令和链接。原稿、输入清单及发布哈希见[生成记录](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/e09-provenance.json)。主文沿六步关键代码解释，源码、练习、答案与数据边界另页保留。

本地97项测试通过，Docker断网97项测试通过，自有代码Ruff通过；均保留1条既有DeepEval DAG弃用提示。阅读器本课七条正文/附页路由实测HTTP 200，整站文档与本地链接检查通过。GitHub CI按发布提交记录，飞书创建后回读核对六部分、十二段代码与附页，具体元数据见references/feishu-e09.json。
