import React, { useEffect, useRef, useState } from 'react';
import { 
  Camera, 
  CheckCircle2, 
  AlertTriangle, 
  XCircle, 
  Loader2, 
  Sun, 
  UserCheck, 
  ShieldCheck, 
  Sparkles,
  ArrowRight
} from 'lucide-react';
import cameraService from '../../services/cameraService';
import faceDetectionService from '../../services/faceDetectionService';
import landmarkService from '../../services/landmarkService';

export default function CameraSetup({ onSetupComplete, onCancel }) {
  const videoPreviewRef = useRef(null);
  const canvasOverlayRef = useRef(null);
  const setupLoopRef = useRef(null);

  const [setupState, setSetupState] = useState({
    cameraPermission: false,
    faceDetected: false,
    lightingAdequate: false,
    facePositioned: false,
    monitoringReady: false
  });

  const [diagnostics, setDiagnostics] = useState({
    lightingScore: 0,
    faceConfidence: 0,
    actionableFeedback: 'Initializing camera and sensors...',
    isChecking: true,
    error: null
  });

  const [readyCountdown, setReadyCountdown] = useState(null);

  useEffect(() => {
    let isMounted = true;

    async function initCameraCheck() {
      try {
        setDiagnostics(d => ({ ...d, actionableFeedback: 'Requesting local camera access...' }));
        const camRes = await cameraService.requestCamera(320, 240);

        if (!isMounted) return;

        if (videoPreviewRef.current && camRes.stream) {
          videoPreviewRef.current.srcObject = camRes.stream;
          await videoPreviewRef.current.play();
        }

        await faceDetectionService.init();

        setSetupState(s => ({ ...s, cameraPermission: true }));

        // Start 8 FPS Verification Loop
        setupLoopRef.current = setInterval(() => {
          if (!isMounted) return;
          runQualityCheck();
        }, 125);

      } catch (err) {
        if (!isMounted) return;
        setDiagnostics(d => ({
          ...d,
          isChecking: false,
          error: err.message || 'Camera permission denied or camera device unavailable.'
        }));
      }
    }

    initCameraCheck();

    return () => {
      isMounted = false;
      if (setupLoopRef.current) {
        clearInterval(setupLoopRef.current);
      }
    };
  }, []);

  const runQualityCheck = async () => {
    if (!videoPreviewRef.current || videoPreviewRef.current.readyState < 2) return;

    // 1. Process Lighting Quality
    const frameQuality = cameraService.processCurrentFrame();
    const lightingScore = frameQuality ? frameQuality.lightingScore : 80;
    const isLightingAdequate = frameQuality ? frameQuality.isLightingAdequate : true;

    // 2. Process Face Detection & Centering
    const faceData = await faceDetectionService.detect(videoPreviewRef.current, frameQuality);
    const landmarks = landmarkService.extractFeatures(faceData, null);

    const faceDetected = Boolean(faceData && faceData.detected && !faceData.multipleFaces);
    const facePositioned = Boolean(faceData && faceData.isCentered && faceData.isAdequateSize);
    const cameraPermission = true;

    // Build Actionable Feedback
    let feedback = 'Camera and face position optimal.';
    if (faceData && faceData.multipleFaces) {
      feedback = 'Multiple faces detected. Please ensure only you are visible in frame.';
    } else if (!faceDetected) {
      feedback = 'Please position yourself in front of the camera.';
    } else if (frameQuality && frameQuality.lightingIssue === 'LOW_ILLUMINATION') {
      feedback = 'Lighting is too low. Please move to a brighter area.';
    } else if (frameQuality && frameQuality.lightingIssue === 'EXCESSIVE_BACKLIGHTING') {
      feedback = 'Avoid strong light directly behind you.';
    } else if (!facePositioned) {
      feedback = faceData.feedback || 'Please center your face within the camera frame.';
    }

    const allReady = cameraPermission && faceDetected && isLightingAdequate && facePositioned;

    setSetupState({
      cameraPermission,
      faceDetected,
      lightingAdequate: isLightingAdequate,
      facePositioned,
      monitoringReady: allReady
    });

    setDiagnostics({
      lightingScore,
      faceConfidence: faceData?.confidence ? Math.round(faceData.confidence * 100) : 0,
      actionableFeedback: feedback,
      isChecking: false,
      error: null
    });

    // Draw video overlay
    drawOverlay(faceData, allReady);
  };

  const drawOverlay = (faceData, isReady) => {
    const canvas = canvasOverlayRef.current;
    if (!canvas || !videoPreviewRef.current) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width;
    const h = canvas.height;

    ctx.clearRect(0, 0, w, h);

    // Subtle alignment guide ellipse in center
    ctx.strokeStyle = isReady ? 'rgba(46, 125, 50, 0.7)' : 'rgba(15, 15, 15, 0.25)';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.ellipse(w / 2, h / 2, w * 0.28, h * 0.38, 0, 0, 2 * Math.PI);
    ctx.stroke();
    ctx.setLineDash([]);

    if (faceData && faceData.detected && faceData.box) {
      const scaleX = w / (videoPreviewRef.current.videoWidth || 320);
      const scaleY = h / (videoPreviewRef.current.videoHeight || 240);
      const bx = faceData.box.x * scaleX;
      const by = faceData.box.y * scaleY;
      const bw = faceData.box.width * scaleX;
      const bh = faceData.box.height * scaleY;

      ctx.strokeStyle = isReady ? '#2E7D32' : '#F57F17';
      ctx.lineWidth = 2;
      ctx.strokeRect(bx, by, bw, bh);

      // Landmarks dots if available
      if (faceData.rawLandmarks) {
        ctx.fillStyle = '#0284C7';
        faceData.rawLandmarks.forEach(pt => {
          ctx.beginPath();
          ctx.arc(pt[0] * scaleX, pt[1] * scaleY, 2.5, 0, 2 * Math.PI);
          ctx.fill();
        });
      }
    }
  };

  const handleProceed = () => {
    if (setupLoopRef.current) clearInterval(setupLoopRef.current);
    onSetupComplete();
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[#FFFFFF] border border-[#E5E5E5] p-6 rounded-2xl max-w-xl w-full shadow-xl space-y-5">
        
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#E5E5E5] pb-3">
          <div className="flex items-center gap-2.5">
            <Camera className="w-5 h-5 text-[#FF0000]" />
            <h2 className="text-base font-bold text-[#0F0F0F]">Camera Setup & Quality Check</h2>
          </div>
          <span className="text-[11px] font-semibold text-[#606060] bg-[#F2F2F2] px-2.5 py-1 rounded-full">
            Step 1 of 2
          </span>
        </div>

        {diagnostics.error ? (
          <div className="p-4 rounded-xl bg-[#FFEBEE] border border-[#FFCDD2] space-y-3">
            <div className="flex items-start gap-2.5 text-xs text-[#C62828]">
              <XCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <div>
                <strong className="block font-bold">Camera Unavailable</strong>
                <span>{diagnostics.error}</span>
              </div>
            </div>
            <p className="text-xs text-[#606060]">
              Focus monitoring is optional. You can still watch the full lecture without camera monitoring.
            </p>
            <div className="flex justify-end gap-2 pt-1">
              <button
                type="button"
                onClick={onCancel}
                className="yt-btn-secondary text-xs py-1.5 px-4"
              >
                Continue Without Camera
              </button>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            
            {/* Live Camera View with Visual Guide Overlay */}
            <div className="relative aspect-[4/3] bg-[#0F0F0F] rounded-xl overflow-hidden border border-[#E5E5E5] flex items-center justify-center">
              <video
                ref={videoPreviewRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-cover scale-x-[-1]"
              />
              <canvas
                ref={canvasOverlayRef}
                width={320}
                height={240}
                className="absolute inset-0 w-full h-full pointer-events-none scale-x-[-1]"
              />
              <div className="absolute bottom-2 left-2 right-2 bg-black/70 backdrop-blur-sm text-white px-2.5 py-1 rounded-lg text-[10px] flex items-center justify-between">
                <span>Lighting Score: <strong>{diagnostics.lightingScore}%</strong></span>
                <span className="text-emerald-400 font-mono">100% Local</span>
              </div>
            </div>

            {/* Checklist & Diagnostic Feedback */}
            <div className="space-y-3.5 flex flex-col justify-between">
              <div className="space-y-2">
                <p className="text-[11px] uppercase tracking-wider text-[#606060] font-bold">Setup Checklist</p>
                
                <div className="space-y-2 text-xs">
                  <div className="flex items-center justify-between p-2 rounded-lg bg-[#F9F9F9] border border-[#E5E5E5]">
                    <span className="text-[#0F0F0F]">Camera Permission</span>
                    {setupState.cameraPermission ? (
                      <span className="text-[#2E7D32] font-semibold flex items-center gap-1">✓ Connected</span>
                    ) : (
                      <Loader2 className="w-3.5 h-3.5 text-[#606060] animate-spin" />
                    )}
                  </div>

                  <div className="flex items-center justify-between p-2 rounded-lg bg-[#F9F9F9] border border-[#E5E5E5]">
                    <span className="text-[#0F0F0F]">Face Detection</span>
                    {setupState.faceDetected ? (
                      <span className="text-[#2E7D32] font-semibold flex items-center gap-1">✓ Detected</span>
                    ) : (
                      <span className="text-[#F57F17] font-semibold">Searching...</span>
                    )}
                  </div>

                  <div className="flex items-center justify-between p-2 rounded-lg bg-[#F9F9F9] border border-[#E5E5E5]">
                    <span className="text-[#0F0F0F]">Lighting Quality</span>
                    {setupState.lightingAdequate ? (
                      <span className="text-[#2E7D32] font-semibold flex items-center gap-1">✓ Adequate ({diagnostics.lightingScore}%)</span>
                    ) : (
                      <span className="text-[#C62828] font-semibold">Adjust Lighting</span>
                    )}
                  </div>

                  <div className="flex items-center justify-between p-2 rounded-lg bg-[#F9F9F9] border border-[#E5E5E5]">
                    <span className="text-[#0F0F0F]">Face Position</span>
                    {setupState.facePositioned ? (
                      <span className="text-[#2E7D32] font-semibold flex items-center gap-1">✓ Centered</span>
                    ) : (
                      <span className="text-[#F57F17] font-semibold">Align to Guide</span>
                    )}
                  </div>

                  <div className="flex items-center justify-between p-2 rounded-lg bg-[#F9F9F9] border border-[#E5E5E5]">
                    <span className="font-semibold text-[#0F0F0F]">Monitoring Ready</span>
                    {setupState.monitoringReady ? (
                      <span className="text-[#2E7D32] font-bold flex items-center gap-1">✓ Ready</span>
                    ) : (
                      <span className="text-[#606060]">Waiting for alignment</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Actionable Feedback Prompt */}
              <div className={`p-2.5 rounded-xl border text-xs leading-relaxed ${
                setupState.monitoringReady
                  ? 'bg-[#E8F5E9] border-[#C8E6C9] text-[#2E7D32]'
                  : 'bg-[#FFF8E1] border-[#FFE082] text-[#F57F17]'
              }`}>
                <strong>Status: </strong>
                <span>{diagnostics.actionableFeedback}</span>
              </div>
            </div>

          </div>
        )}

        {/* Footer Actions */}
        <div className="flex items-center justify-between pt-2 border-t border-[#E5E5E5]">
          <button
            type="button"
            onClick={onCancel}
            className="yt-btn-secondary text-xs py-2 px-4"
          >
            Cancel
          </button>

          <button
            type="button"
            onClick={handleProceed}
            disabled={!setupState.monitoringReady && !diagnostics.error}
            className="yt-btn-primary text-xs py-2 px-5 flex items-center gap-2 disabled:opacity-40"
          >
            <span>Proceed to Calibration</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

      </div>
    </div>
  );
}
