import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Send, Activity, User, Bot, FileUp, Loader2, Database, BookOpen, Terminal, FileText, CheckCircle2, PieChart as PieChartIcon, BarChart2 } from 'lucide-react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import Sidebar from './component/Sidebar';
import CreateCompanyModal from './component/CreateCompanyModal';
import './index.css';

// 🌐 [추가] 백엔드 API Base URL 공통 변수화 (유지보수 및 배포 최적화)
const API_BASE_URL = 'http://localhost:5000/api';

function App() {
    const [selectedCompany, setSelectedCompany] = useState(null);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [activeTab, setActiveTab] = useState('예측홈');
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [documents, setDocuments] = useState([]);
    const [insights, setInsights] = useState(null);
    const [companyChats, setCompanyChats] = useState({});

    const keyframes = `
      @keyframes gradient-move {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
      }
    `;

    const gradientStyle = {
        background: 'linear-gradient(-45deg, #2563eb, #4f46e5, #0891b2, #2563eb)',
        backgroundSize: '400% 400%',
        animation: 'gradient-move 7s ease infinite',
    };

    const currentMessages = selectedCompany && companyChats[selectedCompany.id]
        ? companyChats[selectedCompany.id]
        : [];

    useEffect(() => {
        const fetchDocumentsAndInsights = async () => {
            if (selectedCompany?.id) {
                const botName = selectedCompany.bot_name || 'JAVIS';

                setCompanyChats(prev => {
                    if (!prev[selectedCompany.id]) {
                        return {
                            ...prev,
                            [selectedCompany.id]: [
                                { role: 'assistant', content: `[${selectedCompany.name}] 에이전트 네트워크 가동. AI 협업 팀(${botName})이 준비되었습니다. 규정 문서를 업로드하거나 질문을 입력하세요.` }
                            ]
                        };
                    }
                    return prev;
                });

                try {
                    // 🚀 공통 URL 변수 적용
                    const response = await axios.get(`${API_BASE_URL}/document/list/${selectedCompany.id}`);
                    setDocuments(response.data);

                    // 🚀 공통 URL 변수 적용
                    const insightRes = await axios.get(`${API_BASE_URL}/company/insights/${selectedCompany.id}`);
                    setInsights(insightRes.data);

                } catch (error) {
                    console.error("데이터 불러오기 실패:", error);
                    setDocuments([]);
                }
            } else {
                setDocuments([]);
                setInsights(null);
            }
        };

        fetchDocumentsAndInsights();
    }, [selectedCompany]);

    const handleFileUpload = async (e) => {
        const file = e.target.files[0];
        if (!file || !selectedCompany?.id) return;

        const currentId = selectedCompany.id;
        const formData = new FormData();
        formData.append('file', file);
        formData.append('company_id', parseInt(currentId));

        setIsLoading(true);
        setCompanyChats(prev => ({
            ...prev,
            [currentId]: [...(prev[currentId] || []), { role: 'assistant', content: `LlamaParse 에이전트가 파일 구조 분석 및 벡터화를 진행 중입니다: ${file.name}...` }]
        }));

        try {
            // 🚀 공통 URL 변수 적용
            await axios.post(`${API_BASE_URL}/ai/upload`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });

            setCompanyChats(prev => ({
                ...prev,
                [currentId]: [...(prev[currentId] || []), { role: 'assistant', content: "지식 데이터 적재 완료. 이제 해당 규정 및 문서에 대해 다중 에이전트 교차 검증 질의가 가능합니다." }]
            }));

            setDocuments(prev => [...prev, { id: Date.now(), name: file.name, date: new Date().toLocaleDateString() }]);
        } catch (error) {
            console.error("업로드 에러:", error);
            setCompanyChats(prev => ({
                ...prev,
                [currentId]: [...(prev[currentId] || []), { role: 'assistant', content: "파일 업로드 및 파싱에 실패했습니다. 백엔드 로그를 확인하세요." }]
            }));
        } finally {
            setIsLoading(false);
            e.target.value = '';
        }
    };

    const sendMessage = async () => {
        if (!input.trim() || isLoading || !selectedCompany?.id) return;

        const currentId = selectedCompany.id;
        const userMsg = { role: 'user', content: input };

        setCompanyChats(prev => ({
            ...prev,
            [currentId]: [...(prev[currentId] || []), userMsg]
        }));

        setInput('');
        setIsLoading(true);

        try {
            // 🚀 LangGraph 멀티 에이전트 파이프라인 연쇄 가동을 위해 타임아웃을 120초(2분)로 넉넉하게 확장
            const response = await axios.post(`${API_BASE_URL}/ai/chat`, {
                message: userMsg.content,
                company_id: parseInt(currentId)
            }, {
                timeout: 300000
            });

            setCompanyChats(prev => ({
                ...prev,
                [currentId]: [...(prev[currentId] || []), { role: 'assistant', content: response.data.answer }]
            }));

            // 🚀 공통 URL 변수 적용
            const insightRes = await axios.get(`${API_BASE_URL}/company/insights/${currentId}`);
            setInsights(insightRes.data);

        } catch (error) {
            console.error("채팅 에러:", error);
            setCompanyChats(prev => ({
                ...prev,
                [currentId]: [...(prev[currentId] || []), { role: 'assistant', content: "에이전트 통신 오류가 발생했습니다. API 서버 가동 여부를 확인하세요." }]
            }));
        } finally {
            setIsLoading(false);
        }
    };

    const handleCompanyCreated = () => {
        window.location.reload();
    };

    return (
        <div className="flex h-screen bg-[#0B1220] text-white overflow-hidden font-mono">
            <style>{keyframes}</style>
            <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-[#001735] blur-[120px] rounded-full pointer-events-none" />

            <Sidebar
                onSelect={setSelectedCompany}
                current={selectedCompany}
                openModal={() => setIsModalOpen(true)}
            />

            {selectedCompany ? (
                <main className="flex-1 flex flex-col p-8 relative overflow-hidden">
                    <header
                        style={gradientStyle}
                        className="flex justify-between items-center p-4 rounded-xl backdrop-blur-md mb-4 shadow-[0_0_20px_rgba(34,211,238,0.3)]"
                    >
                        <div className="flex items-center gap-2">
                            <Activity className="animate-pulse text-cyan-400" size={20} />
                            <h1 className="text-xl font-bold tracking-widest text-white uppercase">
                                {selectedCompany.name} COMMAND CENTER
                            </h1>
                        </div>

                        <div className="flex items-center gap-4">
                            <div className="text-[10px] text-cyan-400 border border-cyan-400/50 px-2 py-1 rounded bg-cyan-950/50 font-bold tracking-wider shadow-[0_0_10px_rgba(34,211,238,0.2)]">
                                CORE: MULTI-AGENT ENGINE READY
                            </div>
                            <label className="cursor-pointer flex items-center gap-1 text-[11px] font-bold tracking-widest text-cyan-400 border border-cyan-500/50 px-3 py-1.5 rounded bg-cyan-900/30 hover:bg-cyan-400 hover:text-black transition-all shadow-[0_0_10px_rgba(34,211,238,0.2)]">
                                <FileUp size={14} /> 규정(PDF) 추가
                                <input type="file" className="hidden" onChange={handleFileUpload} accept=".pdf" />
                            </label>
                        </div>
                    </header>

                    <div className="flex gap-4 mb-6 border-b border-cyan-500/20 pb-2">
                        <button onClick={() => setActiveTab('예측홈')} className={`flex items-center gap-2 px-4 py-2 rounded-t-lg transition-all ${activeTab === '예측홈' ? 'text-cyan-400 border-b-2 border-cyan-400 bg-cyan-900/20' : 'text-slate-500 hover:text-cyan-300'}`}>
                            <Terminal size={16} /> <span className="font-bold text-sm tracking-widest">예측홈</span>
                        </button>
                        <button onClick={() => setActiveTab('참고문서')} className={`flex items-center gap-2 px-4 py-2 rounded-t-lg transition-all ${activeTab === '참고문서' ? 'text-cyan-400 border-b-2 border-cyan-400 bg-cyan-900/20' : 'text-slate-500 hover:text-cyan-300'}`}>
                            <BookOpen size={16} /> <span className="font-bold text-sm tracking-widest">참고문서</span>
                        </button>
                        <button onClick={() => setActiveTab('조직동향')} className={`flex items-center gap-2 px-4 py-2 rounded-t-lg transition-all ${activeTab === '조직동향' ? 'text-cyan-400 border-b-2 border-cyan-400 bg-cyan-900/20' : 'text-slate-500 hover:text-cyan-300'}`}>
                            <PieChartIcon size={16} /> <span className="font-bold text-sm tracking-widest">조직동향</span>
                        </button>
                    </div>

                    {activeTab === '예측홈' && (
                        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex-1 flex flex-col overflow-hidden">
                            <div className="flex-1 overflow-y-auto p-6 space-y-4 border border-cyan-500/20 rounded-xl bg-white/5 backdrop-blur-xl mb-6">
                                {currentMessages.map((msg, idx) => (
                                    <motion.div key={idx} initial={{ opacity: 0, x: msg.role === 'user' ? 20 : -20 }} animate={{ opacity: 1, x: 0 }} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                        <div className={`max-w-[80%] p-4 rounded-2xl backdrop-blur-sm ${msg.role === 'user' ? 'bg-cyan-600/20 text-cyan-50' : 'bg-blue-600/10 text-blue-50'}`}>
                                            <div className="text-[10px] uppercase mb-1 flex items-center gap-1 opacity-60">
                                                {msg.role === 'user' ? (
                                                    <><User size={12}/> USER</>
                                                ) : (
                                                    <><Bot size={12}/> {selectedCompany?.bot_name || 'JAVIS'}</>
                                                )}
                                            </div>
                                            <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                                        </div>
                                    </motion.div>
                                ))}
                            </div>

                            <div className="flex gap-2">
                                <input
                                    className="flex-1 bg-white/5 border border-cyan-500/30 rounded-lg p-4 outline-none focus:border-cyan-400 transition-all text-white placeholder-cyan-900"
                                    placeholder="협업 팀 에이전트에게 명령을 전달하세요..."
                                    value={input}
                                    onChange={(e) => setInput(e.target.value)}
                                    onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                                    disabled={isLoading}
                                />
                                <button
                                    onClick={sendMessage}
                                    className="bg-cyan-600/20 border border-cyan-500 text-cyan-400 hover:bg-cyan-500 hover:text-white transition-all p-4 rounded-lg disabled:opacity-50"
                                    disabled={isLoading}
                                >
                                    {isLoading ? <Loader2 className="animate-spin" size={20} /> : <Send size={20} />}
                                </button>
                            </div>
                        </motion.div>
                    )}

                    {activeTab === '참고문서' && (
                        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex-1 overflow-y-auto p-6 border border-cyan-500/20 rounded-xl bg-[#001735]/40 backdrop-blur-xl">
                            <div className="mb-10">
                                <div className="flex items-center gap-3 mb-6 border-b border-cyan-500/30 pb-4">
                                    <FileText className="text-cyan-400" size={24} />
                                    <h2 className="text-lg font-bold text-cyan-50 tracking-widest">저장된 내규 문서 목록</h2>
                                </div>
                                {documents.length > 0 ? (
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        {documents.map((doc) => (
                                            <div key={doc.id} className="p-4 border border-cyan-500/30 rounded-lg bg-black/40 hover:bg-cyan-900/20 transition-all flex items-center justify-between shadow-[0_0_15px_rgba(34,211,238,0.05)]">
                                                <div className="flex items-center gap-3">
                                                    <div className="bg-cyan-900/50 p-2 rounded-lg">
                                                        <FileText size={18} className="text-cyan-400" />
                                                    </div>
                                                    <div>
                                                        <div className="text-sm font-bold text-slate-200">{doc.name}</div>
                                                        {doc.date && <div className="text-[10px] text-cyan-600 mt-0.5 tracking-widest">{doc.date} UPLOADED</div>}
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-1 text-[10px] text-emerald-400 bg-emerald-900/30 border border-emerald-800/50 px-2 py-1 rounded">
                                                    <CheckCircle2 size={12} /> INJECTED
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="text-center py-10 border border-dashed border-cyan-500/30 rounded-lg bg-black/20">
                                        <FileUp size={32} className="text-cyan-800 mx-auto mb-3" />
                                        <p className="text-sm text-cyan-600/70 tracking-widest">업로드된 참고문서가 없습니다.</p>
                                    </div>
                                )}
                            </div>
                        </motion.div>
                    )}

                    {activeTab === '조직동향' && (
                        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="flex-1 overflow-y-auto p-6 border border-cyan-500/20 rounded-xl bg-[#001735]/40 backdrop-blur-xl">
                            <div className="flex items-center gap-3 mb-6 border-b border-cyan-500/30 pb-4">
                                <BarChart2 className="text-cyan-400" size={24} />
                                <h2 className="text-lg font-bold text-cyan-50 tracking-widest">AI 사내 동향 분석 리포트</h2>
                            </div>

                            {insights ? (
                                <div className="space-y-6">
                                    <div className="p-5 border border-cyan-500/50 rounded-xl bg-black/40 shadow-[0_0_15px_rgba(34,211,238,0.1)] relative overflow-hidden">
                                        <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-cyan-400 to-blue-600"></div>
                                        <div className="text-[10px] text-cyan-400 tracking-widest mb-2 flex items-center gap-2">
                                            <Bot size={14} /> DEEP LEARNING INSIGHT
                                        </div>
                                        <p className={`text-sm leading-relaxed font-bold ${insights.briefing.includes('경고') ? 'text-rose-400' : 'text-emerald-400'}`}>
                                            {insights.briefing}
                                        </p>
                                    </div>

                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                        <div className="p-4 border border-cyan-900/50 rounded-xl bg-black/20 shadow-[0_0_15px_rgba(34,211,238,0.05)]">
                                            <h3 className="text-xs text-slate-400 tracking-widest mb-4 text-center">직원 감정 지수 (SENTIMENT)</h3>
                                            <div className="h-[250px]">
                                                {insights.sentiment.length > 0 ? (
                                                    <ResponsiveContainer width="100%" height="100%">
                                                        <PieChart>
                                                            <Pie data={insights.sentiment} innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value">
                                                                {insights.sentiment.map((entry, index) => (
                                                                    <Cell key={`cell-${index}`} fill={entry.name === '긍정' ? '#10b981' : entry.name === '부정' ? '#f43f5e' : '#3b82f6'} />
                                                                ))}
                                                            </Pie>
                                                            <Tooltip contentStyle={{ backgroundColor: '#000', borderColor: '#22d3ee', color: '#fff', borderRadius: '8px' }} />
                                                        </PieChart>
                                                    </ResponsiveContainer>
                                                ) : (
                                                    <div className="flex items-center justify-center h-full text-xs text-slate-500">데이터가 없습니다.</div>
                                                )}
                                            </div>
                                        </div>

                                        <div className="p-4 border border-cyan-900/50 rounded-xl bg-black/20 shadow-[0_0_15px_rgba(34,211,238,0.05)]">
                                            <h3 className="text-xs text-slate-400 tracking-widest mb-4 text-center">주요 문의 주제 (TOPICS)</h3>
                                            <div className="h-[250px]">
                                                {insights.topic.length > 0 ? (
                                                    <ResponsiveContainer width="100%" height="100%">
                                                        <BarChart data={insights.topic}>
                                                            <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                                                            <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} />
                                                            <Tooltip cursor={{ fill: 'rgba(34,211,238,0.1)' }} contentStyle={{ backgroundColor: '#000', borderColor: '#22d3ee', color: '#fff', borderRadius: '8px' }} />
                                                            <Bar dataKey="value" fill="#22d3ee" radius={[4, 4, 0, 0]} />
                                                        </BarChart>
                                                    </ResponsiveContainer>
                                                ) : (
                                                    <div className="flex items-center justify-center h-full text-xs text-slate-500">데이터가 없습니다.</div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ) : (
                                <div className="flex justify-center py-12">
                                    <Loader2 className="animate-spin text-cyan-500" size={32} />
                                </div>
                            )}
                        </motion.div>
                    )}
                </main>
            ) : (
                <main className="flex-1 flex flex-col items-center justify-center bg-[#0B1220] relative z-10">
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="flex flex-col items-center text-cyan-500/50"
                    >
                        <Database size={64} className="mb-6 animate-pulse" />
                        <h2 className="text-2xl font-bold tracking-[0.3em] mb-2 text-white/50">JAVIS 3 SYSTEM</h2>
                        <p className="text-sm tracking-widest uppercase">Select a Workspace to Initialize Multi-Agent Node</p>
                    </motion.div>
                </main>
            )}

            <CreateCompanyModal
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                onSuccess={handleCompanyCreated}
            />
        </div>
    );
}

export default App;