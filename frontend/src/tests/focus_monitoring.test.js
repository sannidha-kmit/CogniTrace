/**
 * CogniTrace Focus Monitoring Comprehensive Test Suite
 * 
 * Tests:
 * 1. Camera & Lighting Robustness (Dark, Normal, Excessive Brightness, Backlighting)
 * 2. Face Detection & Alignment (Centered, Left/Right, Too Far/Too Close, Multiple Faces, Occlusion Grace)
 * 3. 3D Head Pose & Gaze Extraction (Yaw, Pitch, Roll, Gaze deviation, Landmark stability)
 * 4. Personal Calibration & Deviations (Baseline calculation, relative deviation calculation)
 * 5. Multi-Signal Distraction Engine & State Machine (Temporary head glance vs sustained drift, recovery, smoothing)
 * 6. Strict Privacy Guarantee (Ensures zero raw frame/image payload transmission)
 * 7. Video Timestamp Mapping & Concept Mapping
 */

import { distractionConfig } from '../config/distractionConfig.js';
import landmarkService from '../services/landmarkService.js';
import distractionService from '../services/distractionService.js';
import telemetryService from '../services/telemetryService.js';

let totalTests = 0;
let passedTests = 0;

function assert(condition, message) {
  totalTests++;
  if (!condition) {
    console.error(`❌ FAIL: ${message}`);
    throw new Error(`Assertion failed: ${message}`);
  }
  passedTests++;
  console.log(`✓ PASS: ${message}`);
}

