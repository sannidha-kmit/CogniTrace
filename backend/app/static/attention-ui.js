/**
 * CogniTrace Attention UI Controller & Telemetry Connector
 */

class CogniTraceAttentionUI {
  constructor(config = {}) {
    this.config = Object.assign({
      courseId: 'demo_course_id',
      courseName: 'Data Structures & Algorithms Lecture 1',
      apiBaseUrl: '/api/v1',
      authToken: localStorage.getItem('cognitrace_token') || '',
      getVideoTimestamp: () => '00:00'
    }, config);

    this.engine = null;
    this.isConsentGranted = false;
    this.cameraPref = true;
    this.micPref = false;

    this.initElements();
    this.bindEvents();
    this.checkInitialConsent();
  }

  initElements() {
    this.widgetStatusBadge = document.getElementById('attn-status-badge');
    this.widgetStatusText = document.getElementById('attn-status-text');
    this.widgetScoreVal = document.getElementById('attn-score-val');
    this.widgetDurationVal = document.getElementById('attn-duration-val');
    this.widgetNoiseVal = document.getElementById('attn-noise-val');
    this.widgetPauseBtn = document.getElementById('attn-pause-btn');
    this.cameraToggle = document.getElementById('attn-camera-toggle');
    this.micToggle = document.getElementById('attn-mic-toggle');
    this.consentModal = document.getElementById('consent-modal');
    this.privacyModal = document.getElementById('privacy-modal');
    this.settingsModal = document.getElementById('settings-modal');
    this.toastContainer = document.getElementById('toast-container');
    this.telemetryFeed = document.getElementById('telemetry-feed');
  }

  bindEvents() {
    // Consent Modal Buttons
    const btnConsentEnable = document.getElementById('btn-consent-enable');
    const btnConsentNotNow = document.getElementById('btn-consent-not-now');
    const consentCamToggle = document.getElementById('consent-cam-toggle');
    const consentMicToggle = document.getElementById('consent-mic-toggle');

    if (btnConsentEnable) {
      btnConsentEnable.addEventListener('click', () => {
        this.cameraPref = consentCamToggle ? consentCamToggle.checked : true;
        this.micPref = consentMicToggle ? consentMicToggle.checked : false;
        this.grantConsentAndStart();
      });
    }

    if (btnConsentNotNow) {
      btnConsentNotNow.addEventListener('click', () => {
        this.dismissConsent();
      });
    }

    // Widget Pause/Resume Button
    if (this.widgetPauseBtn) {
      this.widgetPauseBtn.addEventListener('click', () => {
        this.togglePause();
      });
    }

    // Live Toggles
    if (this.cameraToggle) {
      this.cameraToggle.addEventListener('change', (e) => {
        this.cameraPref = e.target.checked;
        if (this.engine) {
          this.engine.cameraEnabled = this.cameraPref;
          if (this.cameraPref && !this.engine.videoStream) {
            this.engine.initCamera().catch(console.warn);
          }
        }
      });
    }

    if (this.micToggle) {
      this.micToggle.addEventListener('change', (e) => {
        this.micPref = e.target.checked;
        if (this.engine) {
          this.engine.micEnabled = this.micPref;
          if (this.micPref && !this.engine.audioStream) {
            this.engine.initMicrophone().catch(console.warn);
          }
        }
      });
    }

    // Privacy Modal Open/Close
    const privacyBtns = document.querySelectorAll('.open-privacy-modal');
    privacyBtns.forEach(btn => {
      btn.addEventListener('click', () => this.showPrivacyModal());
    });

    const closePrivacyBtn = document.getElementById('close-privacy-btn');
    if (closePrivacyBtn) {
      closePrivacyBtn.addEventListener('click', () => this.hidePrivacyModal());
    }

    // Settings Modal
    const settingsBtn = document.getElementById('open-settings-btn');
    if (settingsBtn) {
      settingsBtn.addEventListener('click', () => this.showSettingsModal());
    }
    const saveSettingsBtn = document.getElementById('save-settings-btn');
    if (saveSettingsBtn) {
      saveSettingsBtn.addEventListener('click', () => this.saveSettings());
    }
    const closeSettingsBtn = document.getElementById('close-settings-btn');
    if (closeSettingsBtn) {
      closeSettingsBtn.addEventListener('click', () => this.hideSettingsModal());
    }
  }

