/**
 * CogniTrace Face Detection Service
 * 
 * In-browser face detection with multi-face detection guards,
 * occlusion handling, face bounding box geometry, and actionable alignment feedback.
 */

import { distractionConfig } from '../config/distractionConfig.js';

class FaceDetectionService {
  constructor() {
    this.model = null;
    this.isLoadingModel = false;
    this.consecutiveOcclusionFrames = 0;
    this.lastDetectedFace = null;
  }

  /**
   * Initializes TensorFlow / BlazeFace model if available globally,
   * or prepares the browser fallback algorithm.
   */
  async init() {
    if (this.model) return true;
    if (this.isLoadingModel) return false;

    if (typeof window !== 'undefined' && window.blazeface) {
      try {
        this.isLoadingModel = true;
        this.model = await window.blazeface.load();
        this.isLoadingModel = false;
        return true;
      } catch (err) {
        console.warn('[CogniTrace FaceDetection] BlazeFace model load warning:', err);
        this.isLoadingModel = false;
      }
    }
    return false;
  }

  /**
   * Detects faces in the current video element.
   * Returns a structured detection result with geometry, confidence, and status.
   */
  async detect(videoElement, frameQuality) {
    if (!videoElement || videoElement.readyState < 2) {
      return {
        detected: false,
        faceCount: 0,
        confidence: 0,
        feedback: 'Initializing camera feed...',
        isCentered: false,
        isAdequateSize: false,
        rawLandmarks: null,
        box: null
      };
    }

    const vw = videoElement.videoWidth || 320;
    const vh = videoElement.videoHeight || 240;

    let predictions = [];

    if (this.model) {
      try {
        predictions = await this.model.estimateFaces(videoElement, false);
      } catch (e) {
        console.warn('[CogniTrace FaceDetection] Model inference error:', e);
      }
    }

    // 1. Multiple Faces Detected Guard
    if (predictions && predictions.length > 1) {
      return {
        detected: false,
        faceCount: predictions.length,
        multipleFaces: true,
        confidence: 0.95,
        feedback: 'Multiple faces detected. Focus monitoring is paused.',
        box: null,
        rawLandmarks: null,
        isCentered: false,
        isAdequateSize: false
      };
    }

    // 2. Single Face via Model
    if (predictions && predictions.length === 1) {
      const pred = predictions[0];
      const start = pred.topLeft;
      const end = pred.bottomRight;
      const width = end[0] - start[0];
      const height = end[1] - start[1];
      const cx = start[0] + width / 2;
      const cy = start[1] + height / 2;

      const sizeRatio = width / vw;
      const xOffsetRatio = Math.abs(cx - (vw / 2)) / (vw / 2);
      const yOffsetRatio = Math.abs(cy - (vh / 2)) / (vh / 2);

      const isCentered = xOffsetRatio < 0.45 && yOffsetRatio < 0.45;
      const isTooFar = sizeRatio < distractionConfig.quality.minFaceSizeRatio;
      const isTooClose = sizeRatio > distractionConfig.quality.maxFaceSizeRatio;
      const isAdequateSize = !isTooFar && !isTooClose;

      let feedback = 'Face properly positioned.';
      if (start[0] < 5 || end[0] > vw - 5 || start[1] < 5 || end[1] > vh - 5) {
        feedback = 'Please center your face within the camera frame.';
      } else if (isTooFar) {
        feedback = 'Move slightly closer to the camera.';
      } else if (isTooClose) {
        feedback = 'Move slightly back from the camera.';
      } else if (!isCentered) {
        feedback = 'Please center your face within the camera frame.';
      }

      this.consecutiveOcclusionFrames = 0;
      this.lastDetectedFace = {
        detected: true,
        faceCount: 1,
        multipleFaces: false,
        confidence: pred.probability ? (Array.isArray(pred.probability) ? pred.probability[0] : pred.probability) : 0.92,
        box: { x: start[0], y: start[1], width, height, cx, cy },
        sizeRatio,
        xOffsetRatio,
        yOffsetRatio,
        isCentered,
        isAdequateSize,
        feedback,
        rawLandmarks: pred.landmarks || null // [rightEye, leftEye, nose, mouth, rightEar, leftEar]
      };

      return this.lastDetectedFace;
    }

    // 3. Fallback Canvas Detection (Skin Tone & Feature Cluster)
    const fallback = this.fallbackSkinDetection(videoElement, vw, vh);
    if (fallback.detected) {
      this.consecutiveOcclusionFrames = 0;
      this.lastDetectedFace = fallback;
      return fallback;
    }

    // 4. No Face / Occlusion Grace Period
    this.consecutiveOcclusionFrames++;
    const maxGraceFrames = Math.round(distractionConfig.temporal.frameRateFps * distractionConfig.temporal.occlusionGraceSec);
    const isUnderGracePeriod = this.consecutiveOcclusionFrames <= maxGraceFrames;

    return {
      detected: false,
      faceCount: 0,
      multipleFaces: false,
      confidence: 0,
      isOccluded: isUnderGracePeriod,
      feedback: 'Please position yourself in front of the camera.',
      box: null,
      rawLandmarks: null,
      isCentered: false,
      isAdequateSize: false
    };
  }

  /**
   * Lightweight browser fallback skin and face geometry detector.
   */
  fallbackSkinDetection(videoElement, vw, vh) {
    const canvas = document.createElement('canvas');
    canvas.width = 160;
    canvas.height = 120;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(videoElement, 0, 0, 160, 120);

    const imgData = ctx.getImageData(0, 0, 160, 120);
    const d = imgData.data;

    let skinCount = 0;
    let sumX = 0;
    let sumY = 0;
    let minX = 160, maxX = 0, minY = 120, maxY = 0;

    for (let i = 0; i < d.length; i += 4) {
      const r = d[i], g = d[i + 1], b = d[i + 2];
      // Parametric skin tone rule
      if (r > 95 && g > 40 && b > 20 && (Math.max(r, g, b) - Math.min(r, g, b) > 15) && (Math.abs(r - g) > 15) && r > g && r > b) {
        const px = (i / 4) % 160;
        const py = Math.floor((i / 4) / 160);
        sumX += px;
        sumY += py;
        if (px < minX) minX = px;
        if (px > maxX) maxX = px;
        if (py < minY) minY = py;
        if (py > maxY) maxY = py;
        skinCount++;
      }
    }

    if (skinCount < 600 || skinCount > 9500) {
      return { detected: false };
    }

    const scaleX = vw / 160;
    const scaleY = vh / 120;
    const cx = (sumX / skinCount) * scaleX;
    const cy = (sumY / skinCount) * scaleY;
    const width = Math.max(45, (maxX - minX) * scaleX);
    const height = Math.max(55, (maxY - minY) * scaleY);

    const sizeRatio = width / vw;
    const isCentered = Math.abs(cx - vw / 2) < vw * 0.25;
    const isAdequateSize = sizeRatio >= 0.15 && sizeRatio <= 0.85;

    return {
      detected: true,
      faceCount: 1,
      multipleFaces: false,
      confidence: 0.78,
      box: { x: cx - width / 2, y: cy - height / 2, width, height, cx, cy },
      sizeRatio,
      isCentered,
      isAdequateSize,
      feedback: isCentered && isAdequateSize ? 'Face detected.' : 'Please center your face in the camera.',
      rawLandmarks: null,
      fallbackUsed: true
    };
  }
}

export const faceDetectionService = new FaceDetectionService();
export default faceDetectionService;
