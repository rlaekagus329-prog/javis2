# llm/agents/agent.py
from typing import TypedDict, Annotated, Sequence
import operator
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage
import os
from mem0 import Memory


# 🚀 오직 구글 제미나이(Gemini) 모델만 로드하도록 통합
from langchain_google_genai import ChatGoogleGenerativeAI

# 내부 검색 도구 및 장기 기억 라이브러리
from llm.tools.engine import search_documents
from mem0 import Memory

# ---------------------------------------------------------
# 1. 멀티 AI 에이전트 및 메모리 시스템 초기화 (All Gemini)
# ---------------------------------------------------------
# 라우팅, 검색어 추출, 문서 조립 등 빠르고 가벼운 작업은 flash 모델 사용
manager_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
analyzer_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
synthesizer_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

# 코딩 및 엄격한 품질 검수 작업은 추론 능력이 뛰어난 pro 모델 할당
developer_llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0.2)
reviewer_llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0)

# Mem0 장기 기억 저장소 인스턴스
mem0_config = {
    "llm": {
        "provider": "gemini",
        "config": {
            "model": "gemini-2.5-flash",
            "temperature": 0,
            "api_key": os.environ.get("GOOGLE_API_KEY")
        }
    },
    "embedder": {
        "provider": "gemini",
        "config": {
            "model": "models/text-embedding-004", # 구글의 최신 텍스트 임베딩 모델
            "api_key": os.environ.get("GOOGLE_API_KEY")
        }
    },
    "vector_store": {
        "provider": "qdrant",
        "config": {
            "path": "./javis_memory_db",  # 👈 프로젝트 폴더 안에 이 이름으로 DB 폴더가 생성됩니다.
        }
    }
}

# 설정이 적용된 Mem0 장기 기억 저장소 인스턴스 생성
long_term_memory = Memory.from_config(mem0_config)

# ---------------------------------------------------------
# 2. State (데이터 그릇) 정의
# ---------------------------------------------------------
class JavisState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    company_id: int
    user_intent: str
    current_worker: str
    review_feedback: str
    final_answer: str
    past_memories: str

class ResearcherState(TypedDict):
    original_query: str
    company_id: int
    past_memories: str
    search_keywords: str
    retrieved_context: str
    draft_answer: str
    review_feedback: str   # 리뷰어의 피드백을 받기 위한 상태 추가

# ---------------------------------------------------------
# 3. 🕵️‍♂️ 리서처 서브그래프 (Researcher Subgraph)
# ---------------------------------------------------------
def sub_query_analyzer(state: ResearcherState):
    print("  └─ 🔍 [Sub-Researcher] pgvector 검색 최적화 키워드 추출 중...")
    prompt = f"""당신은 사내 지식 검색을 위한 핵심 키워드 추출기입니다.
    사용자의 [질문]을 분석하여, 벡터 데이터베이스에서 관련 규정이나 문서를 찾아내기 가장 적합한 명사 위주의 검색 키워드를 3~4개 이내로 추출하세요.
    결과는 오직 쉼표로 구분된 키워드들만 출력하고, 인사말이나 부연 설명은 절대 하지 마세요. (예: 연차 휴가, 잔여 수당, 보상 휴가)
    
    [질문]: {state['original_query']}"""

    response = analyzer_llm.invoke(prompt)
    return {"search_keywords": response.content.strip()}

def sub_retriever(state: ResearcherState):
    print(f"  └─ 📚 [Sub-Researcher] 사내 문서 탐색 중... (검색어: {state['search_keywords']})")
    context = search_documents(state["search_keywords"], state["company_id"])
    return {"retrieved_context": context}

def sub_synthesizer(state: ResearcherState):
    print("  └─ ✍️ [Sub-Researcher] 장기 기억과 사내 문서를 융합하여 답변 작성 중...")

    # 리뷰어의 피드백 텍스트 구성
    feedback = state.get("review_feedback", "")
    feedback_text = f"\n\n[🔥 이전 답변 반려 사유 및 수정 지시]: {feedback}\n위 지시사항을 철저히 반영하여 답변을 전면 수정하세요." if feedback and feedback != "PASS" else ""

    prompt = f"""당신은 사내 규정 및 문서 분석 전문가입니다. 
    제공된 [참고 문서]와 사용자의 [과거 핵심 기억]을 바탕으로 원래 질문에 대해 사실에 근거하여 명확하게 답변을 작성하세요.
    만약 참고 문서에서 직접적인 답변을 도출할 수 없다면, 임의로 말을 지어내지 말고 "업로드된 문서에서 관련 내용을 찾을 수 없습니다."라고 정중하게 답변하세요.{feedback_text}
    
    [과거 핵심 기억]
    {state['past_memories']}
    
    [참고 문서]
    {state['retrieved_context']}
    
    [원래 질문]
    {state['original_query']}"""

    response = synthesizer_llm.invoke(prompt)
    return {"draft_answer": response.content}

# 서브 워크플로우 그래프 조립
researcher_workflow = StateGraph(ResearcherState)
researcher_workflow.add_node("analyzer", sub_query_analyzer)
researcher_workflow.add_node("retriever", sub_retriever)
researcher_workflow.add_node("synthesizer", sub_synthesizer)

researcher_workflow.set_entry_point("analyzer")
researcher_workflow.add_edge("analyzer", "retriever")
researcher_workflow.add_edge("retriever", "synthesizer")
researcher_workflow.add_edge("synthesizer", END)

researcher_app = researcher_workflow.compile()

# ---------------------------------------------------------
# 4. 🌐 메인 그래프 (Main Graph) 노드 정의
# ---------------------------------------------------------
def recall_memory_node(state: JavisState):
    print("\n⏳ [Memory Node] 사용자의 과거 대화 히스토리 및 장기 기억 검색 중...")
    user_message = state["messages"][-1].content
    user_id = str(state["company_id"])

    memories = long_term_memory.search(query=user_message, filters={"user_id": user_id})
    parsed_memories = []

    if memories:
        memory_list = memories.get("results", memories) if isinstance(memories, dict) else memories
        for m in (memory_list or []):
            if isinstance(m, dict):
                parsed_memories.append(f"- {m.get('memory', m)}")
            elif hasattr(m, 'memory'):
                parsed_memories.append(f"- {m.memory}")
            elif isinstance(m, str):
                parsed_memories.append(f"- {m}")

    memory_str = "\n".join(parsed_memories) if parsed_memories else ""
    if memory_str:
        print(f"💡 [Memory Node] 로드된 장기 기억 내역:\n{memory_str}")
    else:
        print("💡 [Memory Node] 관련된 과거 장기 기억이 존재하지 않습니다.")

    return {"past_memories": memory_str}

def manager_node(state: JavisState):
    print("🚦 [Manager Node] 사용자 요청 의도 파악 및 라우팅 판단 중... (Gemini 2.5 Flash)")
    user_message = state["messages"][-1].content
    memories = state.get("past_memories", "")

    prompt = f"""당신은 Javis 시스템의 총괄 지휘 매니저입니다.
    사용자의 질문 및 과거 기억 컨텍스트를 분석하여 시스템 분기 처리를 수행해야 합니다.
    
    - 코딩 질문, 알고리즘 구현, 시스템 에러 로그 해석, 아키텍처 설계와 관련된 요청이라면 단 한 단어로 "code"라고 답변하세요.
    - 회사 규정, 복지, 인사 제도, 일반 문서 조회 및 일반 상식 문의라면 단 한 단어로 "research"라고 답변하세요.
    
    [과거 기억]: {memories}
    [사용자 질문]: {user_message}"""

    response = manager_llm.invoke(prompt)
    intent = "code" if "code" in response.content.strip().lower() else "research"
    return {"user_intent": intent}

def researcher_node_wrapper(state: JavisState):
    print("🕵️‍♂️ Gemini 2.5 Flash [Researcher Node] 서브 워크플로우(Analyzer ➔ Retriever ➔ Synthesizer) 가동")

    user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    user_message = user_messages[-1].content if user_messages else state["messages"][0].content

    sub_initial_state = {
        "original_query": user_message,
        "company_id": state["company_id"],
        "past_memories": state.get("past_memories", ""),
        "search_keywords": "",
        "retrieved_context": "",
        "draft_answer": "",
        "review_feedback": state.get("review_feedback", "") # 메인 그래프의 피드백 인계
    }

    sub_final_state = researcher_app.invoke(sub_initial_state)

    return {
        "current_worker": "researcher",
        "final_answer": sub_final_state["draft_answer"]
    }

