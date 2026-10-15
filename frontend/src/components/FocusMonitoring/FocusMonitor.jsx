import React, { useState, useEffect, useRef } from 'react';
import { 
  ShieldCheck, 
  Camera, 
  Settings, 
  Sliders, 
  Lock, 
  Terminal, 
  Sparkles,
  Info
} from 'lucide-react';

import ConsentModal from './ConsentModal';
import CameraSetup from './CameraSetup';
import Calibration from './Calibration';
import LiveMonitoringPanel from './LiveMonitoringPanel';
import FocusNotification from './FocusNotification';
import DeveloperDebugPanel from './DeveloperDebugPanel';
import DemoModeController from './DemoModeController';

import cameraService from '../../services/cameraService';
import faceDetectionService from '../../services/faceDetectionService';
import landmarkService from '../../services/landmarkService';
import distractionService from '../../services/distractionService';
import telemetryService from '../../services/telemetryService';
import { distractionConfig } from '../../config/distractionConfig';

export default function FocusMonitor({
  courseId,
  getVideoTimestamp,
  getCurrentTimeSec,
  getPlayerState,
  onSeekTo,
  isLectureEnded = false
}) {
  // Wizard Stages: 'IDLE' -> 'CONSENT' -> 'SETUP' -> 'CALIBRATING' -> 'ACTIVE'
  const [wizardStage, setWizardStage] = useState('IDLE');
  const [isMonitoringActive, setIsMonitoringActive] = useState(false);
  const [isPaused, setIsPaused] = useState(false);

  // Live Metrics State
  const [attentionState, setAttentionState] = useState(distractionConfig.states.FOCUSED);
  const [focusLevel, setFocusLevel] = useState(100);
  const [distractionScore, setDistractionScore] = useState(0);
  const [eventsCount, setEventsCount] = useState(0);
  const [currentNotification, setCurrentNotification] = useState(null);

  // Diagnostics & Modals State
  const [frameQuality, setFrameQuality] = useState(null);
  const [currentFaceData, setCurrentFaceData] = useState(null);
  const [currentLandmarks, setCurrentLandmarks] = useState(null);
  const [personalBaseline, setPersonalBaseline] = useState(null);

  const [showConsentModal, setShowConsentModal] = useState(false);
  const [showSetupModal, setShowSetupModal] = useState(false);
  const [showCalibrationModal, setShowCalibrationModal] = useState(false);
  const [showPrivacyModal, setShowPrivacyModal] = useState(false);
  const [showDevPanel, setShowDevPanel] = useState(false);
  const [showDemoMode, setShowDemoMode] = useState(false);

  // Refs for processing loop
  const processingLoopRef = useRef(null);
  const lastTelemetrySyncRef = useRef(0);
  const isEvaluatingRef = useRef(false);

  // Initial load check
  useEffect(() => {
    const savedConsent = sessionStorage.getItem('cognitrace_focus_consent');
    if (savedConsent === 'ENABLED') {
      startMonitoringFlow();
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopMonitoring();
    };
  }, []);

  const handleOpenEnableModal = () => {
    setShowConsentModal(true);
  };

  const handleConsentGranted = () => {
    sessionStorage.setItem('cognitrace_focus_consent', 'ENABLED');
    setShowConsentModal(false);
    setShowSetupModal(true);
    setWizardStage('SETUP');
  };

  const handleConsentDismissed = () => {
    setShowConsentModal(false);
  };

  const handleSetupComplete = () => {
    setShowSetupModal(false);
    setShowCalibrationModal(true);
    setWizardStage('CALIBRATING');
  };

  const handleSetupCancel = () => {
    setShowSetupModal(false);
    cameraService.stopCamera();
    setWizardStage('IDLE');
  };

  const handleCalibrationComplete = (baseline) => {
    setPersonalBaseline(baseline);
    setShowCalibrationModal(false);
    setWizardStage('ACTIVE');
    setIsMonitoringActive(true);
    setIsPaused(false);

    // Start Real-Time 8 FPS Inference Loop
    startInferenceLoop();
  };

  const handleCalibrationCancel = () => {
    setShowCalibrationModal(false);
    cameraService.stopCamera();
    setWizardStage('IDLE');
  };

  const startMonitoringFlow = async () => {
    setShowSetupModal(true);
    setWizardStage('SETUP');
  };

  const startInferenceLoop = () => {
    if (processingLoopRef.current) clearInterval(processingLoopRef.current);

    processingLoopRef.current = setInterval(async () => {
      if (isPaused || isEvaluatingRef.current) return;
      isEvaluatingRef.current = true;
      try {
        await processSingleFrame();
      } catch (err) {
        console.warn('[CogniTrace FocusMonitor] Frame processing error:', err);
      } finally {
        isEvaluatingRef.current = false;
      }
    }, distractionConfig.temporal.sampleIntervalMs);
  };

  const stopMonitoring = () => {
    if (processingLoopRef.current) {
      clearInterval(processingLoopRef.current);
      processingLoopRef.current = null;
    }
    cameraService.stopCamera();
    setIsMonitoringActive(false);
  };

  const togglePauseMonitoring = () => {
    if (!isMonitoringActive) {
      handleOpenEnableModal();
      return;
    }
    setIsPaused(prev => !prev);
  };

  const processSingleFrame = async () => {
    const video = cameraService.videoElement;
    if (!video || video.readyState < 2) return;

    // 1. Lighting Quality Preprocessing Pipeline (Requirement 3)
    const quality = cameraService.processCurrentFrame();
    setFrameQuality(quality);

    // 2. Face Detection with Multi-Face & Occlusion Guards (Requirements 4, 12, 23)
    const faceData = await faceDetectionService.detect(video, quality);
    setCurrentFaceData(faceData);

    // 3. Facial Landmark & 3D Pose Extraction (Requirement 4)
    const landmarks = landmarkService.extractFeatures(faceData, personalBaseline);
    setCurrentLandmarks(landmarks);

    // 4. Multi-Signal Distraction Evaluation (Requirements 6, 8, 9, 10, 11)
    const vTimestamp = getVideoTimestamp ? getVideoTimestamp() : '00:00';
    const cTimeSec = getCurrentTimeSec ? getCurrentTimeSec() : 0;
    const pState = getPlayerState ? getPlayerState() : 1;

    const evalResult = distractionService.evaluate({
      faceData,
      landmarks,
      frameQuality: quality,
      videoTimestamp: vTimestamp,
      currentTimeSec: cTimeSec,
      playerState: pState
    });

    setAttentionState(evalResult.state);
    setDistractionScore(evalResult.distractionScore);
    setFocusLevel(evalResult.focusLevel);
    setEventsCount(evalResult.eventsCount || 0);

    if (evalResult.notification) {
      setCurrentNotification(evalResult.notification);
    }

    // 5. Throttled Privacy-Preserving Derived Telemetry Sync (Requirement 13)
    const now = Date.now();
    if (now - lastTelemetrySyncRef.current >= distractionConfig.temporal.telemetrySyncIntervalMs) {
      lastTelemetrySyncRef.current = now;
      telemetryService.queueAttentionEvent(courseId, vTimestamp, {
        attention_state: evalResult.state,
        distraction_score: evalResult.distractionScore,
        distraction_duration: evalResult.distractionDuration,
        event_type: evalResult.state === 'FOCUSED' ? 'FOCUSED_HEARTBEAT' : 'LOOKING_AWAY',
        confidence: faceData?.confidence || 0.92,
        head_pose: {
          yaw: landmarks.yaw,
          pitch: landmarks.pitch,
          roll: landmarks.roll
        },
        noise_level: 'DISABLED',
        environmental_distraction: false,
        behavioral_distraction: evalResult.state !== 'FOCUSED',
        notification_triggered: Boolean(evalResult.notification)
      });
    }
  };

  const handleApplyDemoState = (demoState) => {
    setAttentionState(demoState.state);
    setDistractionScore(demoState.score);
    setFocusLevel(demoState.focusLevel);
    setCurrentLandmarks({
      yaw: demoState.yaw,
      pitch: demoState.pitch,
      roll: 0,
      gazeDeviation: demoState.gaze,
      faceVisibility: 95
    });
    if (demoState.notification) {
      setCurrentNotification(demoState.notification);
    }
  };

  return (
    <div className="space-y-4">
      
      {/* If Not Yet Enabled -> Banner with Opt-In Button (Requirement 1) */}
      {!isMonitoringActive && (
        <div className="p-4 rounded-2xl bg-[#F9F9F9] border border-[#E5E5E5] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-[#FFEBEE] flex items-center justify-center text-[#FF0000] shrink-0">
              <Camera className="w-4 h-4" />
            </div>
            <div>
              <h4 className="font-bold text-[#0F0F0F] text-xs">Intelligent Focus Assistance</h4>
              <p className="text-[11px] text-[#606060]">
                Analyze posture & attention locally in your browser • Zero raw video is ever uploaded.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-start sm:self-auto">
            <button
              type="button"
              onClick={handleOpenEnableModal}
              className="yt-btn-primary text-xs py-2 px-4 shadow-sm"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>Enable Focus Monitoring</span>
            </button>
            <button
              type="button"
              onClick={() => setShowDemoMode(true)}
              className="yt-btn-secondary text-[11px] py-1.5 px-3"
              title="Demo Mode for project presentations"
            >
              <Sparkles className="w-3 h-3 text-[#FF0000]" />
              <span>Demo Mode</span>
            </button>
          </div>
        </div>
      )}

      {/* Active Live Monitoring Panel (Requirement 17) */}
      {isMonitoringActive && (
        <div className="space-y-2">
          <LiveMonitoringPanel
            isMonitoring={isMonitoringActive}
            isPaused={isPaused}
            onTogglePause={togglePauseMonitoring}
            attentionState={attentionState}
            focusLevel={focusLevel}
            distractionScore={distractionScore}
            eventsCount={eventsCount}
            frameQuality={frameQuality}
            faceData={currentFaceData}
            videoElementRef={{ current: cameraService.videoElement }}
            onOpenPrivacy={() => setShowPrivacyModal(true)}
            onOpenCalibration={() => setShowCalibrationModal(true)}
            onToggleDevPanel={() => setShowDevPanel(!showDevPanel)}
          />

          {/* Quick Dev/Demo controls in footer */}
          <div className="flex items-center justify-end gap-3 px-1 text-[11px] text-[#606060]">
            <button
              type="button"
              onClick={() => setShowDevPanel(!showDevPanel)}
              className="hover:text-[#0F0F0F] flex items-center gap-1 transition-colors"
            >
              <Terminal className="w-3 h-3 text-[#00E676]" />
              <span>{showDevPanel ? 'Hide Dev Metrics' : 'Dev Diagnostics'}</span>
            </button>
            <button
              type="button"
              onClick={() => setShowDemoMode(!showDemoMode)}
              className="hover:text-[#FF0000] flex items-center gap-1 transition-colors"
            >
              <Sparkles className="w-3 h-3 text-[#FF0000]" />
              <span>Demo Simulation</span>
            </button>
          </div>
        </div>
      )}

      {/* Opt-in Consent Modal (Requirement 1) */}
      {showConsentModal && (
        <ConsentModal 
          onEnable={handleConsentGranted} 
          onDismiss={handleConsentDismissed} 
        />
      )}

      {/* Camera Setup & Quality Check Modal (Requirement 2) */}
      {showSetupModal && (
        <CameraSetup 
          onSetupComplete={handleSetupComplete} 
          onCancel={handleSetupCancel} 
        />
      )}

      {/* Personal Baseline Calibration Modal (Requirement 5) */}
      {showCalibrationModal && (
        <Calibration 
          onCalibrationComplete={handleCalibrationComplete} 
          onCancel={handleCalibrationCancel} 
        />
      )}

      {/* Explainable Gentle Notifications Toast (Requirements 14, 15) */}
      {currentNotification && (
        <FocusNotification 
          notification={currentNotification} 
          onDismiss={() => setCurrentNotification(null)} 
        />
      )}

      {/* Developer Debug Panel (Requirement 29) */}
      {showDevPanel && (
        <DeveloperDebugPanel
          faceData={currentFaceData}
          landmarks={currentLandmarks}
          frameQuality={frameQuality}
          distractionData={{ state: attentionState, distractionScore }}
          personalBaseline={personalBaseline}
          fps={distractionConfig.temporal.frameRateFps}
          onClose={() => setShowDevPanel(false)}
        />
      )}

      {/* Safe Demo Simulation Mode (Requirement 30) */}
      {showDemoMode && (
        <DemoModeController 
          onApplyDemoState={handleApplyDemoState}
          onClose={() => setShowDemoMode(false)}
        />
      )}

      {/* Privacy Guarantee Modal */}
      {showPrivacyModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#FFFFFF] border border-[#E5E5E5] p-6 rounded-2xl max-w-md w-full shadow-xl space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-full bg-[#E8F5E9] flex items-center justify-center text-[#2E7D32]">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <h3 className="text-base font-bold text-[#0F0F0F]">Privacy-Preserving Architecture</h3>
            </div>
            
            <p className="text-xs text-[#606060] leading-relaxed">
              🔒 <strong>Camera processing is 100% local. No video or images are recorded or uploaded.</strong>
            </p>

            <p className="text-xs text-[#606060] leading-relaxed">
              All facial detection and angle estimations execute strictly inside your web browser's memory using lightweight client-side models. CogniTrace sends only aggregated numeric telemetry scores to assist your learning feedback.
            </p>

            <button
              type="button"
              onClick={() => setShowPrivacyModal(false)}
              className="w-full yt-btn-primary py-2 text-xs font-semibold"
            >
              Understood
            </button>
          </div>
        </div>
      )}

    </div>
  );
}
