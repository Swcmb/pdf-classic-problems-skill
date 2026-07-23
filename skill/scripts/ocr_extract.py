#!/usr/bin/env python3
"""OCR 提取脚本：将图片 PDF 转换为逐页文本文件。

采用流式分批处理策略，避免全量图片驻留内存导致 OOM：
每批次转换 batch_size 页 → 逐页 OCR → 写入文本 → 释放 Image。

命令行接口：
    python3 ocr_extract.py <pdf_path> <output_dir> \
        [--dpi 300] [--lang chi_sim+eng] [--keep-temp] [--batch-size 20]

退出码：0 = 成功，1 = 错误
"""
import argparse
import gc
import json
import re
import sys
from pathlib import Path

# 控制字符正则：去除除制表符(\x09)、换行(\x0a)、回车(\x0d)外的控制字符
_CTRL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
# 匹配 3 个及以上连续换行，合并为 2 个（即最多保留一个空行）
_MULTI_NEWLINE_PATTERN = re.compile(r"\n{3,}")


def _get_total_pages(pdf_path) -> int:
    """获取 PDF 总页数。

    优先使用 pypdf；pypdf 不可用时使用 pdf2image.pdfinfo_from_path()。
    两者均失败时返回 0（视为空 PDF）。
    """
    pdf_path = str(pdf_path)
    # 优先方案：pypdf 读取页数
    try:
        from pypdf import PdfReader

        reader = PdfReader(pdf_path)
        return len(reader.pages)
    except Exception:
        pass

    # 回退方案：pdf2image 的 pdfinfo 获取页数
    try:
        from pdf2image import pdfinfo_from_path

        info = pdfinfo_from_path(pdf_path)
        return int(info.get("Pages", 0))
    except Exception:
        return 0


def convert_pdf_to_images(pdf_path: str, dpi: int = 300,
                          first_page: int = None, last_page: int = None) -> list:
    """将 PDF 指定页范围转为 PIL Image 列表。

    通过 first_page/last_page 参数实现按批次转换，由 extract_pages 在批次循环中调用。
    使用 pdf2image.convert_from_path()。
    """
    from pdf2image import convert_from_path

    # 仅传入非 None 的分页参数，避免覆盖 pdf2image 默认行为
    kwargs = {"dpi": dpi}
    if first_page is not None:
        kwargs["first_page"] = first_page
    if last_page is not None:
        kwargs["last_page"] = last_page

    return convert_from_path(str(pdf_path), **kwargs)


def ocr_image(image, lang: str = "chi_sim+eng") -> str:
    """对单页图片执行 OCR，返回文本字符串。

    使用 pytesseract.image_to_string()。
    """
    import pytesseract

    return pytesseract.image_to_string(image, lang=lang)


def sanitize_text(text: str) -> str:
    """清理 OCR 文本：去除控制字符、合并多余空行。

    处理步骤：
    1. 去除控制字符（保留制表符、换行、回车）
    2. 合并 3 个及以上连续换行为 2 个
    3. 去除每行首尾空白
    4. 去除文本整体首尾空白
    """
    if not text:
        return ""
    # 去除控制字符
    text = _CTRL_PATTERN.sub("", text)
    # 合并多余空行
    text = _MULTI_NEWLINE_PATTERN.sub("\n\n", text)
    # 清理每行首尾空白
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(lines)
    # 去除整体首尾空白
    return text.strip()


