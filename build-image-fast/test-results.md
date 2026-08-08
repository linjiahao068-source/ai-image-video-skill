# build-image-fast V5 验证记录

本文件只记录本轮真实执行结果。合同 fixture、Agent dry-run、确定性组装和真实图片生成分开统计；前者通过不能替代后者。

## 结论摘要

| 验证层 | 结果 | 能证明什么 |
| --- | --- | --- |
| 状态门单元测试 | 26 / 26 通过 | 0/1/2 门、授权、权利、字段依赖、确认快照、G2 文件链等机器合同 |
| 资产组装器测试 | 15 / 15 通过 | 三件套组装、候选→release、硬拆分限制、非覆盖与报告证据边界 |
| 联合自动化 | 41 / 41 通过 | 状态门与组装器使用同一最终 schema 可共同工作 |
| 合同 fixture | 85 / 85 通过 | 39 个 V4 ID 完整迁移，另有 46 个 V5 场景；schema 2.0.0，Skill 5.0.0 |
| 官方 Skill 校验 | 通过 | Skill 目录与前置元数据符合官方结构校验 |
| 独立代码/合同复审 | RELEASE | 已知状态门绕过经反例重放后被阻断；未发现代码/合同阻断项 |
| 真实图片生成与 G2 | 未执行 | 不能据此推断画质、官方画风相似度或一次生成成功率 |

## 自动化验证

最终联合测试真实输出：

```text
Ran 41 tests in 32.472s
OK
```

其中状态测试 26 条，组装器测试 15 条。关键负例包括：

- 未授权候选、超出候选套件上限、同一交付槽位隐藏第二张正式候选；
- delegated rights、Agent 自行填写授权来源、伪造 `user_confirmed` actor；
- G1 换包、确认后替换资产 SHA、只改依赖边继续沿用旧确认；
- 精确文案变化保留 G1/release，但正式图与文字 QA 失效；
- 角色、权利或资产语义变化使旧 G1 失效；
- 改写已确认决策的 ID、gate、field 或 source 后旧事件失效；
- `copy_character_identity`、`character_copy` 不能伪装成纯文字字段；
- G2 正式图、QA 与 Build Pack 缺文件、路径越界、SHA 变化或依赖指纹变化；
- 任意字节不能冒充正式图片，Pillow 不可用时正式图验证 fail closed；
- 清单不得把 8 槽位、2 类主要职责和 384px 最短边硬限制调松。

最终 fixture 验证真实输出：

```text
VALID: 85 contract fixtures; schema=2.0.0; version=5.0.0
NOTE: fixture validation only; no LLM, image generation, QA scoring, or prompt execution ran.
```

85 条 fixture 均有结构化预期事件、禁止事件和类型；验证器不仅解析 JSON，还检查 ID 集合、0/1/2 拍板数、枚举、风险底线、失效集合和关键跨字段合同。fixture 没有被逐条发送给 LLM，因此不计作 85 次 Agent 实跑。

## 独立 Agent 前向 dry-run

图片调用全部在调用前由测试夹具截断，未制造图片。真实执行的编排行为包括：

- `direct` 原创低风险单图：0 次追加拍板，直接到正式图片调用边界；
- `guided` 精确中文海报：1 次 G0；方向记为 `user_confirmed`，可逆细节记为 `delegated_decision`；
- `controlled` 股票四格：G0 + G1，共 2 次；真实 physical Sub Agent 识别出 Chiikawa 出场合同与第四格三人收尾的冲突，并交由用户拍板；
- 同一股票任务的 `serial_roles` 运行得出相同语义方案，并明确显示“单 Agent 串行专业分工”，没有虚构团队会诊；
- G0 已确认、G1 待确认的恢复不重复团队介绍、不丢确认、不提前生成正式图；
- 中途增加商业公开发布且授权范围未解决时，`rights_lock=hard` 阻断候选、release、正式图和发布，口头降级不能绕过。

详细证据位于测试副本的 `validation/v5-forward-dry-run.md` 与 `validation/v5-edge-behavior-dry-run.md`。这组结果支持交互和编排合同，不支持图片质量结论。

## 股票四格迁移副本

原 V4 项目未改写；测试副本使用 V5 `project-state.json` 真源：

- `state_revision=12`，SHA-256 为 `ccbaf325cbeb5b10eb1d7488b7666a808a76a45dbbb9fa42d4accd23a23b3c3f`；
- 最新 CLI 返回 `valid=true`；项目仍为 `blocked / G0 pending`，没有把 Hachiware 假设冒充确认；
- 18 / 18 个决策具备值、依赖与记录指纹，6 / 6 个历史确认具备决策记录快照；
- Hachiware-only 反事实下，story、Usagi、Chiikawa、phone、rights 的值与记录指纹保持率为 5 / 5；
- V4 清单以 legacy `candidate_preview` 重建带字总览、clean board 和报告成功，但仍 `registry_eligible=false`，未确认 Hachiware 不得晋级；
- 最终 hardened 构建报告明确：合成器未向 clean board 添加标签，但 `pixel_level_text_absence_verified=false`、OCR/人工文字 QA 未运行。

对应证据位于 `image-builds/buy-the-dip-four-panel-v5-forward-20260807/`。原始 V4 Skill 的 19 文件只读副本与 SHA-256 清单保存在 `.v5-baselines/`。

## 静态与结构检查

- `SKILL.md` 136 行，低于 500 行；版本标识为 5.0.0；
- 官方 `quick_validate.py` 通过；
- JSON/YAML、严格 UTF-8、Markdown 本地链接、代码围栏和 Python 语法检查通过；
- staging 目录无 `__pycache__`、`.pyc`、截断标记或乱码替换符；
- 未发现把内部八阶段逐一设为默认确认门、把提示词审批设为生成前硬门、或把路径确认设为完成条件等 V4 遗留合同。

## 未执行与信任边界

以下项目未执行，不能标记通过：

- 图片模型调用、真实候选资产、真实压力测试图、正式漫画或海报；
- 真实图片 `QA >= 85`、自动返修和最终 G2 Build Pack 交付；
- 中文逐字成图、股票交易软件手机界面、角色视觉连续性的真实模型验收；
- clean board 像素级 OCR 或人工无字检查；
- physical/serial 的隐藏状态字节级一致性，只验证了可观察语义一致性。

状态文件没有外部签名。若攻击者同时重写当前状态、完整确认历史和所有快照，使整份文件重新自洽，校验器不能证明聊天中的真实用户行为；本轮关闭的是保留旧事件时的局部换包和意外绕过。

## 最终判断

V5 的编排、状态、资产三件套和合同层达到可发布状态；真实图片效果验收仍待另行授权执行。不得据本记录宣称画质、指定官方画风相似度或一次生成成功率提高。

## V5.2 显示合同增量验证（2026-08-08）

本节只记录这次更新的真实运行结果，不重写上方 V5 历史记录。

| 验证层 | 结果 | 覆盖 |
| --- | --- | --- |
| 状态门 | 27 / 27 通过 | 既有有效性、授权、G0/G1/G2 与文件链 |
| V5.2 显示状态 | 2 / 2 通过 | `display_semantics` 不能被逐字文本绕过；新状态不要求迁移 |
| 资产三件套 | 16 / 16 通过 | V5.2 生产状态、候选/发布和旧清单兼容 |
| 资产覆盖 | 1 / 1 通过 | 身份、表演、风格、道具与场景覆盖 |
| 确定性排字/轮廓 | 2 / 2 通过 | 合法排字通过；字形进入气泡尾巴即失败 |
| 合同 fixture | 85 / 85 通过 | `schema=2.2.0`、`version=5.2.0` |

Python 语法编译、SKILL 前置元数据长度、16 个本地链接和全部 JSON 模板均通过本地检查。官方 `quick_validate.py` 未运行成功：当前工作区 Python 缺少其所需 `PyYAML`，本轮未下载或安装依赖，因此不将该项标记为通过。

未调用图片模型；以上结果不证明真实文字生成、画质、角色/风格相似度或最终漫画 QA 效果。
## V5.3 漫画展示排字增量验证（2026-08-08）

本节记录 V5.3 的真实本地验证；不对图片模型、授权或正式漫画质量作超出证据的声明。

| 验证层 | 结果 | 覆盖 |
| --- | --- | --- |
| 资产三件套 | 16 / 16 通过 | 既有候选、release、字体与清单保护 |
| V5.2 实际轮廓排字 | 2 / 2 通过 | 文字适配、尾巴/弧边越界回归 |
| V5.3 漫画展示排字 | 6 / 6 通过 | 锁定行组、字体哈希、最小字号、占位、居中与合同缺失/篡改失败 |
| V5.3 显示状态 | 3 / 3 通过 | semantic_role、reading_priority、typography_profile 及 G1 依赖分区 |
| V5.2 显示状态 | 2 / 2 通过 | 旧项目继续兼容 |
| 资产覆盖 | 1 / 1 通过 | 角色、表演、风格、道具、场景覆盖 |
| 项目状态 | 27 / 27 通过 | 有效性、授权、G0/G1/G2 与文件链 |

合计 57 / 57 Python 测试通过。V5.3 的漫画模式现在只接受合同指定的字体文件及其 SHA-256；商业范围要求字体权利状态为 confirmed。独立适配器同时输出几何检查和 typography_checks，因此“文字在气泡内但过小、未居中或行组不对”会阻断，而非仅扣分交付。

未调用图片模型，也未修复现有 ETF 图片。以上测试不证明某一真实字体的商业授权、模型对文字的能力、官方风格相似度或实际成图质量。
