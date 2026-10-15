/**
 * CogniTrace Privacy-Preserving Attention Engine
 * 
 * In-browser deep learning face & landmark detection (BlazeFace).
 * PRIVACY GUARANTEES:
 * 1. Zero camera frames are recorded, saved, or transmitted to any server.
 * 2. Zero microphone audio is recorded, saved, or transmitted to any server.
 * 3. Frames are processed locally in volatile browser memory and immediately discarded.
 * 4. Only derived numeric metrics (pose angles, noise RMS, attention state, score) are produced.
 * 5. No facial identification/recognition is performed.
 */

class CogniTraceAttentionEngine {
  constructor(options = {}) {
    this.options = Object.assign({
      sampleRateFps: 10,
      yawThresholdDeg: 20.0,
      pitchThresholdDeg: 15.0,
      rollThresholdDeg: 22.0,
      briefMovementGraceSec: 2.0,
      possibleDistractionSec: 4.0,
      highDistractionSec: 8.0,
      notificationCooldownSec: 35.0,
      noiseRmsThreshold: 0.07,
      onStateChange: null,
      onTelemetryEvent: null,
      onNotification: null,
      onFrameMetrics: null
    }, options);

    // State machine
    this.state = 'FACE_NOT_DETECTED'; // FOCUSED, POSSIBLE_DISTRACTION, SUSTAINED_DISTRACTION, HIGH_DISTRACTION, FACE_NOT_DETECTED, RECOVERED, MONITORING_PAUSED
    this.isActive = false;
    this.isPaused = false;
    this.cameraEnabled = true;
    this.micEnabled = false;

    // Temporal tracking
    this.distractionStartTime = null;
    this.distractionDuration = 0;
    this.lastNotificationTime = 0;
    this.lastStateTransitionTime = Date.now();

    // Smoothed metrics (Exponential Moving Average)
    this.smoothedYaw = 0;
    this.smoothedPitch = 0;
    this.smoothedRoll = 0;
    this.smoothedScore = 0;

    // Media streams
    this.videoStream = null;
    this.videoElement = null;
    this.audioStream = null;
    this.audioContext = null;
    this.analyser = null;
    this.audioDataArray = null;

    // Preview Canvas for Live Picture-in-Picture in Corner
    this.previewCanvas = null;
    this.previewCtx = null;

    // Processing timer
    this.timerId = null;

    // Deep Learning Face Model
    this.model = null;
    this.initModel();
  }

  async initModel() {
    if (window.blazeface) {
      try {
        this.model = await window.blazeface.load();
      } catch (e) {
        console.warn('BlazeFace model loading issue:', e);
      }
    }
  }

  attachPreviewCanvas(canvas) {
    this.previewCanvas = canvas;
    if (canvas) {
      this.previewCtx = canvas.getContext('2d');
    }
  }

  async start(camera = true, microphone = false) {
    this.cameraEnabled = camera;
    this.micEnabled = microphone;
    this.isActive = true;
    this.isPaused = false;
    this.state = 'FACE_NOT_DETECTED';

    if (!this.model && window.blazeface) {
      try {
        this.model = await window.blazeface.load();
      } catch (e) {
        console.warn('BlazeFace load error:', e);
      }
    }

    try {
      if (this.cameraEnabled) {
        await this.initCamera();
      }
      if (this.micEnabled) {
        await this.initMicrophone();
      }

      this.startProcessingLoop();
      this.notifyStateChange('FACE_NOT_DETECTED', 'Attention monitoring active.');
      return { success: true };
    } catch (err) {
      console.warn('[CogniTrace Attention] Media initialization issue:', err);
      return { success: false, error: err.message };
    }
  }

  async initCamera() {
    try {
      this.videoStream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 320 },
          height: { ideal: 240 },
          frameRate: { ideal: this.options.sampleRateFps, max: 15 },
          facingMode: 'user'
        },
        audio: false
      });

      this.videoElement = document.createElement('video');
      this.videoElement.srcObject = this.videoStream;
      this.videoElement.setAttribute('playsinline', 'true');
      this.videoElement.muted = true;
      await this.videoElement.play();
    } catch (e) {
      this.cameraEnabled = false;
      throw new Error('Camera access unavailable or denied: ' + e.message);
    }
  }

  async initMicrophone() {
    try {
      this.audioStream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: false },
        video: false
      });

      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      this.audioContext = new AudioCtx();
      const source = this.audioContext.createMediaStreamSource(this.audioStream);
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 256;
      this.analyser.smoothingTimeConstant = 0.8;
      source.connect(this.analyser);
      this.audioDataArray = new Uint8Array(this.analyser.frequencyBinCount);
    } catch (e) {
      this.micEnabled = false;
    }
  }

  startProcessingLoop() {
    if (this.timerId) clearInterval(this.timerId);
    const intervalMs = Math.round(1000 / this.options.sampleRateFps);

    this.timerId = setInterval(() => {
      if (!this.isActive || this.isPaused) return;
      this.processSample();
    }, intervalMs);
  }

  pause() {
    this.isPaused = true;
    this.notifyStateChange('MONITORING_PAUSED', 'Attention monitoring is paused.');
  }

  resume() {
    this.isPaused = false;
    this.distractionStartTime = null;
    this.notifyStateChange('FACE_NOT_DETECTED', 'Attention monitoring resumed.');
  }

  stop() {
    this.isActive = false;
    if (this.timerId) {
      clearInterval(this.timerId);
      this.timerId = null;
    }
    if (this.videoStream) {
      this.videoStream.getTracks().forEach(t => t.stop());
      this.videoStream = null;
    }
    if (this.audioStream) {
      this.audioStream.getTracks().forEach(t => t.stop());
      this.audioStream = null;
    }
    if (this.audioContext && this.audioContext.state !== 'closed') {
      this.audioContext.close();
      this.audioContext = null;
    }
    this.state = 'MONITORING_PAUSED';
  }

  async processSample() {
    const now = Date.now();
    let faceData = null;
    let noiseLevel = 'DISABLED';
    let noiseRms = 0;

    // 1. Audio Processing
    if (this.micEnabled && this.analyser) {
      noiseRms = this.computeAudioRms();
      if (noiseRms > this.options.noiseRmsThreshold * 1.6) {
        noiseLevel = 'NOISY';
      } else if (noiseRms > this.options.noiseRmsThreshold * 0.8) {
        noiseLevel = 'MODERATE';
      } else {
        noiseLevel = 'QUIET';
      }
    }

    // 2. Video Processing with BlazeFace Model
    if (this.cameraEnabled && this.videoElement && this.videoElement.readyState >= 2) {
      faceData = await this.analyzeVideoFrame();
    }

    // 3. State Machine Transition
    this.evaluateStateAndScore(faceData, noiseLevel, noiseRms, now);

    // 4. Render Corner Picture-in-Picture Preview if attached
    if (this.previewCanvas && this.previewCtx && this.videoElement && this.videoElement.readyState >= 2) {
      this.renderPreviewOverlay(faceData);
    }
  }

  computeAudioRms() {
    if (!this.analyser || !this.audioDataArray) return 0;
    this.analyser.getByteTimeDomainData(this.audioDataArray);
    let sum = 0;
    for (let i = 0; i < this.audioDataArray.length; i++) {
      const normalized = (this.audioDataArray[i] - 128) / 128;
      sum += normalized * normalized;
    }
    return Math.sqrt(sum / this.audioDataArray.length);
  }

  async analyzeVideoFrame() {
    if (this.model) {
      try {
        const predictions = await this.model.estimateFaces(this.videoElement, false);
        if (predictions && predictions.length > 0) {
          const pred = predictions[0];
          const start = pred.topLeft;
          const end = pred.bottomRight;
          const size = [end[0] - start[0], end[1] - start[1]];
          const landmarks = pred.landmarks;

          if (landmarks && landmarks.length >= 4) {
            const rightEye = landmarks[0];
            const leftEye = landmarks[1];
            const nose = landmarks[2];
            const mouth = landmarks[3];

            // Yaw: Nose horizontal offset relative to eye midpoint
            const eyeMidX = (rightEye[0] + leftEye[0]) / 2;
            const eyeSpanX = Math.abs(leftEye[0] - rightEye[0]) || 1;
            const noseDistX = nose[0] - eyeMidX;
            const calculatedYaw = (noseDistX / (eyeSpanX / 2)) * 48;

            // Pitch: Nose vertical position relative to eye-mouth axis
            const eyeMidY = (rightEye[1] + leftEye[1]) / 2;
            const eyeToMouthDist = Math.abs(mouth[1] - eyeMidY) || 1;
            const noseDistY = nose[1] - eyeMidY;
            const pitchRatio = noseDistY / eyeToMouthDist;
            const calculatedPitch = (pitchRatio - 0.45) * 55;

            return {
              detected: true,
              box: { x: start[0], y: start[1], width: size[0], height: size[1] },
              landmarks: landmarks,
              yaw: calculatedYaw,
              pitch: calculatedPitch,
              confidence: 0.95
            };
          }
        }
      } catch (err) {
        console.warn('Face inference error:', err);
      }
    }

    return { detected: false };
  }

  evaluateStateAndScore(faceData, noiseLevel, noiseRms, now) {
    let distractionScore = 0;
    let eventType = 'FOCUSED_HEARTBEAT';
    let behavioralDistraction = false;
    let environmentalDistraction = (noiseLevel === 'NOISY');

    // IF NO HUMAN FACE DETECTED (Wall, Cabinet, Covered Camera, Blank Screen)
    if (!faceData || !faceData.detected) {
      this.state = 'FACE_NOT_DETECTED';
      this.distractionScore = 0;
      this.smoothedScore = 0;
      this.distractionStartTime = null;
      this.distractionDuration = 0;

      this.notifyStateChange('FACE_NOT_DETECTED', 'Face not detected temporarily.');

      if (this.options.onFrameMetrics) {
        this.options.onFrameMetrics({
          state: 'FACE_NOT_DETECTED',
          score: 0,
          duration: 0,
          yaw: 0,
          pitch: 0,
          roll: 0,
          noiseLevel: noiseLevel,
          noiseRms: Math.round(noiseRms * 1000) / 1000,
          eventType: 'FACE_NOT_DETECTED'
        });
      }
      return;
    }

    // HUMAN FACE IS DETECTED
    const alpha = 0.4;
    this.smoothedYaw = alpha * faceData.yaw + (1 - alpha) * this.smoothedYaw;
    this.smoothedPitch = alpha * faceData.pitch + (1 - alpha) * this.smoothedPitch;
    this.smoothedRoll = 0;

    const absYaw = Math.abs(this.smoothedYaw);
    const absPitch = Math.abs(this.smoothedPitch);

    let poseScore = 0;
    let isLookingAway = false;

    if (absYaw > this.options.yawThresholdDeg) {
      poseScore += Math.min(55, (absYaw - this.options.yawThresholdDeg) * 3.0);
      isLookingAway = true;
      eventType = 'LOOKING_AWAY';
      behavioralDistraction = true;
    }
    if (absPitch > this.options.pitchThresholdDeg) {
      poseScore += Math.min(45, (absPitch - this.options.pitchThresholdDeg) * 2.8);
      isLookingAway = true;
      eventType = 'LOOKING_AWAY';
      behavioralDistraction = true;
    }

    let noiseScore = 0;
    if (noiseLevel === 'NOISY') {
      noiseScore = 25;
      if (!behavioralDistraction) eventType = 'HIGH_NOISE';
    }

    distractionScore = Math.min(100, Math.round(poseScore + noiseScore));
    this.smoothedScore = Math.round(0.5 * distractionScore + 0.5 * this.smoothedScore);

    // State Machine
    if (isLookingAway) {
      if (!this.distractionStartTime) {
        this.distractionStartTime = now;
      }
      this.distractionDuration = (now - this.distractionStartTime) / 1000;

      if (this.distractionDuration < this.options.briefMovementGraceSec) {
        this.state = 'FOCUSED';
      } else if (this.distractionDuration < this.options.possibleDistractionSec) {
        this.state = 'POSSIBLE_DISTRACTION';
      } else if (this.distractionDuration < this.options.highDistractionSec) {
        this.state = 'SUSTAINED_DISTRACTION';
      } else {
        this.state = 'HIGH_DISTRACTION';
        this.checkAndTriggerNotification('HIGH_DISTRACTION', now);
      }
    } else {
      if (this.state === 'HIGH_DISTRACTION' || this.state === 'SUSTAINED_DISTRACTION') {
        this.state = 'RECOVERED';
        eventType = 'RECOVERED_ATTENTION';
        this.notifyStateChange('RECOVERED', "Nice — you're back on track.");
        if (this.options.onNotification) {
          this.options.onNotification({
            type: 'RECOVERY',
            message: "Nice — you're back on track.",
            cooldown: 0
          });
        }
      } else {
        this.state = 'FOCUSED';
      }
      this.distractionStartTime = null;
      this.distractionDuration = 0;
    }

    // Frame metrics callback
    if (this.options.onFrameMetrics) {
      this.options.onFrameMetrics({
        state: this.state,
        score: this.smoothedScore,
        duration: Math.round(this.distractionDuration * 10) / 10,
        yaw: Math.round(this.smoothedYaw),
        pitch: Math.round(this.smoothedPitch),
        roll: 0,
        noiseLevel: noiseLevel,
        noiseRms: Math.round(noiseRms * 1000) / 1000,
        eventType: eventType
      });
    }

    // Telemetry event sync
    if (this.options.onTelemetryEvent && (now - this.lastStateTransitionTime > 3000 || eventType !== 'FOCUSED_HEARTBEAT')) {
      this.lastStateTransitionTime = now;
      this.options.onTelemetryEvent({
        attention_state: this.state,
        distraction_score: this.smoothedScore,
        distraction_duration: Math.round(this.distractionDuration * 10) / 10,
        event_type: eventType,
        confidence: faceData.confidence,
        head_pose: {
          yaw: Math.round(this.smoothedYaw * 10) / 10,
          pitch: Math.round(this.smoothedPitch * 10) / 10,
          roll: 0
        },
        noise_level: noiseLevel,
        environmental_distraction: environmentalDistraction,
        behavioral_distraction: behavioralDistraction,
        notification_triggered: (now - this.lastNotificationTime < 2000)
      });
    }
  }

  renderPreviewOverlay(faceData) {
    if (!this.previewCtx || !this.previewCanvas || !this.videoElement) return;

    const pw = this.previewCanvas.width;
    const ph = this.previewCanvas.height;

    this.previewCtx.save();
    this.previewCtx.drawImage(this.videoElement, 0, 0, pw, ph);

    if (faceData && faceData.detected && faceData.box) {
      const scaleX = pw / (this.videoElement.videoWidth || 320);
      const scaleY = ph / (this.videoElement.videoHeight || 240);
      const bx = faceData.box.x * scaleX;
      const by = faceData.box.y * scaleY;
      const bw = faceData.box.width * scaleX;
      const bh = faceData.box.height * scaleY;

      let color = '#10B981';
      if (this.state === 'POSSIBLE_DISTRACTION') color = '#F59E0B';
      if (this.state === 'HIGH_DISTRACTION' || this.state === 'SUSTAINED_DISTRACTION') color = '#EF4444';

      this.previewCtx.strokeStyle = color;
      this.previewCtx.lineWidth = 2;
      this.previewCtx.strokeRect(bx, by, bw, bh);

      // Draw Landmark Dots
      if (faceData.landmarks) {
        this.previewCtx.fillStyle = '#38BDF8';
        faceData.landmarks.forEach((pt) => {
          this.previewCtx.beginPath();
          this.previewCtx.arc(pt[0] * scaleX, pt[1] * scaleY, 2, 0, 2 * Math.PI);
          this.previewCtx.fill();
        });
      }

      this.previewCtx.fillStyle = color;
      this.previewCtx.font = 'bold 10px Inter, sans-serif';
      this.previewCtx.fillText(`Yaw: ${Math.round(this.smoothedYaw)}°`, bx, Math.max(12, by - 4));
    } else {
      this.previewCtx.fillStyle = 'rgba(0, 0, 0, 0.65)';
      this.previewCtx.fillRect(0, 0, pw, ph);
      this.previewCtx.fillStyle = '#EF4444';
      this.previewCtx.font = 'bold 11px Inter, sans-serif';
      this.previewCtx.textAlign = 'center';
      this.previewCtx.fillText('NO FACE DETECTED', pw / 2, ph / 2);
      this.previewCtx.textAlign = 'start';
    }
    this.previewCtx.restore();
  }

  checkAndTriggerNotification(reason, now) {
    const elapsedSinceLast = (now - this.lastNotificationTime) / 1000;
    if (elapsedSinceLast < this.options.notificationCooldownSec) return;

    this.lastNotificationTime = now;
    let message = 'You seem distracted. Take a moment to refocus on the lecture.';
    let type = 'HIGH_DISTRACTION';

    if (reason === 'HIGH_NOISE') {
      message = 'Your surroundings seem noisy. If possible, consider moving to a quieter place.';
      type = 'NOISE_WARNING';
    } else if (this.smoothedScore < 70) {
      message = 'Looks like your attention is moving away from the lecture.';
      type = 'MODERATE_DISTRACTION';
    }

    if (this.options.onNotification) {
      this.options.onNotification({
        type: type,
        message: message,
        cooldown: this.options.notificationCooldownSec
      });
    }
  }

  notifyStateChange(state, message) {
    if (this.options.onStateChange) {
      this.options.onStateChange(state, message);
    }
  }
}

if (typeof window !== 'undefined') {
  window.CogniTraceAttentionEngine = CogniTraceAttentionEngine;
}
