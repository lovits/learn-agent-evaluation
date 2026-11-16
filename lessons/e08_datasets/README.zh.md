# 第8课：评测数据集，从候选题到可审核样本

## 问题

上一课沿资料、检索和生成三个位置排查失败。要把查明的问题交给下一个 Agent 版本复测，还需要保存原任务、证据和成功条件。否则换一份文档、改一句问题，比较的就可能是两件事。

知识库更新后，原来的参考答案可能失去依据。以挂载知识库里的上传接口为例，一条候选需要同时保存：

- 任务：例如上传认证方式或文件大小上限；
- 参考：证据支持的预期答案；
- 来源：文档 ID 与正文 SHA-256；
- 验收合同：编程任务需要检查的文件和标准输出。

本课使用 `synthetic v1` 文档，其中上传上限是 1 MiB，也就是 `1048576` 字节。不要把它与第6课上限为 2 MiB 的 `v2` 文档混用。

这一课先准备数据，目标 Agent 尚未执行。候选样本的 `actual_output` 一律为空。这样可以先核对题目与参考，等真正复测时再填入实际结果。

## 解决方案

![候选题生成与审核流程](images/dataset-pipeline.png)

[点击查看原尺寸流程图](images/dataset-pipeline.png)

流程从真实挂载文档出发。DeepEval 和 Ragas 的原生生成器产生候选题，手写种子补充不可回答题与编程任务。所有来源最后映射到同一种候选结构，再经过独立的参考支持审核、重复检查和题族切分。

图中的“待人工审核”表示候选通过了当前自动检查，可以交给人逐条确认。本次记录的人工通过数为 0；正式测试前还要完成这一步。

完整入口分别是：

- [code.py](code.py)：生成候选、调用自动审核并写报告；
- [dataset.py](dataset.py)：检查结构、来源、重复和题族划分；
- [eval.py](eval.py)：断网重算数据合同，不调用模型。

## 工作原理

**第1步：把问题、参考和证据装进同一种候选结构**

`source_documents`每次读取当前挂载文档，并把文档 ID 和正文 SHA-256 放进证据记录。这样可以查出两次运行之间资料是否变过。下面是 [code.py](code.py) 的局部源码，省略了导入和其他函数：

```python
def source_documents():
    return [{"id": p, **document(p)} for p in SOURCE_IDS]

def evidence(documents):
    return [{"id": d["id"], "sha256": d["sha256"]} for d in documents]
```

候选函数先保存问题和参考，再统一保存 `origin`、`family`、`query_type`、`difficulty`、`answerable`，并明确设置 `actual_output=None`。`difficulty`只是课程里的教学标签，没有经过难度标定，不能把 `easy` 或 `medium` 当作实验结论。

第1课的 `list_files` 和第2课的 `edit_and_run` 也作为编程种子保存。它们不只写自然语言参考，还分别记录必须出现的文件名，以及 `expected_stdout`、结果文件和预期内容。以后真正运行 Agent 时，验收器应检查实际文件与标准输出，不能复制参考答案冒充结果。

**第2步：让 DeepEval 从指定上下文生成两类 Golden**

本课给 DeepEval 一份或两份真实上下文，分别生成一条推理题和一条多上下文题。下面是原生调用的局部源码，省略了模型适配和循环外代码：

```python
goldens = synthesizer.generate_goldens_from_contexts(
    contexts=[[d["text"] for d in docs]],
    max_goldens_per_context=1,
    include_expected_output=True,
    source_files=[[d["id"] for d in docs]],
    context_chunk_source_files=[[d["id"] for d in docs]],
    _send_data=False,
)
```

配置中，`REASONING` 与 `MULTICONTEXT` 各运行一次，`include_expected_output=True` 要求生成参考。critic 与生成器显式共享同一个模型，`max_quality_retries=1`。

真实两条 Golden 的 `synthetic_input_quality` 分别为 `0.4` 和 `0.2`，低于默认阈值 `0.5`，但仍被 SDK 保留。这是因为固定版本的 `_rewrite_inputs` 在重试用完后仍会追加结果，后面还会执行演化、风格加工和参考生成。因此，旧阶段分数既不能保证最终问题质量，也不能直接充当最终拒收分。调用链和固定源码版本见[源码导读](source_walkthrough.md)。

**第3步：用 Ragas 的原生图结构生成单跳与多跳题**

这里选择 Ragas 的预构建图入口：用正则从两份文档中提取共同出现的 `POST /upload`，再建立原生 `Relationship`。局部源码如下，省略了节点构造细节：

```python
common = sorted(set(nodes[0].properties["entities"]) & set(nodes[1].properties["entities"]))
if not common:
    raise ValueError("No shared endpoint; do not manufacture a multi-hop relation")
relation = Relationship(
    source=nodes[0],
    target=nodes[1],
    type="entities_overlap",
    bidirectional=True,
    properties={
        "overlapped_items": [(x, x) for x in common],
        "construction": "exact endpoint rule",
    },
)
```

两份文档的共同端点是连边依据；找不到它时，代码报错，提示先检查资料或构图规则。

预构建的 `KnowledgeGraph` 和手写的 Python 开发者 persona 随后传给 `TestsetGenerator`。`embedding_model=None`，具体单跳与具体多跳生成器各占 `0.5`，总共生成 2 条。本课确实运行了这两种原生 synthesizer，没有运行抽象多跳。

题目即使收到两个节点，也可能只问其中一份文档就能回答的事实。因此 `multi_hop` 仍只是待审核标签，后续还要检查题目是否真的依赖两份文档。

**第4步：统一候选，并让独立入口审核参考**

