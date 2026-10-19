# 辅助文件说明

阅读入口：[返回阅读指南](../0-阅读指南.md)。日常阅读直接打开上一级主目录中的 PDF、HTML 或 Markdown。

- `output/`：配套 Python 示例、数值校验结果、CSV、曲线、MIT 插图及版式审阅记录。
- `sources/`：原网页缓存、提取文本、Fidimag 源码和许可证、KaTeX 与 MuMax3 页面生成脚本。已有 MIT 与 MuMax3 原文 PDF 已移至上一级主目录。
- `tmp/`：页面渲染截图、排版检查结果、Fidimag 页面生成与浏览器校验脚本。
- `tools/`：QAH 学习页面生成脚本。
- `整理清单.json`：本次整理的原路径、新路径和整理前 SHA256，便于核对文件完整性。

## 配套示例

以下命令均在“理论学习资料”主目录运行：

```powershell
python 辅助文件/output/fidimag-learning/macrospin_llg.py
python 辅助文件/output/demag-learning/rectangular_demag.py 200 200 4 --ms 300000 --check
```

单磁矩脚本将结果写入自身旁的 `macrospin_results/`。薄膜脚本位于 `output/fidimag-learning/thinfilm_fidimag.py`，需要另行安装 Fidimag；其完整薄膜求解尚未执行，详见阅读指南中的说明。

## 重新生成阅读页面

以下路径也以“理论学习资料”主目录为基准：

```powershell
python 辅助文件/tools/build_qah_learning.py
node 辅助文件/sources/mumax3/build_study_html.cjs
node 辅助文件/output/mit-ch9/build-reading.cjs
node 辅助文件/tmp/fidimag/build_guide.cjs
node 辅助文件/tmp/fidimag/render_guide.cjs
```

生成的阅读文件输出到主目录，截图和校验记录留在辅助目录。Node 脚本沿用原来配置的本机 Codex 运行库、Chrome/Edge 和 render-html 技能依赖；换电脑时需调整运行环境路径。现有离线 HTML 无需这些生成依赖即可阅读。
