// src/App.jsx
import React, { useState } from 'react';
import { Search, BookOpen, FileText } from 'lucide-react';
import { useExamData } from './hooks/useExamData';

function App() {
    const { exams, loading, error } = useExamData();
    const [searchTerm, setSearchTerm] = useState('');
      
    const filteredExams = exams.filter(exam =>
        exam.subject_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        exam.subject_code.toLowerCase().includes(searchTerm.toLowerCase()) ||
        exam.year.includes(searchTerm)
    );

    return (
        <div style={{ fontFamily: 'Arial, sans-serif', backgroundColor: '#f9fafb', minHeight: '100vh', color: '#1f2937' }}>
            <header style={{ backgroundColor: '#ffffff', borderBottom: '1px solid #e5e7eb', padding: '16px 32px', display: 'flex', alignItems: 'center' }}>
                <BookOpen size={24} color="#2563eb" style={{ marginRight: '10px' }} />
                <h1 style={{ fontSize: '20px', fontWeight: 'bold', margin: 0, color: '#111827' }}>
                    Hệ Thống Phân Loại & Lưu Trữ Đề Thi
                </h1>
            </header>

            <main style={{ maxWidth: '1000px', margin: '0 auto', padding: '32px' }}>
                <div style={{ marginBottom: '32px' }}>
                    <div style={{ position: 'relative' }}>
                        <Search size={20} color="#9ca3af" style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)' }} />
                        <input
                            type="text"
                            placeholder="Tìm kiếm theo tên môn học, mã học phần hoặc năm học..."
                            style={{
                                width: '100%', padding: '12px 12px 12px 42px', border: '1px solid #d1d5db',
                                borderRadius: '8px', fontSize: '16px', outline: 'none', boxSizing: 'border-box'
                            }}
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                        />
                    </div>
                    <div style={{ marginTop: '10px', fontSize: '14px', color: '#6b7280', fontWeight: '500' }}>
                        Tìm thấy {filteredExams.length} kết quả / Tổng số {exams.length} đề thi
                    </div>
                </div>

                {loading && <p style={{ textAlign: 'center', color: '#6b7280' }}>Đang tải dữ liệu...</p>}
                {error && <p style={{ textAlign: 'center', color: '#ef4444' }}>Lỗi: {error}</p>}

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px' }}>
                    {!loading && !error && filteredExams.map((exam) => (
                        <div key={exam.id} style={{ backgroundColor: '#ffffff', padding: '20px', borderRadius: '8px', border: '1px solid #e5e7eb', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}>
                            <h3 style={{ margin: '0 0 10px 0', fontSize: '18px', color: '#1d4ed8' }}>
                                {exam.subject_name !== "Không xác định" ? exam.subject_name : "Đang cập nhật tên môn"}
                            </h3>
                            <div style={{ fontSize: '14px', color: '#4b5563', lineHeight: '1.6' }}>
                                <div><strong>Mã học phần:</strong> {exam.subject_code}</div>
                                <div><strong>Học kỳ:</strong> {exam.semester}</div>
                                <div><strong>Năm học:</strong> {exam.year}</div>
                            </div>
                            
                            {/* Nút Xem PDF */}
                            <button 
                                onClick={() => window.open(`/pdfs/${exam.pdf_file}`, '_blank')}
                                disabled={!exam.pdf_file}
                                style={{
                                    marginTop: '16px', padding: '8px 16px', 
                                    backgroundColor: exam.pdf_file ? '#2563eb' : '#f3f4f6', 
                                    border: 'none', borderRadius: '4px', 
                                    color: exam.pdf_file ? '#ffffff' : '#9ca3af', 
                                    fontWeight: '600', cursor: exam.pdf_file ? 'pointer' : 'not-allowed', 
                                    width: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '8px'
                                }}
                            >
                                <FileText size={18} />
                                {exam.pdf_file ? 'Xem File PDF' : 'Chưa có PDF'}
                            </button>
                        </div>
                    ))}
                </div>
            </main>

        </div>
    );
}

export default App;