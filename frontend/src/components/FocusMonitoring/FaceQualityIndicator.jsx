import React from 'react';
import { Sun, Eye, ShieldCheck, Activity } from 'lucide-react';

export default function FaceQualityIndicator({ 
  lightingScore = 85, 
  faceVisibility = 92, 
  stabilityScore = 88,
  confidence = 94,
  compact = false 
}) {
  const getScoreColor = (val) => {
    if (val >= 75) return 'text-[#2E7D32] bg-[#E8F5E9] border-[#C8E6C9]';
    if (val >= 50) return 'text-[#F57F17] bg-[#FFF8E1] border-[#FFE082]';
    return 'text-[#C62828] bg-[#FFEBEE] border-[#FFCDD2]';
  };

  if (compact) {
    return (
      <div className="flex items-center gap-2 text-[11px]">
        <span className={`px-2 py-0.5 rounded-full border font-mono font-semibold ${getScoreColor(lightingScore)}`}>
          Lighting: {lightingScore}%
        </span>
        <span className={`px-2 py-0.5 rounded-full border font-mono font-semibold ${getScoreColor(faceVisibility)}`}>
          Visibility: {faceVisibility}%
        </span>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-3 gap-2 text-xs">
      <div className="p-2 rounded-lg bg-[#F9F9F9] border border-[#E5E5E5] space-y-1">
        <div className="flex items-center justify-between text-[#606060] text-[11px]">
          <span className="flex items-center gap-1">
            <Sun className="w-3 h-3 text-[#F57F17]" /> Lighting
          </span>
          <span className="font-mono font-bold text-[#0F0F0F]">{lightingScore}%</span>
        </div>
        <div className="w-full bg-[#E5E5E5] rounded-full h-1.5 overflow-hidden">
          <div 
            className="bg-[#F57F17] h-full rounded-full transition-all duration-300"
            style={{ width: `${lightingScore}%` }}
          />
        </div>
      </div>

      <div className="p-2 rounded-lg bg-[#F9F9F9] border border-[#E5E5E5] space-y-1">
        <div className="flex items-center justify-between text-[#606060] text-[11px]">
          <span className="flex items-center gap-1">
            <Eye className="w-3 h-3 text-[#0284C7]" /> Visibility
          </span>
          <span className="font-mono font-bold text-[#0F0F0F]">{faceVisibility}%</span>
        </div>
        <div className="w-full bg-[#E5E5E5] rounded-full h-1.5 overflow-hidden">
          <div 
            className="bg-[#0284C7] h-full rounded-full transition-all duration-300"
            style={{ width: `${faceVisibility}%` }}
          />
        </div>
      </div>

      <div className="p-2 rounded-lg bg-[#F9F9F9] border border-[#E5E5E5] space-y-1">
        <div className="flex items-center justify-between text-[#606060] text-[11px]">
          <span className="flex items-center gap-1">
            <Activity className="w-3 h-3 text-[#2E7D32]" /> Stability
          </span>
          <span className="font-mono font-bold text-[#0F0F0F]">{stabilityScore}%</span>
        </div>
        <div className="w-full bg-[#E5E5E5] rounded-full h-1.5 overflow-hidden">
          <div 
            className="bg-[#2E7D32] h-full rounded-full transition-all duration-300"
            style={{ width: `${stabilityScore}%` }}
          />
        </div>
      </div>
    </div>
  );
}
