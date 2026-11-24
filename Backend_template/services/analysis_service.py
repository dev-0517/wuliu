from sqlalchemy import select
from models.data_model import AnalysisRevision

CATEGORY_FOCUS = {
    "劳动纠纷": "重点核对劳动关系、工资约定、实际支付和沟通记录；缺失的金额、期间、主体需追问。",
    "租房纠纷": "重点核对出租方、合同、租期、押金、交接及沟通记录。",
    "消费纠纷": "重点核对交易主体、付款、商品或服务约定、履行和退款沟通。",
    "合同纠纷": "重点核对签约主体、约定义务、实际履行、付款及违约主张的记录。",
    "婚姻家事": "注意隐私，以用户诉求为中心核对关系、财产和照顾安排，不做道德评价。",
    "其他": "先识别用户诉求和事实缺口；案件类型不清楚时提出具体追问，不擅自确定法律关系。",
}

def analysis_prompt(category):
    return """请先查询当前案件，仅依据返回的记录进行深入、具体的辅助分析。
区分用户陈述、材料文字记录、信息缺口和建议。所有陈述未经独立核验；待补充材料不是已有证据。
不要编造事实、法条、诉讼期限、日期或胜诉率；风险仅描述信息与材料的缺口、矛盾和需专业核实的事项。
每个 facts 项都给出来源编号 source_ref（如 case:1、material:2）和逐字原文 quote；quote 必须从工具返回的案情或材料说明中原样复制连续片段，禁止改写、概括、补字或合并多处文字；不要把推测作为 facts。
timeline 只记录有明确日期的事件：source 填来源编号，quote 必须为该来源的连续原文，date 必须逐字出现在 quote 中，不得将“上个月”等相对时间换算为具体日期；没有把握就留空数组。
没有日期或可靠记录就使用空数组。建议要具体、可执行，并说明先做什么及原因。
最多列出 5 个有助于推进的追问，按重要性排序，避免询问用户已经给出的信息。
返回纯 JSON，不要 Markdown 围栏，严格使用以下字段，不能增加字段：
{"summary":"简明摘要，说明哪些仅为用户陈述", "facts":[{"statement":"记录支持的陈述", "source_ref":"case:1", "quote":"连续原文"}],
"issues":["具体争议"], "missing_information":["具体缺口及其影响"],
"timeline":[{"date":"原文日期", "event":"记录中的事件", "source":"case:1", "quote":"包含该日期的连续原文"}],
"suggested_materials":["建议准备的具体材料及用途，不重复声称待补充材料已经存在"],
"risks":[{"title":"需要关注的事项", "reason":"依据与不确定性", "source_refs":["case:1"]}],
"next_steps":[{"priority":"优先或随后", "action":"可执行的一步", "reason":"为什么要做"}],
"follow_up_questions":["向用户提出的具体问题"]}
facts 最多 12 条、timeline 最多 20 条，其余每组控制在 3 至 6 条；没有内容时使用空数组。
本案关注方向：""" + CATEGORY_FOCUS.get(category, CATEGORY_FOCUS["其他"])


async def archive_analysis(db, case):
    if not case.analysis:
        return
    latest = await db.scalar(select(AnalysisRevision).where(AnalysisRevision.case_id == case.id).order_by(AnalysisRevision.id.desc()).limit(1))
    if latest is None or latest.analysis != case.analysis:
        db.add(AnalysisRevision(case_id=case.id, analysis=case.analysis))
