# 第10课教材生成与审校

本课使用固定PocketFlow-Tutorial-Codebase-Knowledge的FetchRepo、BindLesson、WriteChapters、CombineTutorial节点，输入仅为当前工具池、两种评分投影、实际实验、源码与练习。没有执行主题识别、关系分析或章节排序；16课路线已固定。模型通过宿主机登录Codex、工具禁用生成教材，凭据不进入容器。

实际调用、材料哈希、原稿与发布审校记录见[生成凭证](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/e10-provenance.json)。正文以Learn Claude Code的六部分与分步代码组织，humanizer全文审校保护代码、命令和链接。

正式应用11份模型响应；原生规则配置91项分数不调用模型；第一轮裁判6份响应、修订上下文后13份响应分别记录，教材写作另计。构造轨迹不冒充执行，模拟MCP不冒充线协议，自动判定不冒充人工标签。应用文件与轨迹在修订评分时保持一致。

工具池结构图为可编辑draw.io源及同图数据PNG预览；[图源记录](../references/e10-diagram.json)说明未使用Desktop导出。完整原始报告和局限见[实验解释](../lessons/e10_tool_evaluation/run_summary.md)，发布核验见[验收](../docs/e10-validation.md)。
