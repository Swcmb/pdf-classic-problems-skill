#!/usr/bin/env python3
"""环境检查脚本：验证运行环境是否满足 OCR 提取要求。

检查项目：
- Python 包：pytesseract, pdf2image, Pillow, pypdf
- 系统命令：tesseract, pdftoppm
- 语言包：chi_sim（中文简体）
- PDF 文件：存在性、可读性、加密状态

命令行接口：python3 check_env.py <pdf_path>
退出码：0 = 全部就绪，1 = 有缺失项
"""
import argparse
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# 需要检查的 Python 包：展示名 → 实际导入名
# 注意：Pillow 的 PyPI 包名为 Pillow，但导入时使用 PIL
REQUIRED_PACKAGES = {
    "pytesseract": "pytesseract",
    "pdf2image": "pdf2image",
    "Pillow": "PIL",
    "pypdf": "pypdf",
}


def check_python_packages() -> dict:
    """检查 Python 包是否安装，返回 {"installed": [...], "missing": [...]}

    使用 importlib.util.find_spec() 检测每个包是否可导入。
    find_spec 返回 None 表示该包未安装。
    输出列表使用包的展示名（如 Pillow），检测时使用实际导入名（如 PIL）。
    """
    installed = []
    missing = []
    for display_name, import_name in REQUIRED_PACKAGES.items():
        if importlib.util.find_spec(import_name) is not None:
            installed.append(display_name)
        else:
            missing.append(display_name)
    return {"installed": installed, "missing": missing}


