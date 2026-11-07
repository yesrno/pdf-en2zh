# pdf-en2zh
将英文 PDF 翻译为保留原版式的英中左右对照 PDF

# 安装方式一:
使用Codex的 $skill-installer 安装以下 GitHub 目录中的技能：
https://github.com/yesrno/pdf-en2zh/tree/main/translate-pdf-en-zh

# 安装方式二:手动下载安装
1. 下载技能压缩包并解压。
2. 将其中的 translate-pdf-en-zh 文件夹复制到：
   C:\Users\你的用户名\.codex\skills\
3. 确认最终路径为：
   C:\Users\你的用户名\.codex\skills\translate-pdf-en-zh\SKILL.md
4. 如果技能没有出现，重启 Codex，然后使用 [$translate-pdf-en-zh](C:\\Users\\86198\\.codex\\skills\\translate-pdf-en-zh\\SKILL.md) 调用。

# 优势
日常使用第三方对照翻译工具，如Zotero的PDF翻译插件（调用ai工具的api接口）、WPS全文翻译（会员），都需要一笔不小的花费，甚至翻译效果远不如预期。

而使用Codex帮你翻译英文PDF时，需经常处理排版、格式问题，这造成很大的时间成本以及token成本，而本skill帮你省去每次翻译时的提示词，使用统一的英-中对照翻译风格，并省去第三方翻译费用。

# 效果对比
使用https://github.com/guaguastandup/zotero-pdf2zh.git以及WPS全文翻译工具进行对比

对于一般的PDF文档，第三方工具翻译常出现排版不一致、翻译内容晦涩难懂、不通顺等问题，而本skill有效解决上述问题，对比如下：

图一：第三方工具翻译效果
<img width="1707" height="713" alt="image" src="https://github.com/user-attachments/assets/fe94989f-0975-4216-bbb2-17764b1a1c23" />

图二：使用translate-pdf-en-zh翻译效果
<img width="1640" height="778" alt="image" src="https://github.com/user-attachments/assets/8fb399e2-891b-4aa0-b255-94c35dd90843" />

对于某些使用特殊字体编码的PDF，第三方翻译工具可能无法识别并输出乱码
而本skill能精准识别字体编码并有效排版。对比如下：

图一：第三方工具翻译效果（输出乱码）
<img width="1795" height="781" alt="e09e877a0487348de70c33cc11b06eea" src="https://github.com/user-attachments/assets/38032799-5d76-4c42-b3fe-239081a7e319" />

图二：第三方工具翻译效果（排版混乱）
<img width="1782" height="838" alt="84843ca74cb81df46ea73182429412e3" src="https://github.com/user-attachments/assets/015b127f-27ab-49be-87ab-ec3ff4fbdad4" />

图三：使用translate-pdf-en-zh翻译效果（精准输出）
<img width="1653" height="766" alt="c00248a00ca3657b1f6d4918c0069fe6" src="https://github.com/user-attachments/assets/be562834-a8bd-4c6d-a6b4-1bcd01863077" />


