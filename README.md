# AI Image & Video Skill

面向 Codex 的图片与视频创作 Skill 集合。它将「一句创意」拆成可执行、可检查、可恢复的制作流程；不把模型一次生成的偶然结果当作项目交付。

当前仓库包含：

- 1 个图片制作总控：`build-image-fast`（V5.3）
- 11 个可独立调用的原子 Skill
- 图片工作流的合同、模板、验证脚本和测试夹具

> 图片总控负责静态图片、海报、信息图、角色系列图和漫画。完整 5–30 秒视频项目请使用已安装的 `build-ai-video-fast`，而非本仓库的 `build-image-fast`。

## 最快开始

把需要的 Skill 文件夹复制到 Codex 的 skills 目录，重启或刷新 Codex 后即可调用。

### 从 0 制作一张图片

```text
[$build-image-fast]

为新品咖啡制作一张 4:5 小红书封面。
受众：25–35 岁的上班族。
目标：公开发布。
风格：温暖、干净、有手作感。
标题文字：星期一，也要慢慢醒来。
```

总控会判断风险并推荐工作方式；你只需要确认会改变成品的关键决定。

### 制作需要角色一致性的四格漫画

```text
[$build-image-fast]

制作一组普及 ETF 知识的趣味四格漫画。
角色、画风和商业授权资料已提供。
目标：公开商业发布。
路线：controlled。
本轮不要调用图片模型，也不要先画四格。

请先交付 G0：内容包、角色合同、逐格角色矩阵、显示语义合同和文件清单。
```

确认 G0 后，总控才会安排美术指导交付 G1 资产与版式方案；确认 G1 后，才进入无字底图、确定性排字、QA 与 G2 交付。

### 修复一张已有图片

```text
[$build-image-fast]

修复附件中的对话文字越出气泡问题。
保持：角色、构图、颜色、其余文字和背景都不变。
只改：第一格对话气泡内的两行文字。
```

当变更项和保留项都明确时，系统使用 `edit` 路线；若同时涉及剧情、角色或多个版式变量，会自动退出局部编辑，改走可控项目流程。

## build-image-fast V5.3

`build-image-fast` 不是“把提示词交给图片模型”的单步工具，而是静态图片项目的总控入口。它将项目拆分为四种专业职责，并只让图片总编面对用户。

| 角色 | 负责什么 | 不负责什么 |
| --- | --- | --- |
| 图片总编 | 选路、门控、交接、独立 QA、最终交付 | 替专业角色擅自改写语义或美术规范 |
| 内容与角色导演 | 故事/信息结构、角色合同、逐格矩阵、可见文字语义 | 决定字体、字号、气泡几何 |
| 美术指导 | 视觉风格、资产板、无字底图后的真实容器轮廓与排字几何 | 改写已锁定对白、标签含义、角色职能 |
| 执行场记 | 无字底图提示词、确定性排字、构建和适配报告 | 为塞进容器而缩字、删字、改标签或添加合同外 UI |

### 五种工作模式

| 模式 | 适用场景 | 成图前用户拍板 |
| --- | --- | ---: |
| `atomic` | 只需提示词、参考图分析、模型比较等单点问题 | 不适用 |
| `direct` | 低风险单图，需求完整 | 0 次 |
| `guided` | 有核心创意、文案或发布取舍 | G0 |
| `controlled` | 多角色、商业发布、强风格/文字/连续性要求 | G0 + G1 |
| `edit` | 一张已有图上的单一明确修改 | 通常 0 次 |

`review_mode=adaptive` 是默认值：后台有八个生产阶段，但不会把它们伪装成八次用户确认。只有你明确要求逐阶段审片时，才使用 `full_review`。

### G0 / G1 / G2 的含义

| 门 | 你看到的交付 | 你需要确认什么 |
| --- | --- | --- |
| G0 创意锁定 | 内容包、角色合同、逐格矩阵、权利边界、显示语义合同 | 会改变故事、角色、精确文案、标签含义或发布边界的决定 |
| G1 视觉锚点锁定 | 资产详情方案、视觉规范、无字底图方案、排字/几何合同、压力测试摘要 | 会改变视觉锚点、资产、构图或排字方案的决定 |
| G2 最终交付 | 正式图、QA 结果、已知限制、AI Image Build Pack | 无需额外“确认 QA”；通过后自动交付 |

项目每轮都会明确说明：`当前阶段 / 已完成 / 待确认事项 / 下一步 / 确认后的流程`。如果缺少授权、关键输入或可靠工具，项目会标为“受阻”，而不是用猜测补齐。

