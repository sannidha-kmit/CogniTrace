import React from 'react';
import { BookOpen, AlertTriangle, Play, BrainCircuit, ArrowRight, CheckCircle2 } from 'lucide-react';
import { Link } from 'react-router-dom';

function parseTimestampToSec(ts) {
  if (typeof ts === 'number') return ts;
  if (!ts) return 0;
  const parts = ts.split(':').map(Number);
  if (parts.length === 2) return parts[0] * 60 + parts[1];
  if (parts.length === 3) return parts[0] * 3600 + parts[1] * 60 + parts[2];
  return 0;
}

export default function ConceptDistractionReview({
  concepts = [],
  distractionEvents = [],
  courseId,
  onSeekTo,
  onStartQuiz
}) {
  // Map distraction timestamps against course concepts
  const mappedConcepts = concepts.map(c => {
    const cStart = parseTimestampToSec(c.ConceptStart);
    const cEnd = parseTimestampToSec(c.ConceptEnd);

    // Find any events within this concept's time range
    const relatedEvents = distractionEvents.filter(e => {
      const eTime = e.videoTimeSec !== undefined ? e.videoTimeSec : parseTimestampToSec(e.videoTimestamp);
      return eTime >= cStart && eTime <= cEnd;
    });

    const isDistracted = relatedEvents.length > 0;
    const maxScore = isDistracted ? Math.max(...relatedEvents.map(e => e.score || 70)) : 0;

    return {
      ...c,
      cStart,
      cEnd,
      isDistracted,
      eventCount: relatedEvents.length,
      maxScore,
      firstDistractedTime: relatedEvents[0]?.videoTimestamp || c.ConceptStart
    };
  });

  const distractedConcepts = mappedConcepts.filter(c => c.isDistracted);

  if (distractedConcepts.length === 0) {
    return (
      <div className="p-4 rounded-2xl bg-[#E8F5E9] border border-[#C8E6C9] flex items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2.5 text-[#2E7D32]">
          <CheckCircle2 className="w-5 h-5 shrink-0" />
          <span>You maintained steady focus across all lecture concepts! You are fully primed for the adaptive assessment.</span>
        </div>
        {onStartQuiz && (
          <button
            type="button"
            onClick={onStartQuiz}
            className="yt-btn-primary text-xs py-2 px-4 shadow-sm shrink-0"
          >
            <BrainCircuit className="w-4 h-4" />
            <span>Proceed to Quiz</span>
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="bg-[#FFFFFF] border border-[#E5E5E5] rounded-2xl p-5 shadow-sm space-y-4">
      
      {/* Header Prompt */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#E5E5E5] pb-3">
        <div>
          <h3 className="text-sm font-bold text-[#0F0F0F] flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-[#FF0000]" />
            <span>Concepts Requiring Optional Review</span>
          </h3>
          <p className="text-xs text-[#606060] mt-0.5">
            Prolonged attention drift was detected during these sections of the lecture.
          </p>
        </div>

        {onStartQuiz && (
          <button
            type="button"
            onClick={onStartQuiz}
            className="yt-btn-primary text-xs py-2 px-4 shadow-sm self-start sm:self-auto"
          >
            <BrainCircuit className="w-4 h-4" />
            <span>Start Adaptive Quiz</span>
          </button>
        )}
      </div>

      {/* Suggested Concept Cards */}
      <div className="space-y-2.5">
        {distractedConcepts.map((c, idx) => (
          <div 
            key={idx} 
            className="p-3.5 rounded-xl bg-[#FFF8E1] border border-[#FFE082] flex flex-col sm:flex-row sm:items-center justify-between gap-3"
          >
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[#F57F17]" />
                <h4 className="text-xs font-bold text-[#0F0F0F]">{c.Concept}</h4>
                <span className="text-[10px] font-semibold text-[#F57F17] bg-[#FFFFFF] px-2 py-0.5 rounded-full border border-[#FFE082]">
                  {c.DifficultyLevel || 'Core Concept'}
                </span>
              </div>
              <p className="text-[11px] text-[#606060]">
                Timestamp span: <span className="font-mono font-semibold text-[#0F0F0F]">{c.ConceptStart} – {c.ConceptEnd}</span>
                {c.firstDistractedTime && ` • Drift noted around ${c.firstDistractedTime}`}
              </p>
            </div>

            <button
              type="button"
              onClick={() => onSeekTo && onSeekTo(c.cStart)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-[#FFFFFF] border border-[#FFE082] text-[#0F0F0F] hover:bg-[#FF0000] hover:text-[#FFFFFF] hover:border-[#FF0000] transition-colors shadow-sm self-start sm:self-auto"
            >
              <Play className="w-3 h-3 fill-current" />
              <span>Review Lecture Section</span>
            </button>
          </div>
        ))}
      </div>

      {/* Suggestion Note */}
      <p className="text-[11px] text-[#606060] italic">
        "Would you like to review this concept before starting the quiz?"
      </p>

    </div>
  );
}
