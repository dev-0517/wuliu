import copy
import asyncio
import json
import pytest
import httpx
from sqlalchemy import create_engine, inspect, text, update
from test_mvp import register, create_case
from config.db_config import AsyncSessionLocal
from config.migrations import upgrade_connection
from config import settings
from models.data_model import Case
from services import ai_service
from routers import cases


def analysis_result(case_id):
    return {
        "summary": "用户陈述工资未收到，尚无独立核实材料。",
        "facts": [{"statement": "用户称10月份工资未收到", "source_ref": f"case:{case_id}", "quote": "10月份工资尚未收到"}],
        "issues": ["工资实际支付情况"], "missing_information": ["应发金额及付款记录"],
        "timeline": [{"date": "2026年9月", "event": "用户称入职", "source": f"case:{case_id}", "quote": "2026年9月入职"}],
        "suggested_materials": ["劳动合同，用于核对工资约定"],
        "risks": [{"title": "缺少付款记录", "reason": "暂不能核对实际付款", "source_refs": [f"case:{case_id}"]}],
        "next_steps": [{"priority": "优先", "action": "整理工资支付记录", "reason": "核对实际到账情况"}],
        "follow_up_questions": ["约定的工资金额是多少？"],
    }


def test_general_chat_never_queries_cases_and_keeps_history(client, monkeypatch):
    headers = register(client)
    create_case(client, headers)
    conversation = client.post("/api/conversations", headers=headers, json={}).json()
    assert conversation["case_id"] is None
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "test-only-key")
    calls = []
    async def forbidden(*args):
        pytest.fail("日常聊天不应读取案件")
    async def completion(http_client, messages, tool_choice):
        assert tool_choice is None
        assert "工资" not in json.dumps(messages, ensure_ascii=False)
        assert "日常聊天模式" in messages[0]["content"]
        calls.append(copy.deepcopy(messages))
        return {"role": "assistant", "content": "你好，今天想聊点什么？"}, 8
    monkeypatch.setattr(ai_service, "get_case_context", forbidden)
    monkeypatch.setattr(ai_service, "request_completion", completion)
    url = f"/api/conversations/{conversation['id']}"
    result = client.post(url+"/messages", headers=headers, json={"content": "你好小诺"})
    assert result.status_code == 200, result.text
    assert result.json()["reply"]["sources"] == []
    assert "法律意见" not in result.json()["reply"]["content"]
    assert result.json()["title"] == "你好小诺"
    assert client.post(url+"/messages", headers=headers, json={"content": "陪我聊聊"}).status_code == 200
    assert [m["role"] for m in calls[1]] == ["system", "user", "assistant", "user"]
    assert len(client.get(url, headers=headers).json()["messages"]) == 4


def test_conversation_filters_search_rename_and_ownership(client, monkeypatch):
    first, second = register(client, "first_user"), register(client, "second_user")
    case_id = create_case(client, first)
    general = client.post("/api/conversations", headers=first, json={"case_id": None}).json()
    bound = client.post("/api/conversations", headers=first, json={"case_id": case_id}).json()
    url = f"/api/conversations/{general['id']}"
    assert client.patch(url, headers=second, json={"title": "不应修改"}).status_code == 404
    assert client.patch(url, headers=first, json={"title": " "}).status_code == 422
    assert client.patch(url, headers=first, json={"title": "学习计划"}).status_code == 200
    assert [r["id"] for r in client.get("/api/conversations?mode=general&q=学习", headers=first).json()] == [general["id"]]
    assert [r["id"] for r in client.get("/api/conversations?mode=case", headers=first).json()] == [bound["id"]]
    assert client.get("/api/conversations?q=%25", headers=first).json() == []
    assert client.get("/api/conversations?mode=general", headers=second).json() == []
    async def answer(*args, **kwargs): return "一起拆解难题。", 1
    monkeypatch.setattr("routers.chat.generate_answer", answer)
    assert client.post(url+"/messages", headers=first, json={"content": "复习数学"}).status_code == 200
    assert len(client.get("/api/conversations?q=复习数学", headers=first).json()) == 1
    # 删除一个案件不会删除独立的日常对话。
    assert client.delete(f"/api/cases/{case_id}", headers=first).status_code == 200
    assert client.get(url, headers=first).status_code == 200
    assert client.get(f"/api/conversations/{bound['id']}", headers=first).status_code == 404


