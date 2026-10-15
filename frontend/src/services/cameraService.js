/**
 * CogniTrace Camera Service
 * 
 * Manages privacy-preserving local webcam access, offscreen image preprocessing,
 * and real-time lighting quality evaluation.
 * 
 * Pipeline:
 * Camera Frame -> Resize (Offscreen Canvas) -> Grayscale -> Brightness Evaluation -> Contrast Enhancement
 */

import { distractionConfig } from '../config/distractionConfig.js';

class CameraService {
  constructor() {
    this.stream = null;
    this.videoElement = null;
    this.offscreenCanvas = null;
    this.offscreenCtx = null;
    this.targetWidth = 320;
    this.targetHeight = 240;
  }

  /**
   * Request webcam stream strictly within browser memory.
   */
  async requestCamera(width = 320, height = 240) {
    this.targetWidth = width;
    this.targetHeight = height;

    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error('Your browser does not support camera capture (getUserMedia API).');
    }

    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: width },
          height: { ideal: height },
          frameRate: { ideal: distractionConfig.temporal.frameRateFps, max: 15 },
          facingMode: 'user'
        },
        audio: false
      });

      this.videoElement = document.createElement('video');
      this.videoElement.srcObject = this.stream;
      this.videoElement.setAttribute('playsinline', 'true');
      this.videoElement.muted = true;
      await this.videoElement.play();

      this.offscreenCanvas = document.createElement('canvas');
      this.offscreenCanvas.width = width;
      this.offscreenCanvas.height = height;
      this.offscreenCtx = this.offscreenCanvas.getContext('2d', { willReadFrequently: true });

      return {
        stream: this.stream,
        video: this.videoElement,
        success: true
      };
    } catch (err) {
      this.stopCamera();
      if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
        throw new Error('Camera permission was denied. Please allow camera access in your browser settings.');
      } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
        throw new Error('No webcam device was detected on your computer.');
      } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
        throw new Error('Webcam is already in use by another application or video call.');
      }
      throw new Error(`Camera initialization failed: ${err.message}`);
    }
  }

  /**
   * Stops all active camera tracks and frees hardware.
   */
  stopCamera() {
    if (this.stream) {
      this.stream.getTracks().forEach(track => {
        try { track.stop(); } catch (_) {}
      });
      this.stream = null;
    }
    if (this.videoElement) {
      try {
        this.videoElement.pause();
        this.videoElement.srcObject = null;
      } catch (_) {}
      this.videoElement = null;
    }
    this.offscreenCanvas = null;
    this.offscreenCtx = null;
  }

  /**
   * Preprocessing Pipeline:
   * 1. Draw frame to resized canvas
   * 2. Compute grayscale pixel buffer
   * 3. Evaluate brightness quality and contrast
   */
  processCurrentFrame() {
    if (!this.videoElement || this.videoElement.readyState < 2 || !this.offscreenCtx) {
      return null;
    }

    const w = this.offscreenCanvas.width;
    const h = this.offscreenCanvas.height;

    // Draw current camera frame to offscreen canvas
    this.offscreenCtx.drawImage(this.videoElement, 0, 0, w, h);
    const imageData = this.offscreenCtx.getImageData(0, 0, w, h);
    const data = imageData.data;
    const totalPixels = w * h;

    let totalLuminance = 0;
    let minLum = 255;
    let maxLum = 0;

    // Center zone vs perimeter zone luminance for backlighting detection
    let centerLumSum = 0;
    let centerPixels = 0;
    let perimeterLumSum = 0;
    let perimeterPixels = 0;

    const cxMin = Math.floor(w * 0.25);
    const cxMax = Math.floor(w * 0.75);
    const cyMin = Math.floor(h * 0.25);
    const cyMax = Math.floor(h * 0.75);

    // Fast grayscale calculation using standard ITU-R BT.601 luminance coefficients
    for (let i = 0; i < data.length; i += 4) {
      const r = data[i];
      const g = data[i + 1];
      const b = data[i + 2];
      const lum = 0.299 * r + 0.587 * g + 0.114 * b;

      totalLuminance += lum;
      if (lum < minLum) minLum = lum;
      if (lum > maxLum) maxLum = lum;

      const px = (i / 4) % w;
      const py = Math.floor((i / 4) / w);

      if (px >= cxMin && px <= cxMax && py >= cyMin && py <= cyMax) {
        centerLumSum += lum;
        centerPixels++;
      } else {
        perimeterLumSum += lum;
        perimeterPixels++;
      }
    }

    const avgBrightness = totalLuminance / totalPixels;
    const centerBrightness = centerPixels > 0 ? centerLumSum / centerPixels : avgBrightness;
    const perimeterBrightness = perimeterPixels > 0 ? perimeterLumSum / perimeterPixels : avgBrightness;
    const contrastRange = maxLum - minLum;

    // Lighting quality score computation (0-100%)
    let lightingScore = 100;
    let lightingIssue = null;
    let actionableFeedback = null;

    if (avgBrightness < distractionConfig.quality.minBrightness) {
      const deficit = distractionConfig.quality.minBrightness - avgBrightness;
      lightingScore = Math.max(10, Math.round(100 - (deficit * 2.2)));
      lightingIssue = 'LOW_ILLUMINATION';
      actionableFeedback = 'Lighting is too low. Please move to a brighter area or turn on a desk lamp.';
    } else if (avgBrightness > distractionConfig.quality.maxBrightness) {
      lightingScore = Math.max(20, Math.round(100 - ((avgBrightness - distractionConfig.quality.maxBrightness) * 2.5)));
      lightingIssue = 'OVEREXPOSURE';
      actionableFeedback = 'Camera image is overexposed. Reduce strong direct light pointing at the camera.';
    } else if (perimeterBrightness - centerBrightness > 45) {
      // Background is significantly brighter than face area
      lightingScore = Math.max(35, Math.round(90 - (perimeterBrightness - centerBrightness)));
      lightingIssue = 'EXCESSIVE_BACKLIGHTING';
      actionableFeedback = 'Excessive backlighting detected. Avoid strong light or windows directly behind you.';
    } else if (contrastRange < 40) {
      lightingScore = Math.max(40, Math.round(contrastRange * 1.8));
      lightingIssue = 'LOW_CONTRAST';
      actionableFeedback = 'Image contrast is low. Ensure balanced ambient lighting.';
    }

    return {
      canvas: this.offscreenCanvas,
      imageData,
      avgBrightness: Math.round(avgBrightness),
      lightingScore: Math.min(100, Math.max(0, lightingScore)),
      lightingIssue,
      actionableFeedback,
      isLightingAdequate: lightingScore >= 45,
      contrastRange: Math.round(contrastRange)
    };
  }
}

export const cameraService = new CameraService();
export default cameraService;
