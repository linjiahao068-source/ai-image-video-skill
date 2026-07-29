---
name: build-image-fast
description: "将抽象创意通过八个必须逐阶段确认的关口，转化为已验证的最终静态图片和可复现的 AI Image Build Pack。用于从 0 到 1 完成主视觉、海报、漫画、信息图、产品图等完整图片项目，尤其适合需要创意发散、故事或信息结构、参考锚点、提示词、实际生成、QA 返修和正式交付的任务。不要用于只优化一条提示词、只反推参考图、只比较模型成本、只做局部图片编辑或直接生成视频；这些单点任务应交给对应原子 Skill。English signals: build an image from an idea, end-to-end image workflow, confirmed image build pack, generate and validate a final image."
---

# Build Image Fast

把本 Skill 作为静态图片项目的总控工作流。保留并组合原子 Skill，不复制或替代其方法。V1 始终启用阶段确认，不允许静默越级。

## 不可破坏的合同

1. 严格按 1→8 阶段推进。每一阶段都先把状态设为 `待确认`，只有用户明确确认当前版本后才进入下一阶段。
2. 只使用以下状态：`未开始 / 进行中 / 待确认 / 已通过 / 需返工 / 受阻 / 已完成`。
3. 用户提出修改时，留在当前阶段并递增产物版本。不要把修改意见解释为确认。
4. 新条件影响上游时，返回最早受影响阶段，并把受影响的下游产物标记为 `待重新验证`。
5. 阶段 5 的提示词和生成路线未确认前，不得调用图片生成工具。
6. 阶段 6 只在用户明确选择候选后进入 QA。阶段 7 未达到 85 分或存在硬失败时，不得声称可交付。
7. 阶段 8 的最终文件未经用户确认时，不得把项目状态改成 `已完成`。
8. 默认使用用户当前语言；默认先生成 1 张候选；默认非覆盖保存。

每轮回复必须以 [阶段门与确认协议](references/stage-gates-and-confirmation.md) 的状态栏开头。说明当前位置、本阶段解决的问题、产物版本、待确认项和确认后的下一阶段。

## 原子 Skill 路由

- 素材职责：`generation-mode-reference-selection`
- 创意发散：`constraint-aware-prompt-expansion`
- 图片规格：`image-prompt-specification`
- 参考图证据反推：`reference-image-prompt-reverse-engineering`
- 锚点密度：`reference-anchor-density`
- 成本与能力档位：`capability-cost-fit`
- 单变量返修：`preserve-change-edit-contract`

单点请求不启动八阶段总控，交给对应原子 Skill。完整 5–30 秒视频项目交给 `build-ai-video-fast`；Seedance 2.0 只负责静态图之后的交接。

## 项目状态

持续维护 `project_id`、当前阶段与状态、当前产物版本、已确认版本、锁定项、失效下游、阻断项、选中候选、QA 分数和最终文件。

草稿从 `v0.1` 开始；同阶段每次实质修改递增小版本。确认绑定具体版本和锁定项。返工后的新版本不能继承旧确认。

## 八阶段流程

### 1. 需求与边界确认

最多集中补问一次、最多五项；不阻塞的缺口列为显式假设。收集用途、平台、受众、预期情绪或行动、比例、语言、精确文字、格式、角色或商品、参考素材、质量和迭代限制、授权与发布范围。用 `generation-mode-reference-selection` 给每份素材指定唯一主要职责。

交付 `Creative Brief`、假设清单、风险和权利提醒。读取 [Creative Brief](references/idea-to-creative-brief.md) 与 [权利门](references/rights-and-release-gates.md)。

确认门：用途、规格、必须条件、素材职责和权利边界均被确认。

### 2. 创意方向确认

用 `constraint-aware-prompt-expansion` 生成三个明显不同且可比较的方向。每个方向包含一句话核心表达、情绪曲线、视觉隐喻、画面结构和主要生成风险。给出有理由的推荐，但不得替用户选择。

确认门：用户选择、组合或修改方向。

### 3. 故事或信息结构确认

先验证内容，再处理视觉：单图定义焦点与观看顺序；海报定义标题、主体、卖点、CTA 和留白；信息图定义层级、关系、数据和标注；漫画定义逐格事件、对白、节奏和反转；产品图定义产品、卖点、使用情境和品牌信息。

漫画读取 [漫画与序列图片](references/comics-and-sequential-images.md)。

确认门：事件顺序、精确文案、笑点或卖点、CTA 被确认。

### 4. 视觉规格与锚点确认

用 `image-prompt-specification` 定义时间、主体、场景、风格、构图、阅读方向、颜色、文字预算和安全区。

有参考图时先查看图片，再用 `reference-image-prompt-reverse-engineering` 区分可见证据与推断；用 `reference-anchor-density` 决定多视图、细节图和身份锚点。每张参考图只指定一个主要职责。

确认门：视觉方向、版式、角色或产品不变量、颜色、文字预算和参考职责被确认。受保护角色或品牌按 [权利门](references/rights-and-release-gates.md) 分流。

### 5. 生成路线与提示词确认

按主要失败风险选路线，并用 `capability-cost-fit` 分开草稿档与精修档：

- 快速路线：先看方向，允许轻微漂移，一次生成完整图片。
- 稳定路线：文字、身份、产品、版式或多格连续性必须准确；先做锚点，再分区或分格生成。
- 编辑路线：已有图片大部分通过，只修局部。

交付完整提示词、分格或分区提示词、精确文字、保留项、避免项、执行方式、参数、硬门槛、评分标准和回退条件。读取 [路线选择](references/route-selection.md)、[阅读性与排字](references/readability-and-lettering.md)，需要精确 CLI/API 时再读 [GPT Image 2 操作](references/gpt-image-2-operation.md)。

确认门：用户明确确认提示词、路线、候选数量，并授权实际生成。没有确认就停留在阶段 5。

### 6. 生成与候选确认

只执行阶段 5 已确认的方案：

1. 普通任务使用 Codex 内置 `image_gen`。
2. 用户明确要求精确模型或 API 参数时，调用已安装 `imagegen` Skill 的 CLI/API 路径，使用 `gpt-image-2`；不复制 CLI 脚本，不静默降级。
3. 内置编辑本地图片前，先用 `view_image` 让目标图进入可见上下文。
4. 默认只生成 1 张候选；选中的项目候选复制到项目目录。
5. 内置图片生成结束当前回复；下一轮从阶段 6 候选确认续接，不假装用户已选择。

让用户选择接受进入 QA、做单变量编辑、增加变体或返回阶段 5。快速路线连续两轮发生分格、文字、身份或版式硬失败时，强制切换稳定路线。

确认门：用户明确选择一个候选进入 QA。

### 7. QA 与返修确认

按 [QA 与返修](references/acceptance-and-repair.md) 评分。总分不得低于 85，且不能有关键要求缺失、因果或领域语义错误、关键文字不可读、身份明显漂移、版式或安全区破损、规格错误、发布权利未确认等硬失败。

失败映射到最早责任阶段。局部问题用 `preserve-change-edit-contract` 生成单变量返修；故事问题返回阶段 3，锚点问题返回阶段 4，路线问题返回阶段 5。

确认门：用户接受 QA 结果和最终版本，或批准返修方案。批准返修不等于接受最终图。

### 8. 交付与后续确认

复制 [AI Image Build Pack 模板](assets/AI-Image-Build-Pack-template.md)，填入所有确认版本、锁定项、提示词、生成记录、QA、权利状态和最终路径。

正式目录只保留最终图和复现最终图必需的锚点或分格素材。非覆盖命名：`project-final-v01.png`、`project-character-anchor-v01.png`、`project-panel-01-v01.png`、`AI-Image-Build-Pack.md`。

用户要求动画化时，追加 Seedance 2.0 的素材职责、动作与表演、镜头顺序、转场连续性、必须保持项和提示词。V1 不生成视频。

确认门：用户确认文件完整、路径和规格正确后，才把状态改为 `已完成`。

## 输出纪律

- 区分已确认事实、当前假设、无法验证和用户待决策。
- 需要精确参数时读取当前 `imagegen` Skill，不把模型能力当永久事实。
- 精确排字失败且无排版工具时设为 `受阻`，不要冒充最终成图。
- 每次只改一个失败变量并复验保留项。
- 真实出图与静态合同测试分开记录；没有实际生成就写“未执行”。
