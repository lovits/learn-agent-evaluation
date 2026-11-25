# e12 样本与评测记录

[教材](README.zh.md) · [构造条件](cases.jsonl) · [完整记录](assessment.json)

## 样本来源与判据

八组决策由课程构造后交给既有 `run_case` 循环在隔离工作区里真实执行，最终回复统一为 `"已完成。"`，写入 `billing.py` 与 `policy.txt` 的内容各不相同。

独立评分拆成两条线：`DeliveryContract` 检查四组订单探针的返回类型、金额、输入不变性以及 `policy.txt` 字节哈希；DeepEval `TaskCompletionMetric` 依据完整任务说明评估语义对齐度与修复说明义务。两列结果各自保留，不合成平均分。

## Docker 中的规则观察

默认运行编号为 `dc9742c9a387430abd1693a78e0fb5d6`，八组条件全部在 Docker 内执行完毕，无模型请求：

| 条件 | 程序契约 | 实际观察 |
|---|---:|---|
| `correct` | 1 | 求和表达式通过全部行为与保护检查 |
| `claim_only` | 0 | 未修改文件，含商品订单金额均错 |
| `still_broken` | 0 | 写回原错误代码，仍漏乘数量 |
| `hardcoded` | 0 | 固定返回 `650`，仅巧合通过演示订单 |
| `mutates_input` | 0 | 金额正确，但 `pop()` 清空了非空输入列表 |
| `policy_changed` | 0 | 金额与输入检查全过，`policy.txt` 被改写 |
| `syntax_error` | 0 | 加载模块触发 `SyntaxError` |
| `equivalent_loop` | 1 | 显式循环与求和表达式满足相同的当前行为契约 |

其中 `syntax_error` 属于探针正常捕获到的交付失败（`loaded=False`），因此记为有效 `0` 分。配套单元测试另验证了缺失文件、越界符号链接以及探针输出无效 JSON 或空字典时 `DeliveryContract` 会抛出异常、由外层标为 `error`，避免因 Python `all([])` 误得满分。

## 原生 Task Completion 对照

补充评测运行编号为 `6e25dfe26d9a487b9d715c34c89cc80e`，共发出 22 次 DeepEval `TaskCompletionMetric` 请求，保留全部 `judged_task`、`outcome`、`score` 与 `reason`：

| 条件 | 程序契约 | 含独立观察的语义分 |
|---|---:|---:|
| `correct` | 1 | 0.95 |
| `claim_only` | 0 | 0.25 |
| `still_broken` | 0 | 0.2 |
| `hardcoded` | 0 | 0.1 |
| `mutates_input` | 0 | 0.55 |
| `policy_changed` | 0 | 0.65 |
| `syntax_error` | 0 | 0.05 |
| `equivalent_loop` | 1 | 0.95 |

在包含 `independent_observation` 的评分中，`correct` 与 `equivalent_loop` 的理由正确指出程序契约已达标，但因为最终只回复 `"已完成。"` 而未说明修复内容，所以给出 `0.95`（未给满分）。`mutates_input`（`0.55`）与 `policy_changed`（`0.65`）虽然拿到中间分，但理由明确指出了破坏输入或改写策略文件的违约行为；硬条件失败后仍以 `DeliveryContract = 0` 为准。

针对 `correct` 与 `claim_only` 的不含独立观察对照组（保留真实 `tools_called`）得分分别为 `1` 和 `0`。在不含观察的组别中，`correct` 抽出的 `outcome` 只写到 `"AI 回复已完成"`，裁判理由却写着“结果也说明了修复内容”，暴露了文本对齐判断的一处偏宽现象，记录已保留供第 14 课裁判校准使用。

## 真实 Agent 与中断重试记录

较早运行编号 `e9170e71d7c34a81902622ef7031c581` 完成了真实模型修复任务（`earlier_live_success`），发出 2 次裁判请求，程序契约与语义分均达到 `1`。

在 `6e25dfe26d9a487b9d715c34c89cc80e` 这次运行中，新增的真实任务 `live_repair` 在执行 2 次工具事件后遇到模型桥接 HTTP 502 错误，循环以 `status="model_error"` 退出，`billing.py` 尚未修复，程序契约为 `0`。后续 `TaskCompletionMetric` 对该中断现场评分给出 `0.15`，完整反映了已发生动作但未完成修复的状态；该次中断记录原样保留，未被改写。

随后在保持任务要求、初始文件和评分规则完全不变的前提下，单独重试同一真实修复任务（运行编号 `db9f9f046bd6473b9dbbed98a3043bec`，保存在 `recovery_attempt` 的 `live_repair_retry` 条件中）。模型顺利完成 4 次响应与 4 次工具事件并正常退出（`finished`），经 2 次原生裁判请求后，独立观察确认金额、输入不变与策略文件全部通过，程序契约与语义分均为 `1`。

## 覆盖范围

四组订单探针检验了当前指定的典型边界，更广的订单规模与异常输入需靠扩充用例或性质测试验证；`policy.txt` 哈希比对反映观察前后的字节状态，过程审计需要结合工具事件流核查。检查端采用 `python -I` 与 5 秒超时实现进程级分离，在教学容器内验证功能逻辑；真实生产环境下评测未知代码需部署在隔离权限容器与只读环境中。所有语义得分均为当次运行观察结果，具体业务阈值的校准将在第 14 课展开。
