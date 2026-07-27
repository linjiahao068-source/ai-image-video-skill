---
name: generation-mode-reference-selection
description: |
  当用户要决定用文生、图生或视频参考来做图片/视频，手上同时有文字、图片、动作视频或音频素材，或问“哪种参考最能控制动作、镜头、外观”时使用。先识别最难表达的变量，再把它分配给能直接承载它的输入模态与素材职责。不要用于从零细化静态图片提示词（见 2-1 试点技能），也不要用于只比较模型价格。 English signals: choose generation mode, reference modality, image vs video reference, control motion with reference.
source_book: "《影视飓风 AI 实战课》 Tim"
source_chapter: "1-1、1-2、5-1、5-2"
tags: [generation-mode, multimodal-reference, control]
related_skills:
  - slug: capability-cost-fit
    relation: composes-with
  - slug: preserve-change-edit-contract
    relation: composes-with
  - slug: reference-anchor-density
    relation: composes-with
---

# 生成模式与参考职责匹配

## R — 原文 (Reading)

> 文生图、图生图、文生视频、图生视频、视频生视频，分别对应从文字、图片或已有视频开始生成或修改。
>
> — 1-2 视频生成，00:10:23–00:10:44

> 视频可以提供图片和文字难以描述的细节，比如动作、表演、运镜，还有切镜。
>
> — 5-1 全能参考介绍，00:01:24–00:01:47

## I — 方法论骨架 (Interpretation)

不要先问“哪个功能最强”，而要先问本次最难控制的变量是什么。

静态外观、材质和氛围可由图片承担；动作、表演、运镜和切镜优先由视频承担；节拍由音频承担；没有现成素材才用文字从零发散。每份参考必须有明确职责，否则多素材只会相互干扰。

## A1 — 书中的应用 (Past Application)

### 案例 1：用已有图片继续改图

- **问题**：把猫改成狗，同时保留已有场景。
- **使用**：课程选图生图，而非从文字重做。
- **结论**：图片负责继承现有画面，文字只负责差异。
- **结果**：主体替换后场景基本保持。

### 案例 2：用实拍运动迁移到新场景

- **问题**：文字难以描述手机自拍巡查的运镜。
- **使用**：以视频参考提供运动，再重渲染为废弃医院。
- **结果**：动作/镜头与场景语义由不同输入承担。

## A2 — 触发场景 (Future Trigger) ★

### 适用情境

1. 用户手上同时有文字、图像、视频或音频，不知如何组合。
2. 用户说“动作/运镜很难写清”“想保持人物外观但换背景”。
3. 用户在文生、图生、视频参考之间选择工作流。

### 语言信号

- “我该用图生还是视频参考？”
- “动作很难用 prompt 描述。” / “Which reference modality should control motion?”
- “这些参考图和视频分别该干什么？”

### 与相邻 skill 的区分

- `capability-cost-fit` 决定选什么能力档位；本技能决定输入模式与素材职责。
- `preserve-change-edit-contract` 在模式选定后，明确要改与要保留什么。

## E — 可执行步骤 (Execution)

1. **列出目标中最难表达的变量**：外观、动作、镜头、场景、节拍或叙事顺序。
   - 完成标准：至少标出一个不能交给模型自由猜测的变量。
2. **为每个变量选最直接的输入模态**：图像承载静态外观，视频承载运动/镜头，音频承载节拍，文字补充缺失语义。
   - 完成标准：每份素材都有唯一控制职责；没有“只是多放一张”的素材。
3. **选择生成模式并做小样验证**：用最小片段检查该输入是否真的控制了目标变量。
   - 完成标准：能指出变量是否被正确继承；若失败，换模态或补充锚点而非盲目加形容词。

## B — 边界 (Boundary) ★

- 没有任何参考素材、只需把静态想法写成图像提示词时，使用 2-1 的 `image-prompt-specification`。
- 需要比较成本、速度和模型专长时，使用 `capability-cost-fit`。
- 参考中含版权、肖像、商标或敏感个人数据时，先处理授权与可用范围。
- 多个素材没有明确职责会造成控制冲突；不要把“多参考”误当成“更准确”。

## 相关 skills

- composes-with: `capability-cost-fit`、`preserve-change-edit-contract`、`reference-anchor-density`

## 审计信息

- **验证通过**：V1 ✓ / V2 ✓ / V3 ✓
- **测试通过率**：待阶段 4 盲测
- **蒸馏时间**：2026-07-27
