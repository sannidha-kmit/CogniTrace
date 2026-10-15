import React, { useState } from 'react';
import { Terminal, X, Minimize2, Maximize2, Cpu, Activity, Eye, ShieldAlert } from 'lucide-react';

export default function DeveloperDebugPanel({
  faceData,
  landmarks,
  frameQuality,
  distractionData,
  personalBaseline,
  fps = 8,
  onClose
}) {
  const [minimized, setMinimized] = useState(false);

  if (minimized) {
    return (
      <div className="fixed bottom-3 left-3 z-50">
        <button
          type="button"
          onClick={() => setMinimized(false)}
          className="bg-[#0F0F0F] text-[#FFFFFF] px-3 py-1.5 rounded-full text-xs font-mono font-bold flex items-center gap-2 shadow-lg border border-[#333333] hover:bg-[#262626]"
        >
          <Terminal className="w-3.5 h-3.5 text-[#00E676]" />
          <span>Dev Diagnostics ({fps} FPS)</span>
        </button>
      </div>
    );
  }

  return (
    <aside aria-label="Developer diagnostics" className="fixed bottom-3 left-3 max-w-sm w-full bg-[#0F0F0F] text-[#FFFFFF] rounded-2xl p-4 shadow-2xl border border-[#333333] font-mono text-xs z-50 space-y-3">
      
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#262626] pb-2">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-[#00E676]" />
          <span className="font-bold tracking-tight text-[#FFFFFF]">Developer Monitoring</span>
          <span className="bg-[#262626] text-[#00E676] text-[10px] px-2 py-0.5 rounded-full">
            {fps} FPS
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setMinimized(true)}
            className="p-1 text-[#888888] hover:text-[#FFFFFF] transition-colors"
            title="Minimize"
          >
            <Minimize2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={onClose}
            className="p-1 text-[#888888] hover:text-[#FFFFFF] transition-colors"
            title="Close"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Primary Telemetry Grid */}
      <div className="grid grid-cols-2 gap-2 text-[11px]">
        
        <div className="p-2 rounded-lg bg-[#1A1A1A] border border-[#262626]">
          <span className="text-[#888888] block">Face Confidence</span>
          <span className="text-[#00E676] font-bold">
            {faceData?.confidence ? faceData.confidence.toFixed(2) : '0.00'}
          </span>
        </div>

        <div className="p-2 rounded-lg bg-[#1A1A1A] border border-[#262626]">
          <span className="text-[#888888] block">Face Visibility</span>
          <span className="text-[#00E676] font-bold">
            {landmarks?.faceVisibility || 0}%
          </span>
        </div>

        <div className="p-2 rounded-lg bg-[#1A1A1A] border border-[#262626]">
          <span className="text-[#888888] block">Head Yaw</span>
          <span className="text-[#64B5F6] font-bold">
            {landmarks?.yaw ? `${landmarks.yaw}°` : '0.0°'}
          </span>
        </div>

        <div className="p-2 rounded-lg bg-[#1A1A1A] border border-[#262626]">
          <span className="text-[#888888] block">Head Pitch</span>
          <span className="text-[#64B5F6] font-bold">
            {landmarks?.pitch ? `${landmarks.pitch}°` : '0.0°'}
          </span>
        </div>

        <div className="p-2 rounded-lg bg-[#1A1A1A] border border-[#262626]">
          <span className="text-[#888888] block">Head Roll</span>
          <span className="text-[#64B5F6] font-bold">
            {landmarks?.roll ? `${landmarks.roll}°` : '0.0°'}
          </span>
        </div>

        <div className="p-2 rounded-lg bg-[#1A1A1A] border border-[#262626]">
          <span className="text-[#888888] block">Gaze Deviation</span>
          <span className="text-[#FFD54F] font-bold">
            {landmarks?.gazeDeviation ? landmarks.gazeDeviation.toFixed(2) : '0.00'}
          </span>
        </div>

        <div className="p-2 rounded-lg bg-[#1A1A1A] border border-[#262626]">
          <span className="text-[#888888] block">Lighting Score</span>
          <span className="text-[#FFD54F] font-bold">
            {frameQuality?.lightingScore || 85}%
          </span>
        </div>

        <div className="p-2 rounded-lg bg-[#1A1A1A] border border-[#262626]">
          <span className="text-[#888888] block">Distraction Score</span>
          <span className="text-[#FF5252] font-bold">
            {distractionData?.distractionScore || 0}
          </span>
        </div>

      </div>

      {/* State & Baseline */}
      <div className="p-2.5 rounded-lg bg-[#1A1A1A] border border-[#262626] space-y-1 text-[11px]">
        <div className="flex justify-between">
          <span className="text-[#888888]">Inference State:</span>
          <strong className="text-[#00E676]">{distractionData?.state || 'FOCUSED'}</strong>
        </div>
        <div className="flex justify-between">
          <span className="text-[#888888]">Personal Baseline:</span>
          <span className="text-[#FFFFFF]">
            Yaw ±{personalBaseline?.naturalYawRange || 18}°, Pitch ±{personalBaseline?.naturalPitchRange || 14}°
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-[#888888]">Privacy Mode:</span>
          <span className="text-[#00E676]">100% In-Browser (No Frames Uploaded)</span>
        </div>
      </div>

    </aside>
  );
}
