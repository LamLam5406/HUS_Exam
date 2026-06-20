import React, { useState, useEffect } from 'react';

// Hàm bỏ dấu tiếng Việt
const removeAccents = (str) => {
  if (!str) return '';
  return str.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
};

function App() {
  const [exams, setExams] = useState([]);
  const [searchInput, setSearchInput] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState(''); 
  
  const [matchedResults, setMatchedResults] = useState([]);
  const [unknownResults, setUnknownResults] = useState([]);
  const [hasSearched, setHasSearched] = useState(false);
  
  const [currentPdf, setCurrentPdf] = useState(null);
  const [selectedExamId, setSelectedExamId] = useState(null);

  // 1. TỐI ƯU & XỬ LÝ LỖI PDF TỰ ĐỘNG
  useEffect(() => {
    fetch('/data/database.json')
      .then((res) => res.json())
      .then((data) => {
        const processedData = data.map(exam => {
          const name = exam.subject_name || '';
          const code = exam.subject_code || '';
          
          let rawLink = exam.pdf_drive_link || '';
          let fixedLink = rawLink;
          if (fixedLink.includes('drive.google.com') && fixedLink.includes('/view')) {
            fixedLink = fixedLink.replace(/\/view.*/, '/preview');
          }

          return {
            ...exam,
            pdf_drive_link: fixedLink,
            searchName: removeAccents(name),
            searchCode: removeAccents(code),
            isUnknown: name.toLowerCase().includes('không xác định') || 
                       code.toLowerCase().includes('không xác định')
          };
        });
        setExams(processedData);
      })
      .catch((err) => console.error("Lỗi tải dữ liệu:", err));
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchInput);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    if (!debouncedSearch.trim()) {
      setHasSearched(false);
      setMatchedResults([]);
      setUnknownResults([]);
      return;
    }

    const qNormalized = removeAccents(debouncedSearch).trim();
    const qWords = qNormalized.split(' ').filter(w => w.length > 0);

    const matches = [];
    const unknowns = [];

    const check70Percent = (targetString) => {
      if (targetString.includes(qNormalized)) return true;
      let matchCount = 0;
      for (let i = 0; i < qWords.length; i++) {
        if (targetString.includes(qWords[i])) matchCount++;
      }
      return (matchCount / qWords.length) >= 0.7;
    };

    for (let i = 0; i < exams.length; i++) {
      const exam = exams[i];
      if (exam.isUnknown) {
        unknowns.push(exam); 
      } else {
        if (check70Percent(exam.searchName) || check70Percent(exam.searchCode)) {
          matches.push(exam);
        }
      }
    }

    setMatchedResults(matches);
    setUnknownResults(unknowns);
    setHasSearched(true);
  }, [debouncedSearch, exams]);

  // Hàm xử lý khi click xem đề
  const handleViewPdf = (exam) => {
    if (!exam.pdf_drive_link) {
      alert("Đề thi này chưa có link PDF!");
      return;
    }
    setCurrentPdf(exam.pdf_drive_link);
    setSelectedExamId(exam.post_id);
  };

  return (
    // THAY ĐỔI BACKGROUND TỔNG THỂ TẠI ĐÂY (Sử dụng gradient nhẹ nhàng để làm nổi bật các thẻ trắng)
    <div className="app-container" style={{ display: 'flex', flexDirection: 'column', height: '100vh', padding: '24px', boxSizing: 'border-box', background: '#83c7c1', fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>
      
      {/* GLOBAL STYLE CHO HIỆU ỨNG VÀ RESET */}
      <style>{`
        html, body, #root {
          margin: 0 !important;
          padding: 0 !important;
          max-width: 100% !important;
          width: 100% !important;
          height: 100% !important;
        }
        
        /* Hiệu ứng thanh cuộn hiện đại */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #94a3b8; border-radius: 10px; }
        ::-webkit-scrollbar-thumb:hover { background: #64748b; }

        /* Class tạo hiệu ứng Hover cho thẻ đề thi */
        .modern-card {
          transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
          cursor: pointer;
        }
        .modern-card:hover {
          transform: translateY(-4px);
          box-shadow: 0 12px 24px -8px rgba(0, 0, 0, 0.15), 0 4px 10px -4px rgba(0, 0, 0, 0.1) !important;
          border-color: #cbd5e1;
        }
        .modern-card:active {
          transform: translateY(-1px);
        }
        
        .modern-card.selected:hover {
          border-color: #3b82f6;
          box-shadow: 0 12px 24px -8px rgba(59, 130, 246, 0.3) !important;
        }
      `}</style>

      {/* HEADER: Tỷ lệ 4-6 */}
      <header className="minimal-header" style={{ marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '24px', width: '100%' }}>
        
        {/* LOGO (Chiếm 4 phần) */}
        <div style={{ flex: '4', display: 'flex', alignItems: 'center', gap: '12px', color: '#1e3a8a', whiteSpace: 'nowrap', paddingLeft: '24px', boxSizing: 'border-box' }}>
          <div style={{ padding: '6px', backgroundColor: '#ffffffca', borderRadius: '10px', boxShadow: '0 2px 10px rgba(0,0,0,0.05)' }}>
            <img src="/favicon.png" alt="Logo" width="30" height="30" style={{ objectFit: 'contain' }} />
          </div>
          <h2 style={{ margin: 0, fontSize: '26px', fontWeight: '800', letterSpacing: '-0.5px', color: '#284185' }}>HUS Exam</h2>
        </div>
        
        {/* Ô TÌM KIẾM (Chiếm 6 phần) */}
        <div className="search-bar-wrapper" style={{ flex: '6', boxSizing: 'border-box', position: 'relative' }}>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ position: 'absolute', left: '16px', top: '50%', transform: 'translateY(-50%)' }}>
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input
            type="text"
            placeholder="Nhập tên môn hoặc mã môn..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="main-search-input"
            style={{ width: '100%', padding: '16px 20px 16px 48px', fontSize: '15px', color: '#334155', borderRadius: '16px', border: '1px solid #ffffff', backgroundColor: '#ffffff', boxShadow: '0 4px 20px rgba(0,0,0,0.05)', boxSizing: 'border-box', outline: 'none', transition: 'border-color 0.2s, box-shadow 0.2s' }}
            onFocus={(e) => { e.target.style.borderColor = '#3b82f6'; e.target.style.boxShadow = '0 0 0 4px rgba(59, 130, 246, 0.15)'; }}
            onBlur={(e) => { e.target.style.borderColor = '#ffffff'; e.target.style.boxShadow = '0 4px 20px rgba(0,0,0,0.05)'; }}
          />
        </div>
      </header>

      {/* CHIA LÀM 2 CỘT (Tỷ lệ 4-6) */}
      <div className="main-content" style={{ display: 'flex', gap: '24px', flex: 1, overflow: 'hidden' }}>
        
        {/* CỘT TRÁI: DANH SÁCH */}
        <div className="list-section" style={{ flex: '4', minWidth: '480px', overflowY: 'auto', paddingRight: '12px', paddingLeft: '24px', boxSizing: 'border-box', paddingBottom: '20px' }}>
          {!hasSearched ? (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '60%', color: '#64748b' }}>
              <div style={{ padding: '20px', backgroundColor: '#e2e8f0', borderRadius: '50%', marginBottom: '16px' }}>
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path>
                  <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path>
                </svg>
              </div>
              <p style={{ fontSize: '16px', fontWeight: '500' }}>Hãy nhập từ khóa để tra cứu đề thi</p>
            </div>
          ) : (
            <>
              <div className="result-group">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                  <h3 style={{ margin: 0, color: '#0f172a', fontSize: '18px', fontWeight: '700' }}>Kết quả phù hợp</h3>
                  <span style={{ backgroundColor: '#ffffff', color: '#071932', padding: '4px 12px', borderRadius: '10px', fontSize: '14px', fontWeight: '700', boxShadow: '0 2px 5px rgba(0,0,0,0.05)' }}>{matchedResults.length}</span>
                </div>
                
                {matchedResults.length === 0 ? (
                  <div style={{ padding: '24px', backgroundColor: '#fff', borderRadius: '16px', border: '2px dashed #94a3b8', textAlign: 'center', color: '#64748b' }}>
                    Không có kết quả nào khớp.
                  </div>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                    {matchedResults.map((exam) => {
                      const isSelected = exam.post_id === selectedExamId;
                      return (
                        <div 
                          key={exam.post_id} 
                          className={`modern-card ${isSelected ? 'selected' : ''}`}
                          onClick={() => handleViewPdf(exam)}
                          style={{ 
                            padding: '14px 16px', 
                            border: isSelected ? '2px solid #3b82f6' : '2px solid transparent', 
                            borderRadius: '12px', 
                            backgroundColor: isSelected ? '#eff6ff' : '#ffffff', 
                            display: 'flex', 
                            justifyContent: 'space-between', 
                            alignItems: 'center',
                            boxShadow: isSelected ? '0 8px 20px rgba(59,130,246,0.2)' : '0 4px 12px rgba(0,0,0,0.04)',
                            gap: '10px'
                          }}
                        >
                          <div style={{ flex: 1, overflow: 'hidden' }}>
                            <h4 style={{ margin: 0, fontSize: '14px', fontWeight: '700', lineHeight: '1.4', color: isSelected ? '#1d4ed8' : '#1e293b', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                              [{exam.subject_code}] {exam.subject_name}
                            </h4>
                            {(exam.year || exam.semester) && (
                              <p style={{ margin: '6px 0 0 0', fontSize: '12px', fontWeight: '500', color: isSelected ? '#3b82f6' : '#64748b' }}>
                                HK {exam.semester || '-'} &nbsp;•&nbsp; {exam.year || '-'}
                              </p>
                            )}
                          </div>
                          
                          <div 
                            title={isSelected ? 'Đang xem' : 'Xem đề'}
                            style={{ 
                              width: '36px', 
                              height: '36px', 
                              backgroundColor: isSelected ? '#3b82f6' : '#f1f5f9', 
                              color: isSelected ? '#ffffff' : '#64748b', 
                              borderRadius: '50%', 
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              flexShrink: 0,
                              boxShadow: isSelected ? '0 4px 10px rgba(59,130,246,0.3)' : 'none',
                              transition: 'all 0.2s ease'
                            }}
                          >
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                              <circle cx="12" cy="12" r="3"></circle>
                            </svg>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {unknownResults.length > 0 && (
                <>
                  <div style={{ margin: '32px 0 24px', display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <div style={{ height: '3px', flex: 1, backgroundColor: '#242b35', opacity: 0.3 }}></div>
                    <span style={{ color: '#242b35', fontSize: '17px', fontWeight: '600', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Không xác định</span>
                    <div style={{ height: '3px', flex: 1, backgroundColor: '#242b35', opacity: 0.3 }}></div>
                  </div>

                  <div className="result-group unknown-group">
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                      {unknownResults.map((exam) => {
                        const isSelected = exam.post_id === selectedExamId;
                        return (
                          <div 
                            key={exam.post_id} 
                            className={`modern-card ${isSelected ? 'selected' : ''}`}
                            onClick={() => handleViewPdf(exam)}
                            style={{ 
                              padding: '14px 16px', 
                              border: isSelected ? '2px solid #3b82f6' : '2px solid transparent', 
                              borderRadius: '12px', 
                              backgroundColor: isSelected ? '#eff6ff' : '#f8fafc', 
                              display: 'flex', 
                              justifyContent: 'space-between', 
                              alignItems: 'center',
                              boxShadow: isSelected ? '0 8px 20px rgba(59,130,246,0.15)' : '0 4px 12px rgba(0,0,0,0.03)',
                              gap: '10px'
                            }}
                          >
                            <div style={{ flex: 1, overflow: 'hidden' }}>
                              <h4 style={{ margin: 0, fontSize: '14px', fontWeight: '600', lineHeight: '1.4', color: isSelected ? '#1d4ed8' : '#64748b', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                                [{exam.subject_code}] {exam.subject_name}
                              </h4>
                              {(exam.year || exam.semester) && (
                                <p style={{ margin: '6px 0 0 0', fontSize: '12px', color: isSelected ? '#3b82f6' : '#94a3b8' }}>
                                  HK {exam.semester || '-'} &nbsp;•&nbsp; {exam.year || '-'}
                                </p>
                              )}
                            </div>
                            <div 
                              title={isSelected ? 'Đang xem' : 'Xem đề'}
                              style={{ 
                                width: '36px', 
                                height: '36px', 
                                backgroundColor: isSelected ? '#3b82f6' : '#e2e8f0', 
                                color: isSelected ? '#ffffff' : '#94a3b8', 
                                borderRadius: '50%', 
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                flexShrink: 0,
                                boxShadow: isSelected ? '0 4px 10px rgba(59,130,246,0.3)' : 'none',
                                transition: 'all 0.2s ease'
                              }}
                            >
                              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                                <circle cx="12" cy="12" r="3"></circle>
                              </svg>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </>
              )}
            </>
          )}
        </div>

        {/* CỘT PHẢI: XEM PDF */}
        <div className="viewer-section" style={{ flex: '6', backgroundColor: '#fff', borderRadius: '24px', border: '1px solid #cbd5e1', boxShadow: '0 10px 40px rgba(0,0,0,0.08)', overflow: 'hidden', boxSizing: 'border-box' }}>
          {currentPdf ? (
            <div style={{ position: 'relative', width: '100%', height: '100%', overflow: 'hidden' }}>
              <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', color: '#64748b', zIndex: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
                <div className="spinner" style={{ width: '40px', height: '40px', border: '4px solid #f1f5f9', borderTop: '4px solid #3b82f6', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
                <span style={{ fontSize: '15px', fontWeight: '500' }}>Đang tải tài liệu từ Google Drive...</span>
                <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
              </div>
              
              {/* THỦ THUẬT THU NHỎ KÍCH THƯỚC HIỂN THỊ PDF BÊN TRONG Ô BẰNG CSS SCALE */}
              <iframe
                src={currentPdf}
                title="Trình xem PDF"
                style={{ 
                  border: 'none', 
                  position: 'absolute', 
                  zIndex: 1, 
                  backgroundColor: 'transparent',
                  top: 0,
                  left: 0,
                  width: '125%',         // Mở rộng width để bù lại khi scale
                  height: '125%',        // Mở rộng height để bù lại khi scale
                  transform: 'scale(0.8)', // Thu nhỏ toàn bộ nội dung Iframe xuống 80%
                  transformOrigin: 'top left' // Gắn điểm gốc thu nhỏ ở góc trên bên trái
                }}
              ></iframe>
            </div>
          ) : (
            <div className="no-pdf" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', height: '100%', color: '#94a3b8', backgroundColor: '#f8fafc' }}>
              <div style={{ padding: '24px', backgroundColor: '#f1f5f9', borderRadius: '50%', marginBottom: '20px', boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.05)' }}>
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="#cbd5e1" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                  <polyline points="14 2 14 8 20 8"></polyline>
                  <line x1="16" y1="13" x2="8" y2="13"></line>
                  <line x1="16" y1="17" x2="8" y2="17"></line>
                  <polyline points="10 9 9 9 8 9"></polyline>
                </svg>
              </div>
              <p style={{ fontSize: '16px', fontWeight: '500' }}>Chọn một đề thi ở danh sách bên trái để xem nội dung.</p>
            </div>
          )}
        </div>
        
      </div>
    </div>
  );
}

export default App;