## V5.3 漫画展示排字

当项目在 G0 明确选择 `typography_profile=comic_display`，或用户提供了需要提炼规则的漫画排字参考时，V5.3 启用严格的“语义 + 几何 + 排字”三层合同。

它解决的不是“让模型尽量把字写对”，而是把以下问题变成正式验收项：

- 每一个对话、篮子牌、物品标签、页脚的逐字文本与语义角色；
- 每格是否必须重复主标牌（例如 `ETF`）；标签是否允许为空（默认不允许）；
- 已授权字体文件、哈希、字重、层级、最小字号、行距、描边和对齐；
- 无字底图中气泡尾巴、弧边、标牌和安全边距的真实轮廓；
- 实际断行、光学定位、文字蒙版、裁切证据和构建报告。

以下任一项会阻断 G2：文字越出实际安全轮廓、必需标签为空、字体权利或哈希不符、字号/视觉占位不足、未按合同居中、断行不符，或出现合同外空白 UI。

这套规则只提炼参考图中可观察的视觉规律；不会复制未确认授权的字体、版式或故事。

## 资产与角色一致性

多角色、系列图、受保护角色或指定风格的项目，`controlled` 路线会要求可审阅的资产三件套：

1. 带字资产总览：供用户和 QA 阅读；
2. 无字 clean group：供生成阶段参考；
3. 机器可读资产清单：记录角色、道具、场景、权利和版本。

漫画成图不能替代角色资产板。角色卡应覆盖主/配角色的主要视图、常用表情和动作边界，以及关键道具与场景锚点。系统不会承诺模型必然复刻某一“官方画风”；涉及真实人物、商标、受保护角色或商业发布时，仍须由项目方确认授权、隐私和品牌规范。

## 原子 Skill 索引

| 类别 | Skill |
| --- | --- |
| 图片规格与提示词 | [image-prompt-specification](./image-prompt-specification/SKILL.md)、[reference-image-prompt-reverse-engineering](./reference-image-prompt-reverse-engineering/SKILL.md)、[constraint-aware-prompt-expansion](./constraint-aware-prompt-expansion/SKILL.md) |
| 输入、编辑与一致性 | [generation-mode-reference-selection](./generation-mode-reference-selection/SKILL.md)、[capability-cost-fit](./capability-cost-fit/SKILL.md)、[preserve-change-edit-contract](./preserve-change-edit-contract/SKILL.md)、[reference-anchor-density](./reference-anchor-density/SKILL.md) |
| 视频叙事与装配 | [video-direction-specification](./video-direction-specification/SKILL.md)、[storyboard-event-budgeting](./storyboard-event-budgeting/SKILL.md)、[endpoint-anchored-video-synthesis](./endpoint-anchored-video-synthesis/SKILL.md)、[sequence-continuity-assembly](./sequence-continuity-assembly/SKILL.md) |

完整关系与路由见 [INDEX.md](./INDEX.md)。

## 本地验证

仓库的合同测试不会调用图片模型。以 Windows PowerShell 为例：

```powershell
cd "C:\Users\老大哥柚子\Documents\AI视频SKILL 2\ai-图片&视频-skill"

$py = "$env:USERPROFILE\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
& $py build-image-fast\scripts\test_v53_comic_typography.py
& $py build-image-fast\scripts\test_v53_typography_state.py
& $py build-image-fast\scripts\test_v52_display_state.py
& $py build-image-fast\scripts\test_v51_asset_coverage.py
```

更多验证入口：

- [verified.md](./verified.md)：仓库级已验证范围与未验证边界；
- [build-image-fast/test-prompts.json](./build-image-fast/test-prompts.json)：合同测试夹具；
- [build-image-fast/test-results.md](./build-image-fast/test-results.md)：测试记录与限制；
- [build-image-fast/references](./build-image-fast/references)：工作流、资产、显示合同与 QA 规范。

通过合同测试不等于已经验证真实出图质量、中文逐字成图、角色相似度或一次生成成功率。真实生成与视觉验收必须在获得相应授权后单独执行并记录。

## 发布与许可边界

本仓库发布的是工作流、示例、测试与说明，不包含原始课程视频、音频、转录、课件或截图。真实人物、商标、受保护角色、参考图和商业交付的权利与审核责任仍由项目方承担。

原创蒸馏文本和代码采用 [MIT License](./LICENSE)；该许可不覆盖任何第三方素材或课程原始内容。
