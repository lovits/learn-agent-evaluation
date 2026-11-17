# e01 样本与评测记录

[教材](README.zh.md) · [评分代码](eval.py) · [原始记录](assessment.json)

## 样本怎样选

本课只用一个文件任务 `hello`。要求创建指定结构的 `hello.py`，运行后报告实际结果。它足够小，可以把用户要求、执行证据与判断条件逐项对应起来。

| 样本 | 构造方式 | 要观察什么 |
|---|---|---|
| `hello` | 公开任务交给真实模型驱动的 Agent，在 Docker 中执行 | 命令输出与当前文件是否同时符合要求 |
| `claim_only` | 用受控响应直接返回空动作和“已完成” | 模型正常停止是否会被误当成任务完成 |
| `changed_artifact` | 受控执行产生正确输出，再把当前文件改错 | 旧输出能否掩盖错误文件 |

后两项是验证规则边界的构造反例，不代表真实模型发生过这些错误。

## 已保存的真实运行

运行编号：`5f409464de6e4b5e8c2e76e651384402`。模型提出的 Bash 命令实际执行，返回退出码 `0`，stdout 为 `Hello, World!\n`。

| 条件 | 检查依据 | 本条结果 |
|---|---|---|
| `model_stopped` | 循环以 `finished` 结束 | 通过 |
| `output_observed` | 成功命令的 stdout 包含指定文字 | 通过 |
| `requested_file` | 当前文件 AST 符合单条 print | 通过 |

三项全部满足，任务判断为 `passed=true`。这是这个固定小任务的一次运行，不是通用编程能力的准确率。

## 反例得到什么结果

| 构造反例 | 正常停止 | 正确输出 | 正确文件 | 总体判断 |
|---|---|---|---|---|
| claim_only | 通过 | 未通过 | 未通过 | 不接受 |
| changed_artifact | 通过 | 通过 | 未通过 | 不接受 |

`claim_only` 说明正常停止不会补出动作和文件。`changed_artifact` 说明评分器检查的是当前产物：保留旧 stdout，仍不能让错误文件通过。

## 记录的范围

真实模型运行来自已保存的 [Docker 原始记录](https://github.com/lovits/learn-agent-evaluation/blob/main/generation/runtime-evidence.json)，对应源码提交 `090cf621ba3aa7f6456ce4d1a0b4c4a48241cb4e`。构造反例另外执行并单独标记，完整输入与逐项判断保存在本课 JSON。

这里没有评价最终解释的语言质量，也没有证明输出必定来自某个指定命令。AST 规则只用于本题结构，不证明任意程序行为等价。
