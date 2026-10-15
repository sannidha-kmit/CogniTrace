/**
 * CogniTrace Multi-Signal Distraction & Attention Engine
 * 
 * Synthesizes:
 * - 3D Head Pose deviation from personal baseline
 * - Gaze deviation
 * - Face visibility & detection confidence
 * - Sustained abnormal duration (temporal windowing)
 * - Video player interaction telemetry (pausing, seeking, rewind/replay)
 * 
 * Implements the 4-stage State Machine:
 * FOCUSED -> ATTENTION_DRIFT -> DISTRACTED -> HIGH_DISTRACTION -> (Recovery)
 */

import { distractionConfig } from '../config/distractionConfig.js';

class DistractionService {
  constructor() {
    this.currentState = distractionConfig.states.FOCUSED;
    this.distractionScore = 0;
    this.smoothedScore = 0;
    this.distractionStartTime = null;
    this.distractionDuration = 0;
    this.lastNotificationTime = 0;
    this.eventsHistory = [];
    this.personalBaseline = null;
    this.lastVideoInteraction = null;
  }

  setPersonalBaseline(baseline) {
    this.personalBaseline = baseline;
  }

  recordVideoInteraction(type, timestamp) {
    this.lastVideoInteraction = {
      type,
      timestamp,
      recordedAt: Date.now()
    };
  }

