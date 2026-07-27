---
name: storyboard-event-budgeting
description: |
  当用户要把广告、故事或产品创意做成完整短片，纠结该用文字分镜还是图像分镜、镜头数和时长怎么定，或发现“十秒里塞不下这些事”时使用。先从脚本到分镜分层，再按事件负载和保真风险分配镜头、时长与生成方式。不要用于单一镜头的运镜措辞或已有明确首尾帧的过程补全。 English signals: storyboard, shot list, how many shots, duration budget, text storyboard vs image storyboard.
source_book: "《影视飓风 AI 实战课》 Tim"
source_chapter: "1-2、2-2、5-4、5-5"
tags: [storyboard, narrative, duration, planning]
related_skills:
  - slug: video-direction-specification
    relation: depends-on
  - slug: endpoint-anchored-video-synthesis
    relation: composes-with
  - slug: sequence-continuity-assembly
    relation: composes-with
---

# 分镜保真度与事件预算

## R — 原文 (Reading)

> 完整片子先有文字脚本，再梳理成文字分镜；条件允许时配更直观的分镜图。
>
> — 5-4 分镜直出，00:00:35–00:00:49

> 镜头与事件较多时，要先看时长是否足够承载；不够就不能硬塞进短片段。
>
> — 2-2 视频提示词，00:13:40–00:13:47

## I — 方法论骨架 (Interpretation)

完整视频不能从一句故事直接跳到成片。脚本负责因果与目标，文字分镜负责镜头顺序、时长和叙事方式，图像分镜负责高风险画面的视觉锚点。

先估算每个事件需要的时间和保真度：少量紧密事件可在一次生成中包含切镜；复杂、多镜头或高一致性任务应拆段生成后组接。

## A1 — 书中的应用 (Past Application)

### 案例 1：乌鸦喝水短片

- **问题**：要做多镜头、无对白故事。
- **使用**：先写文字分镜，再决定每段画面与后续延展。
- **结果**：叙事因果和镜头职责可被逐段检查。

### 案例 2：机器人短片的镜内分镜

- **问题**：少量镜头节拍可否一次生成。
- **使用**：将切点、景别和动作顺序放进提示词。
- **结果**：在事件负载可控时减少生成与后期次数。

## A2 — 触发场景 (Future Trigger) ★

### 适用情境

1. 用户要把创意、广告或故事变成多镜头短片。
2. 用户不确定镜头数、总时长、分镜形式或生成顺序。
3. 视频叙事混乱、事件过多或高风险镜头总跑偏。

### 语言信号

- “帮我做分镜。”
- “十秒能讲完这段故事吗？”
- “Should I use text storyboard or image storyboard?”

### 与相邻 skill 的区分

- `video-direction-specification` 为单镜头写动态指令；本技能安排多镜头的整体预算。
- `endpoint-anchored-video-synthesis` 解决段内端点；本技能决定是否拆段以及段间因果。

## E — 可执行步骤 (Execution)

1. **写出故事事件链**：每个事件以“发生什么、观众需知道什么、预计几秒”表示。
   - 完成标准：事件按因果顺序排列，未把镜头技巧当作事件。
2. **选择分镜保真度**：文字分镜用于顺序和节奏，图像分镜用于主体/构图等高风险画面。
   - 完成标准：每个高风险镜头都有可验证的视觉锚点或明确理由不需要。
3. **按事件预算分组生成**：负载低且衔接紧的镜头可合并；超时或需细验的镜头拆开并指定衔接点。
   - 完成标准：每段时长不超过实际承载能力，生成计划包含后续组接顺序。

## B — 边界 (Boundary) ★

- 只有一个镜头或只需改善运镜时，直接使用 `video-direction-specification`。
- 不要把所有镜头都做成高保真图像分镜；这会增加不必要成本。
- 分镜不能代替真实生成验证；课程也将实际生成视为工作流中的必经检查。

## 相关 skills

- depends-on: `video-direction-specification`
- composes-with: `endpoint-anchored-video-synthesis`、`sequence-continuity-assembly`

## 审计信息

- **验证通过**：V1 ✓ / V2 ✓ / V3 ✓
- **测试通过率**：待阶段 4 盲测
- **蒸馏时间**：2026-07-27
