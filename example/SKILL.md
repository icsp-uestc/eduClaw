# PDF 解析技能

## 概述

本技能将 [Docling](https://github.com/DS4SD/docling)（IBM 开源文档解析库）的核心能力封装为可直接调用的 CLI 工具，覆盖以下场景：

| 能力 | Full 引擎 | Light 引擎 |
|------|-----------|------------|
| 文本提取 | ✅ DocLayNet AI 布局 | ✅ PyMuPDF 启发式 |
| 表格识别 | ✅ TableFormer (ACCURATE/FAST) | ✅ PyMuPDF find_tables |
| 图片导出 | ✅ 页面 + 内嵌图片 | ✅ 内嵌图片 |
| OCR | ✅ EasyOCR / Tesseract / RapidOCR | ❌ |
| 双列/多列 | ✅ AI 版面分析 | ⚠️ 基于坐标排序 |
| Markdown 导出 | ✅ | ✅ |
| HTML 导出 | ✅ | ✅ |
| JSON 导出 | ✅ | ✅ |
| Text 导出 | ✅ | ✅ |
| DocTags 导出 | ✅ | ❌ |
| 文档分块 (RAG) | ✅ HybridChunker | ❌ |
| 批量处理 | ✅ convert_all | ❌ |

## 目录结构

```
skills/pdf/
├── SKILL.md                  # 本文件 — 技能文档
├── references/               # 参考文档
│   ├── batch.md              # 批量处理参考
│   ├── chunking.md           # 文档分块参考
│   ├── output.md             # 输出格式参考
│   └── parsing.md            # 解析管线参考
└── scripts/                  # CLI 脚本
    ├── install_deps.sh       # 依赖安装脚本
    ├── utils.py              # 共享工具函数
    ├── docling_full.py       # Full 引擎（需要 docling + torch）
    └── docling_light.py      # Light 引擎（仅需 pymupdf）
```

## Workflow

### Step 1 — Choose Engine

**User explicit request priority**: 
- If user explicitly states engine type (e.g. "use Full engine", "用Light引擎"), use that engine
- If user explicitly states output format (e.g. "output JSON", "导出Markdown"), use that format
- Otherwise, follow decision tree below

**Decision tree**:
```
User needs OCR? 
  → YES: Full engine
  → NO: User needs AI table recognition?
    → YES: Full engine
    → NO: User needs document chunking?
      → YES: Full engine
      → NO: Light engine (recommended)
```

### Step 2 — Install Dependencies

```bash
# Full engine (需要 torch，≥4GB 内存)
bash scripts/install_deps.sh

# Light engine (仅 pymupdf，≥512MB 内存)
bash scripts/install_deps.sh --light
```

### Step 3 — Parse PDF

**Light engine** (推荐先试):
```bash
python3.11 scripts/docling_light.py document.pdf
```

**Full engine** (需要torch):
```bash
python3.11 scripts/docling_full.py document.pdf
```

### Step 4 — Verify Output

**Success criteria**:
- Output files generated
- No error messages
- Content readable

**Failure criteria**:
- Memory error → Use Light engine
- Missing dependency → Install dependencies
- Timeout → Reduce page range

### Step 5 — Table Extraction Accuracy (CRITICAL)

**表格提取必须 100% 准确**。解析表格后，执行以下校验：

#### 5.1 行数校验

| 校验项 | 方法 | 失败处理 |
|--------|------|----------|
| **行数完整性** | 对比 PDF 原文中的行数（如"6 位高管"）与提取行数 | 若不匹配，重新解析或手动补全 |
| **跨页表格** | 检查表格是否跨页，跨页时合并所有页的行 | 使用 `--page-range` 确保覆盖所有页 |
| **表头识别** | 确认表头行不被计入数据行 | 多行表头需特殊处理 |

#### 5.2 数据对齐校验

| 校验项 | 方法 | 失败处理 |
|--------|------|----------|
| **列对齐** | 每行的列数必须与表头列数一致 | 若不一致，检查合并单元格或空值 |
| **数值归属** | 抽查 2-3 个数值，核对是否属于正确的行/列 | 若错位，重新解析或手动修正 |
| **姓名-数据匹配** | 确认每个姓名对应的数据行完整 | 若数据串行，逐行核对 |

#### 5.3 多年数据完整性

| 校验项 | 方法 | 失败处理 |
|--------|------|----------|
| **年份覆盖** | 若表格包含多年数据（如 2023/2024/2025），确认每人每年都有记录 | 缺失年份需从原 PDF 补全 |
| **数据连续性** | 同一人的多年数据应在相邻行或明确标注 | 若分散，需手动整合 |

#### 5.4 校验流程

```
1. 解析完成后，统计提取的行数
2. 与 PDF 原文描述对比（如"共 6 位高管"）
3. 若行数不符：
   a. 检查是否有跨页表格未合并
   b. 检查是否有行被误识别为表头
   c. 手动补全遗漏行
4. 抽查 2-3 个数值的行列归属
5. 若发现错位：
   a. 使用 Full 引擎 + --table-mode accurate 重新解析
   b. 若仍有问题，手动逐行核对
6. 确认多年数据完整性
```

#### 5.5 常见错误模式

| 错误模式 | 原因 | 解决方案 |
|----------|------|----------|
| **遗漏行** | 跨页表格未合并 / 行被误识别为表头 | 扩大 page-range，检查表头识别 |
| **数据错位** | 合并单元格处理不当 / 列对齐偏移 | 使用 Full 引擎 accurate 模式 |
| **多年数据缺失** | 只提取了部分年份 | 核对原 PDF 年份范围，补全缺失 |
| **姓名与数据不匹配** | 行顺序被打乱 | 逐行核对姓名与数值 |

## 表格提取最佳实践

### 高精度表格提取流程

```bash
# 1. 使用 Full 引擎 + accurate 模式
python3.11 scripts/docling_full.py document.pdf --table-mode accurate --formats json markdown

# 2. 检查输出的 JSON，确认行数
cat document_output/document.json | jq '.tables[0].rows | length'

# 3. 若行数不符，检查跨页情况
python3.11 scripts/docling_full.py document.pdf --table-mode accurate --page-range 1-20 --verbose
```

### 数据校验脚本示例

```python
import json

# 加载解析结果
with open('output/document.json') as f:
    data = json.load(f)

# 校验行数
expected_rows = 6  # 如 PDF 中说明"共 6 位高管"
actual_rows = len(data['tables'][0]['rows'])
assert actual_rows == expected_rows, f"行数不符: 期望 {expected_rows}, 实际 {actual_rows}"

# 校验列对齐
header_cols = len(data['tables'][0]['header'])
for i, row in enumerate(data['tables'][0]['rows']):
    assert len(row) == header_cols, f"第 {i+1} 行列数不符: 期望 {header_cols}, 实际 {len(row)}"

print("✅ 表格校验通过")
```

## 快速开始

### 1. 安装依赖

```bash
# 完整安装（含 torch，需要 ≥4GB 内存）
bash scripts/install_deps.sh

# 轻量安装（仅 pymupdf，适用于受限环境）
bash scripts/install_deps.sh --light
```

### 2. 解析 PDF

```bash
# 轻量模式（推荐先试）
python3.11 scripts/docling_light.py document.pdf

# 完整模式（需要 torch）
python3.11 scripts/docling_full.py document.pdf
```

## CLI 参考

### docling_light.py — 轻量解析器

**无 torch 依赖**，使用 PyMuPDF 提供文本提取、表格检测、图片导出。

```
用法: docling_light.py [OPTIONS] SOURCE

位置参数:
  SOURCE                    PDF 文件路径

选项:
  -o, --output DIR          输出目录（默认: <source>_output）
  --formats FMT [FMT ...]   输出格式: markdown html json text（默认: markdown）
  --images                  提取内嵌图片
  --tables / --no-tables    启用/禁用表格检测（默认: 启用）
  --page-range RANGE        页码范围，如 '1-5,8,10-12'
  --max-size-mb N           文件大小上限 MB（默认: 100）
  --verbose                 详细日志
```

**示例：**

```bash
# 基础 Markdown 输出
python3.11 scripts/docling_light.py report.pdf

# 多格式 + 图片
python3.11 scripts/docling_light.py report.pdf --formats markdown json html --images

# 指定页码范围
python3.11 scripts/docling_light.py report.pdf --page-range 1-10,25 -o ./output

# 纯文本导出
python3.11 scripts/docling_light.py report.pdf --formats text --no-tables
```

### docling_full.py — 完整解析器

**需要 docling + torch**，提供 AI 表格识别（TableFormer）、版面分析（DocLayNet）、OCR、分块。

```
用法: docling_full.py [OPTIONS] SOURCE

位置参数:
  SOURCE                    PDF 文件或目录（批量模式）

选项:
  -o, --output DIR          输出目录

OCR 选项:
  --ocr                     启用 OCR
  --ocr-lang LANG [LANG ...]  OCR 语言（默认: en）
  --ocr-engine ENGINE       OCR 引擎: easyocr | tesseract | rapidocr

表格选项:
  --table-mode MODE         表格模式: accurate | fast（默认: accurate）

图片选项:
  --images                  提取图片
  --image-mode MODE         图片模式: embedded | referenced | placeholder

导出选项:
  --formats FMT [FMT ...]   输出格式: markdown html json text doctags

分块选项:
  --chunk                   启用文档分块（用于 RAG）
  --chunk-size N            分块大小 tokens（默认: 512）
  --chunk-overlap N         分块重叠 tokens（默认: 64）

批量选项:
  --batch                   批量模式（SOURCE 为目录）
  --batch-workers N         并行 worker 数（默认: 2）

限制选项:
  --max-pages N             最大页数（0=不限）
  --max-size-mb N           文件大小上限 MB（默认: 100）
  --verbose                 详细日志
```

**示例：**

```bash
# AI 表格识别 + Markdown
python3.11 scripts/docling_full.py report.pdf --table-mode accurate

# OCR 中文文档
python3.11 scripts/docling_full.py scan.pdf --ocr --ocr-lang ch_sim en

# 提取图片 + 多格式导出
python3.11 scripts/docling_full.py report.pdf --images --formats markdown json html

# RAG 分块
python3.11 scripts/docling_full.py report.pdf --chunk --chunk-size 256 --chunk-overlap 32

# 批量处理整个目录
python3.11 scripts/docling_full.py ./pdf_folder/ --batch --batch-workers 4

# 全功能组合
python3.11 scripts/docling_full.py report.pdf \
  --ocr --ocr-lang en ch_sim \
  --table-mode accurate \
  --images --image-mode referenced \
  --formats markdown json html \
  --chunk --chunk-size 512
```

### install_deps.sh — 依赖安装

```bash
# 完整安装
bash scripts/install_deps.sh

# 轻量安装
bash scripts/install_deps.sh --light
```

## 核心技术说明

### 表格识别

- **Full 引擎**: 使用 TableFormer 深度学习模型
  - `ACCURATE` 模式: 基于 transformer 的精确结构识别
  - `FAST` 模式: 轻量级快速检测
  - 支持 cell matching 对齐单元格文本
- **Light 引擎**: 使用 PyMuPDF `find_tables()` 启发式检测
  - 基于线条和文本坐标识别表格
  - 速度快、零 ML 依赖

### 版面分析（双列/多列）

- **Full 引擎**: DocLayNet AI 模型自动识别
  - 支持单列、双列、三列、混合布局
  - 识别标题、段落、表格、图片、页眉页脚
- **Light 引擎**: 基于文本块 Y/X 坐标启发式排序
  - 按 20px 粒度分行，同行按 X 排序
  - 对简单双列有效，复杂布局可能有偏差

### OCR（仅 Full 引擎）

| 引擎 | 语言支持 | 速度 | 精度 |
|------|----------|------|------|
| EasyOCR | 80+ 语言 | 中 | 高 |
| Tesseract | 100+ 语言 | 快 | 中 |
| RapidOCR | 中英 | 快 | 中高 |

### 文档分块（仅 Full 引擎）

使用 `HybridChunker` 生成适合 RAG 管线的文本块：
- 基于文档结构（标题、段落边界）智能切分
- 可配置 `max_tokens` 和 `overlap`
- 输出 JSON 数组，每个 chunk 包含 `index` 和 `text`

## Performance Considerations

- **Large PDFs** (>100 pages): Use `--page-range` to process in batches
- **Memory limited** (<4GB): Use Light engine
- **Batch processing**: Use `--batch-workers 2-4` for parallel processing
- **OCR overhead**: Only enable when needed (scanned documents)
- **Table detection**: Light engine faster, Full engine more accurate
- **Output size**: JSON > Markdown > Text (choose based on needs)

## Pre-execution Checklist

- [ ] Python 3.9+ installed
- [ ] Dependencies installed (Full or Light)
- [ ] PDF file accessible
- [ ] Output directory writable
- [ ] Memory sufficient (≥4GB for Full, ≥512MB for Light)
- [ ] Disk space sufficient (≥2x PDF size)

## Error Recovery

**Retry strategy**:
1. **First attempt**: Use Light engine (fast, low memory)
2. **If output quality poor**: Retry with Full engine
3. **If still failing**: Check PDF quality (corrupted/scanned)
4. **If still failing**: Report to user with specific error

**Memory error**:
1. Switch to Light engine
2. Reduce page range: `--page-range 1-10`
3. Close other applications

**Missing dependency**:
1. Run `bash scripts/install_deps.sh`
2. Verify installation: `python3.11 -c "import docling; import fitz"`

**Timeout**:
1. Reduce page range: `--page-range 1-10`
2. Use Light engine
3. Disable OCR if not needed

**Table recognition poor**:
1. Switch to Full engine
2. Use `--table-mode accurate`
3. Check PDF quality (scanned PDFs need OCR)

## Complete Workflow Example

**Input**: `report.pdf` (50 pages, contains tables)

**Step 1**: Try Light engine first
```bash
python3.11 scripts/docling_light.py report.pdf --formats markdown json
```

**Step 2**: Check output
- If tables not recognized well → Use Full engine
- If output good → Done

**Step 3**: Use Full engine if needed
```bash
python3.11 scripts/docling_full.py report.pdf --table-mode accurate --formats markdown json
```

**Result**: ✅ Markdown + JSON files generated, tables recognized

## 环境要求

| 组件 | Full 引擎 | Light 引擎 |
|------|-----------|------------|
| Python | 3.9+ | 3.9+ |
| 内存 | ≥4 GB | ≥512 MB |
| torch | 必需 | 不需要 |
| GPU | 可选（加速） | 不需要 |

**关键依赖版本：**
- docling: ≥2.75.0 （Full）
- pymupdf: ≥1.27.0 （两者均需）
- Pillow, tabulate, pydantic （共享）

## 输出示例

运行后会在输出目录生成对应格式文件，并打印摘要：

```
==================================================
  Conversion Summary
==================================================
  source              : report.pdf
  total_pages         : 42
  selected_pages      : 42
  formats             : markdown, json
  elapsed             : 3.2s
  markdown_chars      : 28,451
  json_chars          : 45,230
  tables_found        : 8
==================================================
```

## 故障排查

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `libtorch_cpu.so mmap failed` | 内存不足 | 改用 Light 引擎 |
| `No module named 'docling'` | 未安装依赖 | `bash scripts/install_deps.sh` |
| `No module named 'fitz'` | 未安装 pymupdf | `pip install pymupdf` |
| 表格识别不准 | 复杂表格 | Full 引擎 + `--table-mode accurate` |
| 双列文本乱序 | Light 引擎限制 | 改用 Full 引擎 |
| OCR 中文乱码 | 语言未指定 | `--ocr-lang ch_sim en` |
| 输出文件过大 | JSON 格式冗余 | 使用 Markdown 或 Text |
| 处理速度慢 | 页数过多 | 使用 `--page-range` 分批处理 |
