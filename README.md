# AI Image & Video Skills

一套面向 Codex 的 AI 图片与视频创作工作流。它不只生成一段提示词，而是把创意拆成可以选择、确认、执行、检查和恢复的生产流程。

仓库当前包含：

- 1 个静态图片总控 Agent：[`build-image-fast`](./build-image-fast/SKILL.md)，当前版本 V5.4；
- 11 个可以独立调用的原子 Skill；
- 图片项目所需的状态合同、资产计划、排字规范、QA 规则、验证脚本和测试夹具。

> 适合：主视觉、海报、社交媒体图片、信息图、产品图、角色系列图、漫画，以及图片局部编辑。
>
> 不适合：直接完成一条 5–30 秒视频。完整视频项目请使用另行安装的 `build-ai-video-fast`；本仓库的 4 个视频 Skill 用于解决分镜、动态提示、端点控制和片段装配等单点问题。

## 先选入口

| 你的需求 | 推荐入口 | 你会得到什么 |
| --- | --- | --- |
| 从一句创意完成一张或一组正式图片 | [`build-image-fast`](./build-image-fast/SKILL.md) | 路线选择、资产清单、正式图片、QA 和可复现 Build Pack |
| 只想写或优化图片提示词 | [`image-prompt-specification`](./image-prompt-specification/SKILL.md) | 结构化视觉规格、提示词和负面约束 |
| 根据参考图分析可能的提示词 | [`reference-image-prompt-reverse-engineering`](./reference-image-prompt-reverse-engineering/SKILL.md) | 可见证据、推测部分和可执行提示词 |
| 扩写提示词，但不能丢失关键要求 | [`constraint-aware-prompt-expansion`](./constraint-aware-prompt-expansion/SKILL.md) | 不可妥协约束、探索空间和扩写版本 |
| 只改图片的一部分，其余保持不变 | [`preserve-change-edit-contract`](./preserve-change-edit-contract/SKILL.md) | 变更项、保留项和验收清单 |
| 角色、产品或场景总是不一致 | [`reference-anchor-density`](./reference-anchor-density/SKILL.md) | 最小充分的多视图、细节和端帧锚点方案 |
| 不知道该用文字、图片还是视频作参考 | [`generation-mode-reference-selection`](./generation-mode-reference-selection/SKILL.md) | 输入模态与素材职责分配 |
| 想在质量、速度和成本之间选模型 | [`capability-cost-fit`](./capability-cost-fit/SKILL.md) | 最小足够能力档位与升级条件 |
| 只处理视频分镜、镜头或装配问题 | 对应视频原子 Skill | 动态规格、分镜预算、端点方案或装配方案 |

完整路由关系见 [INDEX.md](./INDEX.md)。

## 安装

### 1. 克隆仓库

~~~powershell
git clone https://github.com/linjiahao068-source/ai-image-video-skill.git
Set-Location ai-image-video-skill
~~~

### 2. 安装需要的 Skill

Codex 的每个 Skill 都是一个包含 `SKILL.md` 的独立文件夹。将需要的文件夹复制到：

~~~text
~/.codex/skills/
~~~

例如，只安装静态图片总控：

~~~powershell
$target = Join-Path $env:USERPROFILE '.codex\skills'
New-Item -ItemType Directory -Force $target | Out-Null
$destination = Join-Path $target 'build-image-fast'
if (Test-Path $destination) {
  throw '目标目录已存在 build-image-fast，请先备份或处理本地修改。'
}
Copy-Item '.\build-image-fast' $target -Recurse
~~~

安装仓库内全部 Skill：

~~~powershell
$source = Get-Location
$target = Join-Path $env:USERPROFILE '.codex\skills'
New-Item -ItemType Directory -Force $target | Out-Null

Get-ChildItem $source -Directory |
  Where-Object { Test-Path (Join-Path $_.FullName 'SKILL.md') } |
  ForEach-Object {
    $destination = Join-Path $target $_.Name
    if (Test-Path $destination) {
      Write-Warning ('已跳过现有 Skill：{0}' -f $_.Name)
    } else {
      Copy-Item $_.FullName $target -Recurse
    }
  }
~~~

安装命令不会覆盖同名 Skill。更新已有安装前，请先确认是否需要保留本地修改。复制完成后，重启 Codex 或开启新任务。

### 3. 调用

在请求第一行写 Skill 名称：

~~~text
$build-image-fast

为一家独立咖啡店制作一张 4:5 社交媒体封面。
~~~

也可以直接描述需求，让 Codex 自动路由；显式写出 `$skill-name` 更适合需要固定入口的任务。

