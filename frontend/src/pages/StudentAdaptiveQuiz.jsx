import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getAdaptiveQuiz, submitAdaptiveQuiz } from '../services/quizService';
import telemetryService from '../services/telemetryService';
import {
  ArrowLeft,
  AlertCircle,
  CheckCircle2,
  BrainCircuit,
  ChevronLeft,
  ChevronRight,
  Send,
  Loader2,
  Award,
  Play,
  XCircle,
  Video,
  Sparkles,
  BookOpen,
  Zap,
  TrendingUp,
  Target,
  GitBranch
} from 'lucide-react';

// ─────────────────────────────────────────────────────────────
// Priority & Difficulty Helpers (YouTube Design Palette)
// ─────────────────────────────────────────────────────────────

const PRIORITY_STYLES = {
  HIGH: {
    bg: 'bg-[#FFEBEE]',
    border: 'border-[#FFCDD2]',
    text: 'text-[#C62828]',
    dot: 'bg-[#FF0000]',
    label: 'Focus Area'
  },
  MEDIUM: {
    bg: 'bg-[#FFF8E1]',
    border: 'border-[#FFE082]',
    text: 'text-[#F57F17]',
    dot: 'bg-[#F9A825]',
    label: 'Review'
  },
  LOW: {
    bg: 'bg-[#E8F5E9]',
    border: 'border-[#C8E6C9]',
    text: 'text-[#2E7D32]',
    dot: 'bg-[#2E7D32]',
    label: 'Mastered'
  }
};

const DIFFICULTY_STYLES = {
  EASY: { bg: 'bg-[#E8F5E9]', border: 'border-[#C8E6C9]', text: 'text-[#2E7D32]', label: 'Easy' },
  MEDIUM: { bg: 'bg-[#FFF8E1]', border: 'border-[#FFE082]', text: 'text-[#F57F17]', label: 'Medium' },
  HARD: { bg: 'bg-[#FFEBEE]', border: 'border-[#FFCDD2]', text: 'text-[#C62828]', label: 'Hard' }
};

function getDiffStyle(diff) {
  return DIFFICULTY_STYLES[(diff || 'MEDIUM').toUpperCase()] || DIFFICULTY_STYLES.MEDIUM;
}

function getPriorityStyle(priority) {
  return PRIORITY_STYLES[(priority || 'MEDIUM').toUpperCase()] || PRIORITY_STYLES.MEDIUM;
}

// ─────────────────────────────────────────────────────────────
// Concept Map Visualization Component (YouTube Clean Design)
// ─────────────────────────────────────────────────────────────

