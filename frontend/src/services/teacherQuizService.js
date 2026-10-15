export const getStudentQuizResults = async (rollNumber, courseId, token) => {
  let url = `/api/v1/teacher/students/${rollNumber}/quizzes`;
  if (courseId && courseId !== "ALL") {
    url += `?course_id=${courseId}`;
  }
  
  const res = await fetch(url, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  if (!res.ok) {
    throw new Error("Failed to load adaptive quiz results from backend");
  }
  
  const data = await res.json();
  
  // The backend returns { student_id, course_id, course_name, sessions: [...] }
  // We map the sessions to the format our Teacher Dashboard UI expects.
  if (!data.sessions || !Array.isArray(data.sessions)) {
    return [];
  }
  
  return data.sessions.map((session, idx) => {
    return {
      attempt_id: session.quiz_session_id || `attempt_${idx}`,
      course_name: session.course_name || data.course_name || "Unknown Course",
      quiz_title: session.quiz_type === "full_adaptive" ? "Adaptive Quiz" : "Quiz",
      attempt_date: session.started_at ? new Date(session.started_at).toLocaleString() : "Unknown Date",
      score: session.correct_count || 0,
      total: session.total_questions || 0,
      percentage: session.score_percentage !== undefined ? session.score_percentage : session.score || 0,
      correct_count: session.correct_count || 0,
      incorrect_count: session.wrong_count || 0,
      adaptive_summary: "Adaptive quiz generated based on telemetry models.",
      concept_performance: (session.concept_performance || []).map(cp => ({
        concept: cp.concept,
        total: cp.total_questions,
        correct: cp.correct,
        percentage: cp.accuracy_percentage
      })),
      questions: (session.results || []).map(q => ({
        id: q.question_id,
        text: q.question,
        student_answer: q.selected_answer,
        correct_answer: q.correct_answer,
        is_correct: q.is_correct,
        concept: q.concept,
        difficulty: q.difficulty || "UNKNOWN",
        explanation: q.explanation
      }))
    };
  });
};
