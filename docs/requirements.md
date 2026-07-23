# 需求说明：pdf-classic-problems Skill

## 1. 概述

### 1.1 目标

创建一个自包含、可复现的 TRAE Skill，将图片组成的 PDF（扫描件）自动处理为两个 Markdown 文档：

- `经典题列表.md`：仅含被选为经典题的题号列表，按章节分组
- `经典题详解与拓展.md`：仅含经典题的详细解答、分析与拓展

### 1.2 背景

前次对话中处理了一本扫描版概率论教材 PDF，工作流为：OCR 提取 → 题目识别 → 经典题筛选 → 详解编写 → 输出两个 MD 文件。本 Skill 将该工作流封装为可复用的标准化技能。

### 1.3 适用范围

理工科学科（数学、物理、化学、工程等）的教材或习题集扫描件。

## 2. 设计决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 架构 | 标准结构（SKILL.md + scripts/ + references/） | 符合 TRAE Skill 惯例，脚本可直接执行，文档与代码分离 |
| 学科范围 | 理工科通用 | 选题标准聚焦核心概念与方法论，适用面广且实用 |
| 选题数量 | 可配置，默认 8-12 题 | 兼顾灵活性与一致性，适配不同篇幅的 PDF |

## 3. 输入规格

| 属性 | 说明 |
|------|------|
| 输入类型 | 图片组成的 PDF 文件（扫描件或图片导出的 PDF） |
| 输入路径 | 用户提供 PDF 文件的绝对路径 |
| 输入特征 | PDF 页面为图片而非可选文本，需 OCR 识别 |
| 语言 | 中文为主，可能含英文公式与术语（chi_sim + eng） |
| 内容结构 | 包含教材/习题集中的题目，按章节组织 |

## 4. 输出规格

### 4.1 经典题列表.md

- **内容**：仅含被选为经典题的题号列表
- **格式**：按章节分组，每章下列出题号
- **编码规则**：`章节号-题型序号`（如 `10.1.1-EX1` 表示 10.1.1 节的第 1 道例题）
- **题型标识**：`EX`（例题）、`EXS`（习题）、`T`（定理证明题）、`D`（定义推导题）

示例：

```markdown
## 10.1 随机事件与样本空间
- 10.1.1-EX1
- 10.1.1-EX2
- 10.1.3-EXS1

## 10.2 事件的独立性
- 10.2-EX1
```

### 4.2 经典题详解与拓展.md

- **内容**：每道经典题的详细解答与拓展
- **结构**：每题包含四个部分
  1. **题目**：原题内容（含公式）
  2. **解答**：完整解题过程
  3. **分析**：解题思路与关键步骤说明
  4. **反思与拓展**：方法论总结 + 1-2 道拓展题
- **公式格式**：行内公式 `$...$`，行间公式 `$$...$$`
- **输出位置**：`/workspace/` 目录

## 5. 处理流水线

### 阶段 1：环境检查与依赖验证

- 执行 `scripts/check_env.py` 验证 Python 包与系统依赖
- 若缺失依赖，输出安装指引并终止

### 阶段 2：OCR 文本提取

- 执行 `scripts/ocr_extract.py <pdf_path> <output_dir>`
- 使用 `pdf2image` 将 PDF 每页转为 300dpi 图片
- 使用 `pytesseract` 对每页进行 OCR（`lang='chi_sim+eng'`）
- 输出：每页一个文本文件至 `<output_dir>/pages/page_XXXX.txt`

### 阶段 3：题目识别与组织（LLM 驱动）

- AI 读取 OCR 提取的页面文本
- 识别题目边界、题号、题型、所属章节
- 按章节组织所有题目，生成完整题目索引

### 阶段 4：经典题筛选（LLM 驱动 + 参考标准）

- 参照 `references/selection-criteria.md` 中的标准
- 三大标准：核心概念代表性、方法论启发性、典型性与易错性
- 默认选取 8-12 题，用户可配置
- 确保覆盖各主要章节

### 阶段 5：详解生成与输出（LLM 驱动）

- 对每道经典题生成：原题、详细解答、分析、反思与拓展
- 生成 `经典题列表.md`
- 生成 `经典题详解与拓展.md`
- 输出至 `/workspace/` 目录

