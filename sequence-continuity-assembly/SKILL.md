---
name: sequence-continuity-assembly
description: |
  当用户要拼接多段 AI 视频、做场景转场、循环、换装/产品节奏片，或反馈“转场卡顿、动作断了、音乐和画面不合拍”时使用。先选动作锚点、空镜接缝或节拍时间轴，再检查重复帧并统一装配。不要把它用于单个镜头的提示词或从零故事分镜。 English signals: transition, match cut, action continuity, loop, duplicate frames, cut to beat, sequence pacing.
source_book: "《影视飓风 AI 实战课》 Tim"
source_chapter: "2-2、4-4、4-5、5-6"
tags: [editing, transition, rhythm, continuity]
related_skills:
  - slug: video-direction-specification
    relation: composes-with
  - slug: endpoint-anchored-video-synthesis
    relation: composes-with
  - slug: storyboard-event-budgeting
    relation: depends-on
---

# 序列连续性与节拍装配

## R — 原文 (Reading)

> 上一个镜头是动的，下一个镜头最好也是动的，而且两个动作最好能够衔接上。
>
> — 4-4 AI 视频转场，00:01:27–00:01:39

> 音频除了背景音乐，还有节奏；可以根据音乐节点进行自动剪辑。
>
> — 5-6 节奏剪辑，00:00:09–00:00:44

## I — 方法论骨架 (Interpretation)

多段视频的连贯性来自可诊断的锚点，而不是炫目的特效。角色动作能衔接时用动接动；动作难接时把场景变化藏进空镜或低信息区；出现卡顿时先查重复端帧；需要节奏时用音频节拍安排镜头或素材变化。

将这些选择放在同一装配流程中，能同时处理物理连续、时间节奏和循环闭合。

## A1 — 书中的应用 (Past Application)

### 案例 1：角色穿越转场

- **问题**：两个场景中的动作需看起来连续。
- **使用**：课程以动接动衔接，并删除接缝重复帧。
- **结果**：转场不靠硬切掩盖动作断裂。

### 案例 2：女装节奏展示

- **问题**：多个服装版本需要按音乐有序展示。
- **使用**：用音频节拍控制姿势、换装和素材顺序。
- **结果**：音乐成为画面装配的时间轴，而非事后背景声。

## A2 — 触发场景 (Future Trigger) ★

### 适用情境

1. 用户要拼接多段视频、设计转场或循环片段。
2. 用户说动作断了、转场卡住、有重复帧或节奏不对。
3. 要按音乐节点展示多个产品、服装或画面版本。

### 语言信号

- “怎么让两个镜头接得自然？”
- “转场为什么会卡一下？”
- “How do I cut this sequence to the beat?”

### 与相邻 skill 的区分

- `storyboard-event-budgeting` 先决定镜头序列和时长；本技能解决实际片段如何接合。
- `endpoint-anchored-video-synthesis` 生成段内起止；本技能检查段与段之间的连续性。

## E — 可执行步骤 (Execution)

1. **为每个接缝选主锚点**：优先动作连续；无法连续时选空镜/低信息区域；节奏片另标音频节拍点。
   - 完成标准：每个接缝都有一种明确的衔接策略。
2. **按锚点排列片段并检查端帧**：比较动作方向、姿态、机位与重复帧。
   - 完成标准：重复端帧已删除或被节拍/空镜掩盖；循环首尾状态匹配。
3. **最后统一处理音乐与节奏**：先锁画面大结构，再以清晰节拍的音频安排切换和素材顺序。
   - 完成标准：画面变化能对齐设定节拍，且不存在各片段各自配乐的冲突。

## B — 边界 (Boundary) ★

- 端点动作或主体身份本身不连续时，先重做端点/锚点，不能只靠转场特效掩盖。
- 没有多段素材或节奏目标的单一镜头，不需要调用本技能。
- 不要强行卡每一拍；叙事重点和动作可读性优先于机械对拍。

## 相关 skills

- depends-on: `storyboard-event-budgeting`
- composes-with: `video-direction-specification`、`endpoint-anchored-video-synthesis`

## 审计信息

- **验证通过**：V1 ✓ / V2 ✓ / V3 ✓
- **测试通过率**：待阶段 4 盲测
- **蒸馏时间**：2026-07-27
