---
name: preserve-change-edit-contract
description: |
  当用户要在已有图片或视频上换主体、背景、服装、颜色、光影或局部细节，同时要求其他元素不变，或反馈“改了背景却把人物/动作也改坏了”时使用。把需求分为变更项与保留项，指定高风险不变量并按其验收。不要用于从零发散新画面，或只分析参考图。 English signals: edit but keep, preserve composition, replace background only, change one thing keep everything else.
source_book: "《影视飓风 AI 实战课》 Tim"
source_chapter: "1-1、1-2、5-3"
tags: [editing, constraints, preservation]
related_skills:
  - slug: generation-mode-reference-selection
    relation: depends-on
  - slug: reference-anchor-density
    relation: composes-with
---

# 保留—变更编辑契约

## R — 原文 (Reading)

> 把视频中的背景换成室外雪景、天空飘雪，保留视频中的构图和动作。
>
> — 5-3 AI 换背景，00:01:03–00:01:10

> 让狗睡在大街上，同时保持姿势不变。
>
> — 1-1 图片生成，00:08:23–00:08:34

## I — 方法论骨架 (Interpretation)

局部编辑不是一句“换成 X”，而是一份变更契约：什么必须变、什么必须保留、哪个保留项风险最高。把两类条件并列写出，模型偏移时就能判断是变更失败还是继承失败。

若保留项对结果至关重要，先用现有图/视频作条件输入，再用文字说明差异；必要时增加视角或端帧锚点。

## A1 — 书中的应用 (Past Application)

### 案例 1：猫改成狗

- **问题**：替换主体而不丢掉现有环境。
- **使用**：把原图作为输入，提示词只声明“猫变狗”。
- **结果**：主体替换，场景基本继承。

### 案例 2：视频换雪景背景

- **问题**：替换背景但保持构图和动作。
- **使用**：明确雪景为变更项，构图/动作为保留项。
- **结果**：编辑范围可被检查而不是只看整体好不好看。

## A2 — 触发场景 (Future Trigger) ★

### 适用情境

1. 用户说“只改这一个，其他都别动”。
2. 要换背景、服装、颜色或光影，但保持人物、姿势、镜头或版式。
3. 已有编辑结果出现连带漂移。

### 语言信号

- “只把背景换掉，人物动作别变。”
- “Keep the composition, change only the product color.”
- “为什么改衣服把脸也改了？”

### 与相邻 skill 的区分

- 先用 `generation-mode-reference-selection` 选定使用图/视频条件输入。
- `reference-anchor-density` 解决保留项需要多少视觉锚点；本技能先定义哪些项必须保留。

## E — 可执行步骤 (Execution)

1. **写出两栏契约**：变更项、保留项；将保留项标为高/中/低风险。
   - 完成标准：每项只属于一栏，且高风险项不超过 3–5 个。
2. **绑定可继承的原始素材**：尽量以已有图/视频为条件输入，并保持关键画幅或时间结构兼容。
   - 完成标准：能指出每个保留项由哪份输入或文字约束支持。
3. **按契约验收并最小化返工**：先核对高风险保留项，再核对变更项。
   - 完成标准：失败时只补失效条目，不把已通过的条件重新随机化。

## B — 边界 (Boundary) ★

- 若用户接受大幅重构或仅求灵感，不要强行套用严格保留契约。
- 原始素材本身质量不足、遮挡严重或视角缺失时，不能承诺保留所有细节。
- 商标、肖像、版权元素的替换或保留需先确认权利与用途。

## 相关 skills

- depends-on: `generation-mode-reference-selection`
- composes-with: `reference-anchor-density`

## 审计信息

- **验证通过**：V1 ✓ / V2 ✓ / V3 ✓
- **测试通过率**：待阶段 4 盲测
- **蒸馏时间**：2026-07-27
