from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import select, or_
from config.db_config import get_database_session
from models.data_model import Case, Material, AnalysisRevision, now
from schemas.requests import CaseRequest, MaterialRequest
from crud.cases import get_owned_case, get_case_context
from utils.security import get_current_user
from services.ai_service import generate_answer
from config.settings import DEEPSEEK_MODEL
from services.grounding import source_catalog, validate_analysis_sources, fingerprint
from services.analysis_service import analysis_prompt, archive_analysis
from services.pdf_extract import extract_pdf_materials
from datetime import timedelta
from sqlalchemy import func

router = APIRouter(prefix="/api/cases", tags=["案件与材料"])
busy_analyses = set()

@router.get("")
async def list_cases(q: str = Query("", max_length=100), page: int = Query(1, ge=1), user=Depends(get_current_user), db=Depends(get_database_session)):
    statement = select(Case).where(Case.user_id == user.id)
    if q.strip():
        statement = statement.where(or_(Case.title.contains(q.strip(), autoescape=True), Case.description.contains(q.strip(), autoescape=True)))
    return (await db.scalars(statement.order_by(Case.updated_at.desc(), Case.id.desc()).offset((page-1)*20).limit(20))).all()

@router.post("", status_code=201)
async def create_case(data: CaseRequest, user=Depends(get_current_user), db=Depends(get_database_session)):
    case = Case(user_id=user.id, **data.model_dump())
    db.add(case)
    await db.commit()
    await db.refresh(case)
    return case

@router.get("/{case_id}")
async def detail(case_id: int, user=Depends(get_current_user), db=Depends(get_database_session)):
    return await get_owned_case(db, user.id, case_id)

@router.put("/{case_id}")
async def update(case_id: int, data: CaseRequest, user=Depends(get_current_user), db=Depends(get_database_session)):
    case = await get_owned_case(db, user.id, case_id)
    await archive_analysis(db, case)
    for key, value in data.model_dump().items():
        setattr(case, key, value)
    case.analysis = None  # 案情修改后，旧分析不再作为当前结果展示。
    case.updated_at = now()
    await db.commit()
    return case

@router.delete("/{case_id}")
async def remove(case_id: int, user=Depends(get_current_user), db=Depends(get_database_session)):
    case = await get_owned_case(db, user.id, case_id)
    await db.delete(case)
    await db.commit()
    return {"message": "案件及关联材料、会话已删除"}

@router.get("/{case_id}/materials")
async def materials(case_id: int, user=Depends(get_current_user), db=Depends(get_database_session)):
    await get_owned_case(db, user.id, case_id)
    return (await db.scalars(select(Material).where(Material.case_id == case_id).order_by(Material.id.desc()))).all()

@router.post("/{case_id}/materials", status_code=201)
async def add_material(case_id: int, data: MaterialRequest, user=Depends(get_current_user), db=Depends(get_database_session)):
    case = await get_owned_case(db, user.id, case_id)
    await archive_analysis(db, case)
    material = Material(case_id=case_id, **data.model_dump())
    db.add(material)
    case.analysis = None
    case.updated_at = now()
    await db.commit()
    await db.refresh(material)
    return material

