# 第15课正式模型实验前的依赖检查失败

以下为本次首次本地fixture测试输出的摘录，来自当前工作记录，不是后来重新运行制造的失败日志。此时没有启动第15课的正式裁判实验。

```text
test_native_ragas_alignment_recent_examples_and_validation_pairing
ragas/metrics/discrete.py:83: ModuleNotFoundError: No module named 'sklearn'
ImportError: scikit-learn is required for correlation calculation. Please install it with `pip install scikit-learn`.
1 failed, 12 passed in 2.14s
```

原生 `validate_alignment` 在评分回调完成后计算κ，需要额外依赖。加入并锁定scikit-learn 1.7.2及其必要依赖后，本课13项、本地全套208项与Docker断网208项通过。前述fixture回调不是供应商调用；正式48次裁判响应全部发生在依赖修复、Docker构建成功、源码哈希冻结之后。
