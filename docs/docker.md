# Docker、知识库和模型配置

## 默认启动

```sh
docker compose up --build -d
docker compose ps
docker compose logs --tail=30 course
```

打开 http://localhost:8765。健康检查为 /healthz；课程服务只在本机发布端口。
默认模式不需要 API key，不需要启动数据库或下载模型权重。

首次构建从 GitHub / Python 包索引下载固定依赖；运行时的离线回放不需要网络。
两套真实 SDK 的依赖比简化公式示例多，首次镜像构建时间以本机网络和缓存为准。

## 挂载说明

| 宿主机 | 容器内 | 用途 |
|---|---|---|
| ./knowledge_base | /data/knowledge | Markdown/TXT知识库，只读 |
| ./runs | /data/runs | 逐样本JSON结果，可写、重建容器后保留 |
| ./secrets/judge_api_key.txt | /run/secrets/judge_api_key | 仅使用live override时挂载 |

课程正文和代码打包在镜像中。修改正文或代码后重新构建；
知识库内容每次读取都从挂载目录加载，不需要为修改文本重建镜像。

## 换成自己的知识库

先复制示例结构，保留 policies/refund_policy.md 才能对既有样本运行 live：

```sh
cp -R knowledge_base my_knowledge
cp .env.example .env
```

编辑 .env：

```text
KNOWLEDGE_DIR=./my_knowledge
```

也可以写现有目录的绝对路径。目录必须先存在；Compose 不会静默创建拼错的空目录。

```sh
docker compose up -d --force-recreate
docker compose run --rm course search "退款"
```

浏览器的“挂载知识库”显示当前文件和 SHA-256。知识库是轻量词项检索示例；
检索命中和 Faithfulness 评分是不同阶段。

**为什么修改后 replay 可能报错？** 教学判定绑定了原证据的 hash。
证据变了，就不能沿用旧判定；请选择配置好的 live，或重新人工审核整份 fixture。
单纯修改 hash 而不重审标注不能构成新的有效评测。

## Linux 文件权限

默认容器以 UID/GID 1000 运行。如果你的宿主用户不同，在 .env 设置为
本机 id -u 和 id -g 的输出，确保 runs 目录由本机用户可写。
macOS Docker Desktop 默认共享目录通常可以直接使用。

## 运行实验与查看记录

```sh
docker compose run --rm course replay --sample mixed
docker compose exec course python s07_faithfulness/code.py
```

结果写入 runs/replay-<run_id>.json。浏览器“实验结果”可查看完整逐样本记录。
记录包含版本、证据 hash、声明、verdict、模型阶段响应及评分。
NaN 保存为 null，并保留未评分原因；不要把它当0参与平均。

## 配置真实裁判

在 secrets/judge_api_key.txt 写入自己的 key，并编辑 .env：

```text
JUDGE_MODEL=你的实际模型ID
JUDGE_BASE_URL=https://api.openai.com/v1
```

也可使用支持相同 Chat Completions JSON 接口的服务地址。
如果服务运行在宿主机，Docker Desktop 可使用 host.docker.internal；
容器中的 localhost 指向容器自身。不要把 key 写入 Dockerfile 或 Git。

```sh
docker compose -f compose.yaml -f compose.live.yaml run --rm course live --sample mixed
```

本项目不替模型供应商保证 JSON/temperature 参数兼容性；调用或schema不匹配会报错，
不会自动退回固定回放并把结果冒充live。真实模型分数、token与重试会有变化。

## PocketFlow 生成

宿主机使用已登录的 Codex：

```sh
uv run python tools/generate_lesson.py --backend codex
```

容器内可显式使用自己的模型接口生成：

```sh
docker compose -f compose.yaml -f compose.live.yaml run --rm \
  --entrypoint python course tools/generate_lesson.py --backend openai
```

容器生成输出位于该临时容器 /app/generation/output；需要保留时额外挂载该目录：

```sh
mkdir -p generation/output
docker compose -f compose.yaml -f compose.live.yaml run --rm \
  -v ./generation/output:/app/generation/output \
  --entrypoint python course tools/generate_lesson.py --backend openai
```

默认镜像不包含 Codex CLI，也没有挂载宿主机登录凭据。
已生成并审核的样章随项目提供，不需要重新生成才能学习。

## 停止

```sh
docker compose down
```

该命令保留宿主机知识库和 runs 结果目录。端口冲突时在 .env 修改 COURSE_PORT。
