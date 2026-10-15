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
  Download,
  PlaySquare
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

  const filteredSegments = (transcript?.segments || []).filter(seg => 
    seg.text.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const currentStatus = statusInfo.status || transcript?.status || 'NOT_GENERATED';
  const currentProgress = statusInfo.progress || (currentStatus === 'COMPLETED' ? 100 : 0);

  return (
    <div className="min-h-screen flex flex-col bg-[#F9F9F9] text-[#0F0F0F]">
      {/* Header */}
      <header className="border-b border-[#E5E5E5] bg-[#FFFFFF] sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <Link
            to="/teacher/courses"
            className="inline-flex items-center gap-2 text-sm font-medium text-[#606060] hover:text-[#0F0F0F] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Content
          </Link>
          <span className="text-xs font-semibold px-3 py-1 bg-[#F2F2F2] text-[#606060] rounded-full font-mono">
            Teacher ID: {user?.identifier}
          </span>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 sm:px-6 py-6 space-y-6">
        
        {/* Header Panel */}
        <div className="bg-[#FFFFFF] border border-[#E5E5E5] rounded-xl p-6 space-y-5 shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <span className="text-[11px] font-semibold px-2.5 py-0.5 bg-[#F2F2F2] text-[#0F0F0F] rounded-md">
                {transcript?.subject || 'Subject'}
              </span>
              <h1 className="text-2xl font-bold text-[#0F0F0F] tracking-tight mt-2">
                {transcript?.course_name || 'Course Video Transcript'}
              </h1>
              <p className="text-xs text-[#606060] mt-1">
                Instructor: <span className="font-semibold text-[#0F0F0F]">{transcript?.teacher_name || user?.name}</span>
              </p>
            </div>

            {/* Status Badge */}
            <div className="flex items-center gap-3">
              {currentStatus === 'COMPLETED' ? (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#E8F5E9] text-[#2E7D32] text-xs font-semibold">
                  <CheckCircle2 className="w-4 h-4 text-[#2E7D32]" /> Status: Ready (100%)
                </span>
              ) : isGenerating || currentStatus === 'PROCESSING' || currentStatus === 'PENDING' ? (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#FFF8E1] text-[#F57F17] text-xs font-semibold animate-pulse">
                  <Clock className="w-4 h-4 text-[#F57F17]" /> Status: {statusInfo.stage || 'PROCESSING'} ({currentProgress}%)
                </span>
              ) : currentStatus === 'FAILED' ? (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#FFEBEE] text-[#C62828] text-xs font-semibold">
                  <AlertTriangle className="w-4 h-4 text-[#C62828]" /> Status: Failed
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#F2F2F2] text-[#606060] text-xs font-medium">
                  Status: Not Generated
                </span>
              )}
            </div>
          </div>

          {/* Action buttons */}
          {currentStatus === 'NOT_GENERATED' && !isGenerating && (
            <button
              onClick={handleGenerate}
              className="yt-btn-primary text-xs py-2.5 px-5 font-semibold flex items-center gap-2"
            >
              <Sparkles className="w-4 h-4" />
              <span>Generate Timestamped Transcript with Faster-Whisper</span>
            </button>
          )}

          {currentStatus === 'COMPLETED' && (
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-[#E5E5E5]">
              <Link
                to={`/teacher/courses/${courseId}/concepts`}
                className="yt-btn-secondary text-xs py-2 px-3.5 font-semibold flex items-center gap-2"
              >
                <Layers className="w-4 h-4 text-[#FF0000]" />
                <span>View Derived Concepts</span>
              </Link>

              {/* Export Controls */}
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-semibold text-[#606060] uppercase tracking-wider">Export:</span>
                <button onClick={() => handleExport("csv")} className="yt-btn-secondary py-1.5 px-3 text-xs font-semibold flex items-center gap-1.5"><Download className="w-3.5 h-3.5 text-[#606060]"/> CSV</button>
                <button onClick={() => handleExport("json")} className="yt-btn-secondary py-1.5 px-3 text-xs font-semibold flex items-center gap-1.5"><Download className="w-3.5 h-3.5 text-[#606060]"/> JSON</button>
                <button onClick={() => handleExport("xlsx")} className="yt-btn-primary py-1.5 px-3 text-xs font-semibold flex items-center gap-1.5"><Download className="w-3.5 h-3.5"/> Excel</button>
              </div>
            </div>
          )}

          {currentStatus === 'FAILED' && (
            <button
              onClick={handleRegenerate}
              className="yt-btn-primary text-xs py-2.5 px-5 font-semibold flex items-center gap-2"
            >
              <RotateCw className="w-4 h-4" />
              <span>Retry Transcript Generation</span>
            </button>
          )}
        </div>

        {/* Error message display */}
        {errorMessage && (
          <div className="p-4 rounded-xl bg-[#FFEBEE] border border-[#FFCDD2] flex items-start gap-2.5 text-xs text-[#C62828]">
            <AlertTriangle className="w-4 h-4 text-[#C62828] shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Failed details display */}
        {currentStatus === 'FAILED' && statusInfo.error_message && (
          <div className="p-4 rounded-xl bg-[#FFEBEE] border border-[#FFCDD2] text-xs text-[#C62828] space-y-1">
            <strong className="text-[#0F0F0F]">Error Details:</strong>
            <p className="font-mono text-xs">{statusInfo.error_message}</p>
          </div>
        )}

        {/* Real-Time Progress Bar Display */}
        {(isGenerating || currentStatus === 'PROCESSING' || currentStatus === 'PENDING') && (
          <div className="p-6 bg-[#FFFFFF] border border-[#E5E5E5] rounded-xl space-y-4 shadow-xs">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3.5">
                <div className="w-9 h-9 rounded-full bg-[#FF0000]/10 flex items-center justify-center text-[#FF0000] animate-spin">
                  <RotateCw className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-[#0F0F0F]">
                    {statusInfo.stage === 'DOWNLOADING' ? 'Downloading YouTube Audio Stream...' :
                     statusInfo.stage === 'EXTRACTING_AUDIO' ? 'Extracting Audio Track...' :
                     statusInfo.stage === 'TRANSCRIBING' ? 'Transcribing with Faster-Whisper Model...' :
                     statusInfo.stage === 'SAVING' ? 'Saving Timestamped Segments...' :
                     'Queued for Background Worker...'}
                  </h3>
                  <p className="text-xs text-[#606060] mt-0.5">
                    {statusInfo.message || 'Processing video stream in background worker...'}
                  </p>
                </div>
              </div>

              <span className="text-sm font-bold font-mono text-[#FF0000] px-3 py-1 bg-[#FF0000]/10 rounded-full">
                {currentProgress}%
              </span>
            </div>

            {/* Visual YouTube Red Progress Bar */}
            <div className="w-full bg-[#E5E5E5] rounded-full h-2 overflow-hidden">
              <div 
                className="bg-[#FF0000] h-full rounded-full transition-all duration-500 ease-out"
                style={{ width: `${currentProgress}%` }}
              />
            </div>

            {/* Audio Duration Sub-details */}
            {statusInfo.total_duration_seconds > 0 && (
              <div className="flex items-center justify-between text-xs font-mono text-[#606060] pt-1 border-t border-[#E5E5E5]">
                <span>Processed: {formatTime(statusInfo.processed_seconds)} / {formatTime(statusInfo.total_duration_seconds)}</span>
                <span className="font-semibold text-[#0F0F0F]">Stage: {statusInfo.stage}</span>
              </div>
            )}
          </div>
        )}

        {/* Completed Transcript View */}
        {currentStatus === 'COMPLETED' && transcript && (
          <div className="space-y-4">
            
            {/* Transcript Search Bar */}
            <div className="bg-[#FFFFFF] border border-[#E5E5E5] p-4 rounded-xl space-y-3 shadow-xs">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-[#606060] flex items-center gap-2">
                  <Search className="w-3.5 h-3.5 text-[#0F0F0F]" /> Search Transcript
                </h3>
                <span className="text-xs font-semibold px-2.5 py-0.5 bg-[#F2F2F2] text-[#606060] rounded-full">
                  {filteredSegments.length} of {transcript.segments.length} segments
                </span>
              </div>

              <div className="relative flex items-center">
                <Search className="w-4 h-4 text-[#909090] absolute left-3.5" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search transcript text (e.g. algorithm, memory, binary)..."
                  className="w-full pl-10 pr-9 py-2 rounded-lg bg-[#FFFFFF] border border-[#CCCCCC] text-[#0F0F0F] placeholder-[#909090] text-xs focus:outline-none focus:border-[#0F0F0F]"
                />
                {searchQuery && (
                  <button
                    onClick={() => setSearchQuery('')}
                    className="absolute right-3 p-1 rounded hover:bg-[#F2F2F2] text-[#606060] hover:text-[#0F0F0F] cursor-pointer"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>

            {/* Timestamped Segment List */}
            <div className="bg-[#FFFFFF] border border-[#E5E5E5] p-4 sm:p-5 rounded-xl space-y-2.5 max-h-[600px] overflow-y-auto custom-scrollbar shadow-xs">
              {filteredSegments.length === 0 ? (
                <div className="py-8 text-center text-xs text-[#606060]">
                  No matching transcript segments found.
                </div>
              ) : (
                filteredSegments.map((seg, idx) => (
                  <div key={idx} className="p-3.5 rounded-lg bg-[#F9F9F9] border border-[#E5E5E5] hover:bg-[#F2F2F2] transition-colors flex flex-col sm:flex-row items-start gap-3">
                    <span className="text-xs font-mono font-semibold px-2.5 py-1 rounded bg-[#FFFFFF] border border-[#E5E5E5] text-[#0F0F0F] shrink-0">
                      {seg.TranscriptStart} - {seg.TranscriptEnd}
                    </span>
                    <p className="text-sm text-[#0F0F0F] leading-relaxed pt-0.5">
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
