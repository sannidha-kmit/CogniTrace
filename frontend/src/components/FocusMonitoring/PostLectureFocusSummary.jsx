import React from 'react';
import { 
  Award, 
  Clock, 
  Activity, 
  BrainCircuit, 
  CheckCircle2, 
  AlertTriangle, 
  ChevronRight,
  ShieldCheck,
  RotateCcw
} from 'lucide-react';
import { Link } from 'react-router-dom';
import FocusTimeline from './FocusTimeline';
import DistractionEventTable from './DistractionEventTable';
import ConceptDistractionReview from './ConceptDistractionReview';

function formatDuration(totalSeconds) {
  if (isNaN(totalSeconds) || totalSeconds <= 0) return '00:00';
  const mins = Math.floor(totalSeconds / 60);
  const secs = Math.floor(totalSeconds % 60);
  return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
}

export default function PostLectureFocusSummary({
  courseId,
  duration = 600,
  events = [],
  concepts = [],
  onSeekTo,
  onStartQuiz
}) {
  const totalEvents = events.length;
  const highDistractionEvents = events.filter(e => e.state === 'HIGH_DISTRACTION');
  const driftEvents = events.filter(e => e.state === 'ATTENTION_DRIFT' || e.state === 'DISTRACTED');

  const totalDistractionDurationSec = events.reduce((acc, e) => acc + (e.duration || 0), 0);
  const highDistractionSec = highDistractionEvents.reduce((acc, e) => acc + (e.duration || 0), 0);
  const driftSec = Math.max(0, totalDistractionDurationSec - highDistractionSec);
  const focusedSec = Math.max(0, duration - totalDistractionDurationSec);

  const longestEventSec = events.length > 0 ? Math.max(...events.map(e => e.duration || 0)) : 0;
  const overallFocusScore = Math.max(10, Math.min(100, Math.round((focusedSec / Math.max(1, duration)) * 100)));

  return (
    <div className="space-y-6 pt-2">
      
      {/* Top Banner Card */}
      <div className="bg-[#FFFFFF] border border-[#E5E5E5] rounded-2xl p-6 shadow-sm space-y-6">
        
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#E5E5E5] pb-5">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-[#E8F5E9] flex items-center justify-center text-[#2E7D32]">
              <Award className="w-6 h-6" />
            </div>
            <div>
              <span className="text-[11px] font-bold text-[#2E7D32] uppercase tracking-wider">Post-Lecture Summary</span>
              <h2 className="text-xl font-bold text-[#0F0F0F] tracking-tight">Lecture Attention & Focus Report</h2>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-right">
              <span className="text-[11px] text-[#606060] block font-medium">Overall Focus Score</span>
              <span className="text-2xl font-black text-[#0F0F0F] font-mono">{overallFocusScore}%</span>
            </div>
            <div className="w-12 h-12 rounded-full bg-[#F2F2F2] border border-[#E5E5E5] flex items-center justify-center font-mono font-bold text-base text-[#0F0F0F]">
              {overallFocusScore >= 75 ? 'A' : overallFocusScore >= 60 ? 'B' : 'C'}
            </div>
          </div>
        </div>

        {/* 6-Grid Metric Breakdown (Requirement 18) */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-center">
          
          <div className="p-3.5 rounded-xl bg-[#F9F9F9] border border-[#E5E5E5]">
            <p className="text-[11px] text-[#606060] font-semibold mb-1">Overall Focus</p>
            <p className="text-lg font-bold text-[#0F0F0F] font-mono">{overallFocusScore}%</p>
          </div>

          <div className="p-3.5 rounded-xl bg-[#E8F5E9] border border-[#C8E6C9]">
            <p className="text-[11px] text-[#2E7D32] font-semibold mb-1">Focused Time</p>
            <p className="text-lg font-bold text-[#2E7D32] font-mono">{formatDuration(focusedSec)}</p>
          </div>

          <div className="p-3.5 rounded-xl bg-[#FFF8E1] border border-[#FFE082]">
            <p className="text-[11px] text-[#F57F17] font-semibold mb-1">Attention Drift</p>
            <p className="text-lg font-bold text-[#F57F17] font-mono">{formatDuration(driftSec)}</p>
          </div>

          <div className="p-3.5 rounded-xl bg-[#FFEBEE] border border-[#FFCDD2]">
            <p className="text-[11px] text-[#C62828] font-semibold mb-1">High Distraction</p>
            <p className="text-lg font-bold text-[#C62828] font-mono">{formatDuration(highDistractionSec)}</p>
          </div>

          <div className="p-3.5 rounded-xl bg-[#F9F9F9] border border-[#E5E5E5]">
            <p className="text-[11px] text-[#606060] font-semibold mb-1">Distraction Events</p>
            <p className="text-lg font-bold text-[#0F0F0F] font-mono">{totalEvents}</p>
          </div>

          <div className="p-3.5 rounded-xl bg-[#F9F9F9] border border-[#E5E5E5]">
            <p className="text-[11px] text-[#606060] font-semibold mb-1">Longest Event</p>
            <p className="text-lg font-bold text-[#0F0F0F] font-mono">{longestEventSec} sec</p>
          </div>

        </div>

      </div>

      {/* Interactive Timeline */}
      <FocusTimeline 
        duration={duration} 
        currentTime={duration} 
        events={events} 
        onSeekTo={onSeekTo} 
      />

      {/* Distraction Moments Table */}
      <DistractionEventTable 
        events={events} 
        onSeekTo={onSeekTo} 
      />

      {/* Concept Distraction Mapping */}
      <ConceptDistractionReview 
        concepts={concepts}
        distractionEvents={events}
        courseId={courseId}
        onSeekTo={onSeekTo}
        onStartQuiz={onStartQuiz}
      />

    </div>
  );
}
