# 阶段门与确认协议

## 目录

- [用户侧项目栏](#用户侧项目栏)
- [G0 / G1 / G2](#g0--g1--g2)
- [如何判断拍板](#如何判断拍板)
- [状态事件与产物绑定](#状态事件与产物绑定)
- [何时可以直接生成](#何时可以直接生成)
- [字段级失效传播](#字段级失效传播)
- [全程审片兼容模式](#全程审片兼容模式)
- [图片生成后的续接](#图片生成后的续接)

## 用户侧项目栏

项目回复以精简项目栏开头；首次团队介绍之后每轮都使用，但不要展示无关内部字段：

```text
build-image-fast｜连续性制作
对接窗口：图片总编
本轮主讲：美术指导
当前任务：视觉锚点
用户决策：G1 待拍板
预计正式成图前还需你拍板：1 次
执行方式：实际 Sub Agent 接力
```

显示名与枚举映射：

- `atomic`＝单点调用；`direct`＝快速委托；`guided`＝标准协作；`controlled`＝连续性制作；`edit`＝单变量快修。
- `physical_subagents`＝实际 Sub Agent 接力；`serial_roles`＝单 Agent 串行专业分工。
- 没有用户决策时写 `用户决策：无，团队继续执行`，不得制造确认问题。
- 只有用户查看状态或排障时才附 `后台阶段：N/8`、产物版本、revision、哈希或失效节点。

## G0 / G1 / G2

### G0 creative_lock

把用途与发布范围、核心表达、故事/信息结构、精确文案、角色职责/行为边界、推荐视觉方向和关键假设合成一个决策包。负责人给出明确推荐和理由；需要用户决定的项目最多三项。

`guided` 与 `controlled` 必须有有效 G0；`direct/edit` 只有在执行中暴露新的中高风险决定时才打开 G0。

### G1 visual_anchor_lock

只在 `controlled` 启用。一次提交：

- 分项角色、风格、道具或场景候选；
- 带字资产总览与任务相关的关键无字参考；
- 标签语义、角色/产品归属和合同版本；
- 身份、表演与风格压力测试摘要；
- 未通过项、剩余风险和美术指导建议。

用户一次拍板资产图片、标签语义、角色/风格边界和测试结论。执行场记随后重建 release 三件套；仅批准元数据变化且自动等价检查通过时，不再要求一次 release 确认。视觉或语义内容变化必须重开 G1。

### G2 delivery

图片总编自动提交通过 `QA >= 85` 且无硬失败的最终图、QA 摘要、已知限制和 Build Pack，并把状态设为 `已完成`。不再询问“是否接受 QA”“路径是否正确”或“是否可以完成”。用户要求返修时按字段影响重开项目，而不是把原 G2 删除。

## 如何判断拍板

把明确指向当前 G0/G1 的“确认、OK、通过、采用推荐、就按这个做”等自然语言记录为 `user_confirmed`。用户不需要复述版本号；系统将确认绑定到当前决策包版本、字段指纹和锁定项。

以下不算拍板：只提出修改、只回答补充问题、“继续看看”“再来一个”“大概可以”或未明确选择存在实质差异的方案。修改先形成新值和新指纹，再等待当前所需决策；不要同时把该句写成旧版本确认。

把“按推荐方案推进，其他可逆细节你决定”记录为 `delegated_decision`、委托范围和原始话语。团队自行决定的可逆细节记录为 `agent_decision`；证据不足但不阻塞的缺口记录为 `assumption`。四者不得混写：

- `user_confirmed`：用户明确锁定的字段；
- `delegated_decision`：用户授权团队在指定范围内代决；
- `agent_decision`：无需询问且团队自行确定；
- `assumption`：尚未验证、可能被新证据推翻。

同值重复提交是幂等操作：不升级版本、不追加新的实质确认、不失效下游。只有字段值、语义或适用范围变化才创建新版本。

## 状态事件与产物绑定

确认事件必须保存不可变快照，而不只保存 ID：

- 每个决策的 `record_fingerprint` 必须覆盖 `id`、`gate`、`field`、`source`、值 `fingerprint`、完整 `depends_on` 和逐边 `dependency_fingerprints`；
- `decision_ids`、`decision_fingerprints` 与 `decision_record_fingerprints` 一一对应；确认后改 ID、关口、字段、来源、值或依赖边都会使旧事件失效；
- `artifact_ids` 与对象形式的 `artifact_fingerprints` 精确对应，例如 `{"ART-PREVIEW":"<sha256>"}`；
- 无产物的 G0 事件也必须显式写 `artifact_fingerprints: {}`；
- `user_confirmed` 和 `delegated_decision` 的 actor 只能是 `user`，`system_validation` 只能来自 `qa_system` 或 `system`。

`standing_authorization.source` 只能来自 `user_request`、`user_confirmed` 或 `migrated_user_confirmation`。启用委托时，`delegation_scope` 必须同时记录 `authorized_by=user` 和用户来源，并永远把 `rights_scope` 放入 excluded；团队决定、假设或系统字段不能自我授权。

当前生成产物必须带 `candidate_set_id`。同一套分项角色、preview、压力测试、release 和正式图共享同一 set；`max_candidates` 按不同 set 计数，不能把一套内的多张分项资产误算成多个候选。正式图还必须带 `deliverable_slot_id`，同一 `(deliverable_slot_id, candidate_set_id)` 最多一个当前有效正式图；不同页面 slot 可以共享同一候选套件。

`asset_board_spec.value` 必须以 `dependency_fields` 与 `excluded_g0_fields` 完整、无重叠地划分当前 G0 字段。只有显式白名单 `exact_text`、`exact_copy`、`dialogue_text`、`caption_text`、`lettering_text`、`title_text`、`body_copy` 可以排除；不按前后缀猜测字段语义，`copy_character_identity`、`character_copy`、权利、角色、风格、产品、品牌、身份、行为、标签及未知字段一律 fail closed。G1 决策只直接依赖 included G0；preview、适用压力测试和 release 依赖 G1 加 included 闭包；正式图仍依赖全部当前必需 G0/G1。因此只改精确文案时保留 G1/release，但必须失效正式图及文字 QA。

生产读取 `project-state.json` 时，当前非 planned 的生成产物、QA 和 Build Pack 文件必须位于项目根目录内、真实存在，且文件 SHA-256 等于状态指纹。正式图还必须由 Pillow 成功解码并通过 `verify()`，检查结果记录真实 format、width 和 height；Pillow 缺失、任意字节伪装或损坏图片均 fail closed。G2 的正式图、QA 和 Build Pack 不允许只登记占位记录。

已解决且适用的 `rights_lock` 必须直接引用当前有效的 `rights_scope` 决策，来源仅允许 `user_input` 或 `user_confirmed`，不能用委托、Agent 建议、假设或系统字段代替。

## 何时可以直接生成

用户明确要求制作或生成图片时，记录 `standing_authorization`，默认覆盖当前推荐流程的一张候选：

| 模式 | 生成前条件 |
| --- | --- |
| `direct` | 风险审计通过后直接生成，无额外拍板 |
| `guided` | G0 有效后直接生成 |
| `controlled` | G0 后可生成候选资产与压力测试；G1 有效后生成正式图 |
| `edit` | 变更/保留范围清楚且无阻断时直接编辑 |

额外候选、更高成本档位、外部发布或跨项目复用超出 standing authorization，必须另行授权。提示词、普通参数、文件名、哈希、清单字段和进入 QA 不构成独立确认门。

## 字段级失效传播

保留不可改写的 `confirmation_history`，从当前字段值和依赖计算 `effective_validity`。只失效真实依赖，不按阶段整段清空：

| 变化字段 | 必须失效的典型依赖 |
| --- | --- |
| 精确文案/数据 | 文字预算、排字、相关提示词、受影响成图、文字/语义 QA |
| 比例/尺寸 | 画布、版式、安全区、构图提示词和候选图 |
| 角色行为/故事职能 | 该角色合同、受影响分格矩阵、相关提示词、压力测试和成图 |
| 角色视觉身份/风格 | 相关锚点、三件套节点、压力测试、提示词和成图 |
| 资产源图/裁切/标签/归属 | 对应 manifest、annotated、clean group、引用它们的提示词和成图 |
| 权利范围/发布用途 | 权利结论、受影响生成授权、registry 资格和发布交付 |
| 模型路线/候选数 | prompt-route、执行计划和之后生成的候选；不自动失效内容合同 |
| QA 标准 | 相关 QA 和交付状态；不自动失效源资产 |

依赖缺失、循环或含糊时 fail closed：把相关整项和其下游设为待重新验证，并报告原因；不得猜测性继承。V4 迁移保留历史确认事件，只重算有效性。

## 全程审片兼容模式

`review_mode=full_review` 时，按八阶段分别等待用户通过：需求边界、创意方向、内容结构、视觉规格、提示词路线、候选、QA、交付。用户对某阶段提出修改时留在该阶段，不能把修改当确认。切回 `adaptive` 后按当前风险重算 G0/G1，已有效且字段等价的确认不重复询问。

全程审片是用户提高控制强度的偏好，不是取消 QA、权利、保真或非覆盖合同的途径。

## 图片生成后的续接

内置图片生成结束回复后，下轮先读取状态和输出：

- 用户给出明确返修意见：按 `edit` 或最早责任字段处理。
- 用户说“继续”：自动执行候选检查、QA、必要的安全单变量返修和 G2，不要求先批准进入 QA。
- 用户未选定多候选中的一个：只有候选确有实质差异时才请求选择；默认单候选不制造选择关口。

适用权利未解决、关键输入缺失、精确文字无法可靠排版或工具/凭据缺失时设为 `受阻`。说明已完成内容、影响和解除阻断的最小动作，不用增加确认次数代替解决阻断。

## V5.3 排字决策的门控位置

comic_display 不是新增用户确认门。G0 由内容与角色导演把 typography_profile 与显示语义合同一并提交；用户确认的是可见内容和所选视觉方向，而不是字体路径或脚本参数。G1 由美术指导一次提交资产锚点与 typography_contract 摘要，包括字体权利状态、层级、容器容量和剩余风险。无字底图后的实际几何/行组审核属于 G1 下游的后台专业交接，不追加用户拍板。

项目栏固定包含：当前阶段、已完成、待确认事项、下一步、确认后的流程。没有待决策时，明确写“无，团队继续执行”；不得以确认提示词、确认 QA 或确认路径代替真实问题。

## V5.4?G2 ???????

?????????G2 ???????????G2 ???????? QA????????? Build Pack ????????? `delivered_pending_acceptance`??? QA ?????????

??????????????`???????????` ????????????????????? Build Pack ? `G2/user_confirmed` ??????? `handoff_archive` ?????????????? `G2/user_feedback`??????QA?Build Pack ????????????????????????????????????????? 0/1/2????? G0/G1?
