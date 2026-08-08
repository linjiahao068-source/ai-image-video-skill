# V5 资产详情三件套

## 目标与边界

Character 或 Style Fidelity Gate 触发时，资产系统建立同源三件套：

1. `project-asset-master-annotated-v01.png`：确定性排字的带字总览，供用户、Agent 与 QA 阅读。
2. `project-asset-reference-clean-01-v01.png`：不新增标签的生成参考，可按职责拆成多个 clean group。
3. `asset-manifest-v0.x.json`：机器可读的职责、合同、权利、状态、决策与哈希清单。

三件套只提供更强、可审核的视觉锚点，不保证生成模型必然一致。带字总览默认不得作为生图参考；正式生成只传相关 clean group，并把清单硬约束编译进文本提示词。

## G1 一次确认晋级

V5 不再分别要求用户确认分项资产、release 三件套和压力测试：

1. 美术指导锁定 `asset-board-spec`、标签语义、归属、合同、权利与 clean group。
2. 执行场记生成分项候选，以 `candidate_preview` 组装三件套并完成压力测试。
3. 图片总编在 G1 一次展示带字总览、关键 clean group、角色/风格边界、压力测试摘要和剩余风险。
4. G1 必须由用户确认，事件同时引用当前 `asset_triad_preview` 与适用的已通过 `fidelity_test`；委托决定不能替代高风险视觉锚点确认。两者必须共享同一个当前 `asset_board_spec` 决策指纹。
5. 用户确认 G1 后，执行场记只把批准状态与哈希写入 release 清单，确定性重建三件套。
6. `--baseline-report` 必须解析到 G1 事件所引用 preview 的 `artifact.file`，文件 SHA-256 必须等于该 preview 的 `artifact.fingerprint`，随后再校验 preview→release 等价；仅批准元数据变化时自动晋级，不再次询问用户。

任何源图、规范化图块、标签、归属、合同、权利、布局或 clean group 变化都不是等价晋级，必须重新打开 G1。压力测试通过时只展示摘要；失败或存在真实取舍时才阻塞用户。

## V5 清单接口

模板为 `assets/asset-manifest-template.json`。除 V4 字段外，V5 顶层必须包含：

- `schema_version: "5.0"`；
- `workflow_state_ref`：相对清单或绝对的 `project-state.json` 路径；
- `decision_fingerprint`：当前有效 `asset_board_spec` 决策的 SHA-256；
- `approval_event_id`：候选预览可为空，release 必须引用当前有效的 G1 用户确认事件。

V5 `candidate_preview` 构建前必须有 `standing_authorization.generate_one_candidate=true` 且 `max_candidates>=1`；`controlled` 流程还必须已有有效 G0。该授权是构建前置条件，不得靠清单字段或执行场记自行假定。

`release` 同时要求：受控流程的 G0/G1 有效、项目未阻断、资产全部为 `approved`、清单哈希与源文件一致、G1 事件覆盖 `decision_fingerprint`，并通过候选基线等价检查。旧 V4 清单可继续构建 `candidate_preview`，但不能生成 V5 release 或进入 registry。

`project-state.json` 是确认与有效性的真源；`confirmation_history` 只追加历史事件，`effective_validity` 表示当前有效性。手工把 `approval_status` 改为 `approved` 不能替代有效 G1 事件。每个当前有效的 `asset_triad_release` 都必须自身引用同一 G1 事件、同一 `asset_board_spec` 指纹，并依赖同指纹的 preview 与适用 fidelity test；畸形 release 即使尚未被正式图引用也会硬失败。G1 锚点产物生命周期必须为 `approved`，release 为 `approved` 或 `delivered`。

## 拆分与安全合同

单个 clean group 必须同时满足：

- 最多 8 个视觉槽位；
- 关键资产的输出槽位最短边至少 384px；
- 最多两种 `primary_roles`；
- `contains_text=true` 的资产不得进入 clean group；
- `dedicated_group` 资产只能与同一 dedicated group 的资产同组；
- 资产声明的 `clean_groups` 必须与板内实际成员关系完全一致。

精确产品文字、复杂环境多视角和高风险单角色细节默认独立成组。超限、标签溢出、缺文件、哈希变化、未批准资产、路径逃逸或映射不一致均为硬失败；不得缩小、遗漏或混组绕过。带字总览每个资产卡片最短边至少 384px，中文字体不可用时阻断，不输出乱码。清单只能把这些上限设置得更严格：`max_clean_slots<=8`、`max_clean_primary_roles<=2`、`min_clean_tile_short_side>=384`、`min_annotated_tile_short_side>=384`；放宽硬常量会在构建前失败。

## 执行

先校验状态：

```powershell
& <python> scripts/validate_project_state.py `
  --state <project>/project-state.json
```

构建 G1 候选预览：

```powershell
& <python> scripts/assemble_asset_board.py `
  --manifest <project>/working/asset-manifest-preview-v0.1.json `
  --workflow-state <project>/project-state.json `
  --out-dir <project>/outputs/candidates `
  --font C:\Windows\Fonts\msyh.ttc
```

G1 确认后晋级 release：

```powershell
& <python> scripts/assemble_asset_board.py `
  --manifest <project>/working/asset-manifest-v0.1.json `
  --workflow-state <project>/project-state.json `
  --baseline-report <project>/outputs/candidates/asset-board-build-report-v0.1.json `
  --out-dir <project>/assets/approved `
  --font C:\Windows\Fonts\msyh.ttc
```

`workflow_state_ref` 与 `--workflow-state` 同时存在时必须解析到同一文件。输出仍采取非覆盖保存；失败发生在提交前，不把半成品登记为正式资产。

组装器只保证确定性排版没有向 clean board 新增标签。`contains_text=false` 与报告中的 `clean_source_text_flags_empty=true` 只是资产清单声明，不是像素检查；报告固定记录 `pixel_level_text_absence_verified=false`、`verification_method=not_run`。OCR 或人工逐图检查须在后续 QA 单独执行，未执行时不得声称“无文字残留”。

## QA 硬检查

- 标签、资产 ID、角色/道具归属与清单逐项对应；
- annotated 与 clean 复用同一源文件和规范化图块；确定性排版不向 clean 新增标签；另行执行 OCR 或人工 QA 才能判断源像素是否含字；
- 文件 SHA-256、合同、权利、同一 `asset_board_spec` 决策指纹、G1 用户批准引用和当前有效性一致；
- preview→release 等价快照覆盖画布、分区、标签、职责、资产语义、源哈希、规范化图块和 clean group；
- 正式提示词没有把 annotated 总览当作默认生图输入；
- G2 只接受 `delivered` 的正式图、QA 与 Build Pack；QA 必须依赖并覆盖本次正式图，Build Pack 必须依赖本次全部正式图与通过的 QA，防止旧 QA 或无关 Pack 混入；
- 构建报告明确记录状态哈希、基线报告哈希、等价结论、拆分结果和 registry 资格。
