# 第9课教材生成与审校

当前材料包只包含第9课需要的控制变量、真实循环接入、配对统计、原生实验编排、实际结果、源码与练习。PocketFlow使用固定上游节点FetchRepo、BindLesson、WriteChapters、CombineTutorial；16课顺序已定，没有运行主题识别、关系分析与章节排序。

模型通过宿主机已登录Codex、禁用工具生成正文，凭据不进入容器。实际调用、白名单文件哈希、原稿位置和技术审校/humanizer发布记录保存在[凭证](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/e09-provenance.json)。生成稿与审校教材分别保留。

实验调用另记：正式应用16次运行、64次模型响应；固定输出重复裁判4次，不算新Agent任务，也不算人工审核。一次未完成预运行因错误metadata字段被排除，正式实验在修正后重跑。原始usage与费用缺失分别说明，不凭空填写数字。

正文按六部分与六个短步骤带读；先解释同任务配对，再讲分层、冻结决定、按族重采样和成本。完整实现、空区间原因及方法边界见[源码](../lessons/e09_comparison/source_walkthrough.md)与[验收](../docs/e09-validation.md)。
