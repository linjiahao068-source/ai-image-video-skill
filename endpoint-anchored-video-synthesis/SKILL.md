---
name: endpoint-anchored-video-synthesis
description: |
  当用户明确知道视频开头、结尾、循环落点或关键状态，想让 AI 补中间过程、延长片段，或抱怨“结尾没停在我要的位置”时使用。先决定哪些时间端点必须锁定，再以首帧/尾帧约束生成、延展或闭环。不要在只有模糊氛围且允许自由结局时过度使用。 English signals: start/end frame, keyframe video, loop, extend video, must end at, interpolate between frames.
source_book: "《影视飓风 AI 实战课》 Tim"
source_chapter: "1-2、4-1、4-5、5-5"
tags: [video, keyframe, endpoint, temporal-control]
related_skills:
  - slug: reference-anchor-density
    relation: composes-with
  - slug: storyboard-event-budgeting
    relation: composes-with
  - slug: sequence-continuity-assembly
    relation: composes-with
---

# 端点锚定的视频合成

## R — 原文 (Reading)

> 只给首帧时，后续由 AI 自由发挥；若结尾必须停在某个画面，就把尾帧也确定下来。
>
> — 1-2 视频生成，00:06:41–00:06:55

> 在确定开头和结尾两个画面的前提下，让 AI 通过文字补全中间过程，能让视频更可控。
>
> — 4-1 机械臂运镜，00:00:52–00:01:19

## I — 方法论骨架 (Interpretation)

将短视频视为一段受时间端点约束的过程。起点足够时只锁首帧，让后续探索；终点、闭环或关键状态不能错时，补尾帧或关键帧。中间过程由生成模型补全，但验收的核心是端点是否命中。

当单段时长不足时，按因果关系向前或向后延长，再拼接为完整叙事。

## A1 — 书中的应用 (Past Application)

### 案例 1：猫从沙发到吃猫粮

- **问题**：结尾状态必须落在“吃猫粮”。
- **使用**：课程同时提供首帧和尾帧。
- **结果**：生成目标从“随便动起来”变为命中明确终点。

### 案例 2：动态壁纸循环

- **问题**：循环播放不能有明显断点。
- **使用**：首帧与尾帧保持相同。
- **结果**：时间序列形成闭环。

## A2 — 触发场景 (Future Trigger) ★

### 适用情境

1. 视频必须从/停在确定画面、姿态或产品状态。
2. 要做循环、变形、首尾帧运镜或前后延展。
3. 用户说“结尾跑偏”“要无缝循环”“补中间动作”。

### 语言信号

- “必须从这张图到那张图。”
- “帮我把中间过程补出来。”
- “How do I make this loop seamlessly?”

### 与相邻 skill 的区分

- `reference-anchor-density` 决定端点需要多丰富的参考；本技能决定如何用端点约束时间过程。
- `storyboard-event-budgeting` 决定故事需拆几段；本技能控制每段的起止状态。

## E — 可执行步骤 (Execution)

1. **标出必须命中的时间状态**：起点、终点、循环点或中段关键帧。
   - 完成标准：明确哪些状态可自由、哪些不可错。
2. **选择最小足够的端点约束**：只锁首帧、锁首尾帧，或增加关键帧；确保顺序和画幅正确。
   - 完成标准：每个硬约束都有对应时间锚点。
3. **生成后先验端点，再验过程**：端点不命中即判失败；时长不够则按因果向前/后延展或拆段。
   - 完成标准：端点、方向和闭环都通过后才进入剪辑。

## B — 边界 (Boundary) ★

- 端点素材彼此动作、机位或外观不连续时，不能期待模型自动解决全部衔接；应先重做锚点或使用 `sequence-continuity-assembly`。
- 只求模糊氛围或随机探索时，过多端点会压缩创意空间。
- 端点含有受限人物、商标或版权素材时，先确认许可。

## 相关 skills

- composes-with: `reference-anchor-density`、`storyboard-event-budgeting`、`sequence-continuity-assembly`

## 审计信息

- **验证通过**：V1 ✓ / V2 ✓ / V3 ✓
- **测试通过率**：待阶段 4 盲测
- **蒸馏时间**：2026-07-27
