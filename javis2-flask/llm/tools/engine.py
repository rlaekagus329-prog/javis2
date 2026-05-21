# engine.py
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import PGVector
import os
from dotenv import load_dotenv

load_dotenv()

# DB 연결 정보 (app.py와 동일하게 환경변수 사용 권장)
DATABASE_URL = os.getenv('DATABASE_URL')
COLLECTION_NAME = "javis2_documents"

# 임베딩 모델은 기존대로 BGE-M3 유지 (문서가 이걸로 쪼개져 있기 때문)
embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")

# Vector DB 연결 객체 생성
vector_db = PGVector(
    collection_name=COLLECTION_NAME,
    connection_string=DATABASE_URL,
    embedding_function=embeddings,
)

def search_documents(query: str, company_id: int) -> str:
    """
    LangGraph의 에이전트(리서처)가 사내 문서를 검색할 때 사용할 핵심 도구(Tool)입니다.
    """
    try:
        # 리트리버 세팅
        retriever = vector_db.as_retriever(
            search_kwargs={
                "k": 5,
                "filter": {"company_id": company_id}
            }
        )

        # 1. 문서 검색
        docs = retriever.invoke(query)

        if not docs:
            return "업로드된 참고 문서에서 관련된 내용을 찾을 수 없습니다."

        # 2. 에이전트가 읽기 편하게 하나의 텍스트로 묶어서 반환
        context = "\n\n".join(f"[참고문서 {i+1}]\n{doc.page_content}" for i, doc in enumerate(docs))
        return context

    except Exception as e:
        return f"문서 검색 중 오류 발생: {str(e)}"

# app.py와의 호환성을 위해 이름만 남겨둔 임시 껍데기 함수 (나중에 삭제)
# 당장 app.py에서 에러가 나는 것을 방지합니다.
def generate_answer(user_query, company_id):
    pass