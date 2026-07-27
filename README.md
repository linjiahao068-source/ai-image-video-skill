# AI Video Production Skill

一套可直接调用的 AI 影像创作技能包：将《影视飓风 AI 实战课》中可迁移的方法，蒸馏为 **11 个独立、可组合、可测试** 的 AI skill。

它不是课程笔记的再排版。课程只提供来源；这个仓库的重点是把「怎么选输入、怎么锁定画面、怎么规划镜头、怎么把片段接成成片」转成可执行工作流。

## 这套 skills 能解决什么问题

- 手上同时有文字、参考图、动作视频和音乐，不知道应该怎样分配职责。
- 图生图或视频编辑时，想改变局部，却总把人物、构图、动作一起改坏。
- 人物、产品或场景跨镜头不稳定，不知道该补什么参考素材。
- 只有一个情绪或故事想法，生成结果却像静帧，缺少可见动作和镜头语言。
- 多个生成片段各自看起来不错，但拼起来动作断裂、节奏混乱、配乐不统一。

## 蒸馏了什么

### 图片提示词与静态画面控制

- [`image-prompt-specification`](./image-prompt-specification/SKILL.md)：将模糊想法写成按需取舍的时间、主体、场景、风格四维规格。
- [`reference-image-prompt-reverse-engineering`](./reference-image-prompt-reverse-engineering/SKILL.md)：从参考图的可见证据反推可验证提示词，不承诺像素级复刻。
- [`constraint-aware-prompt-expansion`](./constraint-aware-prompt-expansion/SKILL.md)：在严格控制与创意探索之间选择扩写方式，并让约束可验收。

### 输入模式、编辑与一致性

- [`generation-mode-reference-selection`](./generation-mode-reference-selection/SKILL.md)：按最难控制的变量选择文生、图生、视频或音频参考，并分配素材职责。
- [`capability-cost-fit`](./capability-cost-fit/SKILL.md)：按交付风险选择能力档位，把探索成本与最终交付成本分开。
- [`preserve-change-edit-contract`](./preserve-change-edit-contract/SKILL.md)：把局部编辑写成“要改变什么／必须保留什么”的契约。
- [`reference-anchor-density`](./reference-anchor-density/SKILL.md)：按保真风险配置多视图、端帧与细节锚点。

### 视频叙事、生成与装配

- [`video-direction-specification`](./video-direction-specification/SKILL.md)：把情绪与叙事意图转换为主体、可见动作、效果、镜头和节奏。
- [`storyboard-event-budgeting`](./storyboard-event-budgeting/SKILL.md)：以脚本、时长、事件数与镜头预算制定生成计划。
- [`endpoint-anchored-video-synthesis`](./endpoint-anchored-video-synthesis/SKILL.md)：用首帧、尾帧或关键帧约束生成、延展与循环。
- [`sequence-continuity-assembly`](./sequence-continuity-assembly/SKILL.md)：通过动作、空间、接缝修复与节拍把片段装配成序列。

完整的组合关系和推荐学习顺序见 [INDEX.md](./INDEX.md)。

## 使用方式

1. 在 [INDEX.md](./INDEX.md) 中按你的任务找到对应 skill。
2. 读取该目录的 `SKILL.md`，使用其中的触发条件、执行步骤与边界完成任务。
3. 若任务跨越多个阶段，按 skill 的 `composes-with` 关系串联使用，而不是把所有要求塞进一条提示词。
4. 使用同目录的 `test-prompts.json` 检查触发范围；`test-results.md` 记录了构建时的盲测结果。

要接入 Codex 或其他 agent，把**所需 skill 的完整目录**复制到目标环境的 skills 目录；无需安装整套仓库。跨阶段项目可先从 `generation-mode-reference-selection` 或 `storyboard-event-budgeting` 起步。

## 效果示例

### 示例 1：把一段真人动作改成科幻短片

**用户问题**：

> 我有一段手机自拍视频，人物走路和镜头晃动要保留，但要变成废弃太空站里的巡查。

**调用顺序**：

1. `generation-mode-reference-selection`：将原视频指定为动作与运镜证据，文字／图片只补充太空站语义。
2. `preserve-change-edit-contract`：明确“环境与服装改变；人物行走节奏、镜头轨迹和画幅保留”。
3. `reference-anchor-density`：若角色身份与装备细节也必须一致，补充正侧背视图与关键近景。

**预期输出**：一份素材职责表、变更／保留清单、以及可逐项验收的生成指令，而不是一长串相互冲突的形容词。

### 示例 2：从故事想法做 15 秒产品短片

**用户问题**：

> 做一支 15 秒耳机广告：角色在下雨的夜路上戴上耳机，城市噪音慢慢消失，最后停在产品特写。

**调用顺序**：

1. `video-direction-specification`：把“安静”“沉浸”等抽象词转成动作、表演、声画效果和镜头变化。
2. `storyboard-event-budgeting`：按 15 秒时长控制事件数量，并决定哪些镜头要先出分镜。
3. `endpoint-anchored-video-synthesis`：为产品特写提供尾帧或关键帧，避免收尾跑偏。
4. `sequence-continuity-assembly`：用动作、声音与节拍完成段落连接。

**预期输出**：可生成、可验收的分镜预算和片段装配方案，而不是试图一次生成完整广告。

### 示例 3：为静态主视觉写稳定提示词

**用户问题**：

> 我想做一张武侠人物海报，但每次不是像游戏封面，就是人物和光线跑偏。

**调用顺序**：

1. `image-prompt-specification`：补齐任务真正需要的时间、主体、场景、风格字段，删去无关字段。
2. 如果已有喜欢的参考画面，再用 `reference-image-prompt-reverse-engineering` 从可见事实反推提示词。
3. 当主视觉已经锁定、需要探索变体时，改用 `constraint-aware-prompt-expansion`，先写清不得改变的条件。

## 验证状态

这 11 个 skill 各有 6 条独立盲测用例，合计 **66 条**，构建记录均为 **6/6 通过**。其中 `storyboard-event-budgeting` 与 `sequence-continuity-assembly` 使用经边界修订后的 `test-prompts.json` 作为公开版本。

验证方法、来源范围和已知边界见 [COURSE_OVERVIEW.md](./COURSE_OVERVIEW.md) 与 [verified.md](./verified.md)。

## 来源与边界

- 来源课程：《影视飓风 AI 实战课》；讲师：Tim。
- 本仓库只发布由课程方法蒸馏出的工作流、示例、测试与说明；**不包含**原始视频、音频、转写稿、课件、截图或其它课程素材。
- 模型能力、界面、价格和平台规则会变动；这些 skills 处理的是较稳定的创作决策，不应被理解为对任何平台功能或生成结果的保证。
- 在真实人物、商标、受版权保护的角色或商业交付中，请额外完成授权、隐私、品牌和人工审核。

详见 [NOTICE.md](./NOTICE.md)。

## License

仓库中原创的蒸馏文本与代码采用 [MIT License](./LICENSE)。该许可不覆盖原课程及其素材。
