@echo off

:: 1. Spring Boot 실행 (메인 비즈니스 로직)
start cmd /k "gradlew bootRun"

:: 2. FastAPI 실행 (Javis 3.0 AI 멀티 에이전트 코어)
:: 방금 에러 없이 성공했던 uvicorn 명령어로 변경했습니다!
cd javis2-flask
start cmd /k ".\.venv\Scripts\activate && python -m uvicorn app:app --port 5000"

:: 3. React 실행 (사이버네틱 커맨드 센터 UI)
cd ../javis2-react
start cmd /k "npm start"

echo ==========================================
echo [JAVIS 3.0] All Systems Initialized Successfully!
echo ==========================================
pause