# 显示合同、实际轮廓与确定性排字

适用于任何含可见文字、标签、标牌、气泡、数据标注或重复 UI 的图片。它不是额外用户确认门：只把已经决定的可见语义、真实容器几何和像素证据串成可验收链。

## 何时启用

- 任何精确文字或数据：建立 `display_semantics` 与 `exact_text`。
- 普通矩形标题、页脚、海报 CTA：`profile=simple_rect`；沿用视觉规格的固定安全框。
- 气泡、尾巴、弧形标牌、篮子牌、曲面 UI、重复标签：`profile=actual_shape`；自动升级到足以覆盖版式风险的流程，并在无字底图后建立实际轮廓合同。
- 不含文字或标签 UI：标记不适用，不增加步骤。

## G0：内容与角色导演的显示合同

把“画面里什么必须显示”与“每个位置显示哪一段字”分开锁定：

- `display_semantics`：元素 ID、格/区、目标对象、容器是否出现、文字模式、最大行数、重复组与规则。
- `exact_text.strings`：仅按 `text_key` 保存逐字内容。

每个计划中的可见文字或标签容器都必须是 `required` 或 `forbidden`，不能使用“可有可无”。`required + text_mode=none` 只有在显式 `blank_container_allowed=true` 且写明原因时才合法；否则空白标签是硬失败。

```json
{
  "profile": "actual_shape",
  "elements": [{
    "id": "p2-basket-plaque",
    "panel_id": "p2",
    "target_object": "etf-basket",
    "container_presence": "required",
    "text_mode": "exact",
    "text_key": "basket_etf",
    "max_lines": 1,
    "repeat_group": "etf-basket-plaque",
    "repeat_rule": "same_text"
  }]
}
```

```json
{
  "strings": {"basket_etf": "ETF"}
}
```

`same_text` 要求同组元素使用完全相同的逐字文本；`same_presence` 要求同组容器同时出现或同时不出现；`independent` 必须显式选择。标签、容器存在性或重复规则变动是语义变化，回到 G0；仅改文案且仍在既定容量内，只重做排字和下游正式图。

## G1 与无字底图：美术指导的职责

美术指导在视觉规格中先定义容器容量、最大行数和预留空间。`controlled` 项目将这些规则同资产锚点一起交付 G1；不新增 G1 以外的用户拍板。

执行场记只生成无字视觉底图，并禁止模型生成合同外的空白标签/UI。底图完成后，美术指导必须对每个 `actual_shape` 元素提交 `layout-geometry-contract.json`，绑定底图 SHA-256，包含：

- 实际容器多边形；
- 尾巴、弧边、边框、装饰等排除多边形；
- 最小安全边距；
- 最终安全多边形与排字框；
- 对底图容器是否实际出现的观察。

底图未提供足够容器容量、出现合同外空白标签，或容器位置不正确时，先返修无字底图；不得靠缩写已锁文案、把字移到气泡外或让执行场记自行删标签来通过。

## 执行、验证与 QA

执行场记使用：

```text
assemble_lettering.py --base <no-text.png> --display-contract <display.json>
  --geometry-contract <geometry.json> --font <font> --output <formal.png>
  --mask-dir <masks> --report <lettering-build-report.json>

validate_lettering_geometry.py --base <no-text.png> --final <formal.png>
  --display-contract <display.json> --geometry-contract <geometry.json>
  --build-report <lettering-build-report.json> --output <lettering-fit-report.json>
```

验证器要求每个锁定文本均被逐字编译、字体包含对应字形、所有文字像素均留在安全多边形内，且正式图在文字蒙版之外不改变无字底图。

图片总编随后独立 QA：逐个比对显示合同、检查容器实际存在性、文字与标签语义，并为每个元素保存裁切证据和 SHA-256。任何文字越界、尾巴/弧边碰撞、空白必需标签、合同外空白 UI、重复标牌不一致、缺少证据裁切均为硬失败，G2 必须阻断。

## 状态与速度

V5.2 的文字正式图必须绑定 `lettering_base_image`、美术指导的 `layout_geometry_contract`、执行场记的 `lettering_build_report` 和 `lettering_fit_report`。QA 与 Build Pack 直接依赖适配报告。

该链只在含文字/标签时启用；`simple_rect` 不要求额外人工轮廓步骤，`actual_shape` 才增加一次无字底图后的美术几何审核。全程不增加用户确认次数。

## V5.3：漫画展示排字

V5.3 在现有显示合同之上增加按项目选择的 typography_profile。新 V5.3 文本项目必须显式记录 standard 或 comic_display；后者还要求每个元素具备 semantic_role（dialogue、primary_anchor、object_label、footer）与 reading_priority。

comic_display 的 G1 必须有美术指导交付的 typography_contract：字体文件、SHA-256、商业/内部使用范围、权利状态，以及各语义角色的字重、颜色、描边、对齐、垂直锚点、最小字号、最小视觉占位与行距。无字底图后，实际几何合同中每个元素必须追加 locked_lines 和 optical_offset_px。locked_lines 去除换行后必须逐字等于 G0 文案。

排字器以该合同为唯一来源：商业范围的字体权利不是 confirmed、字体文件或哈希不符、合同字体被命令行覆盖、字号低于下限、行组/占位/光学居中失败，均 fail closed。文字仍须完全位于实际安全多边形中；不会通过缩写、移出气泡或删除标签绕过失败。
