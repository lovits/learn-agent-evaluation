# s07 动手练习

先独立作答，再看 [参考答案](solutions.md)。完整代码为 `code.py`，
所有固定预期来自预设教学标注，不是对真实模型输出的保证。

## 练习 1：先手算再运行

打开 `fixtures.json` 的 mixed 样本。三个声明分别是 supported、unsupported、
contradicted。写下三个指标列的分子、分母与预期结果，再运行：

```sh
docker compose run --rm course replay --sample mixed
```

验收：解释 2/3、1/3、1/3 的来源；不能把差异写成“某框架更聪明”。

## 练习 2：两个开关不是一回事

阅读源码页及 `eval_course/runner.py`。解释为什么
`penalize_ambiguous_claims=True` 仍可能得到 1/3，而 `strict_mode=True`
会把未达到阈值的结果钳制为 0。指出本课命令实际启用了哪一个开关。

验收：能区分“什么 verdict 算通过”和“整个样本是否达到门槛”。

## 练习 3：修改证据，观察快照失效

复制示例知识库至 `my_knowledge`，在复制件的退款规则中补充“退货运费由商家承担”。
设置 `.env` 的 `KNOWLEDGE_DIR=./my_knowledge`，然后运行：

```sh
docker compose up -d --force-recreate
docker compose run --rm course search "运费"
docker compose run --rm course replay --sample unsupported
```

验收：搜索看到新规则；replay 报快照不一致，而不是继续使用旧判定给分。
若已配置裁判，可以显式运行 live；分数应人工复核，不能承诺模型必得 1。
做完后把 KNOWLEDGE_DIR 改回 ./knowledge_base 并重建容器。

## 练习 4：没有声明不等于没有问题

```sh
docker compose run --rm course replay --sample no_claims
```

查看 runs 中结果：为什么 DeepEval 得到 1，而 Ragas 是 null？
为什么不能将其解释为“你好！”是这道退款问题的最佳回答？

验收：指出这是固定的空声明输出；解释 JSON null 表示未评分，不能当 0。

## 练习 5：知识库也可能错

在独立复制件中把期限改成 60 天，写一个与这份错误规则一致的回答。
不用修改官方样本，先说明 Faithfulness 能检测什么、还需要哪类独立证据。

验收：能区分“忠于给定证据”和“符合现实业务真相”；不会用单指标概括质量。
