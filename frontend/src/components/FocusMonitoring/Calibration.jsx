import React, { useEffect, useRef, useState } from 'react';
import { 
  Compass, 
  CheckCircle2, 
  Loader2, 
  Sparkles, 
  Sliders, 
  UserCheck 
} from 'lucide-react';
import cameraService from '../../services/cameraService';
import faceDetectionService from '../../services/faceDetectionService';
import landmarkService from '../../services/landmarkService';
import distractionService from '../../services/distractionService';
import { distractionConfig } from '../../config/distractionConfig';

export default function Calibration({ onCalibrationComplete, onCancel }) {
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('Please look normally at the lecture screen...');
  const [samplesCollected, setSamplesCollected] = useState(0);
  const [baselineResults, setBaselineResults] = useState(null);

  const calibrationLoopRef = useRef(null);
  const collectedSamplesRef = useRef([]);

  useEffect(() => {
    let isMounted = true;
    const requiredSamples = distractionConfig.calibration.minSamplesRequired;
    const intervalMs = 100; // 10 samples/sec

    calibrationLoopRef.current = setInterval(async () => {
      if (!isMounted) return;

      const video = cameraService.videoElement;
      if (!video || video.readyState < 2) return;

      const frameQuality = cameraService.processCurrentFrame();
      const faceData = await faceDetectionService.detect(video, frameQuality);

      if (faceData && faceData.detected && !faceData.multipleFaces) {
        const features = landmarkService.extractFeatures(faceData, null);

        collectedSamplesRef.current.push({
          yaw: features.yaw,
          pitch: features.pitch,
          roll: features.roll,
          gaze: features.gazeDeviation,
          box: faceData.box
        });

        const count = collectedSamplesRef.current.length;
        setSamplesCollected(count);
        const percent = Math.min(100, Math.round((count / requiredSamples) * 100));
        setProgress(percent);

        if (count >= requiredSamples) {
          clearInterval(calibrationLoopRef.current);
          computePersonalBaseline(collectedSamplesRef.current);
        }
      } else {
        setStatusMessage('Please look directly towards the screen to calibrate baseline posture...');
      }
    }, intervalMs);

    return () => {
      isMounted = false;
      if (calibrationLoopRef.current) clearInterval(calibrationLoopRef.current);
    };
  }, []);

  const computePersonalBaseline = (samples) => {
    if (!samples || samples.length === 0) {
      // Fallback default baseline
      const defaultBaseline = {
        isCalibrated: true,
        normalYaw: 0,
        normalPitch: 0,
        normalRoll: 0,
        yawThreshold: distractionConfig.posture.defaultYawThresholdDeg,
        pitchThreshold: distractionConfig.posture.defaultPitchThresholdDeg,
        positionLabel: 'Center',
        naturalYawRange: 12,
        naturalPitchRange: 10
      };
      distractionService.setPersonalBaseline(defaultBaseline);
      setBaselineResults(defaultBaseline);
      return;
    }

    // Mean posture angles
    const avgYaw = samples.reduce((acc, s) => acc + s.yaw, 0) / samples.length;
    const avgPitch = samples.reduce((acc, s) => acc + s.pitch, 0) / samples.length;
    const avgRoll = samples.reduce((acc, s) => acc + s.roll, 0) / samples.length;

    // Variance/Natural movement range
    const yawDevs = samples.map(s => Math.abs(s.yaw - avgYaw));
    const pitchDevs = samples.map(s => Math.abs(s.pitch - avgPitch));
    const maxNaturalYawDev = Math.max(...yawDevs, 6.0);
    const maxNaturalPitchDev = Math.max(...pitchDevs, 5.0);

    // Personalized tolerances: student baseline + natural tolerance margin
    const computedBaseline = {
      isCalibrated: true,
      normalYaw: Math.round(avgYaw * 10) / 10,
      normalPitch: Math.round(avgPitch * 10) / 10,
      normalRoll: Math.round(avgRoll * 10) / 10,
      yawThreshold: Math.max(14.0, Math.min(26.0, Math.round((maxNaturalYawDev + 10.0) * 10) / 10)),
      pitchThreshold: Math.max(12.0, Math.min(22.0, Math.round((maxNaturalPitchDev + 8.0) * 10) / 10)),
      positionLabel: 'Center Aligned',
      naturalYawRange: Math.round(maxNaturalYawDev + 6.0),
      naturalPitchRange: Math.round(maxNaturalPitchDev + 5.0)
    };

    distractionService.setPersonalBaseline(computedBaseline);
    setBaselineResults(computedBaseline);
  };

  const handleFinish = () => {
    onCalibrationComplete(baselineResults);
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[#FFFFFF] border border-[#E5E5E5] p-6 rounded-2xl max-w-md w-full shadow-xl space-y-5">
        
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#E5E5E5] pb-3">
          <div className="flex items-center gap-2.5">
            <Compass className="w-5 h-5 text-[#FF0000]" />
            <h2 className="text-base font-bold text-[#0F0F0F]">Personal Calibration</h2>
          </div>
          <span className="text-[11px] font-semibold text-[#606060] bg-[#F2F2F2] px-2.5 py-1 rounded-full">
            Step 2 of 2
          </span>
        </div>

        {!baselineResults ? (
          <div className="space-y-4 py-2">
            <p className="text-xs text-[#0F0F0F] leading-relaxed">
              Calibrating your normal learning posture...
            </p>

            {/* Progress Bar */}
            <div className="space-y-1.5">
              <div className="w-full bg-[#F2F2F2] rounded-full h-3 overflow-hidden border border-[#E5E5E5]">
                <div 
                  className="bg-[#FF0000] h-full rounded-full transition-all duration-200"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <div className="flex items-center justify-between text-[11px] text-[#606060] font-mono">
                <span>Gathering natural posture baseline</span>
                <span className="font-bold text-[#0F0F0F]">{progress}%</span>
              </div>
            </div>

            <div className="p-3 rounded-xl bg-[#F9F9F9] border border-[#E5E5E5] text-xs text-[#606060] flex items-center gap-2.5">
              <Sparkles className="w-4 h-4 text-[#FF0000] shrink-0" />
              <span>{statusMessage}</span>
            </div>
          </div>
        ) : (
          <div className="space-y-4 py-1">
            <div className="flex items-center gap-2 text-xs font-semibold text-[#2E7D32]">
              <CheckCircle2 className="w-4 h-4 text-[#2E7D32]" />
              <span>Personal Baseline Established</span>
            </div>

            {/* Baseline Parameters Display */}
            <div className="p-4 rounded-xl bg-[#F9F9F9] border border-[#E5E5E5] space-y-2.5 text-xs">
              <p className="font-bold text-[#0F0F0F] text-xs uppercase tracking-wider">
                Personal Baseline
              </p>
              
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2 rounded-lg bg-[#FFFFFF] border border-[#E5E5E5]">
                  <span className="text-[#606060] block text-[11px]">Normal Head Yaw</span>
                  <strong className="text-[#0F0F0F] font-mono">±{baselineResults.naturalYawRange}°</strong>
                </div>
                <div className="p-2 rounded-lg bg-[#FFFFFF] border border-[#E5E5E5]">
                  <span className="text-[#606060] block text-[11px]">Normal Head Pitch</span>
                  <strong className="text-[#0F0F0F] font-mono">±{baselineResults.naturalPitchRange}°</strong>
                </div>
                <div className="p-2 rounded-lg bg-[#FFFFFF] border border-[#E5E5E5]">
                  <span className="text-[#606060] block text-[11px]">Normal Face Position</span>
                  <strong className="text-[#0F0F0F] font-mono">{baselineResults.positionLabel}</strong>
                </div>
                <div className="p-2 rounded-lg bg-[#FFFFFF] border border-[#E5E5E5]">
                  <span className="text-[#606060] block text-[11px]">Tolerance Limits</span>
                  <strong className="text-[#2E7D32] font-mono">Calibrated</strong>
                </div>
              </div>
            </div>

            <p className="text-[11px] text-[#606060] leading-relaxed">
              Deviations will be calculated relative to your personal posture baseline rather than fixed universal angles.
            </p>
          </div>
        )}

        {/* Action Button */}
        <div className="flex items-center justify-end gap-3 pt-2 border-t border-[#E5E5E5]">
          {baselineResults ? (
            <button
              type="button"
              onClick={handleFinish}
              className="w-full yt-btn-primary text-xs py-2.5 flex items-center justify-center gap-2"
            >
              <CheckCircle2 className="w-4 h-4" />
              <span>Start Monitored Lecture</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={onCancel}
              className="yt-btn-secondary text-xs py-2 px-4"
            >
              Cancel
            </button>
          )}
        </div>

      </div>
    </div>
  );
}
