# AI Image & Video Skill Index

本仓库包含 11 个原子 Skill＋1 个总控工作流 Skill。

## 总控入口

- [build-image-fast](./build-image-fast/SKILL.md)：从抽象 Idea 到正式静态图与可恢复 AI Image Build Pack。V5 使用单一团队前台、atomic/direct/guided/controlled/edit 五种模式、G0/G1/G2、standing authorization、字段 provenance/effective validity、自动 asset release 与自动 QA。

### V5 门模型

| 模式 | 正式成图前拍板数 | 执行路径 |
| --- | ---: | --- |
| atomic | 不适用 | 单点原子任务；通常不强制完整 Build Pack |
| direct | 0 | 有效请求 → 正式图 → G2 |
| guided | 1 | G0 → 正式图 → G2 |
| controlled | 2 | G0 → 候选资产/G1 → 自动 asset release → 正式图 → G2 |
| edit | 通常 0 | 单一变更且保留项清楚 → 编辑 → G2；否则退出 edit |

- G0：创意决策包；不是团队入口。
- G1：仅 controlled 的视觉锚点包；不是通用生成授权。
- G2：正式图＋自动 QA＋Build Pack 的最终交付包；不计入 0/1/2，不追加 QA 或路径确认。
- “制作/生成/做/落地”形成范围内 standing authorization；后台角色和工具调用不增加用户拍板。
- risk_floor 记录最低风险级别；升级只补缺失标准门，不改写 G0/G1/G2 的语义。
- 字段变化只让自身及依赖下游失效；恢复从最早无效门续接。
- atomic 不强制完整 Pack；edit 只允许单一清晰变更，第二变量或保留不清时退出到 guided/controlled。
- review_mode 默认 adaptive；只有用户明确要求逐阶段审片时才用 full_review。full_review 暴露八阶段确认，但不是 workflow_mode，也不能降低风险底线或硬门。

## 原子 Skill

### 图片提示词与静态控制

- [image-prompt-specification](./image-prompt-specification/SKILL.md)
- [reference-image-prompt-reverse-engineering](./reference-image-prompt-reverse-engineering/SKILL.md)
- [constraint-aware-prompt-expansion](./constraint-aware-prompt-expansion/SKILL.md)

### 输入、编辑与一致性

- [generation-mode-reference-selection](./generation-mode-reference-selection/SKILL.md)
- [capability-cost-fit](./capability-cost-fit/SKILL.md)
- [preserve-change-edit-contract](./preserve-change-edit-contract/SKILL.md)
- [reference-anchor-density](./reference-anchor-density/SKILL.md)

### 视频叙事、生成与装配

- [video-direction-specification](./video-direction-specification/SKILL.md)
- [storyboard-event-budgeting](./storyboard-event-budgeting/SKILL.md)
- [endpoint-anchored-video-synthesis](./endpoint-anchored-video-synthesis/SKILL.md)
- [sequence-continuity-assembly](./sequence-continuity-assembly/SKILL.md)

## 组合关系

    build-image-fast
      ├─ generation-mode-reference-selection
      ├─ constraint-aware-prompt-expansion
      ├─ image-prompt-specification
      ├─ reference-image-prompt-reverse-engineering
      ├─ reference-anchor-density
      ├─ capability-cost-fit
      └─ preserve-change-edit-contract

    video-direction-specification
      → storyboard-event-budgeting
      → endpoint-anchored-video-synthesis
      → sequence-continuity-assembly

## 路由原则

- 完整 0→1 静态图片项目：build-image-fast，按 direct/guided/controlled 选择 0/1/2
- 单点原子任务：atomic，直接路由对应原子 Skill，通常不强制完整 Build Pack
- 单一变更且保留项清楚的图片编辑：edit，并调用 preserve-change-edit-contract
- 第二变更变量或保留项不清的编辑：退出 edit，转 guided/controlled
- 用户明确要求逐阶段审片：review_mode=full_review；否则保持 adaptive
- 只写或优化图片提示词：image-prompt-specification
- 只反推参考图：reference-image-prompt-reverse-engineering
- 只比较模型成本/能力：capability-cost-fit
- 完整 5–30 秒视频项目：build-ai-video-fast（如已安装）

## 验证入口

- [build-image-fast/test-prompts.json](./build-image-fast/test-prompts.json)：V5 合同 fixture
- [build-image-fast/scripts/validate_contract_cases.py](./build-image-fast/scripts/validate_contract_cases.py)：fixture schema/一致性验证器
- [build-image-fast/test-results.md](./build-image-fast/test-results.md)：当前验证命令、覆盖范围与未验证边界
- 各原子 Skill 的 test-prompts.json 与 test-results.md：原有 66 条测试
