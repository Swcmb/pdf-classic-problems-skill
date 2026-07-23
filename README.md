# pdf-classic-problems Skill

将图片组成的 PDF 自动处理为两个 Markdown 文档的 TRAE Skill：

- `经典题列表.md`（仅含题目列表）
- `经典题详解与拓展.md`（仅含详解与拓展）

## 适用场景

理工科教材/习题集扫描件（纯图片型 PDF），如概率论、高等数学等科目的习题册扫描件。

## 目录结构

```
skill/
├── SKILL.md                              # 主工作流指南（8 章节）
├── scripts/
│   ├── check_env.py                      # 环境检查脚本
│   └── ocr_extract.py                    # OCR 提取脚本
├── references/
│   ├── problem-coding.md                 # 题目编码系统
│   ├── selection-criteria.md             # 选题标准
│   └── output-format.md                  # 输出格式规范
└── examples/
    └── sample-output/                    # 示例输出参考
        ├── 经典题列表.md
        └── 经典题详解与拓展.md
```

## 依赖

### Python 包

```bash
pip install pytesseract pdf2image Pillow pypdf
```

### 系统依赖

| 平台 | Tesseract | poppler-utils |
|------|-----------|---------------|
| Linux (Debian/Ubuntu) | `sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim` | `sudo apt-get install poppler-utils` |
| macOS | `brew install tesseract tesseract-lang` | `brew install poppler` |
| Windows | [Tesseract 安装包](https://github.com/UB-Mannheim/tesseract/wiki) | [poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases) |

## 使用方法

### 1. 环境检查

```bash
python3 skill/scripts/check_env.py <pdf_path>
```

输出 JSON 状态报告，退出码 0 表示环境就绪，1 表示有缺失项。

### 2. OCR 提取

```bash
python3 skill/scripts/ocr_extract.py <pdf_path> <output_dir> [--dpi 300] [--lang chi_sim+eng] [--batch-size 20]
```

将图片 PDF 转为逐页文本文件，输出 JSON 统计报告（含 `quality_warning` 字段）。

### 3. 题目识别与筛选

LLM 读取 OCR 输出的页面文本，参照以下文档执行：

- `references/problem-coding.md`：题目识别与编码规则
- `references/selection-criteria.md`：经典题筛选标准（三大标准 + 综合评分）
- `references/output-format.md`：输出格式规范

### 4. 输出

生成两个 Markdown 文件至指定目录（默认 `/workspace/`）。

## 工作流

```
PDF 输入 → 环境检查 → OCR 提取 → 题目识别 → 经典题筛选 → 详解生成 → 输出 MD 文件
```

## 异常处理

覆盖 9 种边界情况：环境检查失败、OCR 质量低、题目识别为空、选题数量不足、详解生成中断（断点续传）、PDF 加密、输出目录不可写、OCR 乱码、空 PDF。

## 文档

- [需求说明](docs/requirements.md)
- [技术规格](docs/skill-spec.md)
- [执行计划](docs/execution-plan.md)

## 许可证

MIT
