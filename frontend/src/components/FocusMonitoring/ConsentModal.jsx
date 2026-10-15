import React from 'react';
import { ShieldCheck, Camera, CheckCircle2, Lock, Eye, AlertCircle, X } from 'lucide-react';

export default function ConsentModal({ onEnable, onDismiss }) {
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[#FFFFFF] border border-[#E5E5E5] p-6 rounded-2xl max-w-lg w-full shadow-xl space-y-5">
        
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-[#FFEBEE] flex items-center justify-center text-[#FF0000]">
              <Camera className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-[#0F0F0F]">Focus Monitoring</h2>
              <p className="text-xs text-[#606060]">Intelligent In-Browser Learning Assistance</p>
            </div>
          </div>
          <button
            onClick={onDismiss}
            className="p-1.5 rounded-full hover:bg-[#F2F2F2] text-[#606060] transition-colors"
            title="Dismiss"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Core Description */}
        <p className="text-xs text-[#0F0F0F] leading-relaxed">
          CogniTrace can analyze your camera feed locally to estimate attention and detect prolonged distraction during learning.
        </p>

        {/* Strict Privacy Guarantee Box */}
        <div className="p-3.5 rounded-xl bg-[#F0FDF4] border border-[#BBF7D0] space-y-1.5">
          <div className="flex items-center gap-2 text-xs font-semibold text-[#166534]">
            <Lock className="w-4 h-4 text-[#16A34A] shrink-0" />
            <span>🔒 Your video is processed locally and is not recorded or uploaded.</span>
          </div>
          <p className="text-[11px] text-[#15803D] pl-6 leading-relaxed">
            All facial landmark estimations run entirely in your web browser. Only high-level numerical summary scores are synchronized.
          </p>
        </div>

        {/* Feature Highlights */}
        <div className="space-y-2 text-xs text-[#606060]">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-[#2E7D32] shrink-0" />
            <span>Personalized posture baseline calibration</span>
          </div>
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-[#2E7D32] shrink-0" />
            <span>Gentle, non-judgmental reminders during sustained drift</span>
          </div>
          <div className="flex items-center gap-2.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-[#2E7D32] shrink-0" />
            <span>Post-lecture timeline linking distracted moments to course concepts</span>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <button
            type="button"
            onClick={onDismiss}
            className="yt-btn-secondary text-xs py-2 px-4"
          >
            Not Now
          </button>
          <button
            type="button"
            onClick={onEnable}
            className="yt-btn-primary text-xs py-2 px-5 flex items-center gap-2"
          >
            <ShieldCheck className="w-4 h-4" />
            <span>Enable Focus Monitoring</span>
          </button>
        </div>

      </div>
    </div>
  );
}