  /**
   * Main evaluation loop step called on each sampled frame (8 FPS).
   */
  evaluate({
    faceData,
    landmarks,
    frameQuality,
    videoTimestamp,
    currentTimeSec,
    playerState
  }) {
    const now = Date.now();

    // 1. Check Multiple Faces Edge Case (Requirement 23)
    if (faceData && faceData.multipleFaces) {
      this.currentState = distractionConfig.states.MULTIPLE_FACES;
      return {
        state: distractionConfig.states.MULTIPLE_FACES,
        distractionScore: 0,
        focusLevel: 100,
        distractionDuration: 0,
        reason: 'Multiple faces detected. Focus monitoring is paused.',
        isPaused: true,
        canInfer: false
      };
    }

    // 2. Check Lighting / Camera Quality Edge Cases (Requirements 3, 11)
    if (frameQuality && !frameQuality.isLightingAdequate) {
      this.currentState = distractionConfig.states.INSUFFICIENT_VISIBILITY;
      return {
        state: distractionConfig.states.INSUFFICIENT_VISIBILITY,
        distractionScore: 0,
        focusLevel: 100,
        distractionDuration: 0,
        reason: frameQuality.actionableFeedback || 'Camera visibility is insufficient for reliable attention estimation.',
        isPaused: true,
        canInfer: false
      };
    }

    // 3. Check Face Detection Confidence & Occlusion Grace Period (Requirements 11, 12)
    if (!faceData || !faceData.detected) {
      if (faceData && faceData.isOccluded) {
        // Within grace period for temporary movement/hand adjustment
        return {
          state: this.currentState,
          distractionScore: this.smoothedScore,
          focusLevel: Math.max(0, 100 - this.smoothedScore),
          distractionDuration: this.distractionDuration,
          reason: 'Checking camera alignment...',
          canInfer: false
        };
      }

      this.currentState = distractionConfig.states.INSUFFICIENT_VISIBILITY;
      this.distractionStartTime = null;
      this.distractionDuration = 0;
      this.smoothedScore = Math.max(0, Math.round(this.smoothedScore * 0.8));

      return {
        state: distractionConfig.states.INSUFFICIENT_VISIBILITY,
        distractionScore: 0,
        focusLevel: 100,
        distractionDuration: 0,
        reason: 'Please position yourself in front of the camera.',
        canInfer: false
      };
    }

    // 4. Multi-Signal Calculation (Requirements 6, 8, 10)
    const weights = distractionConfig.weights;
    const posture = distractionConfig.posture;

    // A. Head Pose Deviation Component (30%)
    const yawDev = landmarks.yawDeviation || 0;
    const pitchDev = landmarks.pitchDeviation || 0;
    const yawLimit = this.personalBaseline?.yawThreshold || posture.defaultYawThresholdDeg;
    const pitchLimit = this.personalBaseline?.pitchThreshold || posture.defaultPitchThresholdDeg;

    let headSignal = 0;
    if (yawDev > yawLimit) {
      headSignal += Math.min(100, ((yawDev - yawLimit) / 20) * 100);
    }
    if (pitchDev > pitchLimit) {
      headSignal += Math.min(100, ((pitchDev - pitchLimit) / 15) * 100);
    }
    headSignal = Math.min(100, headSignal);

    // B. Gaze Deviation Component (30%)
    const gazeDev = landmarks.gazeDeviation || 0;
    let gazeSignal = 0;
    if (gazeDev > posture.gazeDeviationThreshold) {
      gazeSignal = Math.min(100, ((gazeDev - posture.gazeDeviationThreshold) / 0.4) * 100);
    }

    // C. Duration Component (20%)
    const isAbnormalMovement = headSignal > 30 || gazeSignal > 35;
    if (isAbnormalMovement) {
      if (!this.distractionStartTime) {
        this.distractionStartTime = now;
      }
      this.distractionDuration = (now - this.distractionStartTime) / 1000;
    } else {
      this.distractionStartTime = null;
      this.distractionDuration = 0;
    }

    const durationSignal = Math.min(100, (this.distractionDuration / distractionConfig.temporal.highDistractionDurationSec) * 100);

    // D. Video Interaction Component (20%)
    let interactionSignal = 0;
    if (this.lastVideoInteraction && (now - this.lastVideoInteraction.recordedAt) < 6000) {
      // Recent active interaction (e.g. replay/seek to understand) implies active cognitive engagement
      if (this.lastVideoInteraction.type === 'REPLAY' || this.lastVideoInteraction.type === 'SEEK_BACKWARD') {
        interactionSignal = 0; // Reduces false positive distraction during rewind study
      } else if (playerState === 2) {
        // Paused state
        interactionSignal = 15;
      }
    }

    // Composite Weighted Score Calculation (Normalized 0 to 100)
    const rawScore = (
      headSignal * weights.headWeight +
      gazeSignal * weights.gazeWeight +
      durationSignal * weights.durationWeight +
      interactionSignal * weights.interactionWeight
    );

    // Exponential Moving Average (EMA) Temporal Smoothing (Requirement 7)
    this.smoothedScore = Math.round(0.45 * rawScore + 0.55 * this.smoothedScore);
    this.distractionScore = Math.min(100, Math.max(0, this.smoothedScore));
    const focusLevel = Math.max(0, 100 - this.distractionScore);

    // 5. State Machine Transition Logic (Requirement 9)
    const prevTransitionState = this.currentState;
    let notificationToTrigger = null;
    let explanationReasons = [];

    if (this.distractionDuration < distractionConfig.temporal.briefMovementGraceSec) {
      // 1 abnormal frame or brief movement (<2s) -> IGNORED (Requirement 7)
      this.currentState = distractionConfig.states.FOCUSED;
    } else if (this.distractionDuration < distractionConfig.temporal.attentionDriftThresholdSec) {
      this.currentState = distractionConfig.states.ATTENTION_DRIFT;
    } else if (this.distractionDuration < distractionConfig.temporal.highDistractionDurationSec) {
      this.currentState = distractionConfig.states.DISTRACTED;
    } else {
      // Persistent high distraction (>= 8s) -> HIGH_DISTRACTION
      this.currentState = distractionConfig.states.HIGH_DISTRACTION;

      // Check notification cooldown (Requirement 14)
      const elapsedSinceNotification = (now - this.lastNotificationTime) / 1000;
      if (elapsedSinceNotification >= distractionConfig.temporal.notificationCooldownSec) {
        this.lastNotificationTime = now;

        // Build explainable reasons (Requirement 15)
        if (headSignal > 30) explanationReasons.push('Head orientation moved away from screen');
        if (gazeSignal > 35) explanationReasons.push('Gaze shifted from the lecture');
        if (this.distractionDuration >= 8) explanationReasons.push(`Observed for approximately ${Math.round(this.distractionDuration)} seconds`);

        notificationToTrigger = {
          type: 'HIGH_DISTRACTION',
          title: 'Attention Drift Detected',
          message: 'You may be distracted. Consider returning your attention to the lecture.',
          reasons: explanationReasons,
          timestamp: videoTimestamp,
          duration: Math.round(this.distractionDuration)
        };

        // Record persistent distraction event (Requirement 16)
        this.recordDistractionEvent({
          videoTimestamp,
          videoTimeSec: currentTimeSec || 0,
          duration: Math.round(this.distractionDuration),
          score: this.distractionScore,
          state: distractionConfig.states.HIGH_DISTRACTION,
          reasons: explanationReasons
        });
      }
    }

    // Check for Recovery Transition
    if (prevTransitionState === distractionConfig.states.HIGH_DISTRACTION && this.currentState === distractionConfig.states.FOCUSED) {
      notificationToTrigger = {
        type: 'RECOVERY',
        title: 'Focus Restored',
        message: 'Welcome back! Your focus has returned to the lecture.',
        reasons: []
      };
    }

    return {
      state: this.currentState,
      distractionScore: this.distractionScore,
      focusLevel,
      distractionDuration: Math.round(this.distractionDuration * 10) / 10,
      headSignal: Math.round(headSignal),
      gazeSignal: Math.round(gazeSignal),
      durationSignal: Math.round(durationSignal),
      notification: notificationToTrigger,
      canInfer: true,
      eventsCount: this.eventsHistory.length
    };
  }

  recordDistractionEvent(eventData) {
    const eventId = 'ev_' + Date.now() + '_' + Math.floor(Math.random() * 1000);
    const newEvent = {
      eventId,
      ...eventData,
      recordedAt: new Date().toISOString()
    };
    this.eventsHistory.push(newEvent);
    return newEvent;
  }

  getEvents() {
    return [...this.eventsHistory];
  }

  reset() {
    this.currentState = distractionConfig.states.FOCUSED;
    this.distractionScore = 0;
    this.smoothedScore = 0;
    this.distractionStartTime = null;
    this.distractionDuration = 0;
    this.eventsHistory = [];
  }
}

export const distractionService = new DistractionService();
export default distractionService;
