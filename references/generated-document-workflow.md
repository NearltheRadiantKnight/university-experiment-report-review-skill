# 生成文档与本地 Dashboard 工作流

## 目标

本工作流把 Codex 的语义判断与确定性的本地文档处理分开。Codex 负责读取实验要求、报告文本、表格和截图，判断原文是空白、部分完成还是已完成，并生成结构化修改计划。Python 脚本只执行计划：从原始 DOCX 打开文档，在指定段落后插入带颜色标记的新内容，保存新的 DOCX，并通过本地网页提供下载。任何脚本都不会调用模型 API。

## 输入限制

要得到“原文保持原字体、新内容使用异色字体”的可编辑文件，源文件必须是 `.docx`。PDF、图片和文本仍可用于分析，但 PDF 的字体、段落结构和嵌入对象无法可靠地无损转换为可编辑 DOCX。因此，对 PDF 输入应先让用户在本地另存为 DOCX；无法转换时，输出独立审阅报告并明确不能保证原字体保留。

## Codex 生成计划

Codex 在完成审阅后写出 UTF-8 JSON，结构见 `assets/generation-plan.schema.json`。空白模板使用 `report_kind: execution`，已完成或部分完成报告使用 `report_kind: revision`。计划中的每条 `addition` 都是新增内容，不能包含伪造的实验结果、测量值、截图描述或教师要求。

定位优先使用稳定的 `anchor_text`，例如“实验步骤”“实验结果”“结论”。同一标题出现多次时用 `occurrence` 指定第几次。只有在已读取当前 DOCX 并获得稳定段落顺序时才使用 `paragraph_index`。锚点默认严格匹配；找不到锚点时生成失败并要求修正计划。只有明确属于附录或提交清单的内容才使用 `position: append`，并由 `appendix_title` 命名。

## 空白文档：实验执行报告

空白模板中的新增内容应回答：实验要证明什么、开始前准备什么、真实执行顺序是什么、每一步保留什么证据、各章节如何写、提交前如何检查。命令或参数如果依赖课程专用环境，必须写成“根据任务书确认”，不能补一个看似合理的值。执行报告是指导文档，不应冒充已经完成的实验报告。

推荐类别：`guidance` 用蓝色表示执行动作，`evidence` 用青色表示截图与数据要求，`writing` 用紫色表示章节写法，`warning` 用橙色表示安全、环境和禁止虚构事项。长流程使用 `checklist`，截图要求使用 `bullets` 或 `checklist`，测试用例与要求—证据映射使用 `table`。

## 已完成文档：修改报告

修改报告保留所有原文，在相关段落后插入审阅标记。`issue` 用红色指出问题和影响，`suggestion` 用蓝色给出修改动作，`example` 用绿色给出不含虚构数据的表达示例，`praise` 用紫色标记应保留的优点。不要直接替换学生原文，也不要为了显示修改而强行挑错。若报告已经足够好，计划可以只增加提交判断和少量可选润色。

## 原样式保护

生成器不修改文档的 `Normal` 样式，不遍历或重设原有 run 的字体、字号、颜色、粗体、下划线和段落样式。新增段落继承相邻段落的段落级样式以保持排版位置一致，但新增 run 会显式设置字体、字号和分类颜色，并以“【Codex 新增·类别】”开头。这样既能保留原文视觉状态，也能让用户一眼区分机器新增内容。

需要注意，`python-docx` 对 Word 的高级对象并非完全无损，例如复杂域、部分 SmartArt、宏和某些第三方扩展。生成前始终保留原文件，输出写入新文件，绝不覆盖源文档。宏启用的 `.docm` 不在支持范围内。

## 单命令执行

完成计划后运行：

```powershell
python scripts/run_pipeline.py --source "<原始报告.docx>" --plan "<generation-plan.json>" --output-dir "<输出目录>"
```

流水线依次执行计划质量门禁、结构化文档生成、行动清单生成、确定性质量检查、元数据登记、Dashboard 启动和浏览器打开。页面固定绑定 `127.0.0.1`，默认端口 `8765`。测试或无界面环境使用 `--no-open`。端口冲突时传入 `--port 8766` 等其他本地端口。

## Dashboard 安全边界

Dashboard 没有上传接口，不接收任意文件路径，也不调用 Codex。它只读取流水线写入输出目录的 `*.metadata.json`，并只允许下载元数据中登记且确实位于同一输出目录的 DOCX。服务绑定环回地址，不向局域网公开。

页面展示最新结果、报告类型、原文件名、原始状态、提交判断、新增条目数量和历史结果。下载按钮返回生成后的 DOCX。上传和语义分析仍发生在 Codex 对话中，这是在不接入 Codex API 的前提下保持模型能力和本地隐私的关键边界。

## 故障处理

- 找不到锚点：默认停止生成并修正计划；不得静默创建“未定位内容”区。
- 源文件不是 DOCX：停止生成，要求本地转换；不得假装保留了 PDF 字体。
- 输出文件被 Word 占用：关闭文件后重试，或使用新的输出目录。
- 页面没有结果：确认输出目录包含成对的 DOCX 与 metadata JSON，并刷新页面。
- 端口被占用：指定新的 1024—65535 端口。
- 浏览器未自动打开：手动访问命令输出的 `http://127.0.0.1:<port>`。
- Word 高级对象异常：使用原始文件恢复，并把生成结果作为审阅副本而非唯一版本。

## v1.2 Structured Delivery

Each successful run emits an annotated report, a companion action checklist, a quality JSON file, and metadata. The Dashboard exposes all registered files through loopback-only routes. `include_summary_appendix` is false by default to prevent repeated verdict pages. Numeric scoring is rejected unless `rubric_provided` or `score_requested` is true and `scoring_basis` is present.

The same contract applies in Codex, Claude Code, OpenClaw, and other AgentSkills clients. Agents supply semantic judgment; local Python remains deterministic and model-independent.
## v1.4 Single-Document Contract

- Confirm `time_budget` before creating the plan; default to `full` only when interaction is unavailable.
- Generate one user-facing annotated DOCX. Keep quality JSON, render PDF, and preview images as machine-only local artifacts.
- Append one consolidated review appendix containing the traffic-light signal, up to five budgeted actions, false-completion findings, contamination findings, screenshot evidence, retake instructions, and automatic QA.
- Show only the traffic light, budget, priority actions, screenshot cards, and main DOCX download by default in the dashboard; keep deeper checks collapsed.
