# 执行计划：pdf-classic-problems Skill 封装

> 版本：2.0 | 依据：`docs/requirements.md` + `docs/skill-spec.md`

## 1. 概述

### 1.1 目标

按规格文档将 pdf-classic-problems Skill 的全部组件创建、验证并推送至 GitHub 仓库。

### 1.2 范围

创建 8 个文件（2 脚本 + 3 参考文档 + 1 主文件 + 2 示例），验证 12 项 DoD，完成 5 次 Git 提交。

### 1.3 完整目录结构

```
skill/
├── SKILL.md                              # 主工作流指南
├── scripts/
│   ├── check_env.py                      # 环境检查脚本
│   └── ocr_extract.py                    # OCR 提取脚本
├── references/
│   ├── problem-coding.md                 # 题目编码系统
│   ├── selection-criteria.md             # 选题标准
│   └── output-format.md                  # 输出格式规范
└── examples/
    └── sample-output/
        ├── 经典题列表.md                  # 示例：题号列表
        └── 经典题详解与拓展.md            # 示例：详解与拓展
```

### 1.4 前置条件

- 需求文档已定稿（`docs/requirements.md`）
- 技术规格文档已定稿（`docs/skill-spec.md`，经 3 轮审核通过）
- GitHub 仓库已初始化（`Swcmb/pdf-classic-problems-skill`）

## 2. 任务分解

### 阶段 A：脚本层（任务 1-2）

#### 任务 1：创建 `scripts/check_env.py`

| 步骤 | 内容 | 输入 | 输出 |
|------|------|------|------|
| 1.1 | 实现 `check_python_packages()`：检查 pytesseract、pdf2image、Pillow、pypdf | 无 | `{"installed": [...], "missing": [...]}` |
| 1.2 | 实现 `check_system_dependencies()`：检查 tesseract、chi_sim、pdftoppm | 无 | `{"tesseract": bool, "chi_sim": bool, "pdftoppm": bool}` |
| 1.3 | 实现 `check_pdf_file()`：使用 `pypdf.PdfReader.is_encrypted` 检测加密，对 `pdf_path` 执行 `os.path.realpath()` 规范化以防路径遍历 | `pdf_path` | `{"exists": bool, "readable": bool, "encrypted": bool}` |
| 1.4 | 实现 `run_all_checks()`：聚合结果输出 JSON | `pdf_path` | 完整 JSON 状态报告 |
| 1.5 | 实现命令行入口：`argparse` 解析 `pdf_path` | 命令行参数 | 标准输出 JSON + 退出码 |

**参数表**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `pdf_path` | str | 是 | 输入 PDF 文件绝对路径 |

**退出码定义**：

| 退出码 | 含义 |
|--------|------|
| 0 | 全部检查通过 |
| 1 | 有缺失项或 PDF 异常 |

**跨平台处理**：使用 `pathlib.Path` 处理所有路径拼接，避免 Windows/Linux 路径分隔符差异。

**验证清单**：

- [ ] 运行 `python3 check_env.py <test.pdf>`，输出 JSON 格式正确
- [ ] JSON 包含 `status`、`python_packages`、`system_deps`、`pdf_file`、`install_commands` 五个字段
- [ ] 依赖全部存在时 `status == "ok"`，退出码 0
- [ ] 缺失依赖时 `status == "error"`，退出码 1，`install_commands` 非空

#### 任务 2：创建 `scripts/ocr_extract.py`

| 步骤 | 内容 | 输入 | 输出 |
|------|------|------|------|
| 2.1 | 实现 `convert_pdf_to_images()`：支持 `first_page`/`last_page` 参数 | `pdf_path, dpi, first_page, last_page` | PIL Image 列表 |
| 2.2 | 实现 `ocr_image()`：`pytesseract.image_to_string` | PIL Image, `lang` | 文本字符串 |
| 2.3 | 实现 `sanitize_text()`：去除控制字符、合并空行 | 原始文本 | 清理后文本 |
| 2.4 | 实现 `extract_pages()`：分批流式处理，计算 `quality_warning` | 全部参数 | JSON 统计报告 |
| 2.5 | 实现命令行入口：`argparse` 解析全部参数 | 命令行参数 | 页面文本文件 + JSON |

**参数表**：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `pdf_path` | str | 必填 | 输入 PDF 文件路径 |
| `output_dir` | str | 必填 | 输出目录，不存在时自动创建 |
| `--dpi` | int | 300 | OCR 分辨率 |
| `--lang` | str | chi_sim+eng | Tesseract 语言包 |
| `--keep-temp` | flag | False | 是否保留临时图片 |
| `--batch-size` | int | 20 | 每批次转换页数 |

**退出码定义**：

| 退出码 | 含义 |
|--------|------|
| 0 | 成功完成 |
| 1 | 错误（空 PDF、加密、依赖缺失、MemoryError 等） |

**输出编码**：所有文本文件 UTF-8 编码，无 BOM。

**临时目录隔离**：每次运行使用 `output_dir/pages/` 子目录，运行前检查并清理上一次残留的临时文件。

**验证清单**：

- [ ] 运行 `python3 ocr_extract.py <test.pdf> /tmp/output`，生成 `pages/page_XXXX.txt` 文件
- [ ] JSON 输出包含 `total_pages`、`output_dir`、`empty_pages`、`avg_text_length`、`quality_warning` 五个字段
- [ ] 正常 PDF 非空率 > 80%
- [ ] 空 PDF 返回 `total_pages: 0`，退出码 1

### 阶段 B：参考文档层（任务 3-5）

#### 任务 3：创建 `references/problem-coding.md`

| 步骤 | 内容 |
|------|------|
| 3.1 | 章节标题识别规则（2 种模式 + 正则 + 示例） |
| 3.2 | 题号识别规则（4 种题型 + 正则 + 上下文约束 + 3 条误匹配过滤规则） |
| 3.3 | 题目边界判定（起点/终点/3 条跨页判定规则/公式完整性） |
| 3.4 | 题目编码生成规则（格式/示例/多级章节/递增序号） |

**验证清单**：

- [ ] 包含 4.1-4.4 四个小节
- [ ] 题号识别表有"上下文约束"列
- [ ] 包含"误匹配过滤规则"小节（3 条规则）
- [ ] 跨页判定有 3 条可编码规则

#### 任务 4：创建 `references/selection-criteria.md`

| 步骤 | 内容 |
|------|------|
| 4.1 | 三大标准与权重表（核心概念 40%/方法论 35%/典型性 25%） |
| 4.2 | 评分规则（1-5 分，≥3 入选候选池）与综合评分公式 |
| 4.3 | 筛选流程（6 步） |
| 4.4 | 降级策略（总题数 < 8/< 3/= 0） |

**验证清单**：

- [ ] 包含 5.1-5.4 四个小节
- [ ] 权重表有三行，权重合计 100%
- [ ] 综合评分公式完整
- [ ] 入选阈值 ≥ 3.5

#### 任务 5：创建 `references/output-format.md`

| 步骤 | 内容 |
|------|------|
| 5.1 | 经典题列表.md 格式模板 + 3 条规则 |
| 5.2 | 经典题详解与拓展.md 格式模板（4 部分：题目/解答/分析/反思与拓展） |
| 5.3 | 公式格式要求表（6 种场景） |

**验证清单**：

- [ ] 包含 6.1-6.3 三个小节
- [ ] 详解模板含 4 个 `###` 子标题
- [ ] 公式格式表有 6 行
- [ ] 拓展题解答使用 `<details>` 折叠

### 阶段 C：主文件层（任务 6）

#### 任务 6：创建 `SKILL.md`

| 步骤 | 内容 | 引用 |
|------|------|------|
| 6.1 | 概述与触发条件（触发词 + 适用/不适用场景） | — |
| 6.2 | 前置条件检查流程 | `scripts/check_env.py` |
| 6.3 | OCR 提取流程（含 `quality_warning` 检查） | `scripts/ocr_extract.py` |
| 6.4 | 题目识别规则指引 | `references/problem-coding.md` |
| 6.5 | 经典题筛选流程（默认 10 题，可配置 8-12） | `references/selection-criteria.md` |
| 6.6 | 详解生成规范 | `references/output-format.md` |
| 6.7 | 输出与清理流程（含 `.progress` 断点续传 + 运行前清理残留） | — |
| 6.8 | 异常处理指引（内联 9 种异常矩阵） | — |

**6.8 异常矩阵摘要**（完整内容见 spec 第 8 节）：

