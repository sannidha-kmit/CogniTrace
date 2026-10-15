import React from 'react';
import { Clock, Play, AlertCircle } from 'lucide-react';

function formatSeconds(secs) {
  if (isNaN(secs) || secs < 0) return '00:00';
  const m = Math.floor(secs / 60);
  const s = Math.floor(secs % 60);
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

export default function FocusTimeline({ 
  duration = 600, 
  currentTime = 0, 
  events = [], 
  onSeekTo 
}) {
  const totalDuration = Math.max(1, duration);

  const getStateColor = (state) => {
    switch (state) {
      case 'ATTENTION_DRIFT':
        return 'bg-[#F57F17] hover:bg-[#E65100]';
      case 'DISTRACTED':
        return 'bg-[#E65100] hover:bg-[#BF360C]';
      case 'HIGH_DISTRACTION':
        return 'bg-[#FF0000] hover:bg-[#C62828]';
      default:
        return 'bg-[#2E7D32] hover:bg-[#1B5E20]';
    }
  };

  return (
    <div className="space-y-3 p-4 bg-[#FFFFFF] border border-[#E5E5E5] rounded-2xl shadow-sm">
      <div className="flex items-center justify-between text-xs">
        <div className="flex items-center gap-2 font-bold text-[#0F0F0F]">
          <Clock className="w-4 h-4 text-[#FF0000]" />
          <span>Interactive Attention Timeline</span>
        </div>
        <span className="text-[11px] text-[#606060] font-mono">
          {formatSeconds(currentTime)} / {formatSeconds(totalDuration)}
        </span>
      </div>

      {/* Main Interactive Bar */}
      <div className="relative w-full h-8 bg-[#E8F5E9] rounded-xl overflow-hidden border border-[#C8E6C9] flex items-center cursor-pointer">
        {/* Base Focused Background Layer */}
        <div className="absolute inset-0 bg-[#E8F5E9]" title="Focused session baseline" />

        {/* Distraction Event Markers */}
        {events.map((evt, idx) => {
          const startSec = evt.videoTimeSec || 0;
          const leftPercent = Math.min(100, Math.max(0, (startSec / totalDuration) * 100));
          const widthPercent = Math.min(100 - leftPercent, Math.max(1.5, ((evt.duration || 6) / totalDuration) * 100));

          return (
            <button
              key={evt.eventId || idx}
              type="button"
              onClick={() => onSeekTo && onSeekTo(startSec)}
              className={`absolute top-0 bottom-0 ${getStateColor(evt.state)} transition-all opacity-90 hover:opacity-100 hover:scale-y-110 z-10`}
              style={{ left: `${leftPercent}%`, width: `${widthPercent}%` }}
              title={`Jump to ${evt.videoTimestamp || formatSeconds(startSec)}: ${evt.state} (${evt.duration || 6}s)`}
            />
          );
        })}

        {/* Current Playhead Indicator */}
        <div 
          className="absolute top-0 bottom-0 w-1 bg-[#0F0F0F] z-20 pointer-events-none shadow-md"
          style={{ left: `${Math.min(100, (currentTime / totalDuration) * 100)}%` }}
        />
      </div>

      {/* Legend & Help Footnote */}
      <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-[#606060] pt-1">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#2E7D32]" />
            <span>Focused</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#F57F17]" />
            <span>Attention Drift</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#FF0000]" />
            <span>High Distraction</span>
          </div>
        </div>

        <span className="text-[10px] text-[#606060]">
          💡 Click any colored segment to jump to that moment in the lecture
        </span>
      </div>

    </div>
  );
}
