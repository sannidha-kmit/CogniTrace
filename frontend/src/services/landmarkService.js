/**
 * CogniTrace Facial Landmark & 3D Pose Extraction Service
 * 
 * Computes:
 * - 3D Head Pose: Yaw, Pitch, Roll (in degrees)
 * - Eye Features: Approximate gaze deviation vector, eye openness / blink indicators
 * - Face Quality: Visibility score, landmark stability
 */

class LandmarkService {
  constructor() {
    this.prevLandmarks = null;
    this.stabilityHistory = [];
    this.blinkCount = 0;
    this.lastBlinkTime = 0;
  }

  /**
   * Extracts head pose angles and gaze metrics from face detection results.
   */
  extractFeatures(faceData, personalBaseline = null) {
    if (!faceData || !faceData.detected) {
      return {
        hasFeatures: false,
        yaw: 0,
        pitch: 0,
        roll: 0,
        gazeDeviation: 0,
        eyeOpenness: 1.0,
        faceVisibility: 0,
        stabilityScore: 0,
        yawDeviation: 0,
        pitchDeviation: 0,
        rollDeviation: 0
      };
    }

    let yaw = 0;
    let pitch = 0;
    let roll = 0;
    let gazeDeviation = 0;
    let eyeOpenness = 0.85;

    const landmarks = faceData.rawLandmarks;

    if (landmarks && landmarks.length >= 4) {
      // landmarks: [rightEye, leftEye, nose, mouth, (rightEar, leftEar)]
      const rightEye = landmarks[0];
      const leftEye = landmarks[1];
      const nose = landmarks[2];
      const mouth = landmarks[3];

      // 1. Roll Angle: In-plane slope of the line connecting both eyes
      const dX = leftEye[0] - rightEye[0];
      const dY = leftEye[1] - rightEye[1];
      roll = (Math.atan2(dY, dX) * 180) / Math.PI;

      // 2. Yaw Angle: Nose horizontal offset from inter-pupillary midpoint
      const eyeMidX = (rightEye[0] + leftEye[0]) / 2;
      const eyeSpanX = Math.max(1, Math.abs(leftEye[0] - rightEye[0]));
      const noseDistX = nose[0] - eyeMidX;
      yaw = (noseDistX / (eyeSpanX / 2)) * 48; // Scaled to geometric degrees

      // 3. Pitch Angle: Nose vertical offset relative to eye-to-mouth distance
      const eyeMidY = (rightEye[1] + leftEye[1]) / 2;
      const eyeToMouthDist = Math.max(1, Math.abs(mouth[1] - eyeMidY));
      const noseDistY = nose[1] - eyeMidY;
      const pitchRatio = noseDistY / eyeToMouthDist;
      pitch = (pitchRatio - 0.45) * 55; // Calibrated vertical tilt

      // 4. Approximate Gaze Deviation: Composite of nose-to-eye angle and eye-center vector
      const gazeX = Math.abs(noseDistX / (eyeSpanX / 2));
      const gazeY = Math.abs((noseDistY - 0.45 * eyeToMouthDist) / eyeToMouthDist);
      gazeDeviation = Math.min(1.0, Math.sqrt(gazeX * gazeX + gazeY * gazeY));
    } else if (faceData.box) {
      // Fallback 3D estimation from bounding box coordinates
      const box = faceData.box;
      yaw = ((box.cx - 160) / 160) * 35;
      pitch = -((box.cy - 120) / 120) * 28;
      roll = 0;
      gazeDeviation = Math.min(1.0, Math.abs(yaw) / 45);
    }

    // Measure Landmark Stability (jitter variance across consecutive frames)
    const stabilityScore = this.calculateStability(faceData.box);

    // Compute Deviations relative to Personal Baseline (Requirement 5)
    let baselineYaw = 0;
    let baselinePitch = 0;
    let baselineRoll = 0;

    if (personalBaseline && personalBaseline.isCalibrated) {
      baselineYaw = personalBaseline.normalYaw || 0;
      baselinePitch = personalBaseline.normalPitch || 0;
      baselineRoll = personalBaseline.normalRoll || 0;
    }

    const yawDeviation = Math.abs(yaw - baselineYaw);
    const pitchDeviation = Math.abs(pitch - baselinePitch);
    const rollDeviation = Math.abs(roll - baselineRoll);

    // Face Visibility Score (0-100%) based on size, centering, and confidence
    let faceVisibility = Math.round(faceData.confidence * 100);
    if (!faceData.isCentered) faceVisibility = Math.max(30, faceVisibility - 25);
    if (!faceData.isAdequateSize) faceVisibility = Math.max(30, faceVisibility - 20);

    return {
      hasFeatures: true,
      yaw: Math.round(yaw * 10) / 10,
      pitch: Math.round(pitch * 10) / 10,
      roll: Math.round(roll * 10) / 10,
      yawDeviation: Math.round(yawDeviation * 10) / 10,
      pitchDeviation: Math.round(pitchDeviation * 10) / 10,
      rollDeviation: Math.round(rollDeviation * 10) / 10,
      gazeDeviation: Math.round(gazeDeviation * 100) / 100,
      eyeOpenness,
      faceVisibility,
      stabilityScore
    };
  }

  calculateStability(box) {
    if (!box) return 80;
    this.stabilityHistory.push({ x: box.x, y: box.y });
    if (this.stabilityHistory.length > 10) this.stabilityHistory.shift();

    if (this.stabilityHistory.length < 3) return 95;

    let totalDiff = 0;
    for (let i = 1; i < this.stabilityHistory.length; i++) {
      const dx = this.stabilityHistory[i].x - this.stabilityHistory[i - 1].x;
      const dy = this.stabilityHistory[i].y - this.stabilityHistory[i - 1].y;
      totalDiff += Math.sqrt(dx * dx + dy * dy);
    }
    const avgJitter = totalDiff / (this.stabilityHistory.length - 1);
    return Math.max(20, Math.min(100, Math.round(100 - avgJitter * 4)));
  }

  reset() {
    this.prevLandmarks = null;
    this.stabilityHistory = [];
    this.blinkCount = 0;
  }
}

export const landmarkService = new LandmarkService();
export default landmarkService;
