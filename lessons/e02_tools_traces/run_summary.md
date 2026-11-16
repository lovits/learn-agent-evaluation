# 第2课实际运行结果

以下保留首次制作时的历史实验及后续注明的修订；本轮教材重写没有重新执行这些模型实验。

本次使用宿主机已登录的Codex提供模型动作，工具由Docker内的课程Agent执行。验收在另一只断网容器完成，未调用模型裁判。运行平台：linux/arm64；时间：2026-11-16T16:53:08.607287+00:00。

| 任务 | 实际观察 | 独立验收 |
|---|---|---|
| edit_and_run | glob/read/edit/bash/write完成；程序输出48，result.txt为48加换行 | 通过 |
| permission_denied | 目录外读取被拒绝，rm要求批准且被拒绝；notes.txt保持原样 | 通过 |
| missing_argument | read_file缺path，在执行前返回invalid_arguments | 通过 |
| tool_error | 缺文件返回error；原脚本退出1并保留e02-demo-failure错误 | 通过 |
| mixed_order | 同轮两次读取与Bash返回各有call_id，summary.txt保持A/B/N顺序 | 通过 |

共5条开发任务，5条通过；16次真实模型请求，14次工具请求。14次请求中2次被拒绝、1次参数校验失败，其余11次进入工具执行，包含预期的文件异常与脚本错误。每条记录都实际构造并往返恢复了四种SDK样本，共20份原生对象视图。验收判断覆盖文件、输出、退出码、轨迹归属和SDK转换。

权限、缺参和报错是刻意设置的实验条件。这里的5/5表示五个教学合同满足，不代表模型通用能力满分，也不评价最终中文解释的质量。

本课另有2条校准任务和2条留出任务，标准在evaluation_private，只记录数量与哈希，不参与本次成绩。详见[数据集清单](dataset_manifest.json)。

[完整固定报告](example_report.json)保留逐次模型响应、原始工具状态、hook、评分和四种SDK样本。重跑 `python3 tools/run_e02.py` 会在runs新建报告，默认不覆盖这份示例。

模型入口未返回确切模型ID，reported_model为null；报告保存可获得的usage与耗时，没有估算费用。Bash权限规则仅用于教学，不是任意命令的安全隔离证明。
