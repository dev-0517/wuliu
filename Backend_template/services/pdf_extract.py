"""从 PDF 提取可入库的文字材料。扫描件无文字层时无法解析，不提供 OCR。"""
import re
from io import BytesIO
from pypdf import PdfReader

MAX_MATERIAL_CHARS = 3000
MAX_PAGES = 40
MAX_FILE_BYTES = 12 * 1024 * 1024
_CJK = r"\u4e00-\u9fff"


def extract_pdf_materials(filename: str, data: bytes) -> list[dict]:
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("PDF 超过 12MB，请先压缩或拆分后再导入")
    try:
        reader = PdfReader(BytesIO(data))
    except Exception as exc:
        raise ValueError("无法读取该 PDF，请确认文件未损坏且未加密") from exc
    if getattr(reader, "is_encrypted", False):
        raise ValueError("暂不支持加密 PDF，请先解除密码后再导入")
    if len(reader.pages) > MAX_PAGES:
        raise ValueError(f"PDF 超过 {MAX_PAGES} 页，请先拆分后再导入")

    stem = (filename or "材料").rsplit(".", 1)[0].strip() or "材料"
    stem = stem[:80]
    chunks: list[dict] = []
    for index, page in enumerate(reader.pages, start=1):
        text = normalize_pdf_text(page.extract_text() or "")
        if not text:
            continue
        for part_index, part in enumerate(_split_text(text), start=1):
            suffix = f"第{index}页" if part_index == 1 else f"第{index}页-{part_index}"
            chunks.append({
                "name": f"{stem} · {suffix}"[:100],
                "description": part,
                "status": "已有",
            })
    if not chunks:
        raise ValueError("未能从 PDF 提取到文字。若为扫描件图片，当前版本不支持 OCR，请先转为可复制文字的 PDF，或手工录入材料")
    return chunks


def normalize_pdf_text(raw: str) -> str:
    """合并换行：中文之间不插空格，避免摘录校验因排版换行失败。"""
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in raw.replace("\r", "\n").split("\n")]
    lines = [line for line in lines if line]
    if not lines:
        return ""
    merged = lines[0]
    for line in lines[1:]:
        if re.search(rf"[{_CJK}]$", merged) and re.search(rf"^[{_CJK}]", line):
            merged += line
        else:
            merged += " " + line
    return merged.strip()


def _split_text(text: str) -> list[str]:
    if len(text) <= MAX_MATERIAL_CHARS:
        return [text]
    parts, start = [], 0
    while start < len(text):
        end = start + MAX_MATERIAL_CHARS
        if end < len(text):
            cut = text.rfind("。", start, end)
            if cut <= start:
                cut = text.rfind(" ", start, end)
            if cut > start:
                end = cut + 1
        parts.append(text[start:end].strip())
        start = end
    return [part for part in parts if part]