## 使用 build-image-fast

### 它怎样工作

`build-image-fast` 会先判断项目风险和工作模式，再决定需要多少次前置确认：

| 模式 | 适用场景 | 正式成图前确认 |
| --- | --- | ---: |
| `atomic` | 只需提示词、参考分析或模型选择 | 不适用 |
| `direct` | 需求完整、低风险的简单单图 | 0 次 |
| `guided` | 文案、内容或发布边界需要先锁定 | G0，1 次 |
| `controlled` | 多角色、系列图、商业发布、精确文字或高一致性 | G0 + G1，2 次 |
| `edit` | 已有图片上的单一明确修改 | 通常 0 次 |

默认使用 `review_mode=adaptive`：后台可以有多个生产阶段，但不会把每个内部步骤都变成用户确认。只有用户明确要求逐阶段审片时才使用 `full_review`。

### G0、G1、G2

| 阶段 | 内容 | 用户动作 |
| --- | --- | --- |
| G0：创意与范围 | 内容、角色、精确文字、权利边界、速度建议、资产清单 | 确认会改变成品、成本或发布边界的决定 |
| G1：视觉锚点 | 仅用于 `controlled`：已选资产、角色/风格锚点、构图与排字方案 | 确认视觉方向 |
| G2：正式交付 | 正式图片、QA、已知限制和 Build Pack | 判断成品是否视为最终成功 |

如果项目需要视觉资产包，系统必须先在 G0 给出 `required / optional / skipped` 资产清单。用户选择后，只生成确认需要的资产；简单图片可以选择 `minimal` 或 `none`，不会为了凑资产包而额外制作角色卡、关系图或世界观图。

系统还会先推荐 `fast / balanced / quality` 档位，并说明适合的模型能力和思考程度。用户可以改选更快或更高保真的方案；推荐只是工作流建议，不代表当前会话已经切换模型，也不保证固定成本。

正式图片通过 QA 后，系统会询问“这是否就是最终成功”。只有用户确认后，才提供可复现 ZIP；其中可以包含最终图、已选资产、内容大纲、角色/视觉规范、提示词、生成请求、Build Pack 和哈希清单。

## 示例

### 示例 1：快速制作简单封面

~~~text
$build-image-fast

为新品冷萃咖啡制作一张 4:5 小红书封面。
受众：25–35 岁上班族。
标题：星期一，也要慢慢醒来。
风格：温暖、干净、有手作感。
优先速度；不需要角色、关系图或世界观资产。
目标：公开发布。
~~~

预期路线：`direct` 或轻量 `guided`。系统优先推荐快速档位和 `minimal / none` 资产范围，不为简单单图生成完整资产包。

### 示例 2：先确认资产清单，再制作产品海报

~~~text
$build-image-fast

为一款透明玻璃香水瓶制作竖版商业海报。
必须保留：瓶身比例、银色瓶盖、正面品牌字样。
精确文案：雨后，森林醒来。
目标：电商和线下灯箱发布。

本轮先不要生成图片。
请先给出 G0、推荐速度档位，以及 required / optional / skipped 资产清单。
~~~

预期路线：`guided` 或 `controlled`。用户先选择产品多角度图、材质细节、品牌规范等资产；确认后才建立所选资产和正式生成方案。

### 示例 3：多角色四格漫画

~~~text
$build-image-fast

制作一组解释 ETF 定投的四格漫画。
角色：一位新手投资者和一只拟人化储蓄罐。
要求：四格中角色外观一致；对白逐字准确；公开商业发布。
已有：角色授权资料和参考图。
路线：controlled。

先交付 G0：内容大纲、逐格角色矩阵、显示语义合同、
权利边界、资产清单和推荐执行档位。本轮不要调用图片模型。
~~~

预期路线：`controlled`。G0 锁定内容和资产范围，G1 锁定角色、画风、无字底图与排字几何，之后才生成正式四格、执行排字和 QA。

### 示例 4：只修改一处，其他内容不变

~~~text
$build-image-fast

编辑附件图片。
只改：把人物外套从红色改为深蓝色。
保持：人物身份、脸、发型、姿势、构图、背景、光线和全部文字不变。
如果无法只改这一项，请停止并说明冲突，不要扩大修改范围。
~~~

预期路线：`edit`，并调用 `preserve-change-edit-contract`。如果出现第二个变更变量，或保留项无法验证，系统会退出轻量编辑路线。

### 示例 5：只优化一条图片提示词

~~~text
$image-prompt-specification

