# 第8课教材生成与审校

输入材料为本课真实代码、统一候选数据、原生运行解释、固定版本源码导读和独立练习。沿用Learn Claude Code的六部分正文，每步先解释当前困难，再摘出实现中的关键代码。

实际执行工具为固定commit的PocketFlow-Tutorial-Codebase-Knowledge：FetchRepo读取白名单文件，BindLesson绑定既定一课，WriteChapters生成正文，CombineTutorial组织输出。没有运行抽象识别、关系分析和章节排序；16课顺序已经确定。模型使用宿主机已登录Codex，工具禁用，登录凭据不进容器。模型请求的原始哈希与材料清单见[e08-provenance.json](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/e08-provenance.json)，原稿保留在generation/output/e08_datasets。

教材生成与实验生成分别记账：原生数据生成器通过8769请求16份响应，参考审核通过8768请求8份响应；它们均不等同于教材生成调用。目标Agent在这一课没有运行。

发布前核对源码摘录、阶段字段、原生调用范围及实际报告；按humanizer审阅完整正文，保留代码、命令和链接目标。发布记录会写入provenance的publication字段。自动参考审核尚未获得人工认可，不把这种状态写成“数据集已经审核完毕”。

[图源与预览说明](../references/e08-diagram.json)记录同一图数据生成的可编辑draw.io与PNG；没有将本地预览冒充桌面导出。[验收](../docs/e08-validation.md)列出实际运行、测试与同步状态。
