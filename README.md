# AI Image & Video Skill

面向 Codex 的图片与视频创作 Skill 集合。它把一句创意拆成可执行、可检查、可恢复的制作流程；不把一次模型生成的偶然结果当作项目交付。

当前仓库包含：

- 1 个静态图片制作总控：\`build-image-fast\`（V5.4）
- 11 个可独立调用的原子 Skill
- 图片工作流的合同、模板、验证脚本和测试夹具

> \`build-image-fast\` 负责静态图片、海报、信息图、角色系列图和漫画。完整 5–30 秒视频项目请使用已安装的 \`build-ai-video-fast\`。

## 最快开始

将所需 Skill 文件夹复制到 Codex 的 skills 目录，重启或刷新 Codex 后即可调用。

### 从 0 制作一张图片

\`\`\`text
[$build-image-fast]

为新品咖啡制作一张 4:5 小红书封面。
受众：25–35 岁的上班族。
目标：公开发布。
风格：温暖、干净、有手作感。
标题文字：星期一，也要慢慢醒来。
优先速度；如无需角色或道具资产，请给我最小资产清单。
\`\`\`

总控会先给出工作流、速度/思考档位和资产范围建议；你只确认会改变成品、成本或发布边界的决定。

### 制作需要角色一致性的四格漫画

\`\`\`text
[$build-image-fast]

制作一组普及 ETF 知识的趣味四格漫画。
角色、画风和商业授权资料已提供。
目标：公开商业发布。
路线：controlled。
本轮不要调用图片模型，也不要先画四格。

请先交付 G0：内容包、角色合同、逐格角色矩阵、显示语义合同，
以及 required / optional / skipped 资产清单与推荐速度档位。
\`\`\`

确认 G0 后，系统只构建已选且必要的资产；高风险项目再进入 G1 视觉锚点锁定，之后才生成正式图、排字、QA 与 G2 交付。

### 修复一张已有图片

\`\`\`text
[$build-image-fast]

修复附件中的对话文字越出气泡问题。
保持：角色、构图、颜色、其余文字和背景都不变。
只改：第一格对话气泡内的两行文字。
\`\`\`

变更项和保留项明确时，系统走 \`edit\` 路线；若同时涉及剧情、角色或多个版式变量，会自动升级为可控项目流程。

## build-image-fast V5.4

\`build-image-fast\` 是静态图片项目的总控入口，不是把提示词直接丢给图片模型的单步工具。它由四种专业职责协作，但只由图片总编面对用户。

| 角色 | 负责什么 | 不负责什么 |
| --- | --- | --- |
| 图片总编 | 选路、范围、门控、独立 QA、最终交付与验收 | 擅自改写语义或美术规范 |
| 内容与角色导演 | 故事/信息结构、角色合同、逐格矩阵、可见文字语义 | 决定画风、模型参数或生成路线 |
| 美术指导 | 视觉风格、资产计划、角色/场景锚点、排字与几何合同 | 改写锁定的对白、标签含义或角色职能 |
| 执行场记 | 提示词编译、参考分配、生成请求、确定性排字与版本记录 | 为了可生成而静默删改合同 |

### 五种工作模式

| 模式 | 适用场景 | 成图前用户拍板 |
| --- | --- | ---: |
| \`atomic\` | 只需提示词、参考图分析、模型比较等单点问题 | 不适用 |
| \`direct\` | 低风险单图，需求完整 | 0 次 |
| \`guided\` | 有核心创意、文案或发布取舍 | G0 |
| \`controlled\` | 多角色、商业发布、强风格/文字/连续性要求 | G0 + G1 |
| \`edit\` | 一张已有图上的单一明确修改 | 通常 0 次 |

\`review_mode=adaptive\` 是默认值：后台有八个生产阶段，但不会伪装成八次用户确认。只有明确要求逐阶段审片时，才使用 \`full_review\`。

### G0 / G1 / G2 与最终验收

| 阶段 | 你看到的交付 | 你需要决定什么 |
| --- | --- | --- |
| G0 创意与范围锁定 | 内容包、角色/文字/权利边界、推荐速度档位、资产清单 | 会改变故事、角色、精确文案、资产范围、成本或发布边界的决定 |
| G1 视觉锚点锁定 | 仅在 \`controlled\` 项目出现：已选资产、视觉规范、无字底图方案、排字/几何合同、压力测试摘要 | 会改变视觉锚点、资产、构图或排字方案的决定 |
| G2 自动交付 | 正式图、QA、已知限制、AI Image Build Pack | 不确认 QA 流程；只在成品后回答是否视为最终成功 |

G2 通过后会询问“这是否就是最终成功”。确认后，系统才创建可复现 ZIP；要求返修则重开受影响的决定和下游产物。

### 先选速度与思考程度

图片总编先给推荐，用户可以改选更快或更高保真档位：

| 档位 | 适用 | 推荐执行配置 | 路线 |
| --- | --- | --- | --- |
| \`fast\` | 简单单图、时间优先、资产最少 | \`gpt-5.6-luna\` + \`low\` | \`fast\` |
| \`balanced\` | 默认：质量、速度与稳定性的折中 | \`gpt-5.6-terra\` + \`medium\` | \`fast\` 或 \`stable\` |
| \`quality\` | 复杂文字、多角色、连续性或高保真优先 | \`gpt-5.6-sol\` + \`high\` | \`stable\` |

这些是工作流推荐，不是对当前 Codex 会话实际模型或思考强度的声明。实际生效值必须写入 \`generation-request\` 与执行日志；\`fast\` 也不等于一定更低费用，额外候选或高成本调用仍需授权。

### 先选资产，避免无谓生成

G0 使用现有 \`asset-plan\` 把每项资产标为 \`required / optional / skipped\`。低风险单图可以选择 \`minimal\` 或 \`none\`，不会为了凑“资产包”而生成角色卡、关系图或世界观图；多角色、连续性、权利或强风格风险则会把相应资产列为必需。

只有用户已选的必需资产才进入生成与 QA。高保真 \`controlled\` 项目的 G1 仍然只负责视觉锚点确认，不新增第三次前置确认。

### 可复现交付，而非隐藏调用

每次正式成图都绑定一份 \`generation-request\`：记录编译提示词、负面约束、参数、干净参考及其 SHA-256、上游合同指纹和候选/正式槽位。它是执行场记的正式交付物，不是额外让用户审核提示词的关口。

用户确认最终成功后，\`scripts/package_handoff.py\` 生成 ZIP，包含最终图、已选资产、内容与角色合同、视觉规范、提示词包、生成请求、Build Pack 和哈希清单；候选图、缓存、密钥、环境文件和未选资产不得进入交付包。

## V5.3 漫画展示排字仍保留

当项目在 G0 选择 \`typography_profile=comic_display\`，或用户提供需要提炼规则的漫画排字参考时，系统执行“语义 + 几何 + 排字”三层合同：每个对白、标牌、标签和页脚的逐字文本、语义角色与重复规则；字体权利与哈希、字重、层级、最小字号、行距、描边和对齐；以及无字底图中的实际容器轮廓、安全边距、断行、文字蒙版与裁切证据。

文字越出实际轮廓、必需标签为空、字体权利或哈希不符、字号/视觉占位不足、未按合同居中、断行不符或出现合同外 UI，都会阻断 G2。

## 资产与角色一致性

多角色、系列图、受保护角色或指定风格的 \`controlled\` 项目，按需建立可审阅的资产三件套：带字资产总览、无字 clean group 与机器可读资产清单。漫画成图不能替代角色资产板。

系统不会承诺模型必然复刻某一“官方画风”。涉及真实人物、商标、受保护角色、参考图或商业发布时，项目方仍须确认授权、隐私与品牌规范。

## 原子 Skill 索引

| 类别 | Skill |
| --- | --- |
| 图片规格与提示词 | [image-prompt-specification](./image-prompt-specification/SKILL.md)、[reference-image-prompt-reverse-engineering](./reference-image-prompt-reverse-engineering/SKILL.md)、[constraint-aware-prompt-expansion](./constraint-aware-prompt-expansion/SKILL.md) |
| 输入、编辑与一致性 | [generation-mode-reference-selection](./generation-mode-reference-selection/SKILL.md)、[capability-cost-fit](./capability-cost-fit/SKILL.md)、[preserve-change-edit-contract](./preserve-change-edit-contract/SKILL.md)、[reference-anchor-density](./reference-anchor-density/SKILL.md) |
| 视频叙事与装配 | [video-direction-specification](./video-direction-specification/SKILL.md)、[storyboard-event-budgeting](./storyboard-event-budgeting/SKILL.md)、[endpoint-anchored-video-synthesis](./endpoint-anchored-video-synthesis/SKILL.md)、[sequence-continuity-assembly](./sequence-continuity-assembly/SKILL.md) |

完整关系与路由见 [INDEX.md](./INDEX.md)。

## 本地验证

合同测试不会调用图片模型。以 Windows PowerShell 为例：

\`\`\`powershell
cd "C:\\Users\\老大哥柚子\\Documents\\AI视频SKILL 2\\ai-图片&视频-skill\\build-image-fast"

$py = "$env:USERPROFILE\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe"
& $py -m unittest discover -s scripts -p 'test_*.py' -v
& $py scripts\\validate_contract_cases.py test-prompts.json
\`\`\`

当前 V5.4 回归覆盖 61 个单元测试与 85 条合同夹具。更多验证入口：

- [verified.md](./verified.md)：仓库级已验证范围与未验证边界；
- [build-image-fast/test-prompts.json](./build-image-fast/test-prompts.json)：合同测试夹具；
- [build-image-fast/test-results.md](./build-image-fast/test-results.md)：历史测试记录与限制；
- [build-image-fast/references](./build-image-fast/references)：工作流、资产、显示合同与 QA 规范。

通过合同测试不等于已经验证真实出图质量、中文逐字成图、角色相似度或一次生成成功率。真实生成与视觉验收必须在获得相应授权后单独执行并记录。

## 发布与许可边界

本仓库发布的是工作流、示例、测试与说明，不包含原始课程视频、音频、转录、课件或截图。真实人物、商标、受保护角色、参考图和商业交付的权利与审核责任仍由项目方承担。

原创蒸馏文本和代码采用 [MIT License](./LICENSE)；该许可不覆盖任何第三方素材或课程原始内容。
