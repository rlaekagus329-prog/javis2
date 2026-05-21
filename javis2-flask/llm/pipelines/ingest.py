import os
import nest_asyncio
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import PGVector
from llama_parse import LlamaParse

# Flask 비동기 환경 충돌 방지
nest_asyncio.apply()

# 💡 발급받은 Llama Cloud API 키를 여기에 넣어주세요!
os.environ["LLAMA_CLOUD_API_KEY"] = "llx-ocOCnplQe2cBcpRQGtKQhOGkvYuCLpHI1b38LiZfrQfwIjBm"

# 현님의 진짜 DB 연결 정보 (유지 완료!)
CONNECTION_STRING = "postgresql+psycopg2://postgres:1234@localhost:3300/javis2"
COLLECTION_NAME = "javis2_documents"

def process_pdf_to_db(file_path, company_id):
    print(f"\n🚀 [ID: {company_id}] LlamaParse로 PDF 정밀 분석 시작... (표/이미지 변환 중)")

    # 1. PyMuPDF 대신 LlamaParse로 로드
    parser = LlamaParse(
        result_type="markdown", # 표와 구조를 마크다운으로 추출!
        language="ko",
        verbose=True
    )

    parsed_docs = parser.load_data(file_path)
    full_markdown_text = "\n\n".join([doc.text for doc in parsed_docs])
    print("👉 PDF 마크다운 변환 완료!")

    # 2. 텍스트 분할 (마크다운 헤더 기준 1차 분할 -> 글자수 기준 2차 분할)
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3")
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    md_chunks = markdown_splitter.split_text(full_markdown_text)

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=100)
    final_chunks = text_splitter.split_documents(md_chunks)
    print(f"👉 텍스트 분할 완료: 총 {len(final_chunks)}개의 의미 단위 조각 생성!")

    # 3. ⭐️ 핵심: 각 조각(Chunk)에 회사 ID 이름표 달기 (유지 완료!)
    for chunk in final_chunks:
        chunk.metadata["company_id"] = int(company_id)
        # 출처를 알 수 있도록 파일명도 메타데이터에 추가해 주면 좋습니다
        chunk.metadata["source"] = os.path.basename(file_path)

    # 4. 로컬 임베딩 모델 설정 (BGE-M3 유지!)
    print("🧠 BGE-M3 임베딩 시작...")
    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-m3"
    )

    # 5. Vector DB 저장 (pgvector)
    print("💾 Vector DB에 저장 중...")
    vector_db = PGVector.from_documents(
        embedding=embeddings,
        documents=final_chunks,
        collection_name=COLLECTION_NAME,
        connection_string=CONNECTION_STRING,
        pre_delete_collection=False
    )

    print(f"✅ [ID: {company_id}] LlamaParse 문서 분석 완료: {len(final_chunks)}개의 조각이 저장되었습니다.\n")