  checkInitialConsent() {
    // Show consent prompt only if not already decided in session
    const consentDecision = sessionStorage.getItem('cognitrace_attn_consent');
    if (!consentDecision) {
      this.showConsentModal();
    } else if (consentDecision === 'ENABLED') {
      this.grantConsentAndStart();
    } else {
      this.setWidgetState('MONITORING_PAUSED', 'Monitoring Disabled');
    }
  }

  showConsentModal() {
    if (this.consentModal) this.consentModal.style.display = 'flex';
  }

  hideConsentModal() {
    if (this.consentModal) this.consentModal.style.display = 'none';
  }

  showPrivacyModal() {
    if (this.privacyModal) this.privacyModal.style.display = 'flex';
  }

  hidePrivacyModal() {
    if (this.privacyModal) this.privacyModal.style.display = 'none';
  }

  showSettingsModal() {
    if (this.settingsModal) this.settingsModal.style.display = 'flex';
  }

  hideSettingsModal() {
    if (this.settingsModal) this.settingsModal.style.display = 'none';
  }

  dismissConsent() {
    sessionStorage.setItem('cognitrace_attn_consent', 'DECLINED');
    this.hideConsentModal();
    this.setWidgetState('MONITORING_PAUSED', 'Monitoring Off');
    this.showToast('Attention monitoring is paused. Lecture continuing normally.', 'toast-recovery');
  }

  async grantConsentAndStart() {
    sessionStorage.setItem('cognitrace_attn_consent', 'ENABLED');
    this.hideConsentModal();
    this.isConsentGranted = true;

    if (this.cameraToggle) this.cameraToggle.checked = this.cameraPref;
    if (this.micToggle) this.micToggle.checked = this.micPref;

    this.engine = new CogniTraceAttentionEngine({
      onStateChange: (state, msg) => this.handleStateChange(state, msg),
      onTelemetryEvent: (ev) => this.handleTelemetryEvent(ev),
      onNotification: (notif) => this.handleNotification(notif),
      onFrameMetrics: (metrics) => this.updateFrameMetrics(metrics)
    });

    const previewCanvas = document.getElementById('attn-corner-preview');
    const previewBox = document.getElementById('corner-preview-box');
    if (previewCanvas) {
      this.engine.attachPreviewCanvas(previewCanvas);
    }
    if (previewBox && this.cameraPref) {
      previewBox.style.display = 'flex';
    }

    const togglePreviewBtn = document.getElementById('toggle-preview-btn');
    if (togglePreviewBtn && previewBox) {
      togglePreviewBtn.onclick = () => {
        previewBox.style.display = previewBox.style.display === 'none' ? 'flex' : 'none';
      };
    }

    const result = await this.engine.start(this.cameraPref, this.micPref);
    if (!result.success) {
      this.showToast('Camera access is unavailable. Lecture will continue normally.', 'toast-distracted');
      this.setWidgetState('MONITORING_PAUSED', 'Camera Unavailable');
    } else {
      this.setWidgetState('FOCUSED', 'Focused');
      this.showToast('Attention assistance activated.', 'toast-recovery');
    }
  }


  togglePause() {
    if (!this.engine || !this.isConsentGranted) {
      this.showConsentModal();
      return;
    }

    if (this.engine.isPaused) {
      this.engine.resume();
      if (this.widgetPauseBtn) this.widgetPauseBtn.innerText = 'Pause Monitoring';
    } else {
      this.engine.pause();
      if (this.widgetPauseBtn) this.widgetPauseBtn.innerText = 'Resume Monitoring';
    }
  }

  handleStateChange(state, msg) {
    this.setWidgetState(state, state.replace(/_/g, ' '));
  }

