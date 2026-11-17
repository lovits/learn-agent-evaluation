# 集成接线首次运行的连接失败

首次Docker运行使用references/e16-foundation-protocol.json，原报告与逐调用记录原样保留。应用和目标审查各尝试一次SDK请求，均在发送HTTP前失败；0次成功模型响应，宿主模型桥没有收到POST。它不是一次通过的Agent任务。

实际容器探测确认宿主接口HTTP 200，原生SDK的异常链为：APIConnectionError → LocalProtocolError: Illegal header value b'Bearer '。适配器将空字符串传给OAuth参数，SDK生成了非法的空Bearer请求头。修复为在临时、不含用户OAuth值的导入配置中创建客户端，然后恢复原环境；本地桥只使用明确的占位API Key。

新增回归检查经Runtime创建真实原生SDK，对实际HTTP服务读取healthz，检查未发送Authorization头、未继承用户测试token、未请求模型。此检查通过后另建v2协议、独立工作区和报告，未覆盖本次记录。之前的SDK通路测试直接创建客户端，未覆盖Runtime构造路径，因此没有发现这一错误。
