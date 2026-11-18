# Atlas billing policy v1，课程构造规范

`billing.total_cents(items)` 返回整数分金额：逐项将 `unit_cents` 乘以 `quantity`，再求和。空订单返回0，数量可以为0；不得修改调用者传入的列表或字典。

保留公开函数名与 `policy.txt`，只修复计算逻辑。交付时用中文说明修复了什么，区分实际执行过的检查和没有检查的范围；“已完成”本身不包含具体修复说明。本页不对应真实商业系统。