| 编号 | 异常名称 | 阶段 | 处理概要 |
|------|----------|------|----------|
| 8.1 | 环境检查失败 | 1 | 输出安装命令，终止 |
| 8.2 | OCR 质量低 | 2 | 警告并建议调高 DPI |
| 8.3 | 题目识别为空 | 3 | 输出前 5 页供检查，终止 |
| 8.4 | 选题数量不足 | 4 | 选取 50-80%，提示 |
| 8.5 | 详解生成中途失败 | 5 | `.progress` 断点续传 |
| 8.6 | PDF 加密 | 1 | 提示解除密码保护，终止 |
| 8.7 | 输出目录不可写 | 5 | 提示更换目录 |
| 8.8 | OCR 乱码 | 2 | 触发 `quality_warning` |
| 8.9 | 空 PDF | 2 | 提示无有效页面，终止 |

**验证清单**：

- [ ] 8 个章节完整（6.1-6.8）
- [ ] 引用路径正确（`scripts/` 和 `references/` 前缀）
- [ ] 异常矩阵 9 行
- [ ] 断点续传机制描述完整（含 `.progress` 格式与清理）

### 阶段 D：示例层（任务 7）

#### 任务 7：创建示例输出

| 步骤 | 内容 | 来源 |
|------|------|------|
| 7.1 | `examples/sample-output/经典题列表.md` | 前次对话产出 `/workspace/经典题题号.md`（概率论 10 道经典题） |
| 7.2 | `examples/sample-output/经典题详解与拓展.md` | 前次对话产出 `/workspace/经典题详解与拓展.md`（概率论 10 道详解） |

**验证清单**：

- [ ] 示例文件格式符合 `references/output-format.md` 规范
- [ ] 题号编码格式为 `章节号-题型序号`
- [ ] 详解含 4 部分（题目/解答/分析/反思与拓展）

### 阶段 E：验证层（任务 8）

#### 任务 8：验证与测试

| 步骤 | 验证内容 | 通过条件 | 类型 |
|------|----------|----------|------|
| 8.1 | 运行 `check_env.py` | JSON 输出格式正确，退出码符合预期 | 自动化 |
| 8.2 | 运行 `ocr_extract.py` | 页面文件生成，JSON 统计正确 | 自动化 |
| 8.3 | 检查目录结构 | 8 个文件 + 目录结构与 1.3 节一致 | 手动 |
| 8.4 | 逐条核对 DoD 12 项 | 全部通过 | 手动 |

**运行时检查点说明**（CP3-CP5 为运行时检查，由 LLM 在 Skill 实际执行时验证，不纳入交付前验证）：

| 检查点 | 位置 | 验证内容 | 通过条件 | 类型 |
|--------|------|----------|----------|------|
| CP1 | 环境检查后 | `check_env.py` 返回值 | `status == "ok"`；若 `encrypted == true` 则走 8.6 异常处理 | 交付前可验证 |
| CP2 | OCR 提取后 | 页面文件与质量统计 | 文件数 = PDF 页数；`quality_warning == false` 或用户确认继续（LLM 向用户输出警告并询问） | 交付前可验证 |
| CP3 | 题目识别后 | 题目索引 | 长度 > 0，编码格式合规；若为空走 8.3 异常处理 | 运行时 |
| CP4 | 选题后 | 选题结果 | 数量 8-12（默认 10），每章 ≥ 1 题；若不足走 8.4 降级 | 运行时 |
| CP5 | 详解生成后 | 输出文件 | 两文件均存在，格式符合模板；中断走 8.5 断点续传 | 运行时 |
| CP6 | 清理后 | 临时文件 | 临时文件已删除，`.progress` 已删除 | 运行时 |

### 阶段 F：交付层（任务 9）

> **前提**：任务 8 全部验证通过后方可执行。

| 步骤 | 内容 |
|------|------|
| 9.1 | 将全部 Skill 文件推送到仓库 `skill/` 目录 |
| 9.2 | 更新 `README.md`（添加 Skill 使用说明与目录结构） |
| 9.3 | 创建最终提交 |

**验证清单**：

- [ ] GitHub 仓库 `skill/` 目录下 8 个文件均可访问
- [ ] README.md 包含使用说明
- [ ] 最终提交哈希已记录

## 3. 数据流

