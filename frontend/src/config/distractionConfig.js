/**
 * CogniTrace Focus & Attention Monitoring Configuration
 * 
 * Centralized, configurable parameters for:
 * - Multi-signal contribution weights
 * - Temporal smoothing windows
 * - Personal calibration tolerances
 * - Lighting & camera quality thresholds
 * - Edge case grace periods
 * 
 * Note: Weights and thresholds are configurable heuristic parameters designed
 * for adaptive instructional feedback, not claimed as definitive absolutes.
 */

export const distractionConfig = {
  // Multi-signal contribution weights (normalized to 1.0)
  weights: {
    headWeight: 0.30,
    gazeWeight: 0.30,
    durationWeight: 0.20,
    interactionWeight: 0.20,
  },

  // Temporal smoothing and duration thresholds (in seconds)
  temporal: {
    frameRateFps: 8,                    // 5-10 analysis frames/second for lightweight performance
    sampleIntervalMs: 125,              // ~8 FPS
    briefMovementGraceSec: 2.0,         // Brief glance/head turn ignored (no false alert)
    attentionDriftThresholdSec: 4.0,    // Transition from FOCUSED to ATTENTION_DRIFT
    distractedThresholdSec: 6.0,        // Transition to DISTRACTED
    highDistractionDurationSec: 8.0,    // Transition to HIGH_DISTRACTION & trigger gentle notification
    notificationCooldownSec: 35.0,      // Minimum delay between student notifications
    occlusionGraceSec: 3.0,             // Grace period for hand gesture/glasses adjustment before warning
    telemetrySyncIntervalMs: 3500,      // Throttled derived-data sync to backend
  },

  // Angle & Gaze Thresholds (Defaults before personal calibration)
  posture: {
    defaultYawThresholdDeg: 18.0,       // Horizontal head rotation tolerance
    defaultPitchThresholdDeg: 14.0,     // Vertical head tilt tolerance
    defaultRollThresholdDeg: 20.0,      // Head tilt tolerance
    gazeDeviationThreshold: 0.28,       // Normalized pupil/eye deviation tolerance
    eyeOpennessThreshold: 0.16,         // Eye aspect ratio threshold for drowsiness/eye closure
  },

  // Lighting & Camera Quality Parameters
  quality: {
    minBrightness: 38,                  // 0-255 grayscale average (below = poor lighting)
    maxBrightness: 225,                 // 0-255 (above = strong overexposure/backlighting)
    minFaceConfidence: 0.65,            // Detection confidence required for valid inference
    minFaceSizeRatio: 0.14,             // Min face bounding box width relative to camera width
    maxFaceSizeRatio: 0.85,             // Max face size ratio (too close to camera)
    stabilityThreshold: 0.08,           // Maximum allowable landmark jitter for calibration
  },

  // Calibration settings
  calibration: {
    durationSec: 3.5,                   // Calibration countdown duration
    minSamplesRequired: 20,             // Number of stable frames needed to compute baseline
  },

  // State Machine definitions
  states: {
    FOCUSED: 'FOCUSED',
    ATTENTION_DRIFT: 'ATTENTION_DRIFT',
    DISTRACTED: 'DISTRACTED',
    HIGH_DISTRACTION: 'HIGH_DISTRACTION',
    INSUFFICIENT_VISIBILITY: 'INSUFFICIENT_VISIBILITY',
    MULTIPLE_FACES: 'MULTIPLE_FACES',
    CALIBRATING: 'CALIBRATING',
    MONITORING_PAUSED: 'MONITORING_PAUSED',
  }
};

export default distractionConfig;