把下面的想法改成可控的文生图提示词：
“一个人在深夜便利店等雨停，孤独但不悲惨。”

请保留情绪核心，并补齐主体、环境、时间、光线、构图和镜头距离。
~~~

预期结果：结构化意图、缺失信息判断、可执行提示词和必要的负面约束；不会启动完整图片项目或强制生成 Build Pack。

### 示例 6：规划一条 10 秒产品视频

~~~text
$storyboard-event-budgeting

把“耳机从桌面悬浮、拆解、重新组合并落回充电盒”
规划成 10 秒产品短片。
请判断需要多少镜头、每个事件占用多少时间，以及哪些镜头需要首尾帧。
~~~

预期结果：镜头与时长预算。随后可分别调用 `video-direction-specification` 编写动态提示、`endpoint-anchored-video-synthesis` 锁定关键端点、`sequence-continuity-assembly` 设计装配与转场。完整视频生产仍应交给 `build-ai-video-fast`。

## 11 个原子 Skill

### 图片提示词

| Skill | 适用问题 |
| --- | --- |
| [`image-prompt-specification`](./image-prompt-specification/SKILL.md) | 把模糊图片想法变成可控提示词 |
| [`reference-image-prompt-reverse-engineering`](./reference-image-prompt-reverse-engineering/SKILL.md) | 从参考图拆解可见特征和可能的提示词 |
| [`constraint-aware-prompt-expansion`](./constraint-aware-prompt-expansion/SKILL.md) | 在保持硬约束的同时扩写或探索方向 |

### 输入、成本、编辑与一致性

| Skill | 适用问题 |
| --- | --- |
| [`generation-mode-reference-selection`](./generation-mode-reference-selection/SKILL.md) | 决定文字、图片、视频或音频各自承担什么控制职责 |
| [`capability-cost-fit`](./capability-cost-fit/SKILL.md) | 按失败风险选择最小足够模型能力 |
| [`preserve-change-edit-contract`](./preserve-change-edit-contract/SKILL.md) | 明确“改什么”和“必须保持什么” |
| [`reference-anchor-density`](./reference-anchor-density/SKILL.md) | 决定一致性任务需要多少参考角度和细节锚点 |

### 视频规划与装配

| Skill | 适用问题 |
| --- | --- |
| [`video-direction-specification`](./video-direction-specification/SKILL.md) | 把情绪、动作、运镜和节奏写成动态规格 |
| [`storyboard-event-budgeting`](./storyboard-event-budgeting/SKILL.md) | 分配镜头数、事件量和时长 |
| [`endpoint-anchored-video-synthesis`](./endpoint-anchored-video-synthesis/SKILL.md) | 锁定首帧、尾帧、关键状态或循环落点 |
| [`sequence-continuity-assembly`](./sequence-continuity-assembly/SKILL.md) | 处理转场、动作接缝、重复帧和节拍装配 |

## 交付与恢复

`build-image-fast` 使用 `project-state.json` 作为项目状态真源。正式生成会绑定 `generation-request`，记录提示词、负面约束、参数、参考文件指纹和产物槽位，使中断后的项目可以核对状态后继续，而不是依赖聊天记忆猜测。

典型正式交付包括：

- 最终图片；
- 已选且通过门控的视觉资产；
- 内容、角色与视觉规范；
- 提示词包和生成请求；
- QA 结果、已知限制和 AI Image Build Pack；
- 用户确认最终成功后生成的可复现 ZIP。

涉及真实人物、商标、受保护角色、客户素材或商业发布时，使用者仍需确认授权、隐私、平台条款和品牌规范。

## 验证

进入 `build-image-fast` 后运行：

~~~powershell
python -m unittest discover -s scripts -p 'test_*.py'
python scripts/validate_contract_cases.py
~~~

这些命令不会调用图片模型。它们可以验证状态门、资产组装、确定性排字、归档及合同 fixture，但不能证明真实图片质量、模型一次成功率或外部发布结果。

更多信息：

- [验证入口与边界](./build-image-fast/test-results.md)
- [合同测试夹具](./build-image-fast/test-prompts.json)
- [工作流与 QA 参考](./build-image-fast/references)
- [完整 Skill 路由](./INDEX.md)

## 来源与许可

本仓库发布的是原创蒸馏后的工作流、示例、测试和代码，不包含原始课程视频、音频、转录、课件或截图。来源与第三方权利边界见 [NOTICE.md](./NOTICE.md)。

原创内容采用 [MIT License](./LICENSE)。MIT 不覆盖第三方素材、参考图、字体、商标、课程内容或其他受保护资产。
