import React from 'react';
import FocusMonitor from './FocusMonitoring/FocusMonitor';

/**
 * AttentionMonitor Wrapper
 * 
 * Provides backwards compatibility for existing imports in CogniTrace
 * while providing the modular FocusMonitoring system.
 */
export default function AttentionMonitor(props) {
  return <FocusMonitor {...props} />;
}
