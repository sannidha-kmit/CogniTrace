export const getAdaptiveQuiz = async (courseId, token) => {
  const res = await fetch(`/api/v1/student/courses/${courseId}/adaptive-quiz`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  
  if (!res.ok) {
    let errorDetail = "Failed to load adaptive quiz from backend";
    try {
      const errJson = await res.json();
      if (errJson && errJson.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch (_) {}
    throw new Error(errorDetail);
  }
  const data = await res.json();
  // Pass through concept_map and difficulty per question from backend
  return {
    ...data,
    concept_map: data.concept_map || null,
    questions: (data.questions || []).map(q => ({
      ...q,
      difficulty: q.difficulty || "MEDIUM"
    }))
  };
};

export const submitAdaptiveQuiz = async (courseId, quizId, answers, token) => {
  // answers is an object like { "q1": "Option A", "q2": "Option B" }
  // Backend expects { quiz_session_id: "...", answers: [ { question_id: "...", selected_answer: "..." } ] }
  const formattedAnswers = Object.entries(answers).map(([question_id, selected_answer]) => ({
    question_id,
    selected_answer
  }));

  const res = await fetch(`/api/v1/student/courses/${courseId}/adaptive-quiz/submit`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ 
      quiz_session_id: quizId,
      answers: formattedAnswers 
    })
  });

  if (!res.ok) {
    throw new Error("Failed to submit adaptive quiz to backend");
  }
  const data = await res.json();
  
  // Map backend BulkSubmitResponse to what StudentAdaptiveQuiz.jsx expects
  return {
    score: data.correct_count,
    total: data.total_questions,
    percentage: data.score_percentage,
    correct_count: data.correct_count,
    incorrect_count: data.wrong_count,
    concept_performance: (data.concept_performance || []).map(cp => ({
      concept: cp.concept,
      total: cp.total_questions,
      correct: cp.correct,
      percentage: cp.accuracy_percentage
    })),
    explanations: (data.results || []).map(r => ({
      question_id: r.question_id,
      question: r.question,
      options: r.options,
      selected_answer: r.selected_answer,
      correct_answer: r.correct_answer,
      is_correct: r.is_correct,
      concept: r.concept,
      explanation: r.explanation,
      timestamp_seconds: r.timestamp_seconds,
      timestamp_display: r.timestamp_display,
      transcript_excerpt: r.transcript_excerpt,
      video_url: r.video_url,
      revision_url: r.revision_url
    }))
  };
};

export const getStudentConceptState = async (studentId, courseId, token) => {
  const res = await fetch(`/api/v1/research/student/${studentId}/concept-state?course_id=${courseId}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  if (!res.ok) {
    throw new Error("Failed to load concept state");
  }
  return await res.json();
};

export const getResearchMetrics = async (courseId, token) => {
  const url = courseId ? `/api/v1/research/metrics?course_id=${courseId}` : `/api/v1/research/metrics`;
  const res = await fetch(url, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  if (!res.ok) {
    throw new Error("Failed to load research metrics");
  }
  return await res.json();
};


