---
name: capability-cost-fit
description: |
  当用户要为图片/视频生成选择模型、清晰度、速度或预算，比较“轻量模型够不够”“何时升级 Pro/高质量”，或希望先低成本发散再精修时使用。先按交付物的主要失败风险匹配能力，再在质量、速度、成本之间选最小足够档位。不要用于选择图片/视频参考模态，或把预算问题简化为只选最贵模型。 English signals: choose model, model capability, quality speed cost tradeoff, cheap exploration then refine.
source_book: "《影视飓风 AI 实战课》 Tim"
source_chapter: "1-1、3-1、5-1"
tags: [model-selection, cost, quality]
related_skills:
  - slug: generation-mode-reference-selection
    relation: composes-with
  - slug: storyboard-event-budgeting
    relation: composes-with
---

# 能力—成本适配

## R — 原文 (Reading)

> 版本越新、越 Pro 的模型通常更好，但也意味着消耗更多积分、生成速度更慢；简单需求不必默认选最高档。
>
> — 1-1 图片生成，00:10:29–00:10:54

> 选择合适的 AI 模型很重要，可以按不同场景切换模型。
>
> — 3-1 工具介绍，00:05:58–00:06:16

## I — 方法论骨架 (Interpretation)

模型选择是交付风险管理，不是品牌排名。先定义本次交付最不能失败的能力：排版、人物一致性、动作、光影、局部编辑或分辨率。再选择满足该能力的最低成本档位。

探索阶段容许低成本、多候选；确定方向后再对少数方案提高质量。这样避免把昂贵模型浪费在简单任务，也避免用不擅长的模型反复试错。

## A1 — 书中的应用 (Past Application)

### 案例 1：简单猫图选较轻模型

- **问题**：基础生成需求对高规格能力没有明显收益。
- **使用**：课程比较不同版本后，选择更快、更省的档位。
- **结果**：保留足够质量，降低成本与等待。

### 案例 2：包装与平面任务换专长模型

- **问题**：不同交付物对模型能力的要求不同。
- **使用**：课程说明平面设计、包装、封面应选择相应专长模型。
- **结果**：模型选择服务于交付物，而非固定默认值。

## A2 — 触发场景 (Future Trigger) ★

### 适用情境

1. 用户在多个模型、画质或时长档位之间犹豫。
2. 用户预算有限，但需要在探索和最终交付间分配成本。
3. 用户反馈“模型很贵却没有改善关键问题”。

### 语言信号

- “这个任务需要上高阶模型吗？”
- “怎么兼顾质量、速度和费用？”
- “Which model tier is enough for this deliverable?”

### 与相邻 skill 的区分

- `generation-mode-reference-selection` 先决定从什么输入生成；本技能再决定使用何种能力档位。
- `storyboard-event-budgeting` 决定镜头规模和分解；本技能决定每个镜头的资源投入。

## E — 可执行步骤 (Execution)

1. **定义交付物和主要失败风险**：只选 1–2 个核心指标，如文字排版、动作、角色一致性或局部修改。
   - 完成标准：能说明“换高档模型必须改善什么”。
2. **建立两档预算**：探索档用于多候选，交付档用于已验证方向的高保真输出。
   - 完成标准：每档有生成次数/费用或时间上限。
3. **用同一规格比较后升级**：保持提示词、参考和画幅不变，只换模型/档位。
   - 完成标准：只有可见改善核心指标时才升级；否则回到更低成本档。

## B — 边界 (Boundary) ★

- 模型升级不能修复模糊需求、错误输入模态或缺失参考锚点。
- 平台价格、版本和能力会变化；课程中的模型名不是长期推荐。
- 单次较贵输出不等于适合最终交付，仍要按约束验收。

## 相关 skills

- composes-with: `generation-mode-reference-selection`、`storyboard-event-budgeting`

## 审计信息

- **验证通过**：V1 ✓ / V2 ✓ / V3 ✓
- **测试通过率**：待阶段 4 盲测
- **蒸馏时间**：2026-07-27
