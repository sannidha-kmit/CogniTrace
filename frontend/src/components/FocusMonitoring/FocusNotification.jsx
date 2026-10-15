import React, { useEffect, useState } from 'react';
import { Eye, AlertTriangle, CheckCircle2, X, Sparkles, Info } from 'lucide-react';

export default function FocusNotification({ notification, onDismiss }) {
  if (!notification) return null;

  const { type, title, message, reasons, timestamp, duration } = notification;

  const isRecovery = type === 'RECOVERY';
  const isHighDistraction = type === 'HIGH_DISTRACTION';

  return (
    <aside aria-label="Learning focus notification" className="fixed bottom-6 right-6 max-w-sm w-full z-50 animate-in fade-in slide-in-from-bottom-4 duration-300">
      <div className={`p-4 rounded-2xl shadow-xl border backdrop-blur-md ${
        isRecovery 
          ? 'bg-[#FFFFFF]/95 border-[#C8E6C9] text-[#2E7D32]' 
          : isHighDistraction
            ? 'bg-[#FFFFFF]/95 border-[#FFCDD2] text-[#C62828]'
            : 'bg-[#FFFFFF]/95 border-[#FFE082] text-[#F57F17]'
      }`}>
        
        {/* Title & Close */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            {isRecovery ? (
              <CheckCircle2 className="w-5 h-5 text-[#2E7D32] shrink-0" />
            ) : isHighDistraction ? (
              <AlertTriangle className="w-5 h-5 text-[#FF0000] shrink-0" />
            ) : (
              <Eye className="w-5 h-5 text-[#F57F17] shrink-0" />
            )}
            <h4 className="text-xs font-bold text-[#0F0F0F]">{title}</h4>
          </div>
          
          <button
            onClick={onDismiss}
            className="p-1 rounded-full hover:bg-[#F2F2F2] text-[#606060] transition-colors"
            title="Dismiss notification"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Message */}
        <p className="text-xs text-[#0F0F0F] mt-2 leading-relaxed">
          {message}
        </p>

        {/* Explainable Reasons List (Requirement 15) */}
        {reasons && reasons.length > 0 && (
          <div className="mt-2.5 p-2.5 rounded-xl bg-[#F9F9F9] border border-[#E5E5E5] space-y-1">
            <p className="text-[10px] uppercase font-bold text-[#606060] tracking-wider">
              Observation Summary:
            </p>
            <ul className="text-[11px] text-[#0F0F0F] space-y-0.5 list-disc list-inside">
              {reasons.map((reason, idx) => (
                <li key={idx} className="leading-snug">{reason}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Non-judgmental footer footnote */}
        <div className="mt-2.5 pt-2 border-t border-[#E5E5E5] flex items-center justify-between text-[10px] text-[#606060]">
          <span className="flex items-center gap-1">
            <Info className="w-3 h-3 text-[#606060]" />
            <span>Estimated behavioral suggestion</span>
          </span>
          {timestamp && <span className="font-mono">at {timestamp}</span>}
        </div>

      </div>
    </aside>
  );
}
