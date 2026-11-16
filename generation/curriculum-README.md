# 编程 Agent 课程的 PocketFlow 规划记录

入口：tools/generate_curriculum.py。使用固定版本原版节点，未修改vendor中的上游实现。
模型传输复用用户确认的本机Codex登录，不复制凭据；完整prompt/response保留于Git忽略的private目录。

实际流程为FetchRepo → IdentifyAbstractions → AnalyzeRelationships → OrderChapters → WriteCurriculumPlan。
前四项为原版节点，最后一项为本课程的设计输出适配。16主题和原24课知识覆盖由课程要求约束，
关系是教学先修/数据依赖，不描述成未经验证的源码调用边。

输入目录curriculum_inputs包括：课程要求、两框架知识地图、17机制清单与原项目前两课的
教学/代码样本。原24课完整清单保留并由结构核验使用，模型侧避免重复传入。
输入没有包括整套集成Agent；正式逐课生成时只交给当前课需要的代码与实验材料。

本次只规划课程，没有运行原版WriteChapters逐课生成16章，也未运行CombineTutorial。
这些节点用于后续已经核验的逐课材料；不能把本轮计划称为16课正文已生成。

原始大纲、结构化节点输出、调用记录和输入/输出哈希在generation/output/curriculum_v2。
审校后的公开课程设计在docs/curriculum.md。原24课方案在docs/archive保留作覆盖对照。

重新规划会产生新的模型调用并覆盖原始规划输出：

```sh
uv run python tools/generate_curriculum.py
```

执行前应保留当前生成凭证；工具只生成草稿，不自动覆盖已审校的课程文件。
中断恢复可加 --resume，仅复用prompt完全相同的已保存真实响应，并在凭证中标记。
适配器会把有效的裸YAML补上原版解析器要求的围栏；原始模型响应保持不变。

参见 [审校后的16课大纲](../docs/curriculum.md)和 [课程设计核验](../docs/curriculum-validation.md)。
