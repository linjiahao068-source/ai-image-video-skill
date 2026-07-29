# AI Image & Video Skill

一套可直接调用的 AI 影像创作技能包：包含 **11 个原子 Skill＋1 个总控工作流 Skill**。11 个原子 Skill 来自《影视飓风 AI 实战课》的方法蒸馏；`build-image-fast` 在其上增加从抽象 Idea 到最终图片的阶段确认、生成、QA 与交付状态机。

## 两种使用方式

### 完整静态图片项目

使用 [`build-image-fast`](./build-image-fast/SKILL.md)。它按八个必须确认的阶段推进：

`需求与边界 → 创意方向 → 故事/信息结构 → 视觉规格与锚点 → 生成路线与提示词 → 候选生成 → QA/返修 → 正式交付`

默认调用：

```text
Use $build-image-fast to turn my idea into a confirmed AI Image Build Pack and a validated final image.
```

V1 默认一次生成 1 张候选；提示词和路线未确认前不出图；QA 低于 85 分或存在硬失败时不交付；最终文件未经确认时不标记完成。Seedance 2.0 只提供可选动画化交接，不在本工作流中生成视频。

### 单点任务

直接调用原子 Skill，不启动八阶段工作流：

#### 图片提示词与静态画面

- [`image-prompt-specification`](./image-prompt-specification/SKILL.md)：把模糊画面意图变成按需裁剪的视觉规格。
- [`reference-image-prompt-reverse-engineering`](./reference-image-prompt-reverse-engineering/SKILL.md)：从参考图的可见证据反推可验证提示词。
- [`constraint-aware-prompt-expansion`](./constraint-aware-prompt-expansion/SKILL.md)：在严格控制和创意探索之间选择扩写方式。

#### 输入、编辑与一致性

- [`generation-mode-reference-selection`](./generation-mode-reference-selection/SKILL.md)：按最难控制的变量分配输入模态和素材职责。
- [`capability-cost-fit`](./capability-cost-fit/SKILL.md)：按失败风险选择能力、速度和成本档位。
- [`preserve-change-edit-contract`](./preserve-change-edit-contract/SKILL.md)：把局部编辑写成变更项与保留项合同。
- [`reference-anchor-density`](./reference-anchor-density/SKILL.md)：按保真风险配置多视图、端帧和细节锚点。

#### 视频叙事、生成与装配

- [`video-direction-specification`](./video-direction-specification/SKILL.md)：把情绪和故事写成可观察的动作、镜头与节奏。
- [`storyboard-event-budgeting`](./storyboard-event-budgeting/SKILL.md)：用时长和事件预算决定分镜颗粒度。
- [`endpoint-anchored-video-synthesis`](./endpoint-anchored-video-synthesis/SKILL.md)：用首尾帧或关键帧锁定必须命中的状态。
- [`sequence-continuity-assembly`](./sequence-continuity-assembly/SKILL.md)：修复多片段之间的动作、空间、接缝和节奏。

完整索引与组合关系见 [INDEX.md](./INDEX.md)。

## 安装

复制需要的完整 Skill 目录到 Codex skills 目录。使用 `build-image-fast` 时，同时安装它调用的图片原子 Skill。仓库不要求安装全部 11 个原子 Skill 才能使用某一个单点 Skill。

## 验证范围

- 11 个原子 Skill 的原有独立测试保持 **66 条**，统计不与总控工作流混合。
- `build-image-fast` 另有阶段合同测试、股票四格情境演练和真实生成验证记录；三类结果分开报告。

详见 [verified.md](./verified.md) 与 [`build-image-fast/test-results.md`](./build-image-fast/test-results.md)。

## 来源、边界与许可

仓库只发布课程方法蒸馏出的工作流、示例、测试和说明，不包含原始课程视频、音频、转写稿、课件或截图。真实人物、商标、受保护角色和商业交付仍需确认授权、隐私、品牌规范与人工审核。

原创蒸馏文本与代码采用 [MIT License](./LICENSE)；该许可不覆盖原课程及其素材。
