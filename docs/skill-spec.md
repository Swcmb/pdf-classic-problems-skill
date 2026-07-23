# 技术规格文档：pdf-classic-problems Skill

> 版本：2.1 | 状态：已定稿 | 基于需求文档 `docs/requirements.md` 编写
> 审核经历：3 轮 document-reviewer 审核，共修复 18 个问题（1 阻塞 + 6 高 + 7 中 + 4 低），最终获审核员确认通过

## 1. 技术架构

### 1.1 整体架构

Skill 采用标准 TRAE Skill 结构，由三类组件协作：

- **SKILL.md**：主工作流指南，定义 5 阶段处理流水线，指引 LLM 按阶段执行
- **scripts/**：Python 自动化脚本，负责 OCR 提取与环境检查等确定性任务
- **references/**：规则与标准文档，LLM 参照执行题目识别、选题与输出格式化

### 1.2 目录结构

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

### 1.3 组件职责矩阵

| 阶段 | 组件 | 职责 | 执行者 |
|------|------|------|--------|
| 阶段 1 | `scripts/check_env.py` | 验证 Python 包与系统依赖 | Python 脚本 |
| 阶段 2 | `scripts/ocr_extract.py` | PDF 转图片 + OCR 提取 | Python 脚本 |
| 阶段 3 | SKILL.md 阶段 3 | 题目识别与组织 | LLM |
| 阶段 4 | SKILL.md 阶段 4 + `references/selection-criteria.md` | 经典题筛选 | LLM + references |
| 阶段 5 | SKILL.md 阶段 5 + `references/output-format.md` | 详解生成与输出 | LLM + references |

### 1.4 SKILL.md 章节与流水线阶段映射

| SKILL.md 章节 | 对应阶段 | 说明 |
|---------------|----------|------|
| 3.1 概述与触发条件 | — | 入口判定，非处理阶段 |
| 3.2 前置条件检查 | 阶段 1 | 环境验证 |
| 3.3 OCR 提取流程 | 阶段 2 | 文本提取 |
| 3.4 题目识别规则 | 阶段 3 | 题目识别与组织 |
| 3.5 经典题筛选流程 | 阶段 4 | 选题 |
| 3.6 详解生成规范 | 阶段 5 | 详解编写 |
| 3.7 输出与清理 | 阶段 5 | 文件输出与清理 |
| 3.8 异常处理指引 | 全阶段 | 异常应对 |

## 2. 脚本规格

### 2.1 check_env.py

**功能**：验证运行环境是否满足要求。

**函数签名**：

```python
def check_python_packages() -> dict:
    """检查 Python 包是否安装，返回 {"installed": [...], "missing": [...]}"""

def check_system_dependencies() -> dict:
    """检查系统命令与语言包，返回 {"tesseract": bool, "chi_sim": bool, "pdftoppm": bool}"""

def check_pdf_file(pdf_path: str) -> dict:
    """验证 PDF 文件，返回 {"exists": bool, "readable": bool, "encrypted": bool}"""

def run_all_checks(pdf_path: str) -> dict:
    """执行全部检查，返回综合状态报告"""
```

**输出格式**（JSON）：

```json
{
  "status": "ok | error",
  "python_packages": {"installed": ["pytesseract", "pdf2image", "Pillow", "pypdf", ...], "missing": [...]},
  "system_deps": {"tesseract": true, "chi_sim": true, "pdftoppm": true},
  "pdf_file": {"exists": true, "readable": true, "encrypted": false},
  "install_commands": ["pip install pytesseract pdf2image Pillow pypdf", "..."]
}
```

**退出码**：0 = 全部就绪，1 = 有缺失项。

**命令行接口**：

```bash
python3 check_env.py <pdf_path>
```

**检测逻辑**：

- Python 包：使用 `importlib.util.find_spec()` 检查 `pytesseract`、`pdf2image`、`Pillow`、`pypdf`
- 系统命令：使用 `shutil.which()` 检查 `tesseract` 与 `pdftoppm`
- 语言包：执行 `tesseract --list-langs` 检查输出是否包含 `chi_sim`
- PDF 文件：使用 `os.path.exists()` 与 `os.access()` 检查文件存在性与可读性
- PDF 加密检测：优先使用 `pypdf.PdfReader(pdf_path).is_encrypted` 属性检查，仅当 pypdf 不可用时回退到 `pdf2image.convert_from_path()` 探测（区分 `PDFEncryptionError` 与 `PDFInfoNotInstalledError`）

**跨平台安装命令**：

`install_commands` 字段根据检测结果与操作系统动态生成：

| 平台 | Tesseract | poppler-utils | sudo 需求 |
|------|-----------|---------------|-----------|
| Linux (Debian/Ubuntu) | `sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim` | `sudo apt-get install poppler-utils` | 需要 sudo |
| macOS | `brew install tesseract tesseract-lang` | `brew install poppler` | 不需要 |
| Windows | 下载 Tesseract 安装包 | 下载 poppler for Windows | 不需要 |

**运行环境约束**：本 Skill 优先支持 Linux/macOS。Windows 需手动配置 Tesseract 与 poppler 的 PATH 环境变量。

### 2.2 ocr_extract.py

**功能**：将图片 PDF 转换为逐页文本文件。

**函数签名**：

```python
def convert_pdf_to_images(pdf_path: str, dpi: int = 300,
                          first_page: int = None, last_page: int = None) -> list:
    """将 PDF 指定页范围转为 PIL Image 列表。
    通过 first_page/last_page 参数实现按批次转换，由 extract_pages 在批次循环中调用。
    """

def ocr_image(image, lang: str = "chi_sim+eng") -> str:
    """对单页图片执行 OCR，返回文本字符串"""

def sanitize_text(text: str) -> str:
    """清理 OCR 文本：去除控制字符、合并多余空行"""

def extract_pages(pdf_path: str, output_dir: str, dpi: int = 300,
                  lang: str = "chi_sim+eng", keep_temp: bool = False,
                  batch_size: int = 20) -> dict:
    """主函数：逐页 OCR 提取，输出页面文本文件。
    采用流式处理：每批次转换 batch_size 页 → 逐页 OCR → 写入文本 → 释放 Image。
    """
```

**输出格式**（JSON）：

```json
{
  "total_pages": 120,
  "output_dir": "/tmp/ocr_output/pages",
  "empty_pages": [3, 45, 67],
  "avg_text_length": 850,
  "quality_warning": false
}
```

**`quality_warning` 计算逻辑**：

```
quality_warning = True 当且仅当满足以下任一条件：
  1. len(empty_pages) / total_pages > 0.8
  2. avg_text_length < 50（平均每页文本字符数低于 50，可能为乱码或空白）

注意：当 total_pages == 0 时不计算 quality_warning，直接返回退出码 1（对应空 PDF 异常）。
```

**命令行接口**：

```bash
python3 ocr_extract.py <pdf_path> <output_dir> [--dpi 300] [--lang chi_sim+eng] [--keep-temp] [--batch-size 20]
```

**关键参数**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `pdf_path` | 必填 | 输入 PDF 文件路径 |
| `output_dir` | 必填 | 输出目录，不存在时自动创建 `os.makedirs(exist_ok=True)` |
| `--dpi` | 300 | OCR 分辨率，质量低时可调至 400 |
| `--lang` | chi_sim+eng | Tesseract 语言包 |
| `--keep-temp` | False | 是否保留临时图片文件 |
| `--batch-size` | 20 | 每批次转换页数，控制内存占用 |

**内存管理策略**：

采用流式分批处理，避免全量 Image 驻留内存：

```
循环：for batch_start in range(0, total_pages, batch_size):
    1. images = convert_pdf_to_images(pdf_path, dpi=dpi,
                                      first_page=batch_start+1,
                                      last_page=min(batch_start+batch_size, total_pages))
    2. 对 images 中每张 Image 执行 OCR → 写入文本文件
    3. 显式 del images 及 Image 对象 → 调用 gc.collect() 释放内存
```

**异常处理**：

- `PDFInfoNotInstalledError`：提示安装 poppler-utils
- `TesseractNotFoundError`：提示安装 tesseract-ocr
- `PDFEncryptionError`：提示 PDF 受密码保护
- `MemoryError`：建议减小 `--batch-size`（如 10 或 5），退出码 1
- 通用异常：捕获并输出错误信息，退出码 1

**文件命名规则**：`page_{页码:04d}.txt`（如 `page_0001.txt`）

**清理策略**：默认删除临时图片文件；`--keep-temp` 保留。

## 3. SKILL.md 内容规格

SKILL.md 包含以下 8 个章节：

### 3.1 概述与触发条件

- 触发词：`图片PDF`、`扫描件PDF`、`经典题`、`经典题详解`
- 适用场景：理工科教材/习题集扫描件（纯图片型 PDF）
- 不适用场景：
  - 文本型 PDF（使用 pdf Skill 处理）
  - 非学术 PDF（如小说、报告）
  - 混合型 PDF（部分页为文本层、部分页为扫描图片）—— **不支持，作为非目标声明**
  - 加密或受密码保护的 PDF

### 3.2 前置条件检查

- 指引执行 `python3 scripts/check_env.py <pdf_path>`
- 解析返回的 JSON 状态报告
- 若 `status == "error"`：向用户输出 `install_commands` 并终止

### 3.3 OCR 提取流程

- 指引执行 `python3 scripts/ocr_extract.py <pdf_path> <output_dir>`
- 检查返回的 `quality_warning` 字段
- 若 `quality_warning == true`：
  - 警告用户 OCR 质量可能不佳
  - 输出 `empty_pages` 列表与 `avg_text_length` 值
  - 建议尝试 `--dpi 400` 重新提取
  - 询问用户是否继续（继续则 LLM 尽力处理）

### 3.4 题目识别规则

- 参照 `references/problem-coding.md`
- LLM 读取页面文本文件，识别题目边界、题号、题型、章节
- 生成内部题目索引（不输出文件）

### 3.5 经典题筛选流程

- 参照 `references/selection-criteria.md`
- 对每道题按三大标准评分
- 计算综合评分，按降序选取前 N 题（默认 10 题，可配置 8-12 题）
- 确保章节覆盖

### 3.6 详解生成规范

- 参照 `references/output-format.md`
- 每题四部分：题目、解答、分析、反思与拓展
- 公式格式：行内 `$...$`，行间 `$$...$$`

### 3.7 输出与清理

- 输出路径：默认 `/workspace/`，可通过参数配置
- 输出目录不存在时自动创建 `os.makedirs(exist_ok=True)`
- 输出文件已存在时覆盖写入
- 文件名：`经典题列表.md`、`经典题详解与拓展.md`
- 清理临时目录（OCR 页面文本文件）
- 详解生成全部完成后删除 `.progress` 文件，避免陈旧记录影响后续运行
- **断点续传机制**：详解生成过程中，将已完成的题号写入 `<output_dir>/.progress` 文件；若中途中断，下次从 `.progress` 中读取已完成题号，跳过已生成题目继续。`.progress` 文件格式：每行一个题号编码（如 `10.1.1-EX1`），UTF-8 编码，无 BOM

### 3.8 异常处理指引

本节内联完整异常处理矩阵，与第 8 节保持一致。LLM 在各阶段执行时参照本节处理异常：

| 异常场景 | 所处阶段 | 检测方式 | 处理策略 |
|----------|----------|----------|----------|
| 环境检查失败 | 阶段 1 | `check_env.py` 返回 `status: "error"` | 输出安装命令，终止 |
| OCR 质量低 | 阶段 2 | `quality_warning == true` | 警告并建议调高 DPI，询问是否继续 |
| 题目识别为空 | 阶段 3 | 题目索引长度为 0 | 输出前 5 页 OCR 文本供检查，终止 |
| 选题数量不足 | 阶段 4 | 总题数 < 8 | 选取 50-80%，提示用户 |
| 详解生成中途失败 | 阶段 5 | LLM 上下文溢出或异常 | 从 `.progress` 断点续传 |
| PDF 加密 | 阶段 1 | `check_env.py` 返回 `encrypted: true` | 提示解除密码保护，终止 |
| 输出目录不可写 | 阶段 5 | `os.makedirs` 或文件写入失败 | 提示检查权限或更换目录 |
| OCR 乱码（非空但质量差） | 阶段 2 | `avg_text_length < 50` | 触发 `quality_warning`，同 OCR 质量低处理 |
| 空 PDF（total_pages==0） | 阶段 2 | `ocr_extract.py` 返回 `total_pages==0` 且退出码 1 | 提示用户 PDF 无有效页面，终止 |

## 4. 题目识别规则（references/problem-coding.md）

### 4.1 章节标题识别

| 模式 | 正则 | 示例 |
|------|------|------|
| 中文数字章节 | `第[一二三四五六七八九十百]+章` | 第十章 随机事件与概率 |
| 阿拉伯数字章节 | `第\d+章` 或 `\d+\.\d*(\.\d+)*` | 第10章 或 10.1.1 |

### 4.2 题号识别

| 题型 | 正则模式 | 编码前缀 | 上下文约束 |
|------|----------|----------|------------|
| 例题 | `例\d+`、`例\d+\.\d+`、`Example \d+` | EX | 题号位于行首或段首 |
| 习题 | `习题\d+`、行首`\d+\)`、行首`\(\d+\)` | EXS | 题号位于行首，且后接非标点正文 |
| 定理证明 | `定理\d+.*证明` | T | 需包含"证明"关键词 |
| 定义推导 | `定义\d+.*推导` | D | 需包含"推导"关键词 |

**误匹配过滤规则**：

- 题号必须位于行首或前导空白后（排除正文中引用如"在 3) 的情况下"）
- 题号后必须紧跟题目正文内容（排除"(2) 见下文"等引用语）
- 习题题号需结合当前章节上下文判定（确认位于习题区域而非正文段落）

### 4.3 题目边界判定

- **起点**：题号行或章节标题后的第一个问题
- **终点**：下一题号行、下一章节标题、或解答结束标记（如"解："后的完整解答）
- **跨页判定规则**（满足以下任一即判定为跨页题目）：
  1. 当前页末尾题号后内容未出现下一题号或章节标题
  2. 当前页末行非自然段结束标志（未以句号、问号、分号结尾）
  3. 下一页首行内容与上一题题干语义连续（非新题号、非章节标题）
- **跨页处理**：判定为跨页时，合并前后页内容，拼接处去除分页符
- **公式完整性**：确保公式未被截断，检查 `$`、`$$` 配对，若不配对则向下一页延伸至配对完成

### 4.4 题目编码生成

- 格式：`章节号-题型序号`
- 示例：`10.1.1-EX1` = 第 10.1.1 节的第 1 道例题
- 多级章节：取最细粒度章节号
- 同章节同类型递增序号

## 5. 选题标准（references/selection-criteria.md）

### 5.1 三大标准与权重

| 标准 | 权重 | 核心问题 |
|------|------|----------|
| 核心概念代表性 | 40% | 是否直接考察核心概念？是否综合运用多个知识点？ |
| 方法论启发性 | 35% | 是否展示重要解题技巧？是否有多种解法？ |
| 典型性与易错性 | 25% | 是否为常见考点？是否包含常见错误？ |

### 5.2 评分规则

每项标准评分 1-5 分，≥3 分入选候选池。

**综合评分公式**：

```
总分 = 核心概念 × 0.40 + 方法论 × 0.35 + 典型性 × 0.25
```

**入选阈值**：总分 ≥ 3.5

### 5.3 筛选流程

1. 对所有识别到的题目按三大标准评分
2. 计算综合评分
3. 按总分降序排列
4. 选取前 N 题（默认 10 题，用户可配置范围为 8-12 题）
5. 确保覆盖各主要章节（每章至少 1 题，如有）
6. 若同章节多题高分，取最高分者

### 5.4 数量不足时的降级策略

- 总题数 < 8：选取总题数的 50-80%
- 总题数 < 3：提示用户 PDF 可能不含足够题目
- 总题数 = 0：转入异常处理（8.3 题目识别为空）

## 6. 输出格式规范（references/output-format.md）

### 6.1 经典题列表.md

```markdown
# 经典题列表

## {章节号} {章节名称}
- {题号1}
- {题号2}

## {下一章节号} {下一章节名称}
- {题号3}
```

**规则**：

- 按章节号升序排列
- 同章节内按题号顺序排列
- 仅含题号，不含题目内容

### 6.2 经典题详解与拓展.md

```markdown
# 经典题详解与拓展

---

## {题号}

### 题目
{原题内容，保留公式与格式}

### 解答
{完整解题过程，逐步推导}

### 分析
{解题思路说明，关键步骤解释}

### 反思与拓展
**方法总结**：{该方法论的核心要点}

**拓展题1**：
{拓展题内容}

<details>
<summary>拓展题解答</summary>
{拓展题解答}
</details>
```

### 6.3 公式格式要求

| 场景 | 格式 | 示例 |
|------|------|------|
| 行内公式 | `$...$` | $P(A \cup B)$ |
| 行间公式 | `$$...$$` | $$P(A|B) = \frac{P(AB)}{P(B)}$$ |
| 多行公式 | `\begin{align}...\end{align}` | 对齐推导步骤 |
| 分段函数 | `\begin{cases}...\end{cases}` | 定义域分段 |
| 分隔线 | 题间 `---` | 视觉分隔 |
| 拓展题解答 | `<details>` 折叠 | 默认折叠 |

## 7. Skill/MCP 协作机制

### 7.1 Skill 与脚本协作

- SKILL.md 定义工作流，指引 LLM 按阶段执行
- scripts/ 负责确定性自动化任务（OCR、环境检查）
- LLM 负责语义理解任务（题目识别、选题、详解生成）
- references/ 提供规则与标准，LLM 参照执行

### 7.2 与现有 MCP 的协作

- Sequential Thinking MCP：可选，用于复杂 PDF 的结构化分析
- 不依赖其他 MCP Server

### 7.3 与现有 Skill 的关系

- 完全自包含，不依赖其他 Skill
- 与 pdf Skill 互补：pdf Skill 处理文本型 PDF，本 Skill 处理图片型 PDF

## 8. 异常处理详细流程

### 8.1 环境检查失败

1. LLM 读取 `check_env.py` 返回的 JSON
2. 识别 `missing` 列表中的缺失项
3. 向用户输出 `install_commands` 中的安装命令（含跨平台指令）
4. 终止流程，不进入后续阶段

### 8.2 OCR 质量低

1. LLM 检查 `ocr_extract.py` 返回的 `quality_warning` 字段
2. 若 `quality_warning == true`：
   - 输出 `empty_pages` 列表与 `avg_text_length` 值
   - 警告用户 OCR 质量可能不佳
   - 建议尝试 `--dpi 400` 重新提取
   - 询问用户是否继续（继续则 LLM 尽力处理）

### 8.3 题目识别为空

1. LLM 检查题目索引长度
2. 若为 0：输出 OCR 原始文本前 5 页供用户检查
3. 终止流程

### 8.4 选题数量不足

1. 若总题数 < 8：选取总题数的 50-80%，提示用户
2. 若总题数 < 3：提示 PDF 可能不含足够题目
3. 若总题数 = 0：转入异常处理 8.3

### 8.5 详解生成中途失败

1. 读取 `<output_dir>/.progress` 文件获取已完成的题号
2. 跳过已生成题目，从断点继续
3. 确保已生成题目的完整性（四部分齐全）
4. 若 `.progress` 不存在（首次失败），扫描 `经典题详解与拓展.md` 中已有的 `## {题号}` 标题，与计划生成列表比对，找出缺失题目并从头补生成

### 8.6 PDF 加密

1. `check_env.py` 检测到 `pdf_file.encrypted == true`
2. 向用户提示"PDF 受密码保护，请解除密码保护后重试"
3. 终止流程

### 8.7 输出目录不可写

1. `os.makedirs(output_dir, exist_ok=True)` 或文件写入时抛出 `PermissionError`
2. 向用户提示"输出目录 {path} 不可写，请检查权限或更换目录"
3. 建议使用 `/tmp/` 或用户主目录作为替代

### 8.8 OCR 乱码（非空但质量差）

1. `ocr_extract.py` 检测到 `avg_text_length < 50`（页面非空但文本极短）
2. 触发 `quality_warning = true`
3. 处理流程同 8.2 OCR 质量低

### 8.9 空 PDF

1. `ocr_extract.py` 返回 `total_pages == 0` 且退出码 1
2. 向用户提示"PDF 无有效页面，请检查文件是否为空或损坏"
3. 终止流程

## 9. 验收标准（DoD）

1. `check_env.py` 能正确检测所有依赖并返回 JSON 状态报告
2. `ocr_extract.py` 能将图片 PDF 转为页面文本文件，采用分批流式处理避免 OOM
3. SKILL.md 包含完整的 8 个工作流章节，引用正确的脚本与参考文档
4. `references/selection-criteria.md` 包含三大标准、评分维度、权重与筛选流程
5. `references/output-format.md` 包含两个 MD 文件的完整格式模板
6. `references/problem-coding.md` 包含章节识别、题号识别（含上下文约束）、编码生成规则
7. 异常处理覆盖 9 种边界情况（8.1-8.9），每种有明确的检测与处理策略
8. Skill 完全自包含，不依赖外部 Skill 或 MCP（Sequential Thinking 可选）
9. 所有 Python 脚本可直接通过命令行执行
10. 输出的 MD 文件符合格式规范，公式渲染正确
11. `quality_warning` 字段有明确的计算逻辑并在 SKILL.md 流程中使用
12. 断点续传机制（`.progress` 文件）在详解生成中途失败时可用

## 10. 测试规格

### 10.1 单元测试

| 脚本 | 测试项 | 预期结果 |
|------|--------|----------|
| `check_env.py` | 依赖全部存在 | `status: "ok"`，退出码 0 |
| `check_env.py` | 缺失 pytesseract | `status: "error"`，`missing` 含 pytesseract |
| `check_env.py` | 缺失 pypdf | `status: "error"`，`missing` 含 pypdf |
| `check_env.py` | PDF 不存在 | `pdf_file.exists: false` |
| `check_env.py` | 加密 PDF | `pdf_file.encrypted: true` |
| `ocr_extract.py` | 正常 PDF | 生成页面文本文件，非空率 > 80% |
| `ocr_extract.py` | 空 PDF | `total_pages: 0`，退出码 1 |
| `ocr_extract.py` | 加密 PDF | 捕获 `PDFEncryptionError`，输出提示信息 |
| `ocr_extract.py` | 120 页 PDF（batch_size=20） | 分 6 批完成，内存峰值 < 500MB |
| `ocr_extract.py` | 乱码 PDF（avg_text_length < 50） | `quality_warning: true` |

### 10.2 验证检查点

| 检查点 | 验证内容 | 通过条件 |
|--------|----------|----------|
| OCR 提取后 | 页面文本文件数量与非空率 | 文件数 = PDF 页数，非空率 > 80% |
| 题目识别后 | 题目索引非空、编码规范、无误匹配 | 索引长度 > 0，编码格式合规，正文中引用未被误识别 |
| 选题后 | 选题数量、章节覆盖 | 数量在 8-12 范围内（默认 10），每章 ≥ 1 题 |
| 输出后 | 文件存在性、格式合规性 | 两文件均存在，格式符合模板 |
| 断点续传 | 中断后恢复 | `.progress` 文件正确记录已完成题号，恢复后跳过已生成题目 |
