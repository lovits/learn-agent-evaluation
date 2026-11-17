# 第三方代码与来源

原创教学材料、应用代码与测试使用根目录 MIT 许可；下表所列第三方内容适用各自许可。TinyRAG 副本与其改编文件使用 CC BY-NC-SA 4.0，详见 vendor/tinyrag/LICENSE.md。

| 内容 | 来源及固定版本 | 许可 |
|---|---|---|
| vendor/pocketflow_tutorial | The-Pocket/PocketFlow-Tutorial-Codebase-Knowledge @ 05b24cbbb0fe409c5e23c9791f0342f07524ffdc | MIT，原文见vendor内LICENSE |
| references/upstream/deepeval | confident-ai/deepeval @ 34db63dd005ebc9a905c8ef4741ae0687c93c14c | Apache-2.0 |
| references/upstream/ragas | vibrantlabsai/ragas @ 8c63f10d500c44efbf24fdb9e2920de2104c321c | Apache-2.0 |
| vendor/tinyrag | datawhalechina/tiny-universe/content/TinyRAG @ a5ae08d56bbefb20b1cf56fa34ed5a3157cdd2c2 | CC BY-NC-SA 4.0，包含原算法与已注明的适配 |
| 编程Agent与教学组织依据 | shareAI-lab/learn-claude-code @ 448c75bb596917ad196cc1fb7558f459c5c50fdd | MIT；规划输入含前两课原始样本及许可 |

课程规划输入中新增了 Learn Claude Code 的 s01/s02 README.zh.md 和 code.py 原始样本，
位于 generation/curriculum_inputs/learn_claude_code，附带原版MIT许可；仅用于核对教学方式，
没有将集成Agent提前作为第1课的课程实现。

Apache-2.0和参考项目许可原文在 references/licenses。
源码快照保持原文件内容，SHA-256与固定commit的URL见references/sources.json。
PocketFlow节点未改动，模型适配在tools/generate_lesson.py完成。

本项目与上述开源项目没有官方从属关系。官方资料链接供学习核对；
没有将飞书私人文档合集原始数据整体复制到本仓库。