@router.post("/{case_id}/materials/pdf", status_code=201)
async def import_pdf_materials(case_id: int, file: UploadFile = File(...), user=Depends(get_current_user), db=Depends(get_database_session)):
    """上传 PDF，提取文字后按页写入材料清单，供案情梳理使用。"""
    case = await get_owned_case(db, user.id, case_id)
    filename = file.filename or "材料.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(400, "仅支持 PDF 文件")
    if file.content_type and file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(400, "仅支持 PDF 文件")
    data = await file.read()
    try:
        rows = extract_pdf_materials(filename, data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    await archive_analysis(db, case)
    materials = [Material(case_id=case_id, **row) for row in rows]
    db.add_all(materials)
    case.analysis = None
    case.updated_at = now()
    await db.commit()
    for material in materials:
        await db.refresh(material)
    return {"imported": len(materials), "materials": materials}

@router.put("/{case_id}/materials/{material_id}")
async def update_material(case_id: int, material_id: int, data: MaterialRequest, user=Depends(get_current_user), db=Depends(get_database_session)):
    case = await get_owned_case(db, user.id, case_id)
    await archive_analysis(db, case)
    material = await db.scalar(select(Material).where(Material.id == material_id, Material.case_id == case_id))
    if material is None:
        raise HTTPException(404, "材料不存在")
    for key, value in data.model_dump().items():
        setattr(material, key, value)
    case.analysis = None
    case.updated_at = now()
    await db.commit()
    return material

@router.delete("/{case_id}/materials/{material_id}")
async def delete_material(case_id: int, material_id: int, user=Depends(get_current_user), db=Depends(get_database_session)):
    case = await get_owned_case(db, user.id, case_id)
    await archive_analysis(db, case)
    material = await db.scalar(select(Material).where(Material.id == material_id, Material.case_id == case_id))
    if material is None:
        raise HTTPException(404, "材料不存在")
    await db.delete(material)
    case.analysis = None
    case.updated_at = now()
    await db.commit()
    return {"message": "已删除材料"}

@router.post("/{case_id}/analysis")
async def analyze(case_id: int, user=Depends(get_current_user), db=Depends(get_database_session)):
    case = await get_owned_case(db, user.id, case_id)
    if case_id in busy_analyses:
        raise HTTPException(409, "当前案件正在整理，请等待本次完成")
    busy_analyses.add(case_id)
    try:
        recent_count = await db.scalar(select(func.count(AnalysisRevision.id)).where(AnalysisRevision.case_id == case_id, AnalysisRevision.created_at >= now()-timedelta(minutes=1)))
        if recent_count >= 3:
            raise HTTPException(429, "请稍后再生成，当前案件每分钟最多整理 3 次")
        context = await get_case_context(db, user.id, case_id)
        sources = source_catalog(context)
        await db.commit()
        answer, tokens = await generate_answer(db, user.id, case_id, [], analysis_prompt(case.category), context=context, structured=True)
        try:
            cleaned = answer.strip()
            if cleaned.startswith("```json") and cleaned.endswith("```"):
                cleaned = cleaned[7:-3].strip()
            from schemas.analysis import AnalysisResult
            analysis = AnalysisResult.model_validate_json(cleaned).model_dump()
        except (ValueError, TypeError):
            raise HTTPException(502, "模型未返回完整有效的案情分析，请重试；原记录未更改")
        validate_analysis_sources(analysis, sources)
        # 新事务读取最新记录，并锁住案件，避免保存已过时的结果。
        case = await db.scalar(select(Case).where(Case.id == case_id, Case.user_id == user.id).with_for_update().execution_options(populate_existing=True))
        if case is None:
            raise HTTPException(404, "案件已删除")
        latest_context = await get_case_context(db, user.id, case_id)
        if fingerprint(latest_context) != fingerprint(context):
            raise HTTPException(409, "整理期间案情或材料已变化，请重新整理")
        await archive_analysis(db, case)
        case.analysis = {**analysis, "schema_version": 2, "sources": sources,
                         "input_fingerprint": fingerprint(context), "generated_at": now().isoformat() + "Z",
                         "model": DEEPSEEK_MODEL, "token_usage": tokens}
        db.add(AnalysisRevision(case_id=case_id, analysis=case.analysis))
        case.updated_at = now()
        await db.commit()
        return case.analysis
    finally:
        busy_analyses.discard(case_id)

@router.get("/{case_id}/analysis/history")
async def analysis_history(case_id: int, page: int = Query(1, ge=1), user=Depends(get_current_user), db=Depends(get_database_session)):
    await get_owned_case(db, user.id, case_id)
    rows = (await db.scalars(select(AnalysisRevision).where(AnalysisRevision.case_id == case_id).order_by(AnalysisRevision.id.desc()).offset((page-1)*20).limit(20))).all()
    return [{"id": row.id, "created_at": row.created_at, "summary": row.analysis.get("summary", ""), "model": row.analysis.get("model", "")} for row in rows]

@router.get("/{case_id}/analysis/history/{revision_id}")
async def analysis_revision(case_id: int, revision_id: int, user=Depends(get_current_user), db=Depends(get_database_session)):
    await get_owned_case(db, user.id, case_id)
    row = await db.scalar(select(AnalysisRevision).where(AnalysisRevision.id == revision_id, AnalysisRevision.case_id == case_id))
    if row is None:
        raise HTTPException(404, "分析版本不存在")
    return {"id": row.id, "created_at": row.created_at, "analysis": row.analysis}
