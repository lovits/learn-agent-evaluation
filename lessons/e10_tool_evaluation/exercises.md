# 第10课练习

1. 对照两轮tool_snapshots，指出connect_mcp前后模型能看见的名字。为什么同一轮不能凭空使用尚未发现的工具？
2. 用相同调用重复一次，再交换读/改顺序，手算集合F1并比较原生排序指标。哪些分数没有惩罚重复？
3. reference只要求path，预测多传unused时，DeepEval参数分、Ragas参数分和完整参数集合F1各测到了什么？再把query的字符串42改成整数42，对照handler实际接收结果。
4. 双方空调用时，比较第3课自写集合F1、原生Ragas F1、Accuracy和ArgumentCorrectness。哪些任务应标记不适用，而非解释为成功/失败？
5. 将一个未批准server工具描述写成readOnly并加readOnlyHint。证明handler不会执行；再试用参数tool覆盖已绑定原工具，检查错误边界。
6. 找出第一轮MCP参数判定中的no。真实Agent是否没检索，还是评分投影删掉了证据？列出修订时改变和未改变的对象。
7. 对decision_contexts删除一条先前tool_result，再给更早决策添加未来结果。分别解释信息缺失与未来泄漏；用source_model_span定位问题。
8. 用write_file代替edit_file完成相同修复。业务文件可以通过时，为什么相对某条literal参考的工具分仍可能下降？
9. 修改calculate.py为只写print(48)，保留result.txt，观察直线乘法合同为何拒绝。再写命名中间变量版本，解释本课验收的适用范围。
