import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  ArrowLeft, 
  FileText, 
  Search, 
  X, 
  RotateCw, 
  CheckCircle2, 
  Clock, 
  AlertTriangle, 
  Sparkles,
  Layers,
  Download
} from 'lucide-react';

export default function TeacherTranscriptView() {
  const { courseId } = useParams();
  const { user } = useAuth();

  const [transcript, setTranscript] = useState(null);
  const [statusInfo, setStatusInfo] = useState({
    status: 'NOT_GENERATED',
    progress: 0,
    stage: 'NOT_STARTED',
    message: '',
    processed_seconds: 0.0,
    total_duration_seconds: 0.0
  });

  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');
  
  const [searchQuery, setSearchQuery] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const pollTimerRef = useRef(null);

  const fetchTranscript = async () => {
    const token = localStorage.getItem('cognitrace_token');
    if (!token) return;

    try {
      const res = await fetch(`/api/v1/teacher/courses/${courseId}/transcript`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setTranscript(data);
        setStatusInfo({
          status: data.status,
          progress: data.progress || (data.status === 'COMPLETED' ? 100 : 0),
          stage: data.stage || 'NOT_STARTED',
          message: data.message || '',
          processed_seconds: data.processed_seconds || 0,
          total_duration_seconds: data.total_duration_seconds || 0
        });
        setErrorMessage('');
        
        // Stop polling if completed or failed
        if (data.status === 'COMPLETED' || data.status === 'FAILED') {
          if (pollTimerRef.current) {
            clearInterval(pollTimerRef.current);
            pollTimerRef.current = null;
          }
          setIsGenerating(false);
        } else if (data.status === 'PROCESSING' || data.status === 'PENDING') {
          setIsGenerating(true);
          startPolling();
        }
      } else {
        const errData = await res.json();
        setErrorMessage(errData.detail || 'Failed to load transcript details.');
      }
    } catch (err) {
      setErrorMessage('Network error fetching transcript.');
    } finally {
      setLoading(false);
    }
  };

  const checkStatus = async () => {
    const token = localStorage.getItem('cognitrace_token');
    if (!token) return;

    try {
      const res = await fetch(`/api/v1/teacher/courses/${courseId}/transcript/status`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setStatusInfo(data);
        if (data.status === 'PROCESSING' || data.status === 'PENDING') {
          setIsGenerating(true);
          startPolling();
        } else if (data.status === 'COMPLETED') {
          setIsGenerating(false);
          if (pollTimerRef.current) {
            clearInterval(pollTimerRef.current);
            pollTimerRef.current = null;
          }
          fetchTranscript();
        }
      }
    } catch (err) {
      console.warn('Status check failed:', err);
    }
  };

  const startPolling = () => {
    if (pollTimerRef.current) return;
    pollTimerRef.current = setInterval(() => {
      checkStatus();
    }, 2000);
  };

  useEffect(() => {
    fetchTranscript();
    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, [courseId]);

  const handleGenerate = async () => {
    setIsGenerating(true);
    setErrorMessage('');
    const token = localStorage.getItem('cognitrace_token');
    try {
      const res = await fetch(`/api/v1/teacher/courses/${courseId}/transcript/generate`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        startPolling();
        fetchTranscript();
      } else {
        const errData = await res.json();
        setErrorMessage(errData.detail || 'Failed to start transcript generation.');
        setIsGenerating(false);
      }
    } catch (err) {
      setErrorMessage('Network error starting transcript generation.');
      setIsGenerating(false);
    }
  };

  const handleRegenerate = async () => {
    setIsGenerating(true);
    setErrorMessage('');
    const token = localStorage.getItem('cognitrace_token');
    try {
      const res = await fetch(`/api/v1/teacher/courses/${courseId}/transcript/regenerate`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        startPolling();
        fetchTranscript();
      } else {
        const errData = await res.json();
        setErrorMessage(errData.detail || 'Failed to regenerate transcript.');
        setIsGenerating(false);
      }
    } catch (err) {
      setErrorMessage('Network error during regeneration.');
      setIsGenerating(false);
    }
  };

  // Format seconds helper for UI
  const formatTime = (secs) => {
    if (!secs || secs <= 0) return '00:00';
    const total = Math.round(secs);
    const m = Math.floor(total / 60);
    const s = total % 60;
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const handleExport = async (format) => {
    const token = localStorage.getItem('cognitrace_token');
    const endpoint = `/api/v1/teacher/courses/${courseId}/transcript/export?format=${format}`;
    try {
      const res = await fetch(endpoint, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        const disposition = res.headers.get('content-disposition');
        let filename = `transcript_export.${format}`;
        if (disposition && disposition.indexOf('attachment') !== -1) {
          const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
          const matches = filenameRegex.exec(disposition);
          if (matches != null && matches[1]) { 
            filename = matches[1].replace(/['"]/g, '');
          }
        }
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        a.remove();
      } else {
        const errData = await res.json();
        setErrorMessage(errData.detail || 'Export failed.');
      }
    } catch (err) {
      setErrorMessage('Network error during export.');
    }
  };

  // Filtered segments based on search query
  const filteredSegments = (transcript?.segments || []).filter(seg => 
    seg.text.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const currentStatus = statusInfo.status || transcript?.status || 'NOT_GENERATED';
  const currentProgress = statusInfo.progress || (currentStatus === 'COMPLETED' ? 100 : 0);

  return (
    <div className="min-h-screen flex flex-col bg-slate-950">
      {/* Navbar */}
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link
            to="/teacher/courses"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-400 hover:text-indigo-400 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Back to My Courses
          </Link>
          <span className="text-xs font-mono text-indigo-400 px-3 py-1 rounded-full bg-indigo-950/60 border border-indigo-800/50">
            Teacher ID: {user?.identifier}
          </span>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-5xl w-full mx-auto px-4 py-8 space-y-6">
        
        {/* Header Panel */}
        <div className="glass-panel p-6 sm:p-8 rounded-2xl border border-slate-800 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <span className="text-[10px] font-mono px-2.5 py-0.5 rounded bg-indigo-950 text-indigo-400 border border-indigo-800/50">
                {transcript?.subject || 'Subject'}
              </span>
              <h2 className="text-2xl font-bold text-white tracking-tight mt-1">
                {transcript?.course_name || 'Course Transcript'}
              </h2>
              <p className="text-xs text-slate-400 mt-1">
                Teacher: <strong className="text-white">{transcript?.teacher_name || user?.name}</strong>
              </p>
            </div>

            {/* Status Badge */}
            <div className="flex items-center gap-3">
              {currentStatus === 'COMPLETED' ? (
                <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-950/80 border border-emerald-500/40 text-emerald-400 text-xs font-mono">
                  <CheckCircle2 className="w-4 h-4" /> Status: COMPLETED (100%)
                </span>
              ) : isGenerating || currentStatus === 'PROCESSING' || currentStatus === 'PENDING' ? (
                <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-amber-950/80 border border-amber-500/40 text-amber-400 text-xs font-mono animate-pulse">
                  <Clock className="w-4 h-4" /> Status: {statusInfo.stage || 'PROCESSING'} ({currentProgress}%)
                </span>
              ) : currentStatus === 'FAILED' ? (
                <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-rose-950/80 border border-rose-500/40 text-rose-400 text-xs font-mono">
                  <AlertTriangle className="w-4 h-4" /> Status: FAILED
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-slate-900 border border-slate-700 text-slate-400 text-xs font-mono">
                  Status: NOT GENERATED
                </span>
              )}
            </div>
          </div>

          {/* Action buttons */}
          {currentStatus === 'NOT_GENERATED' && !isGenerating && (
            <button
              onClick={handleGenerate}
              className="inline-flex items-center gap-2 py-2.5 px-5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-lg shadow-indigo-600/20 transition-all"
            >
              <Sparkles className="w-4 h-4" />
              <span>Generate Transcript with Faster-Whisper</span>
            </button>
          )}

          {currentStatus === 'COMPLETED' && (
            <div className="flex flex-col sm:flex-row items-center gap-4">
              <Link
                to={`/teacher/courses/${courseId}/concepts`}
                className="inline-flex items-center gap-2 py-2.5 px-4 rounded-xl bg-cyan-950 hover:bg-cyan-900 border border-cyan-800/60 text-cyan-300 font-bold text-xs transition-colors"
              >
                <Layers className="w-4 h-4 text-cyan-400" />
                <span>View Course Concepts</span>
              </Link>

              {/* Export Controls */}
              <div className="flex items-center gap-2 ml-auto">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Export Transcript:</span>
                <button onClick={() => handleExport("csv")} className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition-colors flex items-center gap-1.5"><Download className="w-3.5 h-3.5"/> CSV</button>
                <button onClick={() => handleExport("json")} className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition-colors flex items-center gap-1.5"><Download className="w-3.5 h-3.5"/> JSON</button>
                <button onClick={() => handleExport("xlsx")} className="px-3 py-1.5 rounded-lg bg-indigo-900/60 border border-indigo-700 text-xs font-semibold text-indigo-200 hover:text-white hover:bg-indigo-800 transition-colors flex items-center gap-1.5"><Download className="w-3.5 h-3.5"/> Excel</button>
              </div>
            </div>
          )}

          {currentStatus === 'FAILED' && (
            <button
              onClick={handleRegenerate}
              className="inline-flex items-center gap-2 py-2 px-4 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs transition-colors"
            >
              <RotateCw className="w-4 h-4" />
              <span>Retry Transcript Generation</span>
            </button>
          )}
        </div>

        {/* Error message display */}
        {errorMessage && (
          <div className="p-4 rounded-xl bg-rose-950/60 border border-rose-800/60 flex items-start gap-2.5 text-xs text-rose-300">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Failed details display */}
        {currentStatus === 'FAILED' && statusInfo.error_message && (
          <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-900/60 text-xs text-rose-300 space-y-1">
            <strong>Error Details:</strong>
            <p className="font-mono text-[11px] text-rose-400">{statusInfo.error_message}</p>
          </div>
        )}

        {/* Real-Time Progress Bar Display */}
        {(isGenerating || currentStatus === 'PROCESSING' || currentStatus === 'PENDING') && (
          <div className="p-6 sm:p-8 glass-panel rounded-2xl border border-slate-800 space-y-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-amber-950/60 border border-amber-800/50 flex items-center justify-center text-amber-400 animate-spin">
                  <RotateCw className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white tracking-wide">
                    {statusInfo.stage === 'DOWNLOADING' ? 'Downloading Video Audio Stream...' :
                     statusInfo.stage === 'EXTRACTING_AUDIO' ? 'Extracting Audio File...' :
                     statusInfo.stage === 'TRANSCRIBING' ? 'Transcribing Audio with Faster-Whisper...' :
                     statusInfo.stage === 'SAVING' ? 'Saving Timestamped Transcript...' :
                     'Queued for Background Processing...'}
                  </h3>
                  <p className="text-xs text-slate-400 font-mono mt-0.5">
                    {statusInfo.message || 'Processing in background worker...'}
                  </p>
                </div>
              </div>

              <span className="text-xl font-bold font-mono text-amber-400 bg-amber-950/60 px-3.5 py-1.5 rounded-xl border border-amber-800/50">
                {currentProgress}%
              </span>
            </div>

            {/* Visual Progress Bar */}
            <div className="w-full bg-slate-900 rounded-full h-3 overflow-hidden border border-slate-800 p-0.5">
              <div 
                className="bg-gradient-to-r from-amber-500 to-indigo-500 h-full rounded-full transition-all duration-500 ease-out"
                style={{ width: `${currentProgress}%` }}
              />
            </div>

            {/* Audio Duration Sub-details */}
            {statusInfo.total_duration_seconds > 0 && (
              <div className="flex items-center justify-between text-xs font-mono text-slate-400 pt-1 border-t border-slate-800/60">
                <span>Processed: {formatTime(statusInfo.processed_seconds)} / {formatTime(statusInfo.total_duration_seconds)}</span>
                <span>Stage: {statusInfo.stage}</span>
              </div>
            )}
          </div>
        )}

        {/* Completed Transcript View */}
        {currentStatus === 'COMPLETED' && transcript && (
          <div className="space-y-6">
            
            {/* Transcript Search Bar */}
            <div className="glass-panel p-4 rounded-2xl border border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Search className="w-4 h-4 text-indigo-400" /> Search Transcript
                </h3>
                <span className="text-[11px] font-mono text-slate-400">
                  {filteredSegments.length} of {transcript.segments.length} segment(s)
                </span>
              </div>

              <div className="relative flex items-center">
                <Search className="w-4 h-4 text-slate-500 absolute left-3.5" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search transcript text (e.g. process, memory, array)..."
                  className="w-full pl-10 pr-9 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-white placeholder-slate-500 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery('')}
                    className="absolute right-3 p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>

            {/* Timestamped Segment List */}
            <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-3 max-h-[600px] overflow-y-auto custom-scrollbar">
              {filteredSegments.length === 0 ? (
                <div className="py-8 text-center text-xs font-mono text-slate-400">
                  No matching transcript segments found.
                </div>
              ) : (
                filteredSegments.map((seg, idx) => (
                  <div key={idx} className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-indigo-500/40 transition-colors flex flex-col sm:flex-row items-start gap-3">
                    <span className="text-xs font-mono text-indigo-400 bg-indigo-950/60 px-2.5 py-1 rounded border border-indigo-800/50 shrink-0">
                      {seg.TranscriptStart} - {seg.TranscriptEnd}
                    </span>
                    <p className="text-xs text-slate-200 leading-relaxed pt-0.5">
                      {seg.text}
                    </p>
                  </div>
                ))
              )}
            </div>

          </div>
        )}

      </main>
    </div>
  );
}