  updateFrameMetrics(metrics) {
    if (this.widgetScoreVal) {
      this.widgetScoreVal.innerText = metrics.score;
      this.widgetScoreVal.style.color = metrics.score > 60 ? '#EF4444' : (metrics.score > 25 ? '#F59E0B' : '#10B981');
    }
    if (this.widgetDurationVal) {
      this.widgetDurationVal.innerText = metrics.duration > 0 ? `${metrics.duration}s` : '0s';
    }
    if (this.widgetNoiseVal) {
      this.widgetNoiseVal.innerText = metrics.noiseLevel;
    }

    this.setWidgetState(metrics.state, metrics.state.replace(/_/g, ' '));
  }

  setWidgetState(state, label) {
    if (!this.widgetStatusBadge || !this.widgetStatusText) return;

    this.widgetStatusBadge.className = 'status-badge';
    this.widgetStatusText.innerText = label;

    switch (state) {
      case 'FOCUSED':
      case 'RECOVERED':
        this.widgetStatusBadge.classList.add('status-focused');
        break;
      case 'POSSIBLE_DISTRACTION':
        this.widgetStatusBadge.classList.add('status-drifting');
        break;
      case 'SUSTAINED_DISTRACTION':
      case 'HIGH_DISTRACTION':
        this.widgetStatusBadge.classList.add('status-distracted');
        break;
      case 'FACE_NOT_DETECTED':
      case 'MONITORING_PAUSED':
      default:
        this.widgetStatusBadge.classList.add('status-paused');
        break;
    }
  }

  handleNotification(notif) {
    let cssClass = 'toast-distracted';
    if (notif.type === 'RECOVERY') cssClass = 'toast-recovery';
    if (notif.type === 'NOISE_WARNING') cssClass = 'toast-noise';

    this.showToast(notif.message, cssClass);
  }

  showToast(message, typeClass = 'toast-distracted') {
    if (!this.toastContainer) return;

    const toast = document.createElement('div');
    toast.className = `toast ${typeClass}`;
    toast.innerHTML = `
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="12" y1="8" x2="12" y2="12"></line>
        <line x1="12" y1="16" x2="12.01" y2="16"></line>
      </svg>
      <span>${message}</span>
    `;

    this.toastContainer.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      setTimeout(() => toast.remove(), 300);
    }, 4500);
  }

  async handleTelemetryEvent(ev) {
    // Append to live feed in UI
    if (this.telemetryFeed) {
      const row = document.createElement('div');
      row.className = 'feed-item';
      const timeStr = new Date().toLocaleTimeString();
      row.innerHTML = `<span>[${timeStr}] ${ev.event_type} (${ev.attention_state})</span><span>Score: ${ev.distraction_score}</span>`;
      this.telemetryFeed.prepend(row);
      if (this.telemetryFeed.children.length > 8) {
        this.telemetryFeed.lastChild.remove();
      }
    }

    // Transmit derived metrics to backend API
    const payload = Object.assign({
      course_id: this.config.courseId,
      video_timestamp: this.config.getVideoTimestamp(),
      client_timestamp: new Date().toISOString()
    }, ev);

    try {
      const headers = { 'Content-Type': 'application/json' };
      if (this.config.authToken) {
        headers['Authorization'] = `Bearer ${this.config.authToken}`;
      }

      await fetch(`${this.config.apiBaseUrl}/student/attention/telemetry`, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(payload)
      });
    } catch (err) {
      // Graceful offline fallback
    }
  }

  saveSettings() {
    const yawInp = document.getElementById('set-yaw-thresh');
    const pitchInp = document.getElementById('set-pitch-thresh');
    const highInp = document.getElementById('set-high-thresh');
    const coolInp = document.getElementById('set-cooldown');

    if (this.engine) {
      if (yawInp) this.engine.options.yawThresholdDeg = parseFloat(yawInp.value) || 24;
      if (pitchInp) this.engine.options.pitchThresholdDeg = parseFloat(pitchInp.value) || 18;
      if (highInp) this.engine.options.highDistractionSec = parseFloat(highInp.value) || 10;
      if (coolInp) this.engine.options.notificationCooldownSec = parseFloat(coolInp.value) || 45;
    }
    this.hideSettingsModal();
    this.showToast('Monitoring settings updated.', 'toast-recovery');
  }
}

window.CogniTraceAttentionUI = CogniTraceAttentionUI;
