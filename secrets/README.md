# 本地模型密钥

默认离线回放不需要密钥，也不需要创建任何密钥文件。

要运行真实裁判，在本目录新建 `judge_api_key.txt`，只放你的 API key。
该文件已被 Git 和 Docker build context 排除。不要把密钥贴到聊天或提交到仓库。
设置 `.env` 的 JUDGE_MODEL，然后使用 compose.live.yaml 挂载。
