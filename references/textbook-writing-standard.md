# 教材写作标准

课程目标：通过可运行的编程 Agent 学会 RAG 与 Agent 评测，并读懂 DeepEval、Ragas 的关键实现。知识库接入使用 Datawhale TinyRAG。

- 每课围绕一个明确的问题，不把指标清单当作讲解主线。
- 先描述具体困难，再引入最小机制；展示关键代码，解释输入、处理和结果。
- 以问题、解决方案、工作原理、本课变化、试一下、接下来为主线，子标题随当前机制安排，参考 Learn Claude Code 的实际中文课文。
- 正文只引用当前知识点需要的代码，完整文件保持可执行，并说明必要的前课依赖。
- 源码导读继续到框架校验、prompt/schema、裁决和聚合，保留版本、方向、分母及重要边界。
- 示例数字解释原理，构造样本与真实调用如实区分；零分、未定义和执行错误分开。
- 不在教材与首页讲制作历史、改写进度、验收计数或服务部署步骤。
- “试一下”给具体任务与观察问题；图服务于代码结构，不以图的数量作为卖点。
- 语言自然、直接，段落沿问题推进，避免模板开场、口号和重复总结。
- 参考与许可单独明确，TinyRAG 改编文件遵守其上游许可。

实际范本：[s01](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s01_agent_loop/README.zh.md)、[s02](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s02_tool_use/README.zh.md)。

实际评测框架仅 DeepEval，Ragas 用于原理和源码导读。每课正文直接嵌入两张紧凑 PNG，字号适度提高，源文件随仓库保存，GitHub 使用课程发布的图片地址；实际在 GitHub 页面核对两图加载。
