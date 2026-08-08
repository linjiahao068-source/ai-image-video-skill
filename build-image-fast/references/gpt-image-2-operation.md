# GPT Image 2 精确执行

只有用户明确要求模型、API 或 CLI 参数时，才走已安装 `imagegen` Skill 的 CLI/API 路径。普通任务继续使用内置 `image_gen`。

- 调用 `imagegen` Skill 已有的 `scripts/image_gen.py`，不要复制或修改脚本。
- 默认模型为 `gpt-image-2`；不要静默切换模型。
- `gpt-image-2` 的图片输入始终高保真，不设置 `input_fidelity`。
- 草稿可用 `quality=low`；精确文字、图表、身份敏感或最终图使用 `medium`、`high` 或 `auto`。
- 参数可能变化；执行前以当前 `imagegen` Skill 的 `references/image-api.md` 和 `references/cli.md` 为准。
- CLI/API 需要 `OPENAI_API_KEY`。缺失时要求用户在本机设置，不在聊天中索要完整密钥。

常见尺寸包括 `1024x1024`、`1536x1024`、`1024x1536`、`2048x2048`、`2048x1152`、`3840x2160`、`2160x3840` 和 `auto`。执行前复核当前模型限制，输出非覆盖版本文件。

本地参考图在内置模式下先用 `view_image` 查看；CLI 模式按 `imagegen` 的文件输入参数执行。每张图只承担一个主要职责。
