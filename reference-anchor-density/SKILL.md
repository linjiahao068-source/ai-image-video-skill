---
name: reference-anchor-density
description: |
  当用户需要角色、产品或复杂场景跨镜头保持身份、细节、角度或运动一致，或反馈“单张参考会崩”“人物每次长得不一样”时使用。按保真风险决定需要多少多视图、端帧和细节锚点，再让生成补未知区。不要在容错高的灵感探索中无谓堆砌参考，也不要把它当作局部编辑的变更清单。 English signals: character consistency, multi-view reference, reference density, keep identity across shots, single image breaks details.
source_book: "《影视飓风 AI 实战课》 Tim"
source_chapter: "1-1、1-2、2-2、4-1、4-3"
tags: [reference, consistency, fidelity]
related_skills:
  - slug: generation-mode-reference-selection
    relation: depends-on
  - slug: endpoint-anchored-video-synthesis
    relation: composes-with
  - slug: preserve-change-edit-contract
    relation: composes-with
---

# 参考锚点密度与身份稳定

## R — 原文 (Reading)

> 人物或细节很多时，只有一张图让 AI 想象后续画面，容易出现主体失真和细节崩坏。
>
> — 4-3 AI 子弹时间，00:01:39–00:01:57

> 先确定好机器人的细节，再生成；让 AI 知道机器人到底长什么样，就不会乱生成。
>
> — 2-2 视频提示词，00:15:24–00:16:14

## I — 方法论骨架 (Interpretation)

一致性取决于模型需要猜多少未知信息。单一、容错高的主体可以用少锚点探索；人物、复杂产品、跨镜头或高保真运动则要增加多视图、细节、首尾帧和真实角度锚点。

先确定身份不变量，再生成场景、动作和镜头。锚点不是越多越好，而是覆盖最可能漂移的角度、时间位置和细节。

## A1 — 书中的应用 (Past Application)

### 案例 1：机器人多视图一致性

- **问题**：文生视频中机器人每次外观不同。
- **使用**：先做正侧背等细节参考，再显式引用。
- **结果**：AI 有更明确的身份资料可继承。

### 案例 2：人物子弹时间

- **问题**：单图不足以支撑复杂人物和多角度细节。
- **使用**：补充真实端帧和多角度采集。
- **结果**：降低中间过程对未知细节的自由想象。

## A2 — 触发场景 (Future Trigger) ★

### 适用情境

1. 角色、产品或服装需要跨镜头一致。
2. 要做环绕、子弹时间、首尾帧或多角度展示。
3. 用户说“人物变脸”“细节崩”“单张图不够稳”。

### 语言信号

- “怎么保持角色一致？”
- “我需要准备几张参考图？”
- “How many views do I need for fidelity?”

### 与相邻 skill 的区分

- `generation-mode-reference-selection` 先决定哪种模态负责什么变量；本技能决定参考的数量和覆盖位置。
- `preserve-change-edit-contract` 定义哪些条件不能变；本技能为这些条件提供足够锚点。

## E — 可执行步骤 (Execution)

1. **列出高风险不变量**：身份、脸部、材质、文字、机位、动作终点或关键细节。
   - 完成标准：每项都能说明漂移后为何不可接受。
2. **按风险补锚点**：外观补多视图，运动补首尾/关键帧，复杂细节补近景或真实端点。
   - 完成标准：每个高风险项至少有一份直接证据；关键运动有时间锚点。
3. **先用小片段做一致性验收**：比较各角度/帧的身份与细节，再扩大生成。
   - 完成标准：若仍漂移，补缺失方向或端点，而非只增加模糊描述。

## B — 边界 (Boundary) ★

- 纯灵感探索、抽象风格或无需身份一致的任务，少锚点反而保留更多创意空间。
- 锚点质量差、遮挡严重或彼此矛盾时，增加数量不会提高保真。
- 真实人物及受保护产品的多视图采集要先确认授权。

## 相关 skills

- depends-on: `generation-mode-reference-selection`
- composes-with: `endpoint-anchored-video-synthesis`、`preserve-change-edit-contract`

## 审计信息

- **验证通过**：V1 ✓ / V2 ✓ / V3 ✓
- **测试通过率**：待阶段 4 盲测
- **蒸馏时间**：2026-07-27
