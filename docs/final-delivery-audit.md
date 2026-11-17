# 全套课程与综合项目交付核验

交付范围是16课递进教材与一个完整编程Agent评测项目。课程编号1–16、上游机制s01–s17、原24课知识映射分别使用，不混作同一套编号。

## 按原要求核对

| 要求 | 证据与结果 |
|---|---|
| 从第1课递进到全部课程 | 16个课程目录齐备；每课六部分、六步关键代码，源码、练习/答案和运行记录分别成页 |
| 延续Learn Claude Code带读 | [统一标准](../references/textbook-writing-standard.md)与各课正文；每课解释问题、接入、输入输出与变化，关键图按需要使用 |
| 评测编程Agent并挂载知识库 | [综合项目](../integrated_agent/README.md)、[完整调用链](../integrated_agent/architecture.md)；只读知识、持久工作区/报告与模型宿主边界明确 |
| DeepEval/Ragas资料与源码 | 323项固定飞书资料解释性正文阅读记录、版本与限制已核对；[阅读范围审计](../references/source-reading-audit.json)，每课保留指标源链 |
| 24课知识合并而不丢主线 | [16课详细规范](course-specification.md)和[课程大纲](curriculum.md)保留原知识映射，RAG、Agent、数据、实验、校准和CI连续贯通 |
| 真正运行PocketFlow | 第1至16课保留生成原稿与实际节点凭证；第16课固定原版四节点，真实生成请求一次 |
| 自然讲解语气 | 各课保留humanizer审校；第16课六节六步通读，66个受保护片段不变；综合说明三份文件另审校 |
| Docker实际运行 | 逐课适用实验保留；综合正常、命令拒绝、越界各有真实模型与独立验收；完整容器断网259项检查通过 |
| 原生17项机制 | [逐项契约](../references/e16-capability-contracts.json)全部有对应通过控制；真实组合任务独立通过，限制没有扩大承诺 |
| 真实数据与构造数据分清 | 原始响应、讲师阶段、退化投影、夹具和历史记录分别标注；未知型号/费用留空；失败不删除 |
| 完整讲解、实验、练习 | [第16课](../lessons/e16_regression/README.zh.md)、[架构](../integrated_agent/architecture.md)、[能力说明](../integrated_agent/capabilities.md)与12道独立练习/答案 |
| 飞书教材与总体说明 | [第16课](https://my.feishu.cn/docx/UzRzdHS2ioW8m1x3702cX54onOh)与[综合项目](https://my.feishu.cn/docx/Odeld6l1Co6pWlx3qBTcItBLn3d)正文、代码换行缩进和图片已回读验证 |
| GitHub与CI | 本地发布材料已齐备；最终远端提交和CI核验结果写入本页的发布记录与机器清单 |

## 实验结论

正常组合任务使用33次真实模型响应，导出28条原生trace；两个错误/边界任务各3次响应。两个API共44条外部输入、原测试和原生状态独立通过。17项机制控制使用明确的模型夹具，供应商请求数为0，实际IO另行执行。

两轮原生评分共20次真实裁判响应、0评分错误。首轮漏掉命令参数的投影和第二轮完整投影均保留；这次修订属于开发诊断。默认Faithfulness聚合、声明拆分和证据范围的差异在[实际记录](../lessons/e16_regression/run_summary.md)逐条解释。框架分数不替代业务与状态验收。

本地及Docker断网259项检查通过，保留第3课已有弃用警告。[Docker原始检查日志](https://github.com/lovits/learn-agent-evaluation/blob/main/docs/e16-checks.log)与[JUnit记录](https://github.com/lovits/learn-agent-evaluation/blob/main/integrated_agent/evidence/native-contracts.xml)随仓库保留。编辑草稿和独立答案已验证不在应用镜像中。

## 总体回归门禁

[实际门禁结果](../integrated_agent/evidence/release-gate.json)逐项读取业务/状态、两次拒绝、17项机制、裁判执行覆盖及已知坏例的预期拦截。全部关键项为真时才接受；将原始验收状态复制后故意改成失败的[控制实验](../integrated_agent/evidence/release-gate-negative-control.json)被正确拒绝，原始记录保持不变。两项检查均未新增模型请求。

Docker实际执行入口已接入CI：

```bash
docker run --rm --network none --entrypoint python \
  learn-agent-evaluation:local -m lessons.e16_regression.check \
  --report /tmp/my-release-gate.json
```

## 资料与能力边界

飞书阅读指固定快照中可得到的全部解释性正文、参数与限制，包含围栏误包内容的补读。没有声称动态FAQ和缺失公式已恢复、所有多语言代码逐行审计或全部示例执行。不同来源和源码版本分别记录。

综合项目验证声明的教学合同，不保证任意任务、全部平台与上游后续版本等价。最小schema、cron损坏加载、Goal恢复、MCP stand-in、进程组与worktree的具体边界见能力说明；评审内容是否正确还需逐发现核对，人工标签状态不伪造。

## 发布记录

飞书两份新文档已回读，总大纲更新与GitHub最后发布核对正在收尾。最终核对记录将保存明确的代码提交、CI链接、远端分支读回和文件哈希；后续文档提交与受测代码版本分别记录，避免自指提交哈希。
