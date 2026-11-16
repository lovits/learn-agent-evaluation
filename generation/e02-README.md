# 第2课教材组织与审校

第2课沿用固定版本PocketFlow-Tutorial-Codebase-Knowledge的原版FetchRepo、WriteChapters、CombineTutorial节点，中间用BindLesson绑定已经批准的课程主题。大纲已确定，因此本轮没有重新运行抽象识别、关系分析与排序节点。

本课输入限定为11份文件：当前课代码、验收器、样本适配、数据清单、开发案例、真实运行摘要、源码导读、练习/答案，以及公共记录与版本文件。未提供整套Agent、宿主机凭据或私有验收标准。

```sh
uv run python tools/generate_lesson.py --lesson e02
```

原始输出保存在generation/output/e02_tools_traces。生成凭证为generation/e02-provenance.json，记录实际模型调用次数与输入输出哈希。私有提示和响应只留本地，不提交GitHub。

发布前按humanizer要求通读正文，调整模板化开场、重复收尾和生硬转折。代码、命令、路径、字段、数据和链接保持不变；事实另按运行报告与源码核对。发布版与原稿分别保存，凭证中记录审校范围及发布哈希。
