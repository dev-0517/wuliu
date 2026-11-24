import json
from fastapi import HTTPException
from sqlalchemy import select
from config.db_config import AsyncSessionLocal
from models.data_model import AgreementRecord, Material, Conversation, Message
from services import ai_service
from config import settings


def register(client, name="test_user"):
    response = client.post("/api/auth/register", json={"username": name, "password": "test-pass-123", "nickname": "测试用户", "agreed": True})
    assert response.status_code == 201, response.text
    return {"Authorization": "Bearer " + response.json()["token"]}


def create_case(client, headers):
    response = client.post("/api/cases", headers=headers, json={"title": "测试工资争议", "category": "劳动纠纷", "description": "2026年9月入职，用户称10月份工资尚未收到。", "goal": "整理材料"})
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_registration_consent_login_logout(client):
    payload = {"username": "test_user", "password": "test-pass-123", "nickname": "测试", "agreed": False}
    assert client.post("/api/auth/register", json=payload).status_code == 400
    headers = register(client)
    async def consent_count():
        async with AsyncSessionLocal() as db:
            return len((await db.scalars(select(AgreementRecord))).all())
    assert client.portal.call(consent_count) == 1
    assert client.post("/api/auth/register", json={**payload, "agreed": True}).status_code == 409
    assert client.post("/api/auth/login", json={"username":"test_user", "password":"wrong-password"}).status_code == 401
    assert client.post("/api/auth/login", json={"username":"test_user", "password":"test-pass-123"}).status_code == 200
    assert client.get("/api/profile",headers=headers).json()["nickname"] == "测试用户"
    assert client.post("/api/auth/logout",headers=headers).status_code == 200
    assert client.get("/api/profile",headers=headers).status_code == 401


def test_case_material_ownership_and_cascade(client):
    first, second = register(client,"first_user"), register(client,"second_user")
    case_id = create_case(client, first)
    assert client.get("/api/cases").status_code == 401
    assert client.get("/api/cases",headers=second).json() == []
    assert client.get(f"/api/cases/{case_id}",headers=second).status_code == 404
    data={"name":"合同", "description":"测试合同文字说明", "status":"已有"}
    material=client.post(f"/api/cases/{case_id}/materials",headers=first,json=data).json()
    assert client.post(f"/api/cases/{case_id}/materials",headers=second,json=data).status_code == 404
    assert client.put(f"/api/cases/{case_id}/materials/{material['id']}",headers=second,json=data).status_code == 404
    conversation=client.post("/api/conversations",headers=first,json={"case_id":case_id}).json()
    assert client.get(f"/api/conversations/{conversation['id']}",headers=second).status_code == 404
    assert client.post(f"/api/conversations/{conversation['id']}/messages",headers=second,json={"content":"查询案件"}).status_code == 404
    assert client.delete(f"/api/cases/{case_id}",headers=second).status_code == 404
    assert client.delete(f"/api/cases/{case_id}",headers=first).status_code == 200
    async def check_deleted():
        async with AsyncSessionLocal() as db:
            for model in [Material,Conversation,Message]:
                assert (await db.scalars(select(model))).all() == []
    client.portal.call(check_deleted)


def test_tool_call_database_grounding_and_history(client, monkeypatch):
    headers=register(client)
    case_id=create_case(client,headers)
    conversation=client.post("/api/conversations",headers=headers,json={"case_id":case_id}).json()
    captured=[]
    async def completion(http_client, messages, tool_choice):
        captured.append([dict(m) for m in messages])
        if len(captured)==1:
            assert tool_choice["function"]["name"]=="get_current_case"
            return {"role":"assistant","content":None,"tool_calls":[{"id":"call_1","type":"function","function":{"name":"get_current_case","arguments":"{}"}}]},10
        context=json.loads(messages[-1]["content"])
        assert context["案件ID"]==case_id
        assert context["材料"]==[]
        return {"role":"assistant","content":"根据用户陈述，尚未录入材料，请补充劳动关系证明。"},20
    monkeypatch.setattr(ai_service,"request_completion",completion)
    monkeypatch.setattr(settings,"DEEPSEEK_API_KEY","test-only-key")
    response=client.post(f"/api/conversations/{conversation['id']}/messages",headers=headers,json={"content":"目前有什么材料？"})
    assert response.status_code==200,response.text
    assert response.json()["reply"]["token_usage"]==30
    assert "仅供参考" in response.json()["reply"]["content"]
    history=client.get(f"/api/conversations/{conversation['id']}",headers=headers).json()
    assert [m["role"] for m in history["messages"]]==["user","assistant"]
    assert client.get("/api/conversations?period=week",headers=headers).json()[0]["id"]==conversation["id"]


def test_model_failure_does_not_save_fake_answer(client, monkeypatch):
    headers=register(client)
    case_id=create_case(client,headers)
    conversation=client.post("/api/conversations",headers=headers,json={"case_id":case_id}).json()
    monkeypatch.setattr(settings,"DEEPSEEK_API_KEY","")
    response=client.post(f"/api/conversations/{conversation['id']}/messages",headers=headers,json={"content":"请整理"})
    assert response.status_code==503
    assert client.get(f"/api/conversations/{conversation['id']}",headers=headers).json()["messages"]==[]


def test_analysis_validation_and_invalidation(client, monkeypatch):
    from routers import cases
    headers=register(client)
    case_id=create_case(client,headers)
    async def analyze(*args, **kwargs):
        return json.dumps({"summary":"用户陈述工资未收到", "issues":[], "missing_information":["付款记录"], "timeline":[], "suggested_materials":["劳动合同"], "facts":[], "risks":[], "next_steps":[], "follow_up_questions":[]}),20
    monkeypatch.setattr(cases,"generate_answer",analyze)
    assert client.post(f"/api/cases/{case_id}/analysis",headers=headers).status_code==200
    assert client.get(f"/api/cases/{case_id}",headers=headers).json()["analysis"]["summary"]=="用户陈述工资未收到"
    client.post(f"/api/cases/{case_id}/materials",headers=headers,json={"name":"付款记录","status":"待补充"})
    assert client.get(f"/api/cases/{case_id}",headers=headers).json()["analysis"] is None
    async def invalid(*args, **kwargs): return "并不是有效 JSON",20
    monkeypatch.setattr(cases,"generate_answer",invalid)
    assert client.post(f"/api/cases/{case_id}/analysis",headers=headers).status_code==502


def test_input_validation_and_literal_search(client):
    headers=register(client)
    create_case(client,headers)
    assert client.post("/api/cases",headers=headers,json={"title":" ","category":"劳动纠纷","description":"too short"}).status_code==422
    assert client.get("/api/cases?q=%25",headers=headers).json()==[]
    assert client.get("/api/conversations?period=invalid",headers=headers).status_code==422