DeepEval 与 Ragas 的结果都经过 `candidate` 映射。自动审核使用宿主机的 `8768` 入口，返回参考是否受支持、是否必须使用多份来源，以及理由。下面是 [code.py](code.py) 的真实校验片段，省略了提示词正文：

```python
result = json.loads(transport.ask(prompt))
if (
    type(result.get("supported")) is not bool
    or type(result.get("requires_multiple_sources")) is not bool
    or not isinstance(result.get("reason"), str)
):
    raise ValueError("Invalid automated support review")
return result
```

`8769` 承担生成角色，`8768` 承担参考审核角色；角色彼此区分，但两者仍来自本机登录的模型来源，不能声称是两种独立模型。

参考模型也可能判断错误，所以本次留下的 7 条候选仍是 `pending_human`，人工通过数为 0。对于“`POST /upload` 会重试几次”这种资料没有回答的问题，参考必须保持未知并请求重试策略，不能猜成 0 次。

**第5步：检查来源版本、重复题和跨题族泄漏**

自动审核之后，[dataset.py](dataset.py) 再检查来源哈希和重复关系。题族被固定映射到三个集合：`upload_contract` 属于开发集，`directory_listing` 属于校准集，`file_edit` 属于留出集。

下面是重复处理的关键源码，省略了其他结构检查：

```python
cluster = clusters[question_key(row["question"])]
duplicate_of = cluster[0]["id"] if cluster[0]["id"] != row["id"] else None
if len({r["family"] for r in cluster}) > 1:
    errors.append("cross_family_duplicate")
elif duplicate_of:
    errors.append("duplicate_question")
```

同一题族的重复题保留第一条，后续题记录 `duplicate_of` 并隔离。若相同问题横跨题族，两条都要隔离，防止同一个任务同时进入开发集和留出集。

`question_key`只执行 NFKC、`casefold` 和去标点，能发现词面重复，却不能保证识别翻译或语义改写。Jaccard 相似度也只提供人工复核提示，不能代替语义去重。这里使用公开课程材料分组只是演示，不是盲测。

**第6步：断网重算14项数据合同**

生成报告后，[eval.py](eval.py) 在独立的断网 verifier 中重新运行 `audit`，并检查14项合同。下面是其中几项真实检查，省略了其余项目：

```python
checks = {
    "duplicate_rejected": "duplicate_question" in by_id["injected-duplicate"]["errors"],
    "wrong_reference_rejected": "reference_not_supported"
    in by_id["injected-wrong-reference"]["errors"],
    # 其余合同检查见完整eval.py。
}
```

控制反例把上限错误写成 `2097152` 字节，而证据中的 `synthetic v1` 是 `1048576` 字节，因此它被标记为 `reference_not_supported`。重复反例则保留 `duplicate_of`，便于追查原题。

真实报告共有原生候选4条、手写种子3条、控制反例2条；最终7条待人工审核、2条隔离，按题族得到5条开发、1条校准、1条留出。完整计数见[运行摘要](run_summary.md)。这里没有 Agent 实际输出，也没有准确率；报告保存的是生成与审核的提示、响应、来源和自动理由。

## 相对上一课的变更

| 方面 | 上一课 | 本课 |
|---|---|---|
| 知识来源 | 使用挂载知识库与业务合同 | 将来源哈希绑定到候选版本 |
| 主要目标 | 定位一次运行中的 bad case | 把问题变成可重复评测的候选 |
| 新机制 | 保存故障记录 | 生成、参考审核、去重与题族划分 |
| Agent | 真实干预并重跑六组任务 | 不运行新的目标 Agent |
| 工具与规划 | 沿用已有能力 | 不引入 Agent 规划或新工具 |

候选冻结了任务、参考和来源，下次修改 Agent 时就能复测同一份合同。

## 试一下

模型登录保留在宿主机，不放进容器。先在两个独立终端分别保持生成桥和审核桥运行：

```bash
python3 tools/generation_bridge.py
```

```bash
python3 tools/judge_bridge.py
```

它们分别监听 `8769` 和 `8768`。然后在第三个终端构建镜像并生成数据：

```bash
docker compose build
docker compose run --rm -T --entrypoint python course \
  -m lessons.e08_datasets.code
```

生成会覆盖 `runs/e08-dataset.json`。需要比较两次运行时，请先把旧文件另存。教材中的 [example_report.json](example_report.json) 固定保留了本次真实运行。

接着执行断网独立验收：

```bash
docker compose --profile verify run --rm -T \
  --entrypoint python verifier -m lessons.e08_datasets.eval
```

验收会覆盖 `runs/e08-dataset-grade.json`；固定结果见 [grade_report.json](grade_report.json)。

阅读课程页面时运行：

```bash
docker compose up -d
```

然后打开 `http://localhost:8765/lesson8`。

请回到报告中观察三个问题：

1. `0.4` 和 `0.2` 为什么仍出现在最终保存的 Golden 中？
2. 错误的 `2097152` 字节参考被隔离时，报告留下了哪些证据和理由？
3. 两条多跳参考分别依赖 `auth.md` 与 `limits.md` 中的哪些事实？

进一步练习与核对材料：

- [源码导读](source_walkthrough.md)
- [练习](exercises.md)
- [参考答案](solutions.md)
- [运行摘要](run_summary.md)
- [独立验收说明](../../docs/e08-validation.md)
- [生成环境说明](../../generation/e08-README.md)

## 接下来

这一课把一次性的 bad case 变成了带任务、参考、来源版本和验收合同的候选数据。自动审核隔离了重复题和错误参考，其余样本仍须人工确认。公开材料上的题族切分演示了操作方法；要检验泛化能力，还需另备未见过的任务族。

下一课在同一批任务上配对比较两个版本：逐题变化是否一致，有没有某类任务退步，少量样本带来的不确定性又该怎样报告。
