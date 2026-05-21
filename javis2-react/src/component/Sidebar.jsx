import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { PlusIcon, BuildingOfficeIcon, CpuChipIcon } from '@heroicons/react/24/outline';
import './Sidebar.css';

// 💡 [수정] App.js와 동일하게 API Base URL을 변수로 분리했습니다.
const API_BASE_URL = 'http://localhost:5000/api';

const Sidebar = ({ onSelect, current, openModal }) => {
    const [companies, setCompanies] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchCompanies = async () => {
            try {
                // 💡 [수정] 공통 URL 변수 적용
                const response = await axios.get(`${API_BASE_URL}/company/list`);
                setCompanies(response.data);

                if (!current && response.data.length > 0) {
                    onSelect(response.data[0]);
                }
            } catch (error) {
                console.error("회사 목록을 불러오는데 실패했습니다.", error);
            } finally {
                setLoading(false);
            }
        };

        fetchCompanies();
    }, [current, onSelect]);

    return (
        <div className="sidebar-container">
            {/* 로고 영역 */}
            <div className="flex items-center gap-2 mb-10 px-2">
                <CpuChipIcon className="w-8 h-8 text-cyan-400 animate-pulse" />
                {/* 💡 [수정] 버전과 타이틀을 JAVIS 3로 당당하게 업데이트! */}
                <h1 className="text-xl font-bold text-white tracking-widest uppercase">JAVIS 3</h1>
            </div>

            {/* 회사 리스트 영역 */}
            <div className="flex-1 flex flex-col gap-2 overflow-y-auto custom-scrollbar">
                <p className="text-[10px] text-cyan-500 font-semibold mb-2 px-2 uppercase tracking-[0.2em] opacity-70">
                    Enterprise AI List
                </p>

                {loading ? (
                    <p className="text-xs text-slate-500 px-2">Loading...</p>
                ) : (
                    companies.map((company) => (
                        <button
                            key={company.id}
                            onClick={() => onSelect(company)}
                            className={`flex items-center gap-3 w-full p-3 rounded-lg transition-all duration-300 ${
                                current?.id === company.id
                                    ? 'bg-cyan-600/20 text-cyan-400 border border-cyan-500/30'
                                    : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
                            }`}
                        >
                            <BuildingOfficeIcon className={`w-5 h-5 ${current?.id === company.id ? 'text-cyan-400' : 'text-slate-500'}`} />
                            <div className="flex flex-col items-start">
                                <span className="text-sm font-bold">{company.name}</span>
                                <span className="text-[10px] opacity-50">{company.bot_name}</span>
                            </div>
                        </button>
                    ))
                )}
            </div>

            {/* 하단 추가 버튼 */}
            <div className="pt-4 border-t border-slate-800">
                <button
                    onClick={openModal}
                    className="btn-add-company flex items-center justify-center gap-2 w-full p-3 rounded-xl text-white font-bold text-sm hover:scale-[1.02] transition-transform"
                >
                    <PlusIcon className="w-4 h-4" />
                    <span>워크스페이스 추가</span>
                </button>
            </div>
        </div>
    );
};

export default Sidebar;