## 6. 组件架构

```
pdf-classic-problems/
├── SKILL.md                    # 主工作流指南
├── scripts/
│   ├── ocr_extract.py          # OCR 提取脚本
│   └── check_env.py            # 环境检查脚本
├── references/
│   ├── selection-criteria.md   # 选题标准
│   ├── output-format.md        # 输出格式规范
│   └── problem-coding.md       # 题目编码系统
└── examples/
    └── sample-output/          # 示例输出参考
```

### 文件职责

| 文件 | 职责 |
|------|------|
| `SKILL.md` | 定义完整工作流、调用链、阶段分工与检查点 |
| `scripts/ocr_extract.py` | PDF 转图片 + OCR 提取，输出每页文本文件 |
| `scripts/check_env.py` | 验证 Python 包与系统依赖是否就绪 |
| `references/selection-criteria.md` | 经典题三大筛选标准与评分维度 |
| `references/output-format.md` | 两个 MD 文件的格式规范与示例 |
| `references/problem-coding.md` | 题目编码规则与题型标识 |

## 7. 依赖与环境

### Python 包

```
pytesseract>=0.3.10
pdf2image>=1.16.0
Pillow>=9.0.0
```

### 系统依赖

- Tesseract OCR 引擎（含 `chi_sim` 中文语言包）
- poppler-utils（提供 `pdftoppm`，`pdf2image` 依赖）

### 安装命令

```bash
pip install pytesseract pdf2image Pillow
apt-get install tesseract-ocr tesseract-ocr-chi-sim poppler-utils
```

## 8. 功能边界

### 做什么

- 从扫描版 PDF 提取文本（OCR）
- 识别和组织题目
- 筛选经典题
- 生成两个格式化的 Markdown 文档

### 不做什么

- 处理文本型 PDF（已有 pdf Skill 处理）
- 生成非 Markdown 格式输出
- 自动安装系统依赖
- 处理加密或受密码保护的 PDF
- 处理非学术类 PDF（如小说、报告）
- 人工校对 OCR 结果（由 LLM 在处理阶段隐式修正）

## 9. 异常处理

| 异常场景 | 检测方式 | 处理策略 |
|----------|----------|----------|
| PDF 文件不存在 | `check_env.py` 启动时检查路径 | 报错并终止，提示检查路径 |
| PDF 为空或页数为 0 | `pdf2image` 转换后检查图片列表长度 | 报错并终止 |
| OCR 提取质量极低 | 检查每页文本长度，超过 80% 页面为空则判定 | 警告用户，建议调高 DPI |
| Tesseract 未安装 | `check_env.py` 验证 | 输出安装命令并终止 |
| 未识别到任何题目 | 阶段 3 完成后检查题目索引 | 警告并输出 OCR 原始文本供检查 |
| 选题数量不足 | 阶段 4 选题时检查可用题目数 | 自动调整为可用数的 50-80%，提示用户 |
| PDF 含密码保护 | `pdf2image` 转换时捕获异常 | 报错并提示解除密码保护 |
| 临时文件残留 | 流程结束后检查 | 自动清理，`--keep-temp` 选项可保留 |

## 10. 调用链

```
用户提供 PDF 路径
    ↓
check_env.py 验证环境
    ↓
ocr_extract.py 提取文本（PDF → 图片 → OCR → 页面文本文件）
    ↓
LLM 读取页面文本 → 识别题目 → 组织题目索引
    ↓
LLM 参照 selection-criteria.md → 筛选经典题（8-12题）
    ↓
LLM 生成详解（解答 + 分析 + 反思与拓展）
    ↓
输出 经典题列表.md + 经典题详解与拓展.md 至 /workspace/
    ↓
清理临时文件
```

## 11. 提示词模板

### 完整版

```
请使用 pdf-classic-problems 技能处理以下 PDF 文件：
- PDF 路径：{pdf_path}
- 选题数量：{count}（可选，默认 8-12 题）
- 输出目录：{output_dir}（可选，默认 /workspace/）

请将图片组成的 PDF 处理为经典题列表和经典题详解与拓展两个 Markdown 文档。
```

### 简化版

```
将这个图片 PDF 处理为经典题列表和经典题详解：{pdf_path}
```