def test_answer_source_snapshots_survive_material_edits(client, monkeypatch):
    headers = register(client)
    case_id = create_case(client, headers)
    base = f"/api/cases/{case_id}"
    material = client.post(base+"/materials", headers=headers, json={"name": "合同", "description": "最初的合同说明", "status": "已有"}).json()
    conversation = client.post("/api/conversations", headers=headers, json={"case_id": case_id}).json()
    async def answer(*args, **kwargs):
        assert kwargs["context"]["材料"][0]["说明"] == "最初的合同说明"
        return "根据合同文字记录，请核对原件。", 10
    monkeypatch.setattr("routers.chat.generate_answer", answer)
    url = f"/api/conversations/{conversation['id']}"
    response = client.post(url+"/messages", headers=headers, json={"content": "有什么材料？"})
    assert response.status_code == 200, response.text
    client.put(base+f"/materials/{material['id']}", headers=headers, json={"name": "合同", "description": "已经修改", "status": "待补充"})
    reply = client.get(url, headers=headers).json()["messages"][-1]
    assert reply["sources"][-1]["text"] == "合同\n最初的合同说明"
    assert reply["sources"][-1]["status"] == "已有"


def test_analysis_source_validation_and_history(client, monkeypatch):
    first, second = register(client, "first_user"), register(client, "second_user")
    case_id = create_case(client, first)
    payload = analysis_result(case_id)
    async def answer(*args, **kwargs): return json.dumps(payload, ensure_ascii=False), 40
    monkeypatch.setattr(cases, "generate_answer", answer)
    url = f"/api/cases/{case_id}"
    result = client.post(url+"/analysis", headers=first)
    assert result.status_code == 200, result.text
    assert result.json()["schema_version"] == 2
    assert result.json()["facts"][0]["record_type"] == "用户陈述"
    history = client.get(url+"/analysis/history", headers=first).json()
    assert len(history) == 1
    revision_url = url+f"/analysis/history/{history[0]['id']}"
    assert client.get(revision_url, headers=second).status_code == 404
    assert client.get(url+"/analysis/history", headers=second).status_code == 404
    client.post(url+"/materials", headers=first, json={"name": "付款记录", "status": "待补充"})
    assert client.get(url, headers=first).json()["analysis"] is None
    assert client.get(revision_url, headers=first).json()["analysis"]["summary"] == payload["summary"]
    assert len(client.get(url+"/analysis/history", headers=first).json()) == 1
    # 已存在的引用编号但伪造摘录，也不能通过。
    payload["facts"][0]["quote"] = "用户已收到赔偿一百万元"
    assert client.post(url+"/analysis", headers=first).status_code == 502
    payload["facts"][0]["quote"] = "10月份工资尚未收到"
    payload["facts"][0]["source_ref"] = "material:99999"
    assert client.post(url+"/analysis", headers=first).status_code == 502
    payload["facts"][0]["source_ref"] = f"case:{case_id}"
    payload["timeline"][0]["date"] = "2027年1月"
    assert client.post(url+"/analysis", headers=first).status_code == 502
    assert len(client.get(url+"/analysis/history", headers=first).json()) == 1


def test_analysis_rejects_changes_during_generation(client, monkeypatch):
    headers = register(client)
    case_id = create_case(client, headers)
    async def answer(*args, **kwargs):
        async with AsyncSessionLocal() as db:
            await db.execute(update(Case).where(Case.id == case_id).values(description="案情已经在其他窗口修改，这是一段新的描述。"))
            await db.commit()
        return json.dumps(analysis_result(case_id), ensure_ascii=False), 40
    monkeypatch.setattr(cases, "generate_answer", answer)
    url = f"/api/cases/{case_id}"
    assert client.post(url+"/analysis", headers=headers).status_code == 409
    assert client.get(url+"/analysis/history", headers=headers).json() == []
    assert client.get(url, headers=headers).json()["analysis"] is None


