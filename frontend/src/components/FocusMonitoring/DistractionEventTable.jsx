import React from 'react';
import { Play, RotateCcw, AlertCircle, Clock, ExternalLink } from 'lucide-react';

export default function DistractionEventTable({ events = [], onSeekTo }) {
  if (!events || events.length === 0) {
    return (
      <div className="p-6 rounded-2xl bg-[#F9F9F9] border border-[#E5E5E5] text-center space-y-2">
        <Clock className="w-6 h-6 text-[#2E7D32] mx-auto opacity-70" />
        <p className="text-xs font-semibold text-[#0F0F0F]">Excellent Focus Recorded</p>
        <p className="text-[11px] text-[#606060]">
          No prolonged distraction episodes were observed during this lecture session.
        </p>
      </div>
    );
  }

  const getStateBadge = (state) => {
    switch (state) {
      case 'ATTENTION_DRIFT':
        return <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-[#FFF8E1] border border-[#FFE082] text-[#F57F17]">Drift</span>;
      case 'DISTRACTED':
        return <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-[#FFF3E0] border border-[#FFE0B2] text-[#E65100]">Distracted</span>;
      case 'HIGH_DISTRACTION':
        return <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-[#FFEBEE] border border-[#FFCDD2] text-[#C62828]">High Distraction</span>;
      default:
        return <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold bg-[#E8F5E9] border border-[#C8E6C9] text-[#2E7D32]">Focused</span>;
    }
  };

  return (
    <div className="bg-[#FFFFFF] border border-[#E5E5E5] rounded-2xl overflow-hidden shadow-sm space-y-0">
      <div className="p-4 border-b border-[#E5E5E5] flex items-center justify-between">
        <div>
          <h3 className="text-xs font-bold text-[#0F0F0F]">Recorded Distraction Moments</h3>
          <p className="text-[11px] text-[#606060]">Moments where sustained attention drift was detected</p>
        </div>
        <span className="text-xs font-mono font-bold text-[#0F0F0F] bg-[#F2F2F2] px-2.5 py-1 rounded-full">
          {events.length} {events.length === 1 ? 'Event' : 'Events'}
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-[#F9F9F9] border-b border-[#E5E5E5] text-[11px] font-bold text-[#606060] uppercase tracking-wider">
            <tr>
              <th className="py-2.5 px-4">Time</th>
              <th className="py-2.5 px-4">Duration</th>
              <th className="py-2.5 px-4">Distraction Score</th>
              <th className="py-2.5 px-4">State</th>
              <th className="py-2.5 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[#E5E5E5]">
            {events.map((evt, idx) => (
              <tr key={evt.eventId || idx} className="hover:bg-[#F9F9F9] transition-colors">
                <td className="py-3 px-4 font-mono font-bold text-[#0F0F0F]">
                  {evt.videoTimestamp || '00:00'}
                </td>
                <td className="py-3 px-4 font-mono text-[#606060]">
                  {evt.duration} sec
                </td>
                <td className="py-3 px-4 font-mono font-semibold text-[#0F0F0F]">
                  {evt.score || evt.distractionScore || 70}
                </td>
                <td className="py-3 px-4">
                  {getStateBadge(evt.state)}
                </td>
                <td className="py-3 px-4 text-right">
                  <button
                    type="button"
                    onClick={() => onSeekTo && onSeekTo(evt.videoTimeSec || 0)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-[#F2F2F2] text-[#0F0F0F] hover:bg-[#FF0000] hover:text-[#FFFFFF] transition-colors shadow-sm"
                  >
                    <Play className="w-3 h-3 fill-current" />
                    <span>Review Moment →</span>
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
