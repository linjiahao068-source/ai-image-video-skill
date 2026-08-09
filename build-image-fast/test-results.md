# build-image-fast 验证入口

此路径保留用于兼容既有 README、索引和外部引用，不再维护易过期的静态测试流水账。

当前验证边界、已知限制与历史结论以[仓库级验证说明](../verified.md)为准；当前代码是否通过，以本地实时命令结果为准。

## 最小验证

```powershell
python -m unittest discover -s scripts -p 'test_*.py'
python scripts/validate_contract_cases.py
```

测试数量、时间和逐项输出不写回本文件，避免把一次运行快照误当成持续事实。