def extract_pages(pdf_path: str, output_dir: str, dpi: int = 300,
                  lang: str = "chi_sim+eng", keep_temp: bool = False,
                  batch_size: int = 20) -> dict:
    """主函数：逐页 OCR 提取，输出页面文本文件。

    采用流式处理：每批次转换 batch_size 页 → 逐页 OCR → 写入文本 → 释放 Image。
    返回 JSON 统计报告。
    """
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)

    # 文本输出目录：output_dir/pages/（与临时图片目录隔离）
    pages_dir = output_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)

    # 临时图片目录：仅 keep_temp=True 时创建并保留
    temp_images_dir = None
    if keep_temp:
        temp_images_dir = output_dir / "tmp_images"
        temp_images_dir.mkdir(parents=True, exist_ok=True)

    # 获取总页数
    total_pages = _get_total_pages(pdf_path)

    # 空 PDF 异常：不计算 quality_warning，由调用方根据 total_pages 决定退出码
    if total_pages == 0:
        return {
            "total_pages": 0,
            "output_dir": str(pages_dir),
            "empty_pages": [],
            "avg_text_length": 0,
            "quality_warning": False,
            "error": "empty_pdf",
        }

    empty_pages = []
    total_text_length = 0

    # 流式分批处理，避免全量 Image 驻留内存
    for batch_start in range(0, total_pages, batch_size):
        first_page = batch_start + 1
        last_page = min(batch_start + batch_size, total_pages)

        # 批次转换：仅渲染当前批次的页面
        images = convert_pdf_to_images(
            str(pdf_path),
            dpi=dpi,
            first_page=first_page,
            last_page=last_page,
        )

        # 逐页 OCR 并写入文本文件
        for offset, image in enumerate(images):
            page_num = batch_start + offset + 1

            # OCR 提取并清理文本
            raw_text = ocr_image(image, lang=lang)
            text = sanitize_text(raw_text)

            # 写入文本文件（UTF-8 编码，无 BOM）
            text_path = pages_dir / f"page_{page_num:04d}.txt"
            text_path.write_text(text, encoding="utf-8")

            # 保留临时图片文件（默认不保留，即处理完即丢弃）
            if keep_temp and temp_images_dir is not None:
                img_path = temp_images_dir / f"page_{page_num:04d}.png"
                image.save(str(img_path), "PNG")

            # 统计空页与文本长度（空页计入长度统计，贡献 0）
            if not text:
                empty_pages.append(page_num)
            total_text_length += len(text)

            # 显式释放当前 Image 对象
            del image

        # 显式释放本批次图片列表并回收内存
        del images
        gc.collect()

    # 计算平均文本长度（包含空页，空页计为 0）
    avg_text_length = total_text_length // total_pages if total_pages > 0 else 0

    # quality_warning：空页占比 > 0.8 或平均文本长度 < 50
    empty_ratio = len(empty_pages) / total_pages if total_pages > 0 else 0
    quality_warning = (empty_ratio > 0.8) or (avg_text_length < 50)

    return {
        "total_pages": total_pages,
        "output_dir": str(pages_dir),
        "empty_pages": empty_pages,
        "avg_text_length": avg_text_length,
        "quality_warning": quality_warning,
    }


def _format_error(error_name: str, message: str) -> str:
    """格式化错误信息为 JSON 字符串。"""
    error_msg = {"error": error_name, "message": message}
    return json.dumps(error_msg, ensure_ascii=False, indent=2)


def main():
    """命令行入口：解析参数、执行提取、输出 JSON 报告。"""
    parser = argparse.ArgumentParser(
        description="将图片 PDF 转换为逐页文本文件（OCR 提取）"
    )
    parser.add_argument("pdf_path", help="输入 PDF 文件路径")
    parser.add_argument("output_dir", help="输出目录，不存在时自动创建")
    parser.add_argument("--dpi", type=int, default=300,
                        help="OCR 分辨率，默认 300")
    parser.add_argument("--lang", default="chi_sim+eng",
                        help="Tesseract 语言包，默认 chi_sim+eng")
    parser.add_argument("--keep-temp", action="store_true", default=False,
                        help="是否保留临时图片文件")
    parser.add_argument("--batch-size", type=int, default=20,
                        help="每批次转换页数，默认 20")
    args = parser.parse_args()

    try:
        report = extract_pages(
            pdf_path=args.pdf_path,
            output_dir=args.output_dir,
            dpi=args.dpi,
            lang=args.lang,
            keep_temp=args.keep_temp,
            batch_size=args.batch_size,
        )
    except MemoryError:
        # 内存不足：建议减小批次大小
        print(_format_error(
            "MemoryError",
            "内存不足，建议减小 --batch-size（如 10 或 5）后重试"
        ), file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        # 根据异常类型给出针对性安装/处理提示
        error_name = type(exc).__name__
        if error_name == "PDFInfoNotInstalledError":
            message = "poppler-utils 未安装，请先安装 poppler-utils"
        elif error_name == "TesseractNotFoundError":
            message = "tesseract-ocr 未安装，请先安装 tesseract-ocr"
        elif error_name == "PDFEncryptionError":
            message = "PDF 受密码保护，请解除密码保护后重试"
        else:
            message = str(exc)

        print(_format_error(error_name, message), file=sys.stderr)
        sys.exit(1)

    # 输出 JSON 统计报告到 stdout
    print(json.dumps(report, ensure_ascii=False, indent=2))

    # 空 PDF：退出码 1（不计算 quality_warning）
    if report.get("total_pages", 0) == 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
