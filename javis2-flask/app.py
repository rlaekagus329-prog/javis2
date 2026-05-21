# app.py
import os
import traceback
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from dotenv import load_dotenv

# 내부 모듈 로드
from database import get_db, engine, Base
from model import Company, Document, CompanyChat
from dl.dl_engine import analyze_chat_intent
from llm.tools.engine import generate_answer
from llm.pipelines.ingest import process_pdf_to_db
from llm.agents.agent import javis_app
from langchain_core.messages import HumanMessage
import traceback

load_dotenv()

# 구동 시 테이블 자동 생성 (없을 경우에만 실행됨)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="JARVIS 2 (AI Server)")

# CORS 미들웨어 통합 설정 (Flask-CORS 대체)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- Pydantic 데이터 검증용 스키마 (DTO) 정의 ---
class ChatRequest(BaseModel):
    message: str
    company_id: int

class CompanyCreateRequest(BaseModel):
    company_name: str
    ai_bot_name: Optional[str] = None
    system_prompt: Optional[str] = None


# --- API 엔드포인트 구현 ---

@app.get('/api/ai/status')
def ai_status():
    return {
        "server": "JARVIS 2 (AI Server)",
        "status": "Online",
        "model": "EEVE-Korean (Ollama) Ready",
        "message": "사내 규정 및 복지 분석 시스템이 가동되었습니다. 🤖"
    }

@app.post('/api/ai/chat')
def ai_chat(payload: ChatRequest, db: Session = Depends(get_db)):
    user_message = payload.message
    company_id = payload.company_id

    if not user_message:
        raise HTTPException(status_code=400, detail="메시지가 없습니다.")

    try:
        # ==========================================
        # 1. 🚀 LangGraph 에이전트 네트워크 가동 (Mem0 장기 기억 포함)
        # ==========================================

        # 에이전트들이 주고받을 첫 번째 택배 상자(초기 상태)를 조립합니다.
        initial_state = {
            "messages": [HumanMessage(content=user_message)],
            "company_id": company_id,
            "user_intent": "",
            "current_worker": "",
            "review_feedback": "",
            "final_answer": "",
            "past_memories": ""  # 👈 방금 추가한 장기 기억 빈 공간!
        }

        # 컴파일된 랭그래프 앱을 실행합니다. (에이전트들이 자동으로 핑퐁을 시작함)
        final_state = javis_app.invoke(initial_state)

        # 모든 노드를 거치고 난 후, 최종 확정된 답변을 추출합니다.
        answer = final_state.get("final_answer", "죄송합니다. 답변을 생성하는 데 실패했습니다.")

        # ==========================================
        # 2. 딥러닝 분석 & DB 저장 (기존 로직 유지)
        # ==========================================
        sentiment, topic = analyze_chat_intent(user_message)
        print(f"✅ [딥러닝 기록] 감정: {sentiment}, 주제: {topic}")

        new_log = CompanyChat(
            company_id=company_id,
            user_message=user_message,
            ai_response=answer,
            sentiment=sentiment,
            topic=topic
        )
        db.add(new_log)
        db.commit()

        return {"answer": answer, "status": "success"}

    except Exception as e:
        db.rollback()
        print(f"🚨 에이전트 구동 중 치명적 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/api/ai/upload')
async def upload_file(
        company_id: int = Form(...),
        file: UploadFile = File(...),
        db: Session = Depends(get_db)
):
    try:
        if not file or file.filename == '':
            raise HTTPException(status_code=400, detail="선택된 파일이 없습니다.")

        filename = file.filename
        file_path = os.path.join(UPLOAD_FOLDER, filename)

        # 파일 수신 청크 비동기 기록 처리
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # 2. 벡터 DB 적재 가동
        process_pdf_to_db(file_path, company_id)

        # 3. Document 인덱스 메타데이터 적재
        new_document = Document(
            company_id=company_id,
            file_name=filename,
            file_path=file_path
        )
        db.add(new_document)
        db.commit()

        return {"status": "success", "message": "업로드 및 격리 저장 완료"}

    except Exception as e:
        db.rollback()
        print("\n" + "🔥"*25)
        print("🚨 업로드 중 에러 발생 🚨")
        traceback.print_exc()
        print("🔥"*25 + "\n")
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/api/company/create', status_code=status.HTTP_201_CREATED)
def create_company(payload: CompanyCreateRequest, db: Session = Depends(get_db)):
    try:
        new_company = Company(
            company_name=payload.company_name,
            ai_bot_name=payload.ai_bot_name,
            system_prompt=payload.system_prompt
        )

        db.add(new_company)
        db.commit()
        db.refresh(new_company) # 주입된 autoincrement ID 확보용

        return {
            "message": "새로운 워크스페이스가 생성되었습니다.",
            "id": new_company.company_id
        }
    except Exception as e:
        db.rollback()
        print(f"DB 저장 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/api/company/list')
def get_companies(db: Session = Depends(get_db)):
    try:
        companies = db.query(Company).all()
        company_list = []

        for c in companies:
            company_list.append({
                "id": c.company_id,
                "name": c.company_name,
                "ai_bot_name": c.ai_bot_name,
                "prompt": c.system_prompt
            })

        print(f"조회된 회사 수: {len(company_list)}")
        return company_list
    except Exception as e:
        print(f"목록 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/api/document/list/{company_id}')
def get_documents(company_id: int, db: Session = Depends(get_db)):
    try:
        docs = db.query(Document).filter(Document.company_id == company_id).all()
        doc_list = []
        for doc in docs:
            doc_list.append({
                "id": doc.doc_id,
                "name": doc.file_name,
                "date": doc.upload_date.strftime("%Y-%m-%d") if doc.upload_date else ""
            })
        return doc_list
    except Exception as e:
        print(f"문서 목록 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get('/api/company/insights/{company_id}')
def get_insights(company_id: int, db: Session = Depends(get_db)):
    try:
        logs = db.query(CompanyChat).filter(CompanyChat.company_id == company_id).all()

        sentiment_counts = {"긍정": 0, "부정": 0, "중립": 0}
        topic_counts = {}

        for log in logs:
            if log.sentiment:
                s = "긍정" if "긍정" in log.sentiment else "부정" if "부정" in log.sentiment else "중립"
                sentiment_counts[s] += 1

            if log.topic:
                topic_counts[log.topic] = topic_counts.get(log.topic, 0) + 1

        sentiment_data = [{"name": k, "value": v} for k, v in sentiment_counts.items() if v > 0]
        topic_data = [{"name": k, "value": v} for k, v in topic_counts.items()]

        briefing = "데이터가 부족하여 분석을 대기 중입니다."
        if logs:
            top_topic = max(topic_counts, key=topic_counts.get) if topic_counts else "없음"
            if sentiment_counts.get("부정", 0) > sentiment_counts.get("긍정", 0):
                briefing = f"⚠️ [경고] 최근 '{top_topic}' 관련 문의가 가장 많으며, 전체 대화의 감정선이 부정적입니다. 즉각적인 조직 문화 점검 및 해당 주제에 대한 제도 개선이 권장됩니다."
            else:
                briefing = f"✅ [안정] 최근 '{top_topic}' 관련 문의가 주를 이루고 있으나, 전반적인 사내 동향은 안정적입니다."

        return {
            "sentiment": sentiment_data,
            "topic": topic_data,
            "briefing": briefing
        }
    except Exception as e:
        print(f"인사이트 조회 오류: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))