function ConceptMapViz({ conceptMap, performanceMap = null, compact = false }) {
  if (!conceptMap || !conceptMap.nodes || conceptMap.nodes.length === 0) return null;

  const { nodes } = conceptMap;

  return (
    <div className="space-y-3.5">
      {/* Summary Stats Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
        <div className="p-3 rounded-xl bg-[#F9F9F9] border border-[#E5E5E5] text-center">
          <p className="text-[11px] uppercase tracking-wider text-[#606060] mb-0.5 font-semibold">Total Concepts</p>
          <p className="text-lg font-bold text-[#0F0F0F] font-mono">{conceptMap.total_concepts}</p>
        </div>
        <div className="p-3 rounded-xl bg-[#FFEBEE] border border-[#FFCDD2] text-center">
          <p className="text-[11px] uppercase tracking-wider text-[#C62828] mb-0.5 font-semibold">Focus Area</p>
          <p className="text-lg font-bold text-[#C62828] font-mono">{conceptMap.high_priority_count}</p>
        </div>
        <div className="p-3 rounded-xl bg-[#FFF8E1] border border-[#FFE082] text-center">
          <p className="text-[11px] uppercase tracking-wider text-[#F57F17] mb-0.5 font-semibold">Review</p>
          <p className="text-lg font-bold text-[#F57F17] font-mono">{conceptMap.medium_priority_count}</p>
        </div>
        <div className="p-3 rounded-xl bg-[#E8F5E9] border border-[#C8E6C9] text-center">
          <p className="text-[11px] uppercase tracking-wider text-[#2E7D32] mb-0.5 font-semibold">Mastered</p>
          <p className="text-lg font-bold text-[#2E7D32] font-mono">{conceptMap.low_priority_count}</p>
        </div>
      </div>

      {/* Dynamic Generation Banner */}
      {conceptMap.dynamically_generated_total > 0 && (
        <div className="flex items-center gap-2 px-3.5 py-2.5 rounded-lg bg-[#F9F9F9] border border-[#E5E5E5]">
          <Zap className="w-4 h-4 text-[#FF0000] shrink-0" />
          <p className="text-xs text-[#0F0F0F]">
            <strong className="font-semibold">{conceptMap.dynamically_generated_total}</strong> adaptive questions generated dynamically from your video telemetry.
          </p>
        </div>
      )}

      {/* Concept Nodes */}
      <div className={`grid gap-2.5 ${compact ? 'grid-cols-1' : 'grid-cols-1 sm:grid-cols-2'}`}>
        {nodes.map((node, idx) => {
          const ps = getPriorityStyle(node.priority);
          const perfData = performanceMap ? performanceMap[node.concept_name] : null;

          return (
            <div
              key={idx}
              className={`relative p-3.5 rounded-xl border transition-colors ${ps.bg} ${ps.border}`}
            >
              {/* Prerequisite Edge Indicator */}
              {node.prerequisite && node.prerequisite !== 'None' && (
                <div className="flex items-center gap-1 text-[11px] text-[#606060] mb-1 font-mono">
                  <GitBranch className="w-3 h-3 text-[#FF0000]" />
                  <span>Prerequisite: {node.prerequisite}</span>
                </div>
              )}

              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <h4 className="text-xs font-bold text-[#0F0F0F] truncate">{node.concept_name}</h4>
                  <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                    {/* Priority Badge */}
                    <span className={`inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded ${ps.bg} ${ps.border} ${ps.text}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${ps.dot}`}></span>
                      {ps.label}
                    </span>
                    {/* Difficulty Badge */}
                    <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-[#FFFFFF] border border-[#E5E5E5] text-[#0F0F0F]">
                      {node.difficulty_level}
                    </span>
                    {/* Question Count */}
                    <span className="text-[10px] font-mono text-[#606060]">
                      {node.question_count}Q
                    </span>
                    {/* Dynamically Generated */}
                    {node.dynamically_generated > 0 && (
                      <span className="inline-flex items-center gap-0.5 text-[10px] font-semibold px-1.5 py-0.5 rounded bg-[#FFEBEE] border border-[#FFCDD2] text-[#FF0000]">
                        <Zap className="w-2.5 h-2.5" />
                        {node.dynamically_generated} new
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Performance Meter */}
              {perfData && (
                <div className="mt-2.5 pt-2 border-t border-[#E5E5E5]">
                  <div className="flex items-center justify-between text-[11px] font-mono mb-1">
                    <span className="text-[#606060]">Mastery</span>
                    <span className="font-bold text-[#0F0F0F]">{perfData.correct}/{perfData.total} ({perfData.percentage}%)</span>
                  </div>
                  <div className="w-full h-1.5 bg-[#E5E5E5] rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-300 ${perfData.percentage >= 70 ? 'bg-[#2E7D32]' : perfData.percentage >= 40 ? 'bg-[#F9A825]' : 'bg-[#FF0000]'}`}
                      style={{ width: `${perfData.percentage}%` }}
                    ></div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────
// Main Component
// ─────────────────────────────────────────────────────────────

export default function StudentAdaptiveQuiz() {
  const { courseId } = useParams();
  const navigate = useNavigate();
  const { token } = useAuth();

  // View state: 'loading' | 'error' | 'empty' | 'intro' | 'playing' | 'submitting' | 'result'
  const [viewState, setViewState] = useState('loading');
  const [errorMessage, setErrorMessage] = useState('');
  
  // Quiz data state
  const [quizData, setQuizData] = useState(null);
  
  // Active playing state
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedAnswers, setSelectedAnswers] = useState({});
  
  // Result state
  const [resultData, setResultData] = useState(null);

  // Attention Summary State for Pre-Quiz Review Prompt
  const [attentionSummary, setAttentionSummary] = useState(null);

  useEffect(() => {
    loadQuiz();
    telemetryService.getStudentAttentionSummary(courseId).then(summary => {
      setAttentionSummary(summary);
    }).catch(() => {});
  }, [courseId, token]);

  const loadQuiz = async () => {
    setViewState('loading');
    setErrorMessage('');
    try {
      const data = await getAdaptiveQuiz(courseId, token);
      if (!data || !data.questions || data.questions.length === 0) {
        setViewState('empty');
      } else {
        setQuizData(data);
        setViewState('intro');
      }
    } catch (err) {
      setErrorMessage(err.message || "Unable to load the adaptive quiz. Please try again.");
      setViewState('error');
    }
  };

  const handleStartQuiz = () => {
    setViewState('playing');
  };

  const handleOptionSelect = (questionId, option) => {
    setSelectedAnswers(prev => ({
      ...prev,
      [questionId]: option
    }));
  };

  const handleNext = () => {
    if (currentQuestionIndex < (quizData.questions.length - 1)) {
      setCurrentQuestionIndex(prev => prev + 1);
    }
  };

  const handlePrevious = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(prev => prev - 1);
    }
  };

  const handleSubmit = async () => {
    setViewState('submitting');
    try {
      const quizId = quizData?.quiz_id || quizData?.quiz_session_id || '';
      const res = await submitAdaptiveQuiz(courseId, quizId, selectedAnswers, token);
      setResultData(res);
      setViewState('result');
    } catch (err) {
      setErrorMessage(err.message || 'Failed to submit quiz. Please try again.');
      setViewState('error');
    }
  };

  const buildPerformanceMap = () => {
    if (!resultData || !resultData.concept_performance) return null;
    const map = {};
    resultData.concept_performance.forEach(cp => {
      map[cp.concept] = cp;
    });
    return map;
  };

  // -------------------------------------------------------------
  // Renders for different states
  // -------------------------------------------------------------

  if (viewState === 'loading') {
    return (
      <div className="min-h-screen bg-[#FFFFFF] flex flex-col items-center justify-center text-[#0F0F0F]">
        <Loader2 className="w-8 h-8 animate-spin mb-3 text-[#FF0000]" />
        <p className="text-sm font-bold text-[#0F0F0F]">Personalizing Adaptive Quiz...</p>
        <p className="text-xs text-[#606060] mt-1 font-mono">Synthesizing telemetry data & generating concept questions</p>
      </div>
    );
  }

  if (viewState === 'submitting') {
    return (
      <div className="min-h-screen bg-[#FFFFFF] flex flex-col items-center justify-center text-[#0F0F0F]">
        <Loader2 className="w-8 h-8 animate-spin mb-3 text-[#FF0000]" />
        <p className="text-sm font-bold text-[#0F0F0F]">Grading Concept Mastery...</p>
      </div>
    );
  }

  if (viewState === 'error') {
    return (
      <div className="min-h-screen bg-[#F9F9F9] p-6 flex flex-col items-center justify-center">
        <div className="max-w-md w-full bg-[#FFFFFF] border border-[#FFCDD2] rounded-xl p-6 text-center space-y-4 shadow-sm">
          <AlertCircle className="w-10 h-10 text-[#FF0000] mx-auto" />
          <h2 className="text-lg font-bold text-[#0F0F0F]">Unable to Load Quiz</h2>
          <p className="text-xs text-[#606060]">{errorMessage}</p>
          <div className="pt-2 flex gap-3 justify-center">
            <Link to={`/student/course/${courseId}/watch`} className="yt-btn-secondary text-xs py-2 px-4">
              Go Back
            </Link>
            <button onClick={loadQuiz} className="yt-btn-primary text-xs py-2 px-4 cursor-pointer">
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (viewState === 'empty') {
    return (
      <div className="min-h-screen bg-[#F9F9F9] p-6 flex flex-col items-center justify-center">
        <div className="max-w-md w-full bg-[#FFFFFF] border border-[#E5E5E5] rounded-xl p-6 text-center space-y-4 shadow-sm">
          <BrainCircuit className="w-10 h-10 text-[#909090] mx-auto" />
          <h2 className="text-lg font-bold text-[#0F0F0F]">Quiz Currently Unavailable</h2>
          <p className="text-xs text-[#606060]">Please finish watching the video to generate adaptive questions.</p>
          <div className="pt-2">
            <Link to={`/student/course/${courseId}/watch`} className="yt-btn-primary text-xs py-2 px-5 inline-block cursor-pointer">
              Return to Video Lesson
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // ─────────────────────────────────────────────────────────────
  // INTRO Screen with Concept Map
  // ─────────────────────────────────────────────────────────────
  if (viewState === 'intro') {
    return (
      <div className="min-h-screen bg-[#F9F9F9] px-4 py-8 flex flex-col items-center text-[#0F0F0F]">
        <div className="max-w-2xl w-full space-y-5">
          <div className="bg-[#FFFFFF] border border-[#E5E5E5] rounded-xl p-6 sm:p-7 space-y-4 shadow-sm">
            
            <div className="flex justify-center">
              <div className="w-12 h-12 rounded-xl bg-[#FFEBEE] border border-[#FFCDD2] flex items-center justify-center">
                <BrainCircuit className="w-6 h-6 text-[#FF0000]" />
              </div>
            </div>
            
            <div className="text-center space-y-1">
              <h1 className="text-2xl font-bold text-[#0F0F0F] tracking-tight">Adaptive Concept Assessment</h1>
              <p className="text-xs text-[#606060]">
                Course: <strong className="text-[#0F0F0F] font-semibold">{quizData.course_name || 'Selected Lesson'}</strong>
              </p>
            </div>

            <div className="bg-[#F9F9F9] border border-[#E5E5E5] rounded-xl p-4 text-center">
              <p className="text-xs text-[#0F0F0F]">
                This assessment contains <strong className="text-[#FF0000] font-bold text-sm mx-1">{quizData.total_questions || quizData.questions.length}</strong> questions tailored to your video watching behavior.
              </p>
            </div>
          </div>

          {/* Concept Map Section */}
          {quizData.concept_map && (
            <div className="bg-[#FFFFFF] border border-[#E5E5E5] rounded-xl p-5 sm:p-6 space-y-3.5 shadow-sm">
              <div className="flex items-center gap-2 border-b border-[#E5E5E5] pb-3">
                <Target className="w-4 h-4 text-[#FF0000]" />
                <h3 className="text-sm font-bold text-[#0F0F0F]">Your Concept Mastery Map</h3>
                <span className="text-[11px] font-mono text-[#606060] ml-auto">Interaction Guided</span>
              </div>
              <p className="text-xs text-[#606060]">
                Questions are targeted to concepts you explored during the video. Concepts requiring reinforcement receive higher question density.
              </p>
              <ConceptMapViz conceptMap={quizData.concept_map} />
            </div>
          )}

          {/* Pre-Quiz Focus Insights Prompt (Requirement 20) */}
          {attentionSummary && attentionSummary.distraction_event_count > 0 && (
            <div className="bg-[#FFF8E1] border border-[#FFE082] rounded-xl p-4 flex items-start gap-3 text-xs shadow-sm">
              <AlertCircle className="w-5 h-5 text-[#F57F17] shrink-0 mt-0.5" />
              <div className="space-y-1.5 flex-1">
                <h4 className="font-bold text-[#0F0F0F]">Focus Insights & Optional Review</h4>
                <p className="text-[#606060] leading-relaxed">
                  {attentionSummary.distraction_event_count} attention drift moments ({attentionSummary.total_distraction_seconds}s total) were observed during your lecture session. Would you like to review difficult concepts before starting the quiz?
                </p>
                <div className="pt-1">
                  <Link
                    to={`/student/course/${courseId}/watch`}
                    className="inline-flex items-center gap-1.5 text-[#0F0F0F] font-semibold hover:text-[#FF0000] underline"
                  >
                    <Play className="w-3 h-3 fill-current" />
                    <span>Review Video Concepts in Lecture →</span>
                  </Link>
                </div>
              </div>
            </div>
          )}

          {/* Start Button */}
          <div className="flex flex-col sm:flex-row gap-3 pt-1">
            <Link to={`/student/course/${courseId}/watch`} className="flex-1 yt-btn-secondary text-center py-2.5 text-xs font-semibold">
              Review Video First
            </Link>
            <button 
              onClick={handleStartQuiz} 
              className="flex-1 yt-btn-primary flex justify-center items-center gap-2 py-2.5 text-xs font-semibold cursor-pointer shadow-sm"
            >
              <span>Begin Assessment</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ─────────────────────────────────────────────────────────────
  // RESULT Screen with Concept Map Performance Overlay
  // ─────────────────────────────────────────────────────────────
  if (viewState === 'result' && resultData) {
    const performanceMap = buildPerformanceMap();

    return (
      <div className="min-h-screen bg-[#F9F9F9] px-4 py-8 flex flex-col items-center text-[#0F0F0F]">
        <div className="w-full max-w-2xl space-y-5">
          <div className="flex items-center justify-between">
            <Link to={`/student/course/${courseId}/watch`} className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#0F0F0F] hover:text-[#FF0000] transition-colors">
              <ArrowLeft className="w-3.5 h-3.5" /> Back to Video Lesson
            </Link>
            <span className="text-xs font-semibold px-2.5 py-0.5 bg-[#E8F5E9] text-[#2E7D32] rounded-full">
              Assessment Completed
            </span>
          </div>

          {/* Score Card */}
          <div className="bg-[#FFFFFF] border border-[#E5E5E5] rounded-xl p-6 sm:p-7 text-center shadow-sm">
            <div className="w-12 h-12 rounded-full bg-[#FFEBEE] border border-[#FFCDD2] flex items-center justify-center mx-auto mb-3">
              <Award className="w-6 h-6 text-[#FF0000]" />
            </div>
            
            <h2 className="text-xl font-bold text-[#0F0F0F] mb-1">Performance Score</h2>
            
            <div className="flex justify-center items-end gap-1.5 mb-5">
              <span className="text-4xl font-bold text-[#0F0F0F] font-mono leading-none">{resultData.score}</span>
              <span className="text-lg text-[#606060] font-mono leading-none mb-0.5">/ {resultData.total}</span>
            </div>
            
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              <div className="p-3 bg-[#F9F9F9] rounded-xl border border-[#E5E5E5] text-center">
                <p className="text-[11px] uppercase tracking-wider text-[#606060] mb-0.5 font-semibold">Correct</p>
                <p className="text-base font-bold text-[#2E7D32] font-mono">{resultData.correct_count}</p>
              </div>
              <div className="p-3 bg-[#F9F9F9] rounded-xl border border-[#E5E5E5] text-center">
                <p className="text-[11px] uppercase tracking-wider text-[#606060] mb-0.5 font-semibold">Incorrect</p>
                <p className="text-base font-bold text-[#C62828] font-mono">{resultData.incorrect_count}</p>
              </div>
              <div className="p-3 bg-[#F9F9F9] rounded-xl border border-[#E5E5E5] text-center">
                <p className="text-[11px] uppercase tracking-wider text-[#606060] mb-0.5 font-semibold">Skipped</p>
                <p className="text-base font-bold text-[#F57F17] font-mono">{(resultData.total || 0) - ((resultData.correct_count || 0) + (resultData.incorrect_count || 0))}</p>
              </div>
              <div className="p-3 bg-[#F9F9F9] rounded-xl border border-[#E5E5E5] text-center">
                <p className="text-[11px] uppercase tracking-wider text-[#606060] mb-0.5 font-semibold">Accuracy</p>
                <p className="text-base font-bold text-[#0F0F0F] font-mono">{resultData.percentage}%</p>
              </div>
            </div>
          </div>

          {/* Concept Map with Performance Overlay */}
          {quizData?.concept_map && (
            <div className="bg-[#FFFFFF] border border-[#E5E5E5] rounded-xl p-5 sm:p-6 space-y-3.5 shadow-sm">
              <div className="flex items-center gap-2 border-b border-[#E5E5E5] pb-3">
                <TrendingUp className="w-4 h-4 text-[#FF0000]" />
                <h3 className="text-sm font-bold text-[#0F0F0F]">Concept-Wise Mastery</h3>
              </div>
              <ConceptMapViz
                conceptMap={quizData.concept_map}
                performanceMap={performanceMap}
                compact={true}
              />
            </div>
          )}

          {/* Explanations & Review */}
          {resultData.explanations && resultData.explanations.length > 0 && (
            <div className="bg-[#FFFFFF] border border-[#E5E5E5] rounded-xl p-5 sm:p-6 space-y-4 shadow-sm">
              <div className="flex items-center justify-between border-b border-[#E5E5E5] pb-3">
                <h3 className="text-sm font-bold text-[#0F0F0F] flex items-center gap-2">
                  <BookOpen className="w-4 h-4 text-[#FF0000]" /> Question Review & Video Timestamps
                </h3>
                <span className="text-xs text-[#606060] font-mono">
                  {resultData.explanations.length} Questions
                </span>
              </div>

              <div className="space-y-4">
                {resultData.explanations.map((exp, idx) => {
                  const qText = exp.question || quizData?.questions?.find(q => (q.question_id || q.id) === exp.question_id)?.question || "Question text unavailable";
                  const isCorrect = exp.is_correct;
                  const targetTimestampSec = exp.timestamp_seconds !== null && exp.timestamp_seconds !== undefined ? exp.timestamp_seconds : 0;
                  const displayTs = exp.timestamp_display || "00:00";

                  return (
                    <div 
                      key={idx} 
                      className={`p-4 rounded-xl border transition-colors ${
                        isCorrect 
                          ? 'bg-[#FFFFFF] border-[#C8E6C9]' 
                          : 'bg-[#FFFFFF] border-[#FFCDD2]'
                      }`}
                    >
                      {/* Top Bar: Question # + Concept + Status Badge */}
                      <div className="flex items-center justify-between gap-2 mb-2.5 flex-wrap">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-[#F2F2F2] text-[#0F0F0F]">
                            Q{idx + 1}
                          </span>
                          {exp.concept && (
                            <span className="text-xs font-medium px-2 py-0.5 rounded bg-[#F9F9F9] border border-[#E5E5E5] text-[#606060]">
                              {exp.concept}
                            </span>
                          )}
                        </div>

                        <div>
                          {isCorrect ? (
                            <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-0.5 bg-[#E8F5E9] text-[#2E7D32] rounded-full">
                              <CheckCircle2 className="w-3.5 h-3.5" /> Correct
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-0.5 bg-[#FFEBEE] text-[#C62828] rounded-full">
                              <XCircle className="w-3.5 h-3.5" /> Incorrect
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Question Text */}
                      <h4 className="text-sm font-bold text-[#0F0F0F] leading-relaxed mb-3">
                        {qText}
                      </h4>

                      {/* Answers Comparison */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 mb-3 text-xs">
                        {exp.selected_answer && (
                          <div className={`p-2.5 rounded-lg border ${
                            isCorrect 
                              ? 'bg-[#E8F5E9] border-[#C8E6C9] text-[#2E7D32]' 
                              : 'bg-[#FFEBEE] border-[#FFCDD2] text-[#C62828]'
                          }`}>
                            <p className="text-[10px] uppercase tracking-wider font-semibold opacity-80 mb-0.5">Your Answer</p>
                            <p className="font-semibold text-xs">{exp.selected_answer}</p>
                          </div>
                        )}

                        <div className="p-2.5 rounded-lg border bg-[#E8F5E9] border-[#C8E6C9] text-[#2E7D32]">
                          <p className="text-[10px] uppercase tracking-wider font-semibold opacity-80 mb-0.5">Correct Answer</p>
                          <p className="font-semibold text-xs text-[#0F0F0F]">{exp.correct_answer}</p>
                        </div>
                      </div>

                      {/* Explanation */}
                      {exp.explanation && (
                        <div className="p-3 rounded-lg bg-[#F9F9F9] border border-[#E5E5E5] space-y-1 mb-3">
                          <div className="flex items-center gap-1 text-xs font-semibold text-[#0F0F0F]">
                            <Sparkles className="w-3.5 h-3.5 text-[#FF0000]" /> Explanation
                          </div>
                          <p className="text-xs text-[#606060] leading-relaxed pl-4">
                            {exp.explanation}
                          </p>
                        </div>
                      )}

                      {/* Video Timestamp Revision Link */}
                      <div className="p-3 rounded-lg bg-[#F9F9F9] border border-[#E5E5E5] flex items-center justify-between flex-wrap gap-2">
                        <div className="flex items-center gap-2 text-xs text-[#606060]">
                          <Video className="w-4 h-4 text-[#FF0000]" />
                          <span>Video Segment:</span>
                          <span className="font-mono bg-[#FFFFFF] px-2 py-0.5 rounded border border-[#CCCCCC] text-[#0F0F0F] text-xs font-semibold">
                            {displayTs}
                          </span>
                        </div>

                        <Link 
                          to={`/student/course/${courseId}/watch?t=${targetTimestampSec}`}
                          className="yt-btn-primary text-xs py-1.5 px-3.5 font-semibold flex items-center gap-1.5 cursor-pointer shadow-sm"
                        >
                          <Play className="w-3 h-3 fill-current" /> Watch at {displayTs}
                        </Link>
                      </div>

                    </div>
                  );
                })}
              </div>
            </div>
          )}
          
          <div className="pt-2 flex justify-center">
            <Link to={`/student/course/${courseId}/watch`} className="yt-btn-primary text-xs py-2.5 px-6 font-semibold cursor-pointer shadow-sm">
              Return to Video Lessons
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // ─────────────────────────────────────────────────────────────
  // PLAYING Screen with Difficulty Badge & Concept Tag
  // ─────────────────────────────────────────────────────────────
  if (viewState === 'playing' && quizData) {
    const totalQuestions = quizData.questions.length;
    const currentQ = quizData.questions[currentQuestionIndex];
    const isLastQuestion = currentQuestionIndex === totalQuestions - 1;
    const qId = currentQ.question_id || currentQ.id;
    const selectedOption = selectedAnswers[qId];
    const diffStyle = getDiffStyle(currentQ.difficulty);
    const progressPercent = ((currentQuestionIndex + 1) / totalQuestions) * 100;

    return (
      <div className="min-h-screen bg-[#F9F9F9] flex flex-col text-[#0F0F0F]">
        {/* Header with YouTube Red Progress Bar */}
        <header className="border-b border-[#E5E5E5] bg-[#FFFFFF] sticky top-0 z-40">
          <div className="max-w-3xl mx-auto px-4 h-14 flex items-center justify-between">
            <button
              onClick={() => {
                if(window.confirm("Are you sure you want to exit? Your progress will be lost.")) {
                  navigate(`/student/course/${courseId}/watch`);
                }
              }}
              className="inline-flex items-center gap-1 text-xs font-semibold text-[#0F0F0F] hover:text-[#FF0000] transition-colors cursor-pointer"
            >
              <ArrowLeft className="w-4 h-4" /> Exit Quiz
            </button>
            <div className="text-xs font-semibold px-2.5 py-0.5 bg-[#F2F2F2] text-[#0F0F0F] rounded-full">
              Question {currentQuestionIndex + 1} of {totalQuestions}
            </div>
          </div>
          {/* YouTube Red Progress Bar */}
          <div className="w-full h-1 bg-[#E5E5E5]">
            <div 
              className="h-full bg-[#FF0000] transition-all duration-200 ease-out"
              style={{ width: `${progressPercent}%` }}
            ></div>
          </div>
        </header>

        <main className="flex-1 max-w-3xl w-full mx-auto px-4 py-8 flex flex-col justify-center">
          <div className="bg-[#FFFFFF] border border-[#E5E5E5] rounded-xl p-6 sm:p-8 space-y-6 shadow-sm">
            
            {/* Concept & Difficulty Tags */}
            <div className="flex items-center gap-2 flex-wrap">
              {currentQ.concept && (
                <span className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full bg-[#F2F2F2] text-[#0F0F0F]">
                  <Target className="w-3.5 h-3.5 text-[#FF0000]" />
                  {currentQ.concept}
                </span>
              )}
              <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full ${diffStyle.bg} ${diffStyle.border} ${diffStyle.text}`}>
                <Zap className="w-3 h-3" />
                {diffStyle.label}
              </span>
            </div>

            {/* Question Text */}
            <h2 className="text-lg sm:text-xl font-bold text-[#0F0F0F] leading-relaxed">
              {currentQ.question}
            </h2>

            {/* Options */}
            <div className="space-y-2.5">
              {currentQ.options.map((opt, idx) => {
                const isSelected = selectedOption === opt;
                return (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => handleOptionSelect(qId, opt)}
                    className={`w-full text-left p-3.5 sm:p-4 rounded-xl border transition-all cursor-pointer ${
                      isSelected 
                        ? 'bg-[#F9F9F9] border-[#0F0F0F] text-[#0F0F0F] shadow-sm' 
                        : 'bg-[#FFFFFF] border-[#E5E5E5] text-[#0F0F0F] hover:border-[#CCCCCC] hover:bg-[#F9F9F9]'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-7 h-7 rounded-full border flex items-center justify-center shrink-0 text-xs font-mono font-bold transition-colors ${
                        isSelected ? 'border-[#0F0F0F] bg-[#0F0F0F] text-white' : 'border-[#CCCCCC] text-[#606060]'
                      }`}>
                        {String.fromCharCode(65 + idx)}
                      </div>
                      <span className="text-xs sm:text-sm font-medium">{opt}</span>
                    </div>
                  </button>
                );
              })}
            </div>

            {/* Navigation Controls */}
            <div className="pt-4 border-t border-[#E5E5E5] flex items-center justify-between">
              <button
                onClick={handlePrevious}
                disabled={currentQuestionIndex === 0}
                className={`yt-btn-secondary text-xs py-2 px-4 flex items-center gap-1.5 ${
                  currentQuestionIndex === 0 ? 'opacity-30 cursor-not-allowed' : 'cursor-pointer'
                }`}
              >
                <ChevronLeft className="w-4 h-4" /> Previous
              </button>

              {isLastQuestion ? (
                <button
                  onClick={handleSubmit}
                  disabled={!selectedOption}
                  className={`yt-btn-primary text-xs py-2 px-5 flex items-center gap-1.5 font-semibold cursor-pointer shadow-sm ${
                    !selectedOption ? 'opacity-40 cursor-not-allowed' : ''
                  }`}
                >
                  <Send className="w-3.5 h-3.5" /> Submit Assessment
                </button>
              ) : (
                <button
                  onClick={handleNext}
                  disabled={!selectedOption}
                  className={`yt-btn-primary text-xs py-2 px-5 flex items-center gap-1.5 font-semibold cursor-pointer shadow-sm ${
                    !selectedOption ? 'opacity-40 cursor-not-allowed' : ''
                  }`}
                >
                  Next <ChevronRight className="w-4 h-4" />
                </button>
              )}
            </div>
            
          </div>
        </main>
      </div>
    );
  }

  // Fallback
  return null;
}

