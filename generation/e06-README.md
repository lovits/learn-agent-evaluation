# 第6课教材生成与审校

沿用固定提交的 PocketFlow-Tutorial-Codebase-Knowledge，实际运行 FetchRepo → BindLesson → WriteChapters → CombineTutorial，教材模型实际调用1次。16课顺序已经确定，未重新运行主题识别、关系分析与排序。vendor节点未修改。

输入是本课最小代码、八条受控回答、版本化reference、真实实测摘要、源码导读、练习/答案和共享记录合同。没有导入集成Agent或未来课程实现。主实验和reference澄清补测均先完成，再交给生成器。

原稿在 [generation/output/e06_answer_quality](output/e06_answer_quality/index.md)，输入与响应哈希在 [生成凭证](e06-provenance.json)。实际命令：

```sh
uv run python tools/generate_lesson.py --lesson e06
```

[发布教材](../lessons/e06_answer_quality/README.zh.md)经过技术核对与humanizer全文润色，共14个正文小节，未审校小节0。技术审校修正FP/FN措辞，补充reference信息范围与可运行补测命令，删除生成器页脚；润色过程保持代码块、行内代码与链接目标不变。发布版哈希单列，不覆盖原始生成稿。

报告明确区分构造回答、人工向量/计数手算和真实原生SDK裁判结果。没有运行embedding模型；未返回的确切模型标识、费用不填造。生成完整prompt/response位于Git忽略的generation/private/e06，宿主机登录凭据不进入Docker或仓库。