def test_chat_rejects_foreign_source_and_does_not_save(client, monkeypatch):
    headers = register(client)
    case_id = create_case(client, headers)
    conversation = client.post("/api/conversations", headers=headers, json={"case_id": case_id}).json()
    async def answer(*args, **kwargs): return "请参照【material:999999】。", 1
    monkeypatch.setattr("routers.chat.generate_answer", answer)
    url = f"/api/conversations/{conversation['id']}"
    assert client.post(url+"/messages", headers=headers, json={"content": "请帮我整理"}).status_code == 502
    assert client.get(url, headers=headers).json()["messages"] == []


def test_general_provider_payload_has_no_case_tools(client, monkeypatch):
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "test-only-key")
    def provider(request):
        body = json.loads(request.content)
        assert "tools" not in body
        assert "tool_choice" not in body
        return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": "你好"}}], "usage": {"total_tokens": 3}})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(provider)) as http:
            result, tokens = await ai_service.request_completion(http, [{"role": "user", "content": "你好"}], None)
            assert result["content"] == "你好"
            assert tokens == 3
    client.portal.call(run)


def test_duplicate_send_is_rejected_during_generation(client, monkeypatch):
    from main import app
    headers = register(client)
    conversation = client.post("/api/conversations", headers=headers, json={}).json()
    url = f"/api/conversations/{conversation['id']}/messages"
    async def run():
        started, release = asyncio.Event(), asyncio.Event()
        async def answer(*args, **kwargs):
            started.set()
            await release.wait()
            return "你好", 1
        monkeypatch.setattr("routers.chat.generate_answer", answer)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as http:
            first = asyncio.create_task(http.post(url, headers=headers, json={"content": "第一条"}))
            try:
                await asyncio.wait_for(started.wait(), timeout=5)
                duplicate = await http.post(url, headers=headers, json={"content": "重复发送"})
                assert duplicate.status_code == 409
            finally:
                release.set()
            assert (await first).status_code == 200
    client.portal.call(run)
    history = client.get(f"/api/conversations/{conversation['id']}", headers=headers).json()["messages"]
    assert len(history) == 2
    assert history[0]["content"] == "第一条"


def test_sqlite_upgrade_preserves_messages_and_is_idempotent(tmp_path):
    engine = create_engine("sqlite:///"+str(tmp_path/"legacy.db"))
    with engine.connect() as c:
        c.exec_driver_sql("PRAGMA foreign_keys=ON")
        c.exec_driver_sql("CREATE TABLE users (id INTEGER PRIMARY KEY)")
        c.exec_driver_sql("CREATE TABLE cases (id INTEGER PRIMARY KEY)")
        c.exec_driver_sql("CREATE TABLE conversations (id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),case_id INTEGER NOT NULL REFERENCES cases(id),title VARCHAR(100) NOT NULL,created_at DATETIME NOT NULL,updated_at DATETIME NOT NULL)")
        c.exec_driver_sql("CREATE TABLE messages (id INTEGER PRIMARY KEY,conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,content TEXT)")
        c.exec_driver_sql("INSERT INTO users VALUES (1)")
        c.exec_driver_sql("INSERT INTO cases VALUES (1)")
        c.exec_driver_sql("INSERT INTO conversations VALUES (1,1,1,'旧对话','2026-11-03','2026-11-03')")
        c.exec_driver_sql("INSERT INTO messages VALUES (1,1,'原消息')")
        c.commit()
        upgrade_connection(c)
        upgrade_connection(c)
        assert next(col for col in inspect(c).get_columns("conversations") if col["name"] == "case_id")["nullable"]
        assert c.execute(text("SELECT content FROM messages")).scalar_one() == "原消息"
        assert c.exec_driver_sql("PRAGMA foreign_key_check").all() == []
        assert c.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        c.exec_driver_sql("INSERT INTO conversations VALUES (2,1,NULL,'日常','2026-11-03','2026-11-03')")
        c.exec_driver_sql("DELETE FROM conversations WHERE id=1")
        assert c.execute(text("SELECT count(*) FROM messages")).scalar_one() == 0
    engine.dispose()