def check_system_dependencies() -> dict:
    """检查系统命令与语言包，返回 {"tesseract": bool, "chi_sim": bool, "pdftoppm": bool}

    使用 shutil.which() 检查 tesseract 和 pdftoppm 是否在 PATH 中；
    执行 tesseract --list-langs 检查输出是否包含 chi_sim 语言包。
    """
    # 检查 tesseract 命令是否存在
    tesseract_ok = shutil.which("tesseract") is not None

    # 检查 pdftoppm 命令是否存在（由 poppler-utils 提供）
    pdftoppm_ok = shutil.which("pdftoppm") is not None

    # 检查 chi_sim 语言包：执行 tesseract --list-langs 并解析输出
    chi_sim_ok = False
    if tesseract_ok:
        try:
            result = subprocess.run(
                ["tesseract", "--list-langs"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            # 按空白拆分语言代码，精确匹配 chi_sim（避免误匹配 chi_sim_vert）
            langs = result.stdout.split()
            chi_sim_ok = "chi_sim" in langs
        except (subprocess.SubprocessError, OSError):
            # 执行失败视为语言包不可用
            chi_sim_ok = False

    return {
        "tesseract": tesseract_ok,
        "chi_sim": chi_sim_ok,
        "pdftoppm": pdftoppm_ok,
    }


def _detect_encryption(pdf_path: str) -> bool:
    """检测 PDF 是否加密。

    优先使用 pypdf.PdfReader().is_encrypted 检测；
    pypdf 不可用时回退到 pdf2image.convert_from_path() 探测，
    区分 PDFEncryptionError（加密）与其他异常。
    """
    # 优先方案：pypdf 直接读取加密属性
    if importlib.util.find_spec("pypdf") is not None:
        try:
            from pypdf import PdfReader

            reader = PdfReader(pdf_path)
            return bool(reader.is_encrypted)
        except Exception:
            # pypdf 解析失败，回退到 pdf2image 探测
            pass

    # 回退方案：使用 pdf2image 探测第一页
    if importlib.util.find_spec("pdf2image") is not None:
        try:
            from pdf2image import convert_from_path
            from pdf2image.exceptions import PDFEncryptionError

            convert_from_path(pdf_path, first_page=1, last_page=1)
            return False
        except PDFEncryptionError:
            # 探测时抛出加密异常，判定为加密
            return True
        except Exception:
            # 其他异常（如 poppler 缺失）无法判定，默认未加密
            return False

    # 两个库均不可用时无法检测，默认未加密
    return False


def check_pdf_file(pdf_path: str) -> dict:
    """验证 PDF 文件，返回 {"exists": bool, "readable": bool, "encrypted": bool}

    使用 os.path.realpath() 规范化路径以防路径遍历；
    使用 os.path.exists() 与 os.access() 检查文件存在性与可读性；
    优先使用 pypdf 检测加密，pypdf 不可用时回退到 pdf2image 探测。
    """
    # 规范化路径，防止路径遍历攻击（如 ../../etc/passwd）
    real_path = os.path.realpath(str(pdf_path))

    exists = os.path.exists(real_path)
    # 文件存在且具有读权限时视为可读
    readable = exists and os.access(real_path, os.R_OK)

    encrypted = False
    if readable:
        encrypted = _detect_encryption(real_path)

    return {"exists": exists, "readable": readable, "encrypted": encrypted}


def _build_install_commands(packages: dict, system_deps: dict) -> list:
    """根据检测结果与操作系统动态生成跨平台安装命令。

    仅针对缺失项生成对应命令；全部就绪时返回空列表。
    """
    commands = []
    missing_packages = packages.get("missing", [])

    # Python 包缺失时给出 pip 安装命令
    if missing_packages:
        commands.append("pip install " + " ".join(missing_packages))

    # 判断系统依赖是否缺失
    need_tesseract = (not system_deps.get("tesseract", True)
                      or not system_deps.get("chi_sim", True))
    need_poppler = not system_deps.get("pdftoppm", True)

    if not need_tesseract and not need_poppler:
        return commands

    # 根据操作系统生成对应的系统依赖安装命令
    system = platform.system()
    if system == "Linux":
        if shutil.which("apt-get"):
            # Debian/Ubuntu 系
            if need_tesseract:
                commands.append(
                    "sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim"
                )
            if need_poppler:
                commands.append("sudo apt-get install poppler-utils")
        elif shutil.which("yum"):
            # CentOS/RHEL 系
            if need_tesseract:
                commands.append(
                    "sudo yum install tesseract tesseract-langpack-chi_sim"
                )
            if need_poppler:
                commands.append("sudo yum install poppler-utils")
    elif system == "Darwin":
        # macOS 使用 Homebrew
        if need_tesseract:
            commands.append("brew install tesseract tesseract-lang")
        if need_poppler:
            commands.append("brew install poppler")
    elif system == "Windows":
        # Windows 需手动下载安装
        if need_tesseract:
            commands.append(
                "下载 Tesseract 安装包: https://github.com/UB-Mannheim/tesseract/wiki"
            )
        if need_poppler:
            commands.append(
                "下载 poppler for Windows: "
                "https://github.com/oschwartz10612/poppler-windows/releases"
            )

    return commands


def run_all_checks(pdf_path: str) -> dict:
    """执行全部检查，返回综合状态报告。

    汇总 Python 包、系统依赖、PDF 文件检查结果，
    根据缺失项生成安装命令与整体状态。
    """
    packages = check_python_packages()
    system_deps = check_system_dependencies()
    pdf_info = check_pdf_file(pdf_path)

    install_commands = _build_install_commands(packages, system_deps)

    # 整体状态：任何缺失项、PDF 不可读或加密均视为 error
    has_missing = bool(packages["missing"])
    deps_ok = all(system_deps.values())
    pdf_ok = pdf_info["exists"] and pdf_info["readable"] and not pdf_info["encrypted"]

    status = "ok" if (not has_missing and deps_ok and pdf_ok) else "error"

    return {
        "status": status,
        "python_packages": packages,
        "system_deps": system_deps,
        "pdf_file": pdf_info,
        "install_commands": install_commands,
    }


def main():
    """命令行入口：解析参数、执行检查、输出 JSON 报告。"""
    parser = argparse.ArgumentParser(
        description="检查 OCR 提取所需的运行环境（Python 包、系统依赖、PDF 文件）"
    )
    parser.add_argument("pdf_path", help="待检查的 PDF 文件路径")
    args = parser.parse_args()

    report = run_all_checks(args.pdf_path)

    # JSON 输出到 stdout，保留中文、缩进 2 空格
    print(json.dumps(report, ensure_ascii=False, indent=2))

    # 退出码：0 = 全部就绪，1 = 有缺失项
    sys.exit(0 if report["status"] == "ok" else 1)


if __name__ == "__main__":
    main()
