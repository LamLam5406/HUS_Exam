// src/hooks/useExamData.js
import { useState, useEffect } from 'react';

export const useExamData = () => {
    const [exams, setExams] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                // Fetch trực tiếp file JSON từ thư mục public
                const response = await fetch('/data/database.json');
                if (!response.ok) {
                    throw new Error('Không thể tải dữ liệu đề thi');
                }
                const data = await response.json();
                setExams(data);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    return { exams, loading, error };
};