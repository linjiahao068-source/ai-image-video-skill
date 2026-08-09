# AI Image Build Pack

- project_id：
- workflow_mode：atomic / direct / guided / controlled / edit
- blocking_confirmations：not_applicable / 0 / 1 / 2
- risk_floor：0 / 1 / 2
- current_gate：none / G0 / G1 / G2 / blocked
- execution_mode：physical_subagents / serial_roles
- frontstage_owner：图片总编（主 Agent）
- project-state 路径：
- Build Pack 版本：
- 最近恢复/更新：

> V5 口径：workflow_mode 只使用 atomic、direct、guided、controlled、edit。0/1/2 只表示正式成图前的阻塞式用户拍板数：direct=0；guided=1（G0）；controlled=2（G0+G1）；满足单变量且保留项清楚的 edit 通常为 0。atomic 是单点原子任务，通常不强制生成完整 Build Pack。G2 是自动交付包，不计入 0/1/2。后台阶段、自检、QA、asset release 和路径检查不得偷偷增加用户拍板。

## 0. Workflow

### 模式合同

| 模式 | 正式成图前拍板数 | 阻塞门 | standing authorization 生效后的执行 |
| --- | ---: | --- | --- |
| atomic | 不适用 | 无 | 只完成所路由的单点任务；通常不强制生成完整 Build Pack |
| direct | 0 | 无 | 请求字段完整且有效时立即生成正式图，然后自动运行 G2 |
| guided | 1 | G0 | G0 通过后立即生成正式图，然后自动运行 G2 |
| controlled | 2 | G0 + G1 | G0 后可生成候选资产；G1 通过并完成 asset release 后生成正式图，然后自动运行 G2 |
| edit | 通常 0 | 无 | 仅当单一变更项与保留项清楚时执行编辑并自动运行 G2；出现第二变量或保留不清时退出 edit |

- 模式选择依据：
- 模式版本：
- risk_floor 与理由：
- 风险升级记录：
- 是否因 risk_floor 升级模式：
- 旧八阶段映射：后台生产阶段 / 非新增用户门
- 当前内部阶段与状态：
- 当前恢复点：

### atomic 与 edit 的 Pack 边界

- atomic：记录路由、输入、输出和必要 provenance 即可；除非单点任务本身要求，不强制填满团队、G0/G1、asset release 与完整 Build Pack。
- edit：必须记录 target image、单一变更项、明确保留项和来源哈希；编辑后自动进入 G2。出现第二变更变量、保留项含糊或目标图变化时，退出 edit 并重新选择 guided 或 controlled。

### 内部阶段文件与审核

| 内部阶段 | 责任角色 | 输入文件 | 产物文件 | 角色自检 | 主 Agent 审核 | 对应 G0/G1/G2 字段 |
| --- | --- | --- | --- | --- | --- | --- |

## 1. Team

只有图片总编是用户前台。内容与角色导演、美术指导、执行场记均为后台角色；后台提问、交接、自检、冲突和工具调用不能直接形成用户拍板。

| 角色 | frontstage / backstage | 输入版本 | 已确认事实 | 当前假设 | 锁定项 | 禁止改动 | 交付物 | 未决冲突 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

- frontstage_owner：
- execution_mode：
- 物理委派可用性：
- 串行回退原因：
- 后台问题如何并入 G0/G1：
- 是否存在角色直接向用户索取确认：否 / 需纠正

## 2. Gates

| 门 | 适用模式 | 包内容 | 状态 | 版本 | 用户拍板证据 | 失效原因 |
| --- | --- | --- | --- | --- | --- | --- |
| G0 创意决策包 | guided / controlled | 需求、故事/信息、角色、权利、推荐方向与关键假设 |  |  |  |  |
| G1 视觉锚点包 | controlled only | 候选资产、三件套 candidate_preview、压力测试摘要、主 Agent 审核 |  |  |  |  |
| G2 最终交付包 | direct / guided / controlled / edit | 正式图或编辑结果、自动 QA、Build Pack、最终路径与哈希 |  |  | 自动执行，不追加用户确认 |  |

### G0 创意决策包

- 用途/平台/受众：
- 故事或信息结构：
- 精确文字/数据：
- 角色职能与行为边界：
- 权利与发布范围：
- 推荐方向与理由：
- 已确认事实：
- 显式假设：
- 用户选择：
- G0 effective validity：

### G1 视觉锚点包（仅 controlled）

- 候选角色/风格/场景/道具资产：
- candidate_preview 带字总览：
- candidate_preview 无字 clean groups：
- candidate manifest / build report：
- 压力测试摘要与失败证据：
- 主 Agent 独立审核：
- 用户整包选择：
- G1 effective validity：

> G1 不是通用“是否生成”授权，也不是逐资产多次确认。制作/生成请求已经形成 standing authorization。G1 只让用户对 controlled 项目的视觉锚点包做一次阻塞式拍板。

### G2 自动交付包

- 正式图版本与路径：
- 自动 QA 结果：
- 自动返修记录：
- Build Pack 完整性：
- 最终文件存在性、规格与 SHA-256：
- G2 状态：not_ready / blocked / ready
- G2 阻断项：

> 正式图生成后自动运行 QA、必要返修、路径检查和 Build Pack 组装。G2 不再询问“是否开始 QA”“是否接受 QA”“是否确认路径”；只有未达到 QA、权利、来源或文件完整性要求时才报告阻断。

## 3. Authorization

### Standing authorization

用户明确要求“制作、生成、做、落地”等实际产出时，记录范围内 standing authorization。它不是发布权利声明，也不能覆盖失效字段、越界用途或缺失权利。

- authorization_id：
- 来源消息/版本：
- 授权动作：
- 作用范围：
- 允许的自动重试/单变量返修：
- 不包含的动作：
- effective_from：
- invalidated_by：
- status：active / inactive / out_of_scope

### 动作授权矩阵

| 动作 | direct | guided | controlled | 当前状态 | 证据 |
| --- | --- | --- | --- | --- | --- |
| 生成正式图 | 请求字段有效后 | G0 有效后 | G1 有效且 asset release 成功后 |  |  |
| 生成候选资产 | 按需后台执行 | 按需后台执行 | G0 有效后 |  |  |
| 自动 QA / 返修 | 正式图后 | 正式图后 | 正式图后 |  |  |
| 构建 asset release | 不适用 | 不适用 | G1 拍板后自动执行 |  |  |
| 公开/商业发布 | 取决于权利字段 | 取决于权利字段 | 取决于权利字段 |  |  |

## 4. Provenance

每个关键字段只引用可定位的来源，不把生成结果、后台推测或旧确认反写成用户事实。

| field_id | 当前值/文件 | 来源类型 | 来源位置/消息 | 来源版本 | 确认门 | 责任角色 | SHA-256/引用 | 备注 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

来源类型只使用：user_request / user_confirmation / authorized_reference / generated_candidate / deterministic_build / role_inference / unknown。

### 事实边界

- 已确认事实：
- 当前假设：
- 合理推测：
- 未知：
- 禁止冒充确认的内容：

## 5. Effective Validity

只让发生变化的字段及其依赖失效；保留不受影响字段、来源和历史版本。恢复时从最早无效门续接，不默认全项目归零。

| field_id | 当前版本 | depends_on | effective_from | valid_until / invalidated_by | status | 受影响下游 | 恢复动作 |
| --- | --- | --- | --- | --- | --- | --- | --- |

状态只使用：effective / pending / invalid / superseded / unknown。

### 失效与恢复日志

| 时间/轮次 | 新条件/变化 | 直接失效字段 | 连带失效字段 | 保留字段 | 返回门 | 恢复证据 |
| --- | --- | --- | --- | --- | --- | --- | --- |

### 恢复快照

- 已恢复 workflow_mode：
- 已恢复 blocking_confirmations：
- 已通过且仍有效的门：
- 最早无效门：
- standing authorization 状态：
- 可复用资产与 release：
- 不得从聊天猜测的字段：

## 6. Creative Brief 与内容合同

- 项目名称：
- 一句话目标：
- 比例/尺寸/格式：
- 语言与精确文字：
- 必须条件：
- 避免项：

| 单元/格 | 内容功能 | 可见事件/信息 | 精确文字 | 阅读顺序 |
| --- | --- | --- | --- | --- |

### 角色合同

| 角色 | 证据来源 | 身份不变量 | 故事职能 | 核心性格 | 动作强度 0–3 | 允许表情/动作 | 禁止表情/动作 | 说话方式 |
| --- | --- | --- | --- | --- | ---: | --- | --- | --- |

### 分格/分区角色矩阵

| 格/区 | 发起者 | 解释者 | 反应者 | 动作强度 | 道具归属 | 连续性变化 | 合同冲突 |
| --- | --- | --- | --- | ---: | --- | --- | --- |

## 7. 视觉规格与资产

- 时间/场景：
- 风格/媒介：
- 构图与阅读方向：
- 色板与颜色语义：
- 文字预算与安全区：
- Character Fidelity Gate：
- Style Fidelity Gate：
- 风格合同版本：
- asset-board-spec 版本：

| 资产 ID/文件 | 类型 | 唯一主要职责 | 必须保持 | 权利范围 | 合同版本 | 状态 | 失效条件 |
| --- | --- | --- | --- | --- | --- | --- | --- |

### Asset release（controlled）

candidate_preview 只进入 G1，不是正式生成输入。G1 拍板后，系统自动把被选择的候选升级为 approved，校验权利、合同与 SHA-256，重建 release 三件套；失败则 G1 的下游有效性为 invalid，不增加第三次用户确认。

- G1 选择的候选版本：
- release manifest：
- release annotated：
- release clean groups：
- release build report：
- approved 资产与 SHA-256：
- registry_eligible：
- release status：pending / released / invalid
- 失败原因：
- 复现命令：

## 8. 生成路线与提示词

- 路线：快速 / 稳定 / 编辑
- 选择原因：
- 草稿档/精修档：
- 候选数量：
- 回退条件：
- 编译结构：[主体与身份锚点] + [动作/表情/状态] + [场景与对象关系] + [构图/视角/版式] + [风格/媒介] + [文字与技术约束]

### 完整提示词

### 分格/分区提示词

### 精确文字

### 保留项

### 避免项

### 执行参数

### Prompt Change Log

| 变换 | 来源字段 | 原因 | 是否改变语义/身份/权利 | 有效性影响 |
| --- | --- | --- | --- | --- |

## 9. 生成与返修记录

| 版本 | 子阶段 | 工具/模型 | 输入 provenance | 单变量变更 | 输出路径 | 结果 | effective validity |
| --- | --- | --- | --- | --- | --- | --- | --- |

## 10. 自动 QA（并入 G2）

| 维度 | 得分 | 证据/问题 |
| --- | ---: | --- |
| 创意、故事或信息表达准确性 | /25 |  |
| 构图、层级与阅读性 | /20 |  |
| 主体、角色或产品一致性 | /15 |  |
| 文字、数据及领域语义准确性 | /15 |  |
| 风格与视觉完成度 | /15 |  |
| 技术规格与交付完整性 | /10 |  |
| 总分 | /100 |  |

- 硬失败：
- 自动 QA 结论：
- 最早责任字段/门：
- 自动返修轮次：
- 返修后复验：
- G2 是否 ready：

## 11. 权利与发布状态

- 已确认可用：
- 用户声明：
- 无法验证：
- 发布阻断项：
- 发布授权是否在 standing authorization 范围内：否，需单独由权利字段决定
- 提醒：

## 12. 正式交付

| 文件 | 规格 | SHA-256 | 用途 | provenance | effective validity | 是否复现必需 |
| --- | --- | --- | --- | --- | --- | --- |

- 最终保存路径：
- 正式图版本：
- Build Pack 路径：
- 复现必需的 release clean groups / manifest / report：
- 复现必需的阶段文件与审核：
- G2 完整性检查：
- 项目状态：

### 可选：Seedance 2.0 动画化交接

- 图片素材职责：
- 动作与表演意图：
- 镜头顺序：
- 转场与连续性：
- 必须保持的主体、构图与文字：
- Seedance 提示词：

## V5.3 漫画展示排字证据（适用时）

- G0 `typography_profile` 与显示语义：
- 美术指导 `typography_contract`：字体文件、SHA-256、权利状态、字重、层级与最小尺寸：
- 实际几何的 `locked_lines`、光学偏移与安全轮廓：
- 执行场记排字构建报告：字体哈希、字号、行组、对齐、占位、蒙版：
- 独立适配报告：几何检查和 `typography_checks`：
- 图片总编逐元素裁切证据与结论：

## V5.4 ???????????

### Production profile

- profile?fast / balanced / quality
- selected_by?agent_recommendation / user_selection / user_confirmed
- recommended_agent_model?
- recommended_reasoning_effort?low / medium / high
- recommended_generation_route?fast / stable / edit
- active_agent_model?????????????
- active_reasoning_effort?????????????
- active_runtime_verified?true / false

### G0 ??????

| ?? | ?? | required / optional / skipped | ?? | ?? | ????/?? | ???? | ???? |
| --- | --- | --- | --- | ---: | --- | --- | --- |

### ??????

- generation-request ??? SHA-256?
- ????????
- avoid / negative?
- ???
- clean references??? / ?? / SHA-256??
- visual-bible / asset-plan / prompt-pack ???
- generation-log ???????

### ????? ZIP

- G2 ???????delivered_pending_acceptance / blocked
- ????????????????
- client acceptance?not_requested / pending / accepted / revision_requested
- G2 ????? SHA-256?
- handoff ZIP ???SHA-256?????
- handoff-manifest ???
- ??????/??/??/??????