```
用户输入 PDF 路径
    ↓
[check_env.py] → JSON 状态报告 → LLM 判断是否继续
    ↓                                    ↓ (encrypted=true → 8.6 终止)
[ocr_extract.py] → pages/page_XXXX.txt + JSON 统计
    ↓                                    ↓ (quality_warning=true → 8.2 警告)
[LLM 读取页面文本] → 题目索引（内存）
    ↓                                    ↓ (索引为空 → 8.3 终止)
[LLM 参照 selection-criteria.md] → 经典题列表
    ↓                                    ↓ (数量不足 → 8.4 降级)
[LLM 参照 output-format.md] → 详解内容 → .progress 记录进度
    ↓                                    ↓ (中途中断 → 8.5 续传)
输出 经典题列表.md + 经典题详解与拓展.md
    ↓
清理临时文件 + 删除 .progress
```

## 4. Git 提交策略

> 验证（任务 8）在提交 1-4 之后、提交 5 之前执行。若验证失败，在提交 5 之前修复并重新验证。

| 提交序号 | 内容 | 提交信息 | 前提 |
|----------|------|----------|------|
| 1 | `scripts/check_env.py` + `scripts/ocr_extract.py` | `feat: add environment check and OCR extraction scripts` | 阶段 A 完成 |
| 2 | 3 个 references 文档 | `feat: add reference documents for problem coding, selection criteria, and output format` | 阶段 B 完成 |
| 3 | `SKILL.md` | `feat: add main SKILL.md workflow guide` | 阶段 C 完成 |
| 4 | 示例输出 | `feat: add sample output examples` | 阶段 D 完成 |
| 5 | README 更新 + 最终提交 | `docs: update README with skill usage instructions` | **任务 8 验证全部通过** |

## 5. 风险与应对

| 风险 | 概率 | 影响 | 应对措施 |
|------|------|------|----------|
| OCR 依赖未安装 | 中 | 高 | `check_env.py` 前置检查，给出跨平台安装命令 |
| 大 PDF 内存溢出 | 低 | 高 | 分批流式处理，`batch_size=20`，`MemoryError` 降级建议减小批次 |
| 题目识别准确率低 | 中 | 中 | 误匹配过滤规则 + 跨页判定规则 + LLM 语义修正 |
| 详解生成中断 | 低 | 中 | `.progress` 断点续传机制 |
| 输出目录不可写 | 低 | 低 | `PermissionError` 捕获 + 建议替代目录 |
| 临时文件残留 | 中 | 低 | 运行前清理上一次残留；使用 `output_dir/pages/` 隔离 |
| 磁盘空间不足 | 低 | 中 | 高 DPI 图片占用大，`check_env.py` 可选检查可用空间 |
| 路径遍历攻击 | 低 | 低 | `os.path.realpath()` 规范化 `pdf_path` |
| 并发文件冲突 | 低 | 低 | 建议每次运行使用不同 `output_dir` |

## 6. 验收标准核对清单

| DoD 项 | 对应任务 | 验证方式 | 状态 |
|--------|----------|----------|------|
| 1. check_env.py 检测依赖并返回 JSON | 任务 1 | 运行脚本检查输出 | 待验证 |
| 2. ocr_extract.py 分批流式处理 | 任务 2 | 运行脚本检查输出 | 待验证 |
| 3. SKILL.md 8 个章节完整 | 任务 6 | 检查章节完整性 | 待验证 |
| 4. selection-criteria.md 完整 | 任务 4 | 对照 spec 第 5 节 | 待验证 |
| 5. output-format.md 完整 | 任务 5 | 对照 spec 第 6 节 | 待验证 |
| 6. problem-coding.md 完整 | 任务 3 | 对照 spec 第 4 节 | 待验证 |
| 7. 异常处理覆盖 9 种 | 任务 6.8 + 任务 1-2 | 检查异常矩阵 9 行 | 待验证 |
| 8. Skill 自包含 | 全部任务 | 检查无外部依赖引用 | 待验证 |
| 9. 脚本可命令行执行 | 任务 1-2 | 运行 `python3 script.py --help` | 待验证 |
| 10. MD 文件格式合规 | 任务 7 | 对照 output-format.md | 待验证 |
| 11. quality_warning 逻辑完整 | 任务 2 + 任务 6.3 | 检查计算逻辑与流程引用 | 待验证 |
| 12. 断点续传可用 | 任务 6.7 + 任务 2 | 检查 .progress 机制 | 待验证 |
