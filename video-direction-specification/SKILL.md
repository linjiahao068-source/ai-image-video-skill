---
name: video-direction-specification
description: |
  当用户要把一个视频画面、情绪或故事念头写成可生成的动态提示词，或说“不要像静帧”“想让镜头更孤独/更紧张”“如何描述动作、运镜和切镜”时使用。按主体、可见动作、效果、节奏及镜头把抽象意图转为动态规格。不要用于静态图片的四维提示词，或决定素材输入模式。 English signals: video prompt, camera movement prompt, make it feel lonely, avoid static shot, describe motion and pacing.
source_book: "《影视飓风 AI 实战课》 Tim"
source_chapter: "2-2、5-6"
tags: [video-prompt, direction, camera, pacing]
related_skills:
  - slug: storyboard-event-budgeting
    relation: composes-with
  - slug: endpoint-anchored-video-synthesis
    relation: composes-with
  - slug: sequence-continuity-assembly
    relation: composes-with
---

# 动态画面导演式规格

## R — 原文 (Reading)

> 视频提示词关键是：主体、动作、效果、节奏；节奏通过切镜头把控视频的脉搏。
>
> — 2-2 视频提示词，00:16:25–00:16:45

> “开心”不能只靠一个词，要让角色有笑容、动作或台词等看得见的表达。
>
> — 2-2 视频提示词，00:02:55–00:03:05

## I — 方法论骨架 (Interpretation)

视频提示词必须描述“变化如何发生”。先指定观众看谁，再把情绪变成可见行为；随后用镜头、焦点、环境效果和切点组织时间。仅写“孤独、电影感、不要动”会让模型缺少可执行的导演指令。

它不是穷举镜头术语，而是让每个动态参数服务于叙事意图。

## A1 — 书中的应用 (Past Application)

### 案例 1：机器人在废墟中的孤独感

- **问题**：静止机器人容易生成像图片的画面。
- **使用**：课程用推进、拉远、摇移等镜头为孤独和信息揭示服务。
- **结果**：同一主体通过镜头变化获得动态叙事。

### 案例 2：把“开心”变成表演

- **问题**：抽象情绪无法直接验收。
- **使用**：课程补充笑容、动作或台词等可观察信号。
- **结果**：情绪成为能被生成与核对的行为。

## A2 — 触发场景 (Future Trigger) ★

### 适用情境

1. 用户只有氛围词或剧情概念，需要形成视频 prompt。
2. 用户需要指定动作、镜头、焦点、特效、切点或时长。
3. 生成视频看起来像静帧、情绪不明显或叙事不清。

### 语言信号

- “帮我写视频提示词。”
- “怎么让它看起来更孤独/紧张？”
- “What camera movement should express this scene?”

### 与相邻 skill 的区分

- `storyboard-event-budgeting` 处理多个镜头和总时长；本技能处理单个动态画面的导演规格。
- `endpoint-anchored-video-synthesis` 在起止状态已知时控制过程；本技能可用于没有端帧的动态意图表达。

## E — 可执行步骤 (Execution)

1. **定义主体与可观察动作**：把情绪词转成姿态、视线、台词、速度或互动。
   - 完成标准：不再只剩抽象形容词。
2. **指定一个叙事目的明确的镜头与效果**：如推进增强临场感、拉远呈现孤立、摇移揭示信息。
   - 完成标准：每个镜头/效果都能回答“它改变观众看到什么”。
3. **给出节奏和验收点**：写明持续时间、切点/景别或焦点变化。
   - 完成标准：能检查动作、镜头、效果和节奏是否各有至少一个明确条件。

## B — 边界 (Boundary) ★

- 若任务是复杂故事或多镜头序列，先用 `storyboard-event-budgeting` 分解。
- 若运镜本身无法可靠文字化，优先给视频运动参考并使用 `generation-mode-reference-selection`。
- 不要为了“电影感”堆叠互相冲突的镜头、天气和效果。

## 相关 skills

- composes-with: `storyboard-event-budgeting`、`endpoint-anchored-video-synthesis`、`sequence-continuity-assembly`

## 审计信息

- **验证通过**：V1 ✓ / V2 ✓ / V3 ✓
- **测试通过率**：待阶段 4 盲测
- **蒸馏时间**：2026-07-27
