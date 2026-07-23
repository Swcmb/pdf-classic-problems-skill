# PDF Classic Problems Skill

A unified TRAE Skill for processing image-based PDFs of math problems into two Markdown documents:
- `经典题列表.md` (classic problem list only)
- `经典题详解与拓展.md` (detailed solutions and extensions only)

## Overview

This skill combines OCR text extraction, problem organization, classic problem selection, and detailed solution writing into a single automated workflow.

## Existing Skills

| Skill | Purpose |
|-------|---------|
| brainstorming | Requirements clarification and design |
| pdf | PDF text extraction and OCR |
| document-reviewer | Document review and quality assurance |

## MCP Servers

| MCP Server | Purpose |
|------------|---------|
| Sequential Thinking | Structured thinking for complex planning |
| GitHub | Repository creation and file management |

## Workflow

1. **OCR**: Extract text from image-based PDF using pytesseract + pdf2image
2. **Extract**: Organize all problems into structured Markdown format
3. **Select**: Filter classic problems based on three criteria (core concepts, representativeness, method inspiration)
4. **Solve**: Write detailed solutions with analysis, reflection, and extension problems
5. **Output**: Generate two Markdown files

## License

MIT
