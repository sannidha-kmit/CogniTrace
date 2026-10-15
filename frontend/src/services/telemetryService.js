/**
 * CogniTrace Privacy-Preserving Telemetry Service
 * 
 * Strict Privacy Guarantee:
 * - Only derived numerical features, durations, timestamps, and state enums are transmitted.
 * - ZERO webcam frames, video recordings, or raw audio data are EVER uploaded or stored.
 */

function getToken() {
  if (typeof localStorage !== 'undefined') {
    return localStorage.getItem('cognitrace_token');
  }
  return null;
}

class TelemetryService {
  constructor() {
    this.batchQueue = [];
    this.flushTimer = null;
    this.batchIntervalMs = 4000;
  }

  /**
   * Send a single derived attention telemetry event.
   * Asserts payload contains only derived metrics.
   */
  async sendAttentionTelemetry(courseId, videoTimestamp, payload) {
    // Strict Privacy Assertion: Ensure no image data or media streams are included
    if (payload.image || payload.frame || payload.rawVideo || payload.audioBlob) {
      console.warn('[CogniTrace Privacy Guard] Stripped raw media from telemetry payload before transmission.');
      delete payload.image;
      delete payload.frame;
      delete payload.rawVideo;
      delete payload.audioBlob;
    }

    const token = getToken();
    if (!token || !courseId) return null;

    try {
      const res = await fetch('/api/v1/student/attention/telemetry', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          course_id: courseId,
          video_timestamp: videoTimestamp || '00:00',
          attention_state: payload.attention_state || 'FOCUSED',
          distraction_score: Number(payload.distraction_score || 0),
          distraction_duration: Number(payload.distraction_duration || 0),
          event_type: payload.event_type || 'FOCUSED_HEARTBEAT',
          confidence: Number(payload.confidence || 0.95),
          head_pose: payload.head_pose ? {
            yaw: Number(payload.head_pose.yaw || 0),
            pitch: Number(payload.head_pose.pitch || 0),
            roll: Number(payload.head_pose.roll || 0)
          } : null,
          noise_level: payload.noise_level || 'DISABLED',
          environmental_distraction: Boolean(payload.environmental_distraction),
          behavioral_distraction: Boolean(payload.behavioral_distraction),
          notification_triggered: Boolean(payload.notification_triggered),
          client_timestamp: new Date().toISOString()
        })
      });

      if (res.ok) {
        return await res.json();
      }
    } catch (err) {
      // Graceful offline degradation
      console.warn('[CogniTrace Telemetry] Failed to send attention telemetry:', err.message);
    }
    return null;
  }

  /**
   * Queue event for batch telemetry transmission to conserve network bandwidth.
   */
  queueAttentionEvent(courseId, videoTimestamp, payload) {
    if (payload.image || payload.frame || payload.rawVideo || payload.audioBlob) {
      delete payload.image;
      delete payload.frame;
      delete payload.rawVideo;
      delete payload.audioBlob;
    }

    this.batchQueue.push({
      course_id: courseId,
      video_timestamp: videoTimestamp || '00:00',
      attention_state: payload.attention_state || 'FOCUSED',
      distraction_score: Number(payload.distraction_score || 0),
      distraction_duration: Number(payload.distraction_duration || 0),
      event_type: payload.event_type || 'FOCUSED_HEARTBEAT',
      confidence: Number(payload.confidence || 0.95),
      head_pose: payload.head_pose ? {
        yaw: Number(payload.head_pose.yaw || 0),
        pitch: Number(payload.head_pose.pitch || 0),
        roll: Number(payload.head_pose.roll || 0)
      } : null,
      noise_level: payload.noise_level || 'DISABLED',
      environmental_distraction: Boolean(payload.environmental_distraction),
      behavioral_distraction: Boolean(payload.behavioral_distraction),
      notification_triggered: Boolean(payload.notification_triggered),
      client_timestamp: new Date().toISOString()
    });

    if (!this.flushTimer) {
      this.flushTimer = setTimeout(() => this.flushBatchQueue(), this.batchIntervalMs);
    }
  }

  async flushBatchQueue() {
    this.flushTimer = null;
    if (this.batchQueue.length === 0) return;

    const eventsToSend = [...this.batchQueue];
    this.batchQueue = [];

    const token = getToken();
    if (!token) return;

    try {
      await fetch('/api/v1/student/attention/batch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ events: eventsToSend })
      });
    } catch (err) {
      console.warn('[CogniTrace Telemetry] Batch sync failed:', err.message);
    }
  }

  /**
   * Fetch student's course attention summary from backend.
   */
  async getStudentAttentionSummary(courseId) {
    const token = getToken();
    if (!token || !courseId) return null;

    try {
      const res = await fetch(`/api/v1/student/attention/summary?course_id=${courseId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        return await res.json();
      }
    } catch (err) {
      console.warn('[CogniTrace Telemetry] Failed to fetch attention summary:', err.message);
    }
    return null;
  }

  /**
   * Fetch extracted course concepts for concept-level distraction mapping.
   */
  async getCourseConcepts(courseId) {
    const token = getToken();
    if (!token || !courseId) return [];

    try {
      const res = await fetch(`/api/v1/student/courses/${courseId}/concepts`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        return data.concepts || [];
      }
    } catch (err) {
      console.warn('[CogniTrace Telemetry] Failed to fetch course concepts:', err.message);
    }
    return [];
  }
}

export const telemetryService = new TelemetryService();
export default telemetryService;
