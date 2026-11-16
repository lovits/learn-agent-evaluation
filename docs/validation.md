# 第1课首次制作验收记录

真实任务已在Docker运行，记录见 [完整示例报告](../lessons/e01_agent_baseline/example_report.json)。
本课模型驱动最小循环执行Bash，随后在独立无网络verifier容器按固定合同验收。
4条任务：列目录、创建运行程序、运行现有脚本、观察原始脚本错误。
当前实际报告为4/4通过、8次模型请求、4条Bash命令；合成假报成功被独立验收器拒绝。

最终中文解释的语义、通用编码能力和模型费用金额不在本课评分范围。
CLI没有回传确切模型ID，报告保留null与CLI默认选择说明，不声称固定型号。
本地和Docker断网环境均为20项测试通过，Ruff通过。已实际检查知识库只读、Agent镜像无私有验收文件和登录凭据、
verifier工作目录只读及外部连接不可达。完整机器记录见docs/validation.json。

教材由PocketFlow原版写作节点实际生成1次，并经源码/报告核对；原始稿与审校稿分开保存。
16课完整制作规范已同步 [飞书云文档](https://my.feishu.cn/docx/V8CPdL3Y8oMZt4xJ8RCc4HfNnfb)。

第1课后续图文改写的检查另见[改写验收](e01-rewrite-validation.md)。上面的任务记录和20项测试是首次制作时的历史事实。
