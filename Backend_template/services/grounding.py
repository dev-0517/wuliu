"""来源快照和结构校验；引用存在不代表陈述已经独立核实。"""
import hashlib
import json
import re
from fastapi import HTTPException


def fingerprint(context):
    return hashlib.sha256(json.dumps(context, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def source_catalog(context):
    sources = [{"ref": context["来源编号"], "label": "案情与诉求", "kind": "用户陈述",
                "status": "待核实", "text": "\n".join([context["名称"], context["案情描述"], context["诉求"], context["阶段"]])}]
    for material in context["材料"]:
        sources.append({"ref": material["来源编号"], "label": material["名称"], "kind": "材料文字记录",
                        "status": material["状态"], "text": material["名称"] + "\n" + material["说明"]})
    return sources


def _compact(text: str) -> str:
    """去掉空白，便于核对 PDF 换行或模型摘录里多出的空格。"""
    return re.sub(r"\s+", "", text or "")


def quote_in_text(text: str, quote: str) -> bool:
    quote = (quote or "").strip()
    if not quote:
        return False
    if quote in text:
        return True
    compact_quote = _compact(quote)
    return bool(compact_quote) and compact_quote in _compact(text)


def resolve_quote_source(preferred_ref: str, quote: str, catalog: dict):
    """优先用模型给出的来源；编号偏差但摘录能唯一落到某条记录时，纠正编号。"""
    if preferred_ref in catalog and quote_in_text(catalog[preferred_ref]["text"], quote):
        return preferred_ref
    matches = [ref for ref, source in catalog.items() if quote_in_text(source["text"], quote)]
    if len(matches) == 1:
        return matches[0]
    return None


def validate_answer_sources(answer, sources):
    known = {source["ref"] for source in sources}
    cited = set(re.findall(r"【((?:case|material):\d+)】", answer))
    if not cited.issubset(known):
        raise HTTPException(502, "回答引用了不属于当前案件的记录，请重试；本轮未保存")


def validate_analysis_sources(analysis, sources):
    catalog = {s["ref"]: s for s in sources}
    for fact in analysis["facts"]:
        ref = resolve_quote_source(fact.get("source_ref", ""), fact.get("quote", ""), catalog)
        if ref is None:
            raise HTTPException(502, "分析中的来源或原文摘录未通过校验，请重新整理；原记录未更改")
        fact["source_ref"] = ref
        source = catalog[ref]
        fact["record_type"] = "待补充项目" if source["status"] == "待补充" else source["kind"]
    for event in analysis["timeline"]:
        ref = resolve_quote_source(event.get("source", ""), event.get("quote", ""), catalog)
        if ref is None:
            raise HTTPException(502, "分析中的来源或原文摘录未通过校验，请重新整理；原记录未更改")
        event["source"] = ref
        if _compact(event.get("date", "")) not in _compact(event.get("quote", "")):
            raise HTTPException(502, "时间线日期未能在原文摘录中定位，请重新整理")
    for risk in analysis["risks"]:
        if any(ref not in catalog for ref in risk["source_refs"]):
            raise HTTPException(502, "分析引用了不存在的材料，请重新整理")
    return analysis
