# e01 源码导读：从动作到评分

[教材](README.zh.md) · [Agent](code.py) · [评分器](eval.py)

## 沿着两个入口读

```text
code.py
  prepare_workspace → agent_loop → call_model
                            ↓
                         run_bash
                            ↓
                  工具结果回填 messages

eval.py
  evaluate → check_rule → 文件 / 执行事件
```

`messages` 给模型继续工作；`events` 给外部程序读取运行过程。两份数据服务于不同角色，评分器不从最终回答里的“成功”推导文件状态。

`call_model` 检查动作结构。`agent_loop` 的空调用分支返回 `finished`，预算耗尽返回 `step_limit`，模型传输或结构异常返回 `model_error`。工具错误照常回填，给模型修正机会。

`run_bash` 设置工作目录、收集 stdout/stderr 和退出码，并处理超时与输出截断。工作目录隔离避免旧文件干扰；Shell 阻断词只覆盖有限教学情形。

## 先看评分标准读了什么

`check_rule` 按规则类型取证：

- `successful_stdout_contains`：只接受退出码为0的对应输出。
- `error_contains`：寻找非零退出及指定错误文本。
- `file_sha256`：检查要求保留的文件内容。
- `python_ast`：解析实际代码与要求的代码结构，再比较 AST。

`evaluate` 汇总逐项检查。通过比例用于定位，全部满足才接受任务。它不评价最终解释是否清楚，也不证明任意 Python 程序功能等价。

## 对照 Learn Claude Code

[s01 的 agent_loop](https://github.com/shareAI-lab/learn-claude-code/blob/448c75bb596917ad196cc1fb7558f459c5c50fdd/s01_agent_loop/code.py) 也是模型请求、提取动作、执行 Bash、回填结果，没有动作就返回。本课在这个主干外增加工作目录、运行记录与独立评分。

模型由宿主接口提供，工具在容器中执行。模型接口只返回动作；本课被评测的是课程 Agent。

## DeepEval 怎样分开样本与指标

[dataset.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/dataset/dataset.py) 分别组织 Golden、测试样本和运行结果。Golden 保存任务及预期，实际输出要由被测应用运行得到。

[evaluate.py](https://github.com/confident-ai/deepeval/blob/34db63dd005ebc9a905c8ef4741ae0687c93c14c/deepeval/evaluate/evaluate.py) 校验样本与指标配置，再选择同步或异步执行并整理结果。框架可以负责调度，业务上的“成功”仍由所选指标定义。

对照[评测入门](https://deepeval.com/docs/evaluation-introduction)，本课的文件规则承担 metric 的职责，运行报告承担被评分记录的职责。

## Ragas 怎样把应用与评价接起来

[experiment.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/experiment.py) 把应用函数用于数据行，并收集逐行结果；数据载体见 [dataset.py](https://github.com/vibrantlabsai/ragas/blob/8c63f10d500c44efbf24fdb9e2920de2104c321c/src/ragas/dataset.py)。[实验概念](https://docs.ragas.io/en/stable/concepts/experimentation/)解释这几个角色怎样配合。

这套分工让我们能替换 Agent 或评分器，而不用把两者写成一个函数。本课使用自己的确定性规则；两框架的样本接口从下一课开始接入。
