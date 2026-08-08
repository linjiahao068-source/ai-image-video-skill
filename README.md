# AI Image & Video Skill

一套可直接调用的 AI 影像创作技能包：包含 11 个原子 Skill＋1 个总控工作流 Skill。11 个原子 Skill 来自《影视飓风 AI 实战课》的方法蒸馏；build-image-fast V5 在其上提供 atomic/direct/guided/controlled/edit 五种工作模式、单一团队前台、0/1/2 拍板、G0/G1/G2、standing authorization、字段级有效性、asset release、自动 QA 与可恢复 Build Pack。

## 完整静态图片项目

使用 [build-image-fast](./build-image-fast/SKILL.md)。

### V5 工作模式与 0 / 1 / 2

| 模式 | 正式成图前阻塞式用户拍板数 | 路径 |
| --- | ---: | --- |
| atomic | 不适用 | 单点原子任务；通常不强制完整 Build Pack |
| direct | 0 | 无门；请求字段有效时立即生成 |
| guided | 1 | G0 创意决策包 |
| controlled | 2 | G0 创意决策包 + G1 视觉锚点包 |
| edit | 通常 0 | 单一变更项与保留项清楚时编辑后自动 G2；否则退出 edit |

0/1/2 只聚焦 direct、guided、controlled 的正式成图前阻塞式用户拍板。edit 在合同清楚时通常为 0；atomic 不进入完整项目拍板模型。团队交接、内部阶段、自检、asset release、QA、返修、Build Pack 和路径检查不额外计数。

review_mode 默认 adaptive。只有用户明确要求逐阶段审片时才使用 full_review，把八个内部阶段分别暴露为确认门；full_review 不是第六种 workflow_mode，也不能降低 risk floor、G0/G1 硬门或权利阻断。用户明确切回 adaptive 后，按当前有效字段恢复标准门。

- G0：需求、故事/信息、角色、权利、推荐方向与关键假设。
- G1：仅 controlled 使用；一次性提交候选资产、三件套 candidate_preview、压力测试摘要和审核。G1 不是通用生成授权。
- G2：正式图、自动 QA、Build Pack、最终路径与哈希的最终交付包；不计入 0/1/2，也不再追加 QA 或路径确认。

用户明确要求“制作、生成、做、落地”时形成范围内 standing authorization。direct 立即生成；guided 在 G0 后生成正式图；controlled 在 G0 后生成候选资产，在 G1 通过并自动完成 asset release 后生成正式图。用途、权利或关键字段越界会让授权或依赖字段失效。

默认调用：

    Use $build-image-fast to turn my idea into a confirmed AI Image Build Pack and a validated final image.

图片总编是唯一用户前台。内容与角色导演、美术指导、执行场记在后台通过版本化文件交接，不各自向用户增加确认。高风险项目用 provenance 与 effective validity 保留来源、字段依赖、失效范围和恢复点。

Seedance 2.0 只提供可选动画化交接，不在本工作流中生成视频。

## atomic 单点任务与 edit

直接调用原子 Skill 时使用 atomic，不启动完整项目的 0/1/2 门，也通常不强制生成完整 Build Pack。

局部图片编辑只有在目标图、单一变更项和保留项都清楚时使用 edit，通常 0 次阻断拍板，编辑后自动 G2。出现第二变更变量或保留边界不清时必须退出 edit，改用 guided 或 controlled。

### 图片提示词与静态画面

- [image-prompt-specification](./image-prompt-specification/SKILL.md)：把模糊画面意图变成按需裁剪的视觉规格。
- [reference-image-prompt-reverse-engineering](./reference-image-prompt-reverse-engineering/SKILL.md)：从参考图的可见证据反推可验证提示词。
- [constraint-aware-prompt-expansion](./constraint-aware-prompt-expansion/SKILL.md)：在严格控制和创意探索之间选择扩写方式。

### 输入、编辑与一致性

- [generation-mode-reference-selection](./generation-mode-reference-selection/SKILL.md)：按最难控制的变量分配输入模态和素材职责。
- [capability-cost-fit](./capability-cost-fit/SKILL.md)：按失败风险选择能力、速度和成本档位。
- [preserve-change-edit-contract](./preserve-change-edit-contract/SKILL.md)：把局部编辑写成变更项与保留项合同。
- [reference-anchor-density](./reference-anchor-density/SKILL.md)：按保真风险配置多视图、端帧和细节锚点。

### 视频叙事、生成与装配

- [video-direction-specification](./video-direction-specification/SKILL.md)：把情绪和故事写成可观察的动作、镜头与节奏。
- [storyboard-event-budgeting](./storyboard-event-budgeting/SKILL.md)：用时长和事件预算决定分镜颗粒度。
- [endpoint-anchored-video-synthesis](./endpoint-anchored-video-synthesis/SKILL.md)：用首尾帧或关键帧锁定必须命中的状态。
- [sequence-continuity-assembly](./sequence-continuity-assembly/SKILL.md)：修复多片段之间的动作、空间、接缝和节奏。

完整索引与组合关系见 [INDEX.md](./INDEX.md)。

## 安装

复制需要的完整 Skill 目录到 Codex skills 目录。使用 build-image-fast 时，同时安装它调用的图片原子 Skill。仓库不要求安装全部 11 个原子 Skill 才能使用某一个单点 Skill。

## 测试与验证

- 11 个原子 Skill 的 66 条原有独立用例保持单独统计。
- build-image-fast/test-prompts.json 是 V5 合同 fixture，不是已执行的 LLM 测试结果。
- build-image-fast/scripts/validate_contract_cases.py 只验证 fixture schema、V4 39 条迁移完整性、V5 覆盖、受控事件枚举与跨字段一致性，不调用 LLM 或图片模型。
- 实际运行结果、未执行边界和历史验证分别记录在 [verified.md](./verified.md) 与 [build-image-fast/test-results.md](./build-image-fast/test-results.md)。

## 来源、边界与许可

仓库只发布课程方法蒸馏出的工作流、示例、测试和说明，不包含原始课程视频、音频、转写稿、课件或截图。真实人物、商标、受保护角色和商业交付仍需确认授权、隐私、品牌规范与人工审核。

原创蒸馏文本与代码采用 [MIT License](./LICENSE)；该许可不覆盖原课程及其素材。
