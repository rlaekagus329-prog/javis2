import React, { useState } from 'react';
import './CreateCompanyModal.css'; // 아래에서 만들 CSS 파일 연결

const CreateCompanyModal = ({ isOpen, onClose, onSuccess }) => {
    const [companyName, setCompanyName] = useState('');
    const [aiBotName, setAiBotName] = useState('');
    const [systemPrompt, setSystemPrompt] = useState('');
    const [isLoading, setIsLoading] = useState(false);

    // 모달이 닫혀있으면 아무것도 렌더링하지 않음
    if (!isOpen) return null;

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsLoading(true);

        try {
            const response = await fetch('http://localhost:5000/api/company/create', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    company_name: companyName,
                    ai_bot_name: aiBotName,
                    system_prompt: systemPrompt
                }),
            });

            const data = await response.json();

            if (response.ok) {
                alert(data.message); // 성공 알림
                onSuccess();         // 부모 컴포넌트(리스트 등) 새로고침 함수 호출
                onClose();           // 모달 닫기
                // 폼 초기화
                setCompanyName('');
                setAiBotName('');
                setSystemPrompt('');
            } else {
                alert(`오류: ${data.error}`);
            }
        } catch (error) {
            console.error("API 호출 에러:", error);
            alert("서버와 통신하는 중 문제가 발생했습니다.");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="modal-overlay">
            <div className="modal-content">
                <h2 className="modal-title">새로운 AI 워크스페이스 생성</h2>
                <form onSubmit={handleSubmit}>
                    <div className="input-group">
                        <label>회사명 (필수)</label>
                        <input
                            type="text"
                            className="cyber-input"
                            value={companyName}
                            onChange={(e) => setCompanyName(e.target.value)}
                            placeholder="예: 스타크 인더스트리"
                            required
                        />
                    </div>

                    <div className="input-group">
                        <label>AI 봇 이름</label>
                        <input
                            type="text"
                            className="cyber-input"
                            value={aiBotName}
                            onChange={(e) => setAiBotName(e.target.value)}
                            placeholder="예: 자비스"
                        />
                    </div>

                    <div className="input-group">
                        <label>시스템 프롬프트 (AI 성격 부여)</label>
                        <textarea
                            className="cyber-input cyber-textarea"
                            value={systemPrompt}
                            onChange={(e) => setSystemPrompt(e.target.value)}
                            placeholder="예: 당신은 사내 규정을 친절하게 설명해 주는 어시스턴트입니다."
                            rows="4"
                        />
                    </div>

                    <div className="modal-actions">
                        <button type="button" className="btn-cancel" onClick={onClose}>취소</button>
                        <button type="submit" className="btn-submit" disabled={isLoading}>
                            {isLoading ? '생성 중...' : 'AI 생성하기'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default CreateCompanyModal;