# TinyRAG 的来源与许可

来源：Datawhale 的 [tiny-universe/content/TinyRAG](https://github.com/datawhalechina/tiny-universe/tree/a5ae08d56bbefb20b1cf56fa34ed5a3157cdd2c2/content/TinyRAG)。

作者：不要葱姜蒜及 Datawhale tiny-universe 贡献者。

上游根 README 声明采用 Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International（CC BY-NC-SA 4.0）。本目录的上游副本及改编文件沿用该许可，不适用仓库根目录 MIT 许可。

[许可说明](https://creativecommons.org/licenses/by-nc-sa/4.0/) · [完整条款](https://creativecommons.org/licenses/by-nc-sa/4.0/legalcode.en)

`VectorBase.py` 保留上游向量生成、持久化、余弦与 top-k 算法，只将 Embeddings 导入换成本目录的无供应商副作用基类。`embeddings.py` 保留上游 BaseEmbeddings 与余弦计算，省去供应商类、环境变量写入和自动读取凭据。完整上游 Embeddings、utils、LLM 以文本副本保存在 upstream，供源码对照。

本课程的挂载元数据、字符分块与本地 TF-IDF 适配位于 eval_course/tinyrag.py。TinyRAG 的上游教程保存在 README.upstream.md。
