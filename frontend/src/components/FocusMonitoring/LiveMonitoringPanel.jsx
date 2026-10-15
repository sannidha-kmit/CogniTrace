import React, { useState, useEffect, useRef } from 'react';
import { 
  ShieldCheck, 
  Camera, 
  Eye, 
  Pause, 
  Play, 
  ChevronDown, 
  ChevronUp, 
  Lock, 
  Activity, 
  Sun,
  AlertCircle,
  HelpCircle
} from 'lucide-react';
import FaceQualityIndicator from './FaceQualityIndicator';

export default function LiveMonitoringPanel({
  isMonitoring,
  isPaused,
  onTogglePause,
  attentionState,
  focusLevel,
  distractionScore,
  eventsCount,
  frameQuality,
  faceData,
  videoElementRef,
  onOpenPrivacy,
  onOpenCalibration,
  onToggleDevPanel
}) {
  const [showPreview, setShowPreview] = useState(false);
  const canvasRef = useRef(null);

  // Render mini live landmark preview when expanded
  useEffect(() => {
    if (!showPreview || !canvasRef.current || !videoElementRef?.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const vw = videoElementRef.current.videoWidth || 320;
    const vh = videoElementRef.current.videoHeight || 240;

    ctx.save();
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    // Mirror draw
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(videoElementRef.current, 0, 0, canvas.width, canvas.height);

    if (faceData && faceData.detected && faceData.box) {
      const scaleX = canvas.width / vw;
      const scaleY = canvas.height / vh;
      const bx = faceData.box.x * scaleX;
      const by = faceData.box.y * scaleY;
      const bw = faceData.box.width * scaleX;
      const bh = faceData.box.height * scaleY;

      let color = '#2E7D32'; // Focused
      if (attentionState === 'ATTENTION_DRIFT') color = '#F57F17';
      if (attentionState === 'DISTRACTED' || attentionState === 'HIGH_DISTRACTION') color = '#FF0000';

      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.strokeRect(bx, by, bw, bh);

      if (faceData.rawLandmarks) {
        ctx.fillStyle = '#0284C7';
        faceData.rawLandmarks.forEach(pt => {
          ctx.beginPath();
          ctx.arc(pt[0] * scaleX, pt[1] * scaleY, 2, 0, 2 * Math.PI);
          ctx.fill();
        });
      }
    }
    ctx.restore();
  }, [showPreview, faceData, attentionState, videoElementRef]);

  const getStateBadge = () => {
    if (isPaused) {
      return {
        label: 'Monitoring Paused',
        color: 'bg-[#F2F2F2] border-[#E5E5E5] text-[#606060]',
        dot: 'bg-[#909090]'
      };
    }
    switch (attentionState) {
      case 'FOCUSED':
        return {
          label: 'Focused',
          color: 'bg-[#E8F5E9] border-[#C8E6C9] text-[#2E7D32]',
          dot: 'bg-[#2E7D32]'
        };
      case 'ATTENTION_DRIFT':
        return {
          label: 'Attention Drift',
          color: 'bg-[#FFF8E1] border-[#FFE082] text-[#F57F17]',
          dot: 'bg-[#F57F17]'
        };
      case 'DISTRACTED':
        return {
          label: 'Distracted',
          color: 'bg-[#FFF3E0] border-[#FFE0B2] text-[#E65100]',
          dot: 'bg-[#E65100]'
        };
      case 'HIGH_DISTRACTION':
        return {
          label: 'High Distraction',
          color: 'bg-[#FFEBEE] border-[#FFCDD2] text-[#C62828]',
          dot: 'bg-[#FF0000]'
        };
      case 'INSUFFICIENT_VISIBILITY':
        return {
          label: 'Low Visibility',
          color: 'bg-[#FFF8E1] border-[#FFE082] text-[#F57F17]',
          dot: 'bg-[#F57F17]'
        };
      case 'MULTIPLE_FACES':
        return {
          label: 'Multiple Faces',
          color: 'bg-[#FFEBEE] border-[#FFCDD2] text-[#C62828]',
          dot: 'bg-[#FF0000]'
        };
      default:
        return {
          label: 'Calibrating...',
          color: 'bg-[#F9F9F9] border-[#E5E5E5] text-[#606060]',
          dot: 'bg-[#606060]'
        };
    }
  };

  const badge = getStateBadge();
  const lightingScore = frameQuality ? frameQuality.lightingScore : 85;
  const isFaceDetected = Boolean(faceData && faceData.detected && !faceData.multipleFaces);

  return (
    <div className="bg-[#FFFFFF] border border-[#E5E5E5] rounded-2xl p-4 shadow-sm space-y-3.5">
      
      {/* Header Row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-[#2E7D32] animate-pulse" />
          <h3 className="text-xs font-bold text-[#0F0F0F] tracking-tight">
            Focus Monitoring
          </h3>
          <span className="text-[10px] text-[#2E7D32] font-semibold bg-[#E8F5E9] px-2 py-0.5 rounded-full flex items-center gap-1">
            <Lock className="w-2.5 h-2.5" /> Local
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={onTogglePause}
            className="p-1.5 rounded-lg hover:bg-[#F2F2F2] text-[#606060] transition-colors"
            title={isPaused ? 'Resume monitoring' : 'Pause monitoring'}
          >
            {isPaused ? <Play className="w-3.5 h-3.5 text-[#2E7D32]" /> : <Pause className="w-3.5 h-3.5" />}
          </button>
          
          <button
            type="button"
            onClick={() => setShowPreview(!showPreview)}
            className="p-1.5 rounded-lg hover:bg-[#F2F2F2] text-[#606060] transition-colors text-xs flex items-center gap-0.5"
            title="Toggle camera preview"
          >
            <Camera className="w-3.5 h-3.5" />
            {showPreview ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
        </div>
      </div>

      {/* Focus Level Progress Bar */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <span className="text-[#606060] font-medium">Focus Level</span>
          <span className="font-mono font-bold text-[#0F0F0F]">{focusLevel}%</span>
        </div>
        <div className="w-full bg-[#F2F2F2] rounded-full h-2.5 overflow-hidden border border-[#E5E5E5]">
          <div 
            className={`h-full rounded-full transition-all duration-300 ${
              focusLevel >= 70 ? 'bg-[#2E7D32]' : focusLevel >= 40 ? 'bg-[#F57F17]' : 'bg-[#FF0000]'
            }`}
            style={{ width: `${focusLevel}%` }}
          />
        </div>
      </div>

      {/* Status Badges & Hardware Indicators Row */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-[11px]">
        {/* Status Pill */}
        <div className={`p-2 rounded-xl border flex items-center gap-1.5 ${badge.color}`}>
          <span className={`w-2 h-2 rounded-full ${badge.dot}`} />
          <span className="font-semibold truncate">{badge.label}</span>
        </div>

        {/* Camera / Lighting Status */}
        <div className="p-2 rounded-xl bg-[#F9F9F9] border border-[#E5E5E5] flex items-center justify-between text-[#0F0F0F]">
          <span className="text-[#606060]">Camera</span>
          <span className="font-semibold text-[#2E7D32]">Good ({lightingScore}%)</span>
        </div>

        {/* Face Status */}
        <div className="p-2 rounded-xl bg-[#F9F9F9] border border-[#E5E5E5] flex items-center justify-between text-[#0F0F0F]">
          <span className="text-[#606060]">Face</span>
          <span className={`font-semibold ${isFaceDetected ? 'text-[#2E7D32]' : 'text-[#F57F17]'}`}>
            {isFaceDetected ? 'Detected' : 'Searching'}
          </span>
        </div>
      </div>

      {/* Distraction Events Counter */}
      <div className="flex items-center justify-between text-[11px] px-1 text-[#606060]">
        <span>Distraction Events Recorded: <strong className="text-[#0F0F0F]">{eventsCount}</strong></span>
        <button
          type="button"
          onClick={onOpenPrivacy}
          className="text-[#606060] hover:text-[#0F0F0F] underline transition-colors flex items-center gap-1"
        >
          <Lock className="w-3 h-3 text-[#2E7D32]" />
          <span>Privacy Guarantee</span>
        </button>
      </div>

      {/* Expandable Mini Camera Preview with Landmarks */}
      {showPreview && (
        <div className="pt-2 border-t border-[#E5E5E5] space-y-2">
          <div className="relative aspect-[4/3] max-w-[240px] mx-auto bg-[#0F0F0F] rounded-xl overflow-hidden border border-[#E5E5E5]">
            <canvas
              ref={canvasRef}
              width={240}
              height={180}
              className="w-full h-full object-cover"
            />
            <div className="absolute bottom-1 left-1.5 right-1.5 text-center bg-black/60 backdrop-blur-sm text-white text-[9px] py-0.5 rounded">
              Local Inference Preview • No Upload
            </div>
          </div>
          <FaceQualityIndicator 
            lightingScore={lightingScore} 
            faceVisibility={faceData ? Math.round(faceData.confidence * 100) : 0}
            compact={true}
          />
        </div>
      )}

    </div>
  );
}
