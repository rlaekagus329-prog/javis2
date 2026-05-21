# [dl_engine.py]
from transformers import pipeline

# 1. 딥러닝 감정 분석 모델 로딩 (HuggingFace)
print("🧠 감정 분석 딥러닝 모델 로딩 중...")
try:
    sentiment_analyzer = pipeline("text-classification", model="matthewburke/korean_sentiment")
    print("✅ 감정 분석 모델 로딩 완료!")
except Exception as e:
    print(f"🚨 모델 로딩 실패: {e}")
    sentiment_analyzer = None

def analyze_chat_intent(user_text):
    if sentiment_analyzer is None:
        return "분석불가", "일반문의"

    try:
        # --- [1단계: 딥러닝 감정 분석] ---
        result = sentiment_analyzer(user_text)[0]
        sentiment = "긍정" if result['label'] == 'LABEL_1' else "부정"

        # --- [2단계: 주제 추출 및 감정 보정 (Rule-based)] ---
        topic = "일반문의"

        # 긍정/인사 키워드
        positive_words = ["안녕", "반가", "고마", "감사", "수고", "좋아", "최고", "추천", "부탁"]

        # 1. 인사 및 감사 (긍정 강화)
        if any(word in user_text for word in positive_words):
            topic = "인사/감사"
            sentiment = "긍정"

        # 2. 퇴사/이직 (기존 로직)
        elif any(word in user_text for word in ["퇴사", "이직", "그만", "퇴직금", "사직"]):
            topic = "퇴사/이직"
            sentiment = "부정"

        # 3. 근무환경 (기존 로직)
        elif any(word in user_text for word in ["야근", "초과근무", "연장", "피곤", "번아웃"]):
            topic = "근무환경/번아웃"

        # 4. 휴가/복지 (기존 로직)
        elif any(word in user_text for word in ["휴가", "연차", "반차", "휴일", "대체휴무", "복지", "지원"]):
            topic = "휴가/복지"
            if sentiment == "부정": sentiment = "긍정"

            # 5. 급여/보상 (기존 로직)
        elif any(word in user_text for word in ["급여", "월급", "연봉", "보너스", "성과급"]):
            topic = "급여/보상"

        print(f"\n🧠 [딥러닝 레이더 작동] 분석 문장: '{user_text}'")
        print(f"👉 도출된 감정: {sentiment} / 주제: {topic}\n")

        return sentiment, topic

    except Exception as e:
        print(f"🚨 딥러닝 분석 중 오류 발생: {e}")
        return "분석불가", "일반문의"

# 자체 테스트
#if __name__ == "__main__":
#    test_text = "아 요새 야근 너무 많아서 피곤한데 연차 어떻게 써?"
#    analyze_chat_intent(test_text)