# build-image-fast 验证

本文件是 build-image-fast 的唯一验证入口。验证命令只检查代码与合同，不调用图片模型。

## 最小验证

```powershell
python -m unittest discover -s scripts -p 'test_*.py'
python scripts/validate_contract_cases.py
```

## 能证明什么

- 单元测试覆盖状态门、资产组装、确定性排字、归档与相关失败边界。
- 合同 fixture 只验证结构、枚举与跨字段一致性，不等于 Agent、图片生成或视觉 QA 实跑。
- 当前是否通过以本地实时命令输出为准，不在文档中保存易过期的数量、耗时或历史快照。

## 未验证

真实图片生成、角色或文字视觉质量、模型一次成功率、真实 G2 QA 和外部发布仍需对应任务单独执行。
