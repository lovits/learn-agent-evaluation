# 第1课PocketFlow教材生成与图文改写

第1课首次制作按“代码与实验先验证，再组织教材”的顺序进行。本次在第7课之后重写第1课的讲解，沿用原可运行代码和历史实验。
原版节点来自固定commit的PocketFlow-Tutorial-Codebase-Knowledge，vendor文件未修改。

实际采用FetchRepo → BindLesson → WriteChapters → CombineTutorial。
BindLesson将已确定的e01目标绑定到本课白名单文件；WriteChapters实际调用本机Codex生成正文。
本轮没有重新运行主题识别、关系分析与排序，因为16课设计已经固定。

输入只包含e01代码、评分器、公开任务、真实运行报告、源码导读、练习/答案、版本信息和第1课改写规则。
不包含整套集成Agent、后续机制或私有验收标准。

本次改写原稿在generation/output/e01_agent_baseline；调用与输入哈希记录在generation/e01-provenance.json。本次实际写作调用1次；首次制作的原稿、brief和凭证完整归档在generation/archive/e01-first-generation，不把两次生成合并成一次。
已审校的课程在lessons/e01_agent_baseline/README.zh.md，含六节正文、六步带读和两张配图。图文改写的检查见[验收](../docs/e01-rewrite-validation.md)。
完整prompt/response在Git忽略的generation/private/e01中。

```sh
uv run python tools/generate_lesson.py
```

重新生成会调用模型并更新原始输出，不会自动覆盖审校版。
课程大纲生成是此前的独立流程，见 [规划记录](curriculum-README.md)。

第2课已使用同一PocketFlow流程完成，详见[第2课生成与审校记录](e02-README.md)。

第3课使用同一FetchRepo → BindLesson → WriteChapters → CombineTutorial流程，实际一次生成调用；凭证见generation/e03-provenance.json。运行 `uv run python tools/generate_lesson.py --lesson e03`。原稿与humanizer审校版分别保留；生成后追加的v2校准证据单独注明。

[第4课生成与审校](e04-README.md)沿用已验证的PocketFlow节点，输入当前课代码、真实记录和资料。

[第6课生成与审校](e06-README.md)以当前课代码、版本化reference、原生评测与参考措辞补测组织教材，并保留原稿与humanizer发布版。

[第7课生成与审校](e07-README.md)先细读Learn Claude Code的正文与代码组织，再按同一带读方式生成，保留六组真实实验和12节审校记录。
