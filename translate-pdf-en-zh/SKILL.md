---
name: translate-pdf-en-zh
description: Translate an English PDF into a side-by-side bilingual PDF with the original English page on the left and its Chinese translation on the right. Preserve white backgrounds, graphics, page geometry, and approximately matching typography and text positions. Use for 英中对照 PDF、左英文右中文、保留原版式的 PDF 翻译.
---

# 英中对照 PDF 翻译

## 输出约定

- 默认翻译全文为简体中文；用户指定繁体、页码范围或术语时遵从用户。
- 每个原文页对应一个输出页：**左侧英文原页，右侧该页中文版**，同页并排，而非交替页或上下排。两侧各保持原页 1:1 物理尺寸，默认无额外间隔。因此 A4 竖页产生约 A3 横页的对照页，不为强塞进 A4 而缩小两侧。
- 左侧直接嵌入原页，保留原始内容、图形和字体，不重新打字、不翻译、不裁边。原文件只读，另存输出。
- 右侧复用原页图形与布局，替换英文文字；保持白色页面背景。不另加底色、装饰、标题栏、水印或说明页。原图表、色块、标识的颜色不是页面底色，不随意改白。若原件本身不是白底，识别冲突并说明，不能宣称两项都原样保留。
- 中文的文本框位置、对齐、字号、层级和视觉密度尽量匹配原文。选择风格相近的可嵌入中文字体，不强用缺少中文字形的原英文字体；不承诺像素级相同。
- 默认交付 `<原文件名>_英中对照.pdf`。独立中文版仅按需交付，中间 JSON、图片不混入交付文件。

## 1. 检查原稿

定位实际 PDF，记录页数、尺寸、CropBox、旋转、文字可提取性及字体。渲染查看首页和所有特殊版式：多栏、表格、密集脚注、图片文字、公式和横向页。不能只依据提取文本判断版式。没有输入 PDF 时请用户提供文件，不虚构内容。

用 `scripts/pdf_layout.py extract` 提取坐标、字体、行和待译块到 JSON。脚本依赖 Python 3.10+、`PyMuPDF>=1.26,<2`；先检查当前或 bundled Python，缺少时只安装所需依赖。脚本不调用翻译 API，语义翻译由执行技能的模型完成。

```text
python <skill-dir>/scripts/pdf_layout.py extract input.pdf work/layout.json
python <skill-dir>/scripts/pdf_layout.py render input.pdf work/original --dpi 120
```

JSON 页码从 1 开始；坐标为规范化旋转后的可见页面坐标，单位 pt，左上角为原点，不能与未规范化 PDF 坐标混用。`needs_visual_review` 是风险提示，不是扫描件/空白页的最终判定。

数字原生文字优先在原页副本上局部替换。扫描件、隐藏 OCR 层、文字转曲和复杂混排，阅读 [references/complex-layouts.md](references/complex-layouts.md)，选择 OCR 或局部重建，不对整份文件一律栅格化。

## 2. 翻译并对应原位置

按语义段落、标题、列表项、表格单元格和图注翻译，不以每行硬切句子。先理清多栏顺序、跨页段落和连字符断词，再回填各页区域；不移动页间内容来逃避排版问题。

建立一致术语表，忠实保留否定、条件、数值、单位、范围、交叉引用和脚注编号。正文、页眉页脚、图表标题、轴标签、图例、表头、脚注均需检查。公式、代码、URL、DOI、型号、变量和专有名称按语义保留，公式旁解释仍需翻译。参考文献作者、期刊名、DOI 可保留原文，必要时翻译标题，避免破坏可检索性。

每个提取块标为 `action: "translate"` 并填入 `zh`，或标为 `action: "keep"` 并填写 `reason`。`keep` 只用于语义上应保留的内容；排版困难不能作为漏译理由。保留原始 `id`、`source`、`bbox`、`lines` 和文件哈希。图片内文字另外核查，“提取结果全部已译”不等于全文完整。

## 3. 在原布局中排中文

衬线正文优先宋体/思源宋体，无衬线正文优先微软雅黑/思源黑体；标题对应粗体字体文件。使用实际存在、覆盖全部目标字符且可合法嵌入的字体，不强行全页一种字体。字段说明见 [references/layout-manifest.md](references/layout-manifest.md)。

优先保持原字号、左上锚点、栏宽、对齐和段间距。空间不足依次尝试：完整语义的精炼译文、自然中文换行、合理调整行距、在邻近空白内微调文本框。最后才小幅调整字号，默认不低于原字号的 90%；原本极小的脚注不再缩小。不允许裁字、省略、重叠、横向压扁中文或把正文缩到难读。

普通水平、单样式文本可运行：

```text
python <skill-dir>/scripts/pdf_layout.py apply input.pdf work/layout.json work/zh.pdf --font <中文字体文件>
```

`apply` 用精细文本区域移除原文，保留图像和矢量图形，再嵌入中文。未完成翻译、无法容纳、字符缺失或不支持的布局会报错，不输出缺字成品。混合粗斜体、复杂表格、上下标、旋转文字或扫描页需要定制局部排版，不能通过随意 `keep` 或删块绕过。先移除所有目标英文再写入中文，防止后续移除操作误删译文。

## 4. 左右拼页

中文版完成且逐页核对后执行：

```text
python <skill-dir>/scripts/pdf_layout.py pair input.pdf work/zh.pdf output/原文件名_英中对照.pdf
```

脚本验证页数及每对页面尺寸，创建白底双宽页面，矢量嵌入两侧；混合尺寸逐页处理。输出是静态阅读副本，批注/表单保留可见外观，原文件仍保留其交互内容与签名。不声称合成件保留数字签名有效性或全部交互功能。

## 5. 渲染验收后交付

```text
python <skill-dir>/scripts/pdf_layout.py render output/原文件名_英中对照.pdf work/final --dpi 140
```

逐页检查顺序对应、白底、内容齐全、表格线完整、中文无乱码/方框、无裁切/重叠、图表和脚注仍在原位。长文档先生成全页联系表逐页扫查，再放大所有密集或异常区域，不能只看首页。另核对源页数等于对照页数、每侧尺寸、数值公式及术语。

`pair` 比较左半页与原页的渲染，差异超阈值就失败；通过该检查仍需检查右侧。扫描件 OCR 错字及遗留图片英文也必须核查。

发现问题就修正并重渲染。只有实际通过检查的文件才称完成；不能完全恢复的局部版式在交付说明中指出具体页码及差异，不在 PDF 内擅自加说明。
