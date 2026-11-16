# Docker与第1课运行

## 模型在本机，命令在容器

宿主机先运行`python3 tools/model_bridge.py`，默认监听127.0.0.1:8766。
Docker使用host.docker.internal访问这个本机入口。无需将Codex登录文件或API Key挂载到容器。
Linux原生Docker需要让host.docker.internal解析到宿主机，并确认能访问该本机入口；
本轮实际验证环境为macOS Docker Desktop。当前不把Linux宿主机网络兼容性标为已测。

```sh
docker compose up --build -d
docker compose run --rm -T course run --case list_files
```

课内模型只提供tool_calls/answer，循环在Docker执行Bash。预设模型只出现在离线单元测试，
示例运行报告使用live_codex_bridge，并保留模型请求、实际命令与状态。

## 挂载与独立验收

| 目录 | Agent容器 | verifier容器 |
|---|---|---|
| knowledge_base | 只读 | 不需要 |
| workspaces | 可写 | 只读 |
| runs | 写轨迹 | 写评分 |
| evaluation_private | 不挂载，镜像也不包含 | /verification只读 |

```sh
docker compose --profile verify run --rm -T verifier verify --run-id 实际run_id
```

verifier没有外部网络，也不调用模型。它在Agent结束后核对固定任务合同。
hello任务限定一条print语句；AST合同接受引号/注释变化，但并非任意程序功能证明。

## 自定义与停止

.env.example包含阅读端口、知识库路径、模型入口与UID/GID示例。修改知识库目录前先创建目录。
Linux文件权限需要与宿主机用户一致；macOS Docker Desktop的共享目录本轮已验证。

```sh
docker compose down
```

宿主机模型入口在对应终端Ctrl+C停止。停止容器不删除workspaces和runs。

## 教材生成

实际代码和实验通过后，在宿主机执行：

```sh
uv run python tools/generate_lesson.py
```

它只读取第1课白名单材料，原始输出保存在generation/output/e01_agent_baseline，
不会自动覆盖审校后的教材。Codex CLI只需要安装在宿主机。