def developer_node(state: JavisState):
    print("👨‍💻 [Developer Node] 소스코드 설계 및 구현 진행 중... (Claude 3.5)")
    user_message = state["messages"][-1].content
    feedback = state.get("review_feedback", "")
    memories = state.get("past_memories", "")

    feedback_text = f"\n\n[시니어 리뷰어의 반려 사유 및 피드백]: {feedback}" if feedback and feedback != "PASS" else ""

    # 🚀 프롬프트 수정: 인사말 생략, 코드 우선, 설명은 짧고 간결하게
    prompt = f"""당신은 실용적이고 핵심만 짚어주는 시니어 소프트웨어 엔지니어입니다.
    사용자의 요청에 대해 인사말이나 장황한 서론 없이, 곧바로 사용할 수 있는 [정확하고 깔끔한 코드]를 먼저 제시하세요.
    코드에 대한 설명은 반드시 3~4줄 이내의 짧은 불릿 포인트로 핵심만 요약해서 작성하세요.
    오버엔지니어링을 피하고 사용자가 요구한 수준에 딱 맞는 코드를 작성하세요.
    [과거 기억]에 코딩 스타일이 있다면 반영하세요.{feedback_text}
    
    [과거 기억]: {memories}
    [개발 요청사항]: {user_message}"""

    response = developer_llm.invoke(prompt)
    return {"current_worker": "developer", "final_answer": response.content}

def reviewer_node(state: JavisState):
    print("🧐 [Reviewer Node] 결과물 품질 검수 및 버그 스캐닝 중... (GPT-4o)")

    user_messages = [m for m in state["messages"] if isinstance(m, HumanMessage)]
    user_message = user_messages[-1].content if user_messages else state["messages"][0].content

    worker_answer = state.get("final_answer", "")

    prompt = f"""당신은 실용적이고 합리적인 품질 검수 리뷰어입니다.
    담당 워커가 작성한 답변이 사용자의 질문에 대한 '핵심적인 답'을 제공하고 있는지 확인하세요.
    
    [검토 기준]
    - 사용자가 묻는 핵심 내용이 포함되어 있는가?
    - 심각한 사실관계 오류나 할루시네이션(환각)이 없는가?
    - 단, 워커가 "문서에서 내용을 찾을 수 없다"고 답변한 경우, 이는 할루시네이션을 방지한 올바른 조치이므로 무조건 "PASS" 처리할 것.
    
    위 기준을 충족한다면 문맥이 다소 투박하더라도 오직 "PASS" 라고만 출력하세요.
    오직 사용자의 질문에 대답하지 못했거나 치명적인 오류가 있을 때만 그 이유와 구체적인 수정 지시사항을 작성하세요.
    
    [사용자 원래 질문]: {user_message}
    [담당 워커의 답변]: {worker_answer}"""

    response = reviewer_llm.invoke(prompt)
    feedback = response.content.strip()

    if "PASS" in feedback.upper():
        print("  ▶ ✅ 검수 통과 (PASS): 사용자 화면으로 전송을 승인합니다.")
        return {"review_feedback": "PASS"}
    else:
        print(f"  ▶ ❌ 검수 반려 (FAIL): 재작업 지시 전달. 사유: {feedback[:50]}...")
        return {"review_feedback": feedback}

def memorize_node(state: JavisState):
    print("💾 [Memorize Node] 최종 통과된 대화 핵심 요소를 인지하고 장기 기억(Mem0)에 영구 각인 중...")
    user_message = state["messages"][-1].content
    final_answer = state["final_answer"]
    user_id = str(state["company_id"])

    conversation = [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": final_answer}
    ]
    long_term_memory.add(conversation, user_id=user_id)
    return {}

# ---------------------------------------------------------
# 5. 🌐 메인 그래프 조립 및 라우팅 엣지 셋업
# ---------------------------------------------------------
def route_from_manager(state: JavisState):
    return state["user_intent"]

def route_from_reviewer(state: JavisState):
    if state["review_feedback"] == "PASS":
        return "memorize"
    return state["current_worker"]

main_workflow = StateGraph(JavisState)

main_workflow.add_node("recall", recall_memory_node)
main_workflow.add_node("manager", manager_node)
main_workflow.add_node("researcher", researcher_node_wrapper)
main_workflow.add_node("developer", developer_node)
main_workflow.add_node("reviewer", reviewer_node)
main_workflow.add_node("memorize", memorize_node)

main_workflow.set_entry_point("recall")
main_workflow.add_edge("recall", "manager")

main_workflow.add_conditional_edges(
    "manager",
    route_from_manager,
    {
        "code": "developer",
        "research": "researcher"
    }
)
main_workflow.add_edge("researcher", "reviewer")
main_workflow.add_edge("developer", "reviewer")

main_workflow.add_conditional_edges(
    "reviewer",
    route_from_reviewer,
    {
        "memorize": "memorize",
        "developer": "developer",
        "researcher": "researcher"
    }
)
main_workflow.add_edge("memorize", END)

javis_app = main_workflow.compile()