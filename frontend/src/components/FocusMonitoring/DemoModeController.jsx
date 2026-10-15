import React, { useState, useEffect } from 'react';
import { Sparkles, Play, RotateCcw, AlertTriangle, CheckCircle2, X } from 'lucide-react';

const DEMO_STEPS = [
  {
    state: 'FOCUSED',
    score: 8,
    focusLevel: 92,
    yaw: 2.1,
    pitch: 1.4,
    gaze: 0.08,
    duration: 0,
    label: '1. Normal Focus (Attentive student reading screen)',
    notification: null
  },
  {
    state: 'ATTENTION_DRIFT',
    score: 38,
    focusLevel: 62,
    yaw: 16.5,
    pitch: 5.2,
    gaze: 0.32,
    duration: 3.5,
    label: '2. Attention Drift (Student looking away briefly)',
    notification: null
  },
  {
    state: 'DISTRACTED',
    score: 68,
    focusLevel: 32,
    yaw: 28.4,
    pitch: -12.1,
    gaze: 0.58,
    duration: 6.2,
    label: '3. Distracted (Looking at phone / outside screen)',
    notification: null
  },
  {
    state: 'HIGH_DISTRACTION',
    score: 86,
    focusLevel: 14,
    yaw: 34.0,
    pitch: -18.5,
    gaze: 0.74,
    duration: 9.0,
    label: '4. High Distraction (>8s trigger explainable reminder)',
    notification: {
      type: 'HIGH_DISTRACTION',
      title: 'Attention Drift Detected',
      message: 'You may be distracted. Consider returning your attention to the lecture.',
      reasons: [
        'Head orientation moved away from screen',
        'Gaze shifted away from lecture window',
        'Observed for approximately 8 seconds'
      ]
    }
  },
  {
    state: 'FOCUSED',
    score: 12,
    focusLevel: 88,
    yaw: 1.8,
    pitch: 0.8,
    gaze: 0.10,
    duration: 0,
    label: '5. Restored Focus (Student returns attention)',
    notification: {
      type: 'RECOVERY',
      title: 'Focus Restored',
      message: 'Welcome back! Your focus has returned to the lecture.',
      reasons: []
    }
  }
];

export default function DemoModeController({ onApplyDemoState, onClose }) {
  const [currentStepIdx, setCurrentStepIdx] = useState(0);
  const [isAutoPlaying, setIsAutoPlaying] = useState(false);

  useEffect(() => {
    let timer = null;
    if (isAutoPlaying) {
      timer = setInterval(() => {
        setCurrentStepIdx(prev => {
          const next = (prev + 1) % DEMO_STEPS.length;
          onApplyDemoState(DEMO_STEPS[next]);
          return next;
        });
      }, 3500);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isAutoPlaying, onApplyDemoState]);

  const handleSelectStep = (idx) => {
    setCurrentStepIdx(idx);
    onApplyDemoState(DEMO_STEPS[idx]);
  };

  return (
    <div className="fixed top-16 right-6 max-w-sm w-full bg-[#FFFFFF] border-2 border-[#FF0000] rounded-2xl p-4 shadow-2xl z-50 space-y-3 font-sans text-xs">
      
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#E5E5E5] pb-2">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-[#FF0000] animate-ping" />
          <h4 className="font-bold text-[#FF0000] uppercase tracking-wider text-[11px]">
            Demo Simulation Mode
          </h4>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-full hover:bg-[#F2F2F2] text-[#606060]"
          title="Close demo mode"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <p className="text-[11px] text-[#606060] leading-relaxed">
        Demonstrates the complete attention state machine, temporal windows, and notification triggers for project presentation:
      </p>

      {/* Step Selector Buttons */}
      <div className="space-y-1.5">
        {DEMO_STEPS.map((step, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => handleSelectStep(idx)}
            className={`w-full text-left p-2 rounded-xl border text-[11px] font-semibold transition-all ${
              currentStepIdx === idx
                ? 'bg-[#FFEBEE] border-[#FFCDD2] text-[#C62828] shadow-sm'
                : 'bg-[#F9F9F9] border-[#E5E5E5] text-[#0F0F0F] hover:bg-[#F2F2F2]'
            }`}
          >
            {step.label}
          </button>
        ))}
      </div>

      {/* Auto-Play Toggle */}
      <div className="flex items-center justify-between pt-2 border-t border-[#E5E5E5]">
        <button
          type="button"
          onClick={() => setIsAutoPlaying(!isAutoPlaying)}
          className={`px-3 py-1.5 rounded-full text-xs font-semibold flex items-center gap-1.5 ${
            isAutoPlaying 
              ? 'bg-[#FF0000] text-[#FFFFFF]' 
              : 'bg-[#F2F2F2] text-[#0F0F0F] hover:bg-[#E5E5E5]'
          }`}
        >
          <Play className="w-3 h-3 fill-current" />
          <span>{isAutoPlaying ? 'Pause Auto Sequence' : 'Auto Play Sequence'}</span>
        </button>

        <span className="text-[10px] text-[#606060] italic">
          Safe Simulation
        </span>
      </div>

    </div>
  );
}