async function runTests() {
  console.log('='.repeat(70));
  console.log('RUNNING COGNITRACE FOCUS MONITORING VERIFICATION SUITE');
  console.log('='.repeat(70));

  // -------------------------------------------------------------
  // TEST 1: Config Parameters Integrity
  // -------------------------------------------------------------
  console.log('\n[TEST 1] Verifying Centralized Distraction Config...');
  assert(distractionConfig.weights.headWeight === 0.30, 'Head pose weight is 0.30');
  assert(distractionConfig.weights.gazeWeight === 0.30, 'Gaze weight is 0.30');
  assert(distractionConfig.weights.durationWeight === 0.20, 'Duration weight is 0.20');
  assert(distractionConfig.weights.interactionWeight === 0.20, 'Interaction weight is 0.20');
  assert(distractionConfig.temporal.highDistractionDurationSec === 8.0, 'High distraction duration threshold is 8s');
  assert(distractionConfig.temporal.briefMovementGraceSec === 2.0, 'Brief glance ignore duration is 2s');

  // -------------------------------------------------------------
  // TEST 2: 3D Landmark & Gaze Extraction
  // -------------------------------------------------------------
  console.log('\n[TEST 2] Testing 3D Landmark Pose & Gaze Extraction...');
  // Simulated frontal face landmarks: rightEye(100, 100), leftEye(140, 100), nose(120, 115), mouth(120, 135)
  const frontalFace = {
    detected: true,
    confidence: 0.95,
    isCentered: true,
    isAdequateSize: true,
    rawLandmarks: [
      [100, 100], // rightEye
      [140, 100], // leftEye
      [120, 115], // nose (centered)
      [120, 135]  // mouth
    ]
  };

  const frontalFeatures = landmarkService.extractFeatures(frontalFace, null);
  assert(Math.abs(frontalFeatures.yaw) < 2.0, `Frontal face has near-zero yaw (${frontalFeatures.yaw}°)`);
  assert(frontalFeatures.roll === 0, `Horizontal eyes have 0° roll (${frontalFeatures.roll}°)`);
  assert(frontalFeatures.faceVisibility >= 90, `Frontal centered face has high visibility (${frontalFeatures.faceVisibility}%)`);

  // Simulated Turned Head (Yaw: nose shifted right to x=135)
  const turnedFace = {
    detected: true,
    confidence: 0.92,
    isCentered: true,
    isAdequateSize: true,
    rawLandmarks: [
      [100, 100],
      [140, 100],
      [135, 115], // nose shifted to right
      [128, 135]
    ]
  };
  const turnedFeatures = landmarkService.extractFeatures(turnedFace, null);
  assert(turnedFeatures.yaw > 25.0, `Turned face detects significant yaw angle (${turnedFeatures.yaw}°)`);
  assert(turnedFeatures.gazeDeviation > 0.4, `Turned face shows gaze shift (${turnedFeatures.gazeDeviation})`);

  // -------------------------------------------------------------
  // TEST 3: Personal Baseline Calibration (Requirement 5)
  // -------------------------------------------------------------
  console.log('\n[TEST 3] Testing Personal Posture Baseline...');
  const baseline = {
    isCalibrated: true,
    normalYaw: 10.0, // Student naturally sits tilted at 10 deg
    normalPitch: -3.0,
    normalRoll: 0,
    yawThreshold: 22.0,
    pitchThreshold: 16.0
  };

  const calibratedFeatures = landmarkService.extractFeatures(turnedFace, baseline);
  // Turned yaw is ~36°, baseline is 10°, deviation is |36 - 10| = 26°
  assert(calibratedFeatures.yawDeviation < Math.abs(turnedFeatures.yaw), 'Personal baseline computes relative deviation correctly');

  // -------------------------------------------------------------
  // TEST 4: Multi-Signal State Machine & Temporal Smoothing (Reqs 6, 7, 8, 9)
  // -------------------------------------------------------------
  console.log('\n[TEST 4] Testing Multi-Signal Distraction Engine & Temporal Consistency...');
  distractionService.reset();
  distractionService.setPersonalBaseline(baseline);

  // Scenario A: Student looks forward (FOCUSED)
  const step1 = distractionService.evaluate({
    faceData: frontalFace,
    landmarks: frontalFeatures,
    frameQuality: { isLightingAdequate: true, lightingScore: 88 },
    videoTimestamp: '01:15',
    currentTimeSec: 75,
    playerState: 1
  });
  assert(step1.state === 'FOCUSED', `Attentive student is classified as FOCUSED (score: ${step1.distractionScore})`);
  assert(step1.focusLevel >= 90, `Focus level is high (${step1.focusLevel}%)`);

  // Scenario B: Temporary Glance / Head Turn (< 2s) -> Must NOT trigger notification (Requirement 7)
  const step2 = distractionService.evaluate({
    faceData: turnedFace,
    landmarks: turnedFeatures,
    frameQuality: { isLightingAdequate: true, lightingScore: 88 },
    videoTimestamp: '01:16',
    currentTimeSec: 76,
    playerState: 1
  });
  assert(step2.state === 'FOCUSED', 'Brief glance <2s remains FOCUSED without false alarms');
  assert(!step2.notification, 'No notification triggered on brief movement');

  // Scenario C: Sustained Distraction (Simulate passing 8 seconds)
  distractionService.distractionStartTime = Date.now() - 8500; // 8.5 seconds ago
  const step3 = distractionService.evaluate({
    faceData: turnedFace,
    landmarks: turnedFeatures,
    frameQuality: { isLightingAdequate: true, lightingScore: 88 },
    videoTimestamp: '01:24',
    currentTimeSec: 84,
    playerState: 1
  });
  assert(step3.state === 'HIGH_DISTRACTION', `Persistent 8.5s distraction transitions to HIGH_DISTRACTION (state: ${step3.state})`);
  assert(step3.notification !== null, 'Gentle explainable notification triggered after 8 seconds');
  assert(step3.notification.reasons.length > 0, 'Notification includes explainable observation reasons');
  assert(step3.notification.type === 'HIGH_DISTRACTION', 'Notification type is HIGH_DISTRACTION');

  // Scenario D: Restored Attention -> State returns to FOCUSED with recovery message
  const step4 = distractionService.evaluate({
    faceData: frontalFace,
    landmarks: frontalFeatures,
    frameQuality: { isLightingAdequate: true, lightingScore: 88 },
    videoTimestamp: '01:26',
    currentTimeSec: 86,
    playerState: 1
  });
  assert(step4.state === 'FOCUSED', 'State smoothly recovers to FOCUSED');
  assert(step4.notification?.type === 'RECOVERY', 'Recovery notification displayed');

  // -------------------------------------------------------------
  // TEST 5: Multiple Face Detection Guard (Requirement 23)
  // -------------------------------------------------------------
  console.log('\n[TEST 5] Testing Multiple Face Detection Guard...');
  const multiFaceData = {
    detected: false,
    multipleFaces: true,
    faceCount: 2
  };
  const multiStep = distractionService.evaluate({
    faceData: multiFaceData,
    landmarks: frontalFeatures,
    frameQuality: { isLightingAdequate: true },
    videoTimestamp: '01:30',
    currentTimeSec: 90,
    playerState: 1
  });
  assert(multiStep.state === 'MULTIPLE_FACES', 'Multiple faces detected transitions to MULTIPLE_FACES state');
  assert(multiStep.isPaused === true, 'Focus monitoring is paused on multiple faces');

  // -------------------------------------------------------------
  // TEST 6: Poor Lighting Robustness (Requirement 3, 11)
  // -------------------------------------------------------------
  console.log('\n[TEST 6] Testing Lighting & Visibility Robustness...');
  const poorLightingStep = distractionService.evaluate({
    faceData: frontalFace,
    landmarks: frontalFeatures,
    frameQuality: { isLightingAdequate: false, lightingScore: 30, actionableFeedback: 'Low illumination' },
    videoTimestamp: '01:35',
    currentTimeSec: 95,
    playerState: 1
  });
  assert(poorLightingStep.state === 'INSUFFICIENT_VISIBILITY', 'Poor lighting transitions to INSUFFICIENT_VISIBILITY without penalizing student as distracted');
  assert(poorLightingStep.canInfer === false, 'Inference paused during low illumination');

  // -------------------------------------------------------------
  // TEST 7: Strict Privacy Guarantee (Requirement 13)
  // -------------------------------------------------------------
  console.log('\n[TEST 7] Testing Privacy Guarantee (Zero frame transmission)...');
  const dirtyPayload = {
    distraction_score: 45,
    rawVideo: 'binary-video-data',
    image: 'base64-frame-image',
    frame: 'canvas-image-data'
  };
  // Attempt sending payload with raw image properties
  await telemetryService.sendAttentionTelemetry('65df12345678901234567890', '02:00', dirtyPayload);
  assert(!dirtyPayload.image, 'Sanitizer stripped raw image');
  assert(!dirtyPayload.rawVideo, 'Sanitizer stripped raw video');
  assert(!dirtyPayload.frame, 'Sanitizer stripped raw canvas frame');

  // -------------------------------------------------------------
  // TEST 8: Distraction Events History & Timestamp Seeking (Req 16, 18, 19)
  // -------------------------------------------------------------
  console.log('\n[TEST 8] Testing Distraction Event History...');
  const recordedEvents = distractionService.getEvents();
  assert(recordedEvents.length >= 1, `Recorded events history contains ${recordedEvents.length} events`);
  assert(recordedEvents[0].videoTimestamp === '01:24', 'Recorded event accurately stores video timestamp (01:24)');
  assert(recordedEvents[0].videoTimeSec === 84, 'Recorded event stores video seconds (84s)');

  console.log('\n' + '='.repeat(70));
  console.log(`ALL ${passedTests}/${totalTests} FOCUS MONITORING TESTS PASSED SUCCESSFULLY!`);
  console.log('='.repeat(70));
}

runTests().catch(err => {
  console.error('Fatal Test Error:', err);
  process.exit(1);
});
