import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  ArrowLeft, 
  Sparkles, 
  Search, 
  Filter, 
  CheckCircle2, 
  Clock, 
  AlertCircle, 
  RefreshCw, 
  FileText,
  Layers,
  Download
} from 'lucide-react';

export default function TeacherConceptView() {
  const { courseId } = useParams();
  const { user } = useAuth();

  const [course, setCourse] = useState(null);
  const [transcriptStatus, setTranscriptStatus] = useState('LOADING');
  const [conceptStatus, setConceptStatus] = useState('NOT_GENERATED');
  
  const [segments, setSegments] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [difficultyFilter, setDifficultyFilter] = useState('ALL');

  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  // Fetch course, transcript status, and concept status
  const fetchCourseAndStatus = async () => {
    const token = localStorage.getItem('cognitrace_token');
    try {
      // 1. Course Details
      const cRes = await fetch(`/api/v1/courses/${courseId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (cRes.ok) {
        const cData = await cRes.json();
        setCourse(cData);
      } else {
        setErrorMessage('Failed to load course details.');
        return;
      }

      // 2. Transcript Status
      const tRes = await fetch(`/api/v1/teacher/courses/${courseId}/transcript/status`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (tRes.ok) {
        const tData = await tRes.json();
        setTranscriptStatus(tData.status);
      }

      // 3. Concept Status & Segments
      const sRes = await fetch(`/api/v1/teacher/courses/${courseId}/concepts/status`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (sRes.ok) {
        const sData = await sRes.json();
        setConceptStatus(sData.status);

        if (sData.status === 'COMPLETED') {
          fetchConcepts();
        }
      }
    } catch (err) {
      setErrorMessage('Network error loading concept extraction data.');
    } finally {
      setLoading(false);
    }
  };

  const fetchConcepts = async () => {
    const token = localStorage.getItem('cognitrace_token');
    try {
      const res = await fetch(`/api/v1/teacher/courses/${courseId}/concepts`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSegments(data.segments || []);
      }
    } catch (err) {
      console.error('Failed to fetch concept segments:', err);
    }
  };

  useEffect(() => {
    fetchCourseAndStatus();
  }, [courseId]);

  // Poll status while PENDING or PROCESSING
  useEffect(() => {
    let interval = null;
    if (conceptStatus === 'PENDING' || conceptStatus === 'PROCESSING') {
      interval = setInterval(() => {
        fetchCourseAndStatus();
      }, 3000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [conceptStatus]);

  // Trigger concept extraction
  const handleExtractConcepts = async () => {
    setActionLoading(true);
    setErrorMessage('');
    const token = localStorage.getItem('cognitrace_token');
    try {
      const res = await fetch(`/api/v1/teacher/courses/${courseId}/concepts/extract`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (res.ok || res.status === 202) {
        const data = await res.json();
        setConceptStatus(data.status);
      } else {
        const errData = await res.json();
        setErrorMessage(errData.detail || 'Failed to queue concept extraction.');
      }
    } catch (err) {
      setErrorMessage('Error connecting to server.');
    } finally {
      setActionLoading(false);
    }
  };

  // Filter segments based on search query and difficulty
  const filteredSegments = segments.filter((s) => {
    const matchesSearch = s.Concept.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          (s.Prerequisite && s.Prerequisite.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesDiff = difficultyFilter === 'ALL' || s.DifficultyLevel.toUpperCase() === difficultyFilter.toUpperCase();
    return matchesSearch && matchesDiff;
  });

  const handleExport = async (format) => {
    const token = localStorage.getItem('cognitrace_token');
    const endpoint = `/api/v1/teacher/courses/${courseId}/concepts/export?format=${format}`;
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
        let filename = `concepts_export.${format}`;
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

  return (
    <div className="min-h-screen flex flex-col bg-[#F9F9F9] text-[#0F0F0F]">
      {/* Header */}
      <header className="border-b border-[#E5E5E5] bg-[#FFFFFF] sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <Link
            to="/teacher/courses"
            className="inline-flex items-center gap-2 text-sm font-medium text-[#606060] hover:text-[#0F0F0F] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Content
          </Link>
          <div className="flex items-center space-x-2 text-xs font-semibold px-3 py-1 bg-[#F2F2F2] text-[#606060] rounded-full">
            <Layers className="w-3.5 h-3.5 text-[#FF0000]" />
            <span>Concept Map Dataset</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 space-y-6">
        
        {loading ? (
          <div className="py-16 text-center text-sm text-[#606060]">Loading course concepts...</div>
        ) : course ? (
          <div className="space-y-6">

            {/* Course Header Banner */}
            <div className="bg-[#FFFFFF] border border-[#E5E5E5] rounded-xl p-6 space-y-4 shadow-xs">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="space-y-1">
                  <span className="text-[11px] font-semibold px-2.5 py-0.5 bg-[#F2F2F2] text-[#0F0F0F] rounded-md">
                    {course.subject} ({course.year})
                  </span>
                  <h1 className="text-2xl font-bold text-[#0F0F0F] tracking-tight mt-1">{course.course_name}</h1>
                  <p className="text-xs text-[#606060]">
                    Instructor: <span className="font-semibold text-[#0F0F0F]">{course.teacher_name}</span>
                  </p>
                </div>

                {/* Action Controls */}
                <div className="flex items-center gap-3 flex-wrap">
                  <Link
                    to={`/teacher/courses/${courseId}/transcript`}
                    className="yt-btn-secondary py-2 px-3.5 text-xs font-semibold flex items-center gap-2"
                  >
                    <FileText className="w-3.5 h-3.5 text-[#606060]" />
                    <span>View Transcript</span>
                  </Link>

                  {conceptStatus === 'NOT_GENERATED' || conceptStatus === 'FAILED' ? (
                    <button
                      type="button"
                      onClick={handleExtractConcepts}
                      disabled={actionLoading || transcriptStatus !== 'COMPLETED'}
                      className="yt-btn-primary py-2 px-4 text-xs font-semibold flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <Sparkles className="w-4 h-4" />
                      <span>{actionLoading ? 'Queuing Extraction...' : 'Extract Concepts'}</span>
                    </button>
                  ) : conceptStatus === 'PENDING' || conceptStatus === 'PROCESSING' ? (
                    <div className="inline-flex items-center gap-2 py-1.5 px-3 rounded-full bg-[#FFF8E1] text-[#F57F17] text-xs font-semibold animate-pulse">
                      <RefreshCw className="w-3.5 h-3.5 animate-spin text-[#F57F17]" />
                      <span>Extracting Concepts: {conceptStatus}...</span>
                    </div>
                  ) : (
                    <div className="inline-flex items-center gap-1.5 py-1.5 px-3 rounded-full bg-[#E8F5E9] text-[#2E7D32] text-xs font-semibold">
                      <CheckCircle2 className="w-3.5 h-3.5 text-[#2E7D32]" />
                      <span>Concepts Extracted</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Status Notice if Transcript is Not Completed */}
              {transcriptStatus !== 'COMPLETED' && (
                <div className="p-3.5 rounded-lg bg-[#FFEBEE] border border-[#FFCDD2] flex items-center gap-2 text-xs text-[#C62828]">
                  <AlertCircle className="w-4 h-4 text-[#C62828] shrink-0" />
                  <span>Transcript is required before concept extraction. Please generate transcript first.</span>
                </div>
              )}
            </div>

            {/* Error Banner */}
            {errorMessage && (
              <div className="p-4 rounded-xl bg-[#FFEBEE] border border-[#FFCDD2] flex items-start gap-2.5 text-xs text-[#C62828]">
                <AlertCircle className="w-4 h-4 text-[#C62828] shrink-0 mt-0.5" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Search & Filter Bar */}
            {conceptStatus === 'COMPLETED' && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="relative">
                  <Search className="w-4 h-4 text-[#909090] absolute left-3.5 top-3" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search concepts or prerequisites..."
                    className="w-full pl-10 pr-4 py-2 rounded-lg bg-[#FFFFFF] border border-[#CCCCCC] text-[#0F0F0F] placeholder-[#909090] text-xs focus:outline-none focus:border-[#0F0F0F]"
                  />
                </div>

                <div className="flex items-center gap-2">
                  <Filter className="w-4 h-4 text-[#606060] shrink-0" />
                  <select
                    value={difficultyFilter}
                    onChange={(e) => setDifficultyFilter(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-lg bg-[#FFFFFF] border border-[#CCCCCC] text-[#0F0F0F] text-xs focus:outline-none focus:border-[#0F0F0F] cursor-pointer"
                  >
                    <option value="ALL">All Difficulty Levels</option>
                    <option value="EASY">Easy</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="HARD">Hard</option>
                  </select>
                </div>
              </div>
            )}

            {/* Concept Timeline Visualization */}
            {conceptStatus === 'COMPLETED' && segments.length > 0 && (
              <div className="bg-[#FFFFFF] border border-[#E5E5E5] p-5 rounded-xl space-y-3 shadow-xs">
                <h3 className="text-xs font-semibold text-[#606060] uppercase tracking-wider flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-[#0F0F0F]" /> Concept Timeline Sequence
                </h3>
                <div className="flex items-center gap-3 overflow-x-auto py-1 custom-scrollbar">
                  {segments.map((seg, idx) => (
                    <div 
                      key={idx} 
                      className="shrink-0 px-3.5 py-2 rounded-lg bg-[#F9F9F9] border border-[#E5E5E5] text-xs space-y-1 hover:border-[#CCCCCC] transition-colors"
                    >
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-[#FFFFFF] border border-[#E5E5E5] text-[#0F0F0F] font-semibold inline-block">{seg.ConceptStart} - {seg.ConceptEnd}</span>
                      <span className="font-semibold text-[#0F0F0F] block">{seg.Concept}</span>
                      <span className="text-[11px] text-[#606060] block">Diff: {seg.DifficultyLevel}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Concept Dataset Table */}
            <div className="bg-[#FFFFFF] border border-[#E5E5E5] p-6 rounded-xl space-y-4 shadow-xs">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-[#E5E5E5]">
                <div>
                  <h3 className="text-lg font-bold text-[#0F0F0F] flex items-center gap-2">
                    <Layers className="w-5 h-5 text-[#FF0000]" /> Extracted Concept Segments
                  </h3>
                  <span className="text-xs font-semibold px-2.5 py-0.5 bg-[#F2F2F2] text-[#606060] rounded-full mt-1 inline-block">
                    {filteredSegments.length} concept segment(s)
                  </span>
                </div>
                
                {/* Export Controls */}
                {conceptStatus === 'COMPLETED' && segments.length > 0 && (
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-semibold text-[#606060] uppercase tracking-wider">Export:</span>
                    <button onClick={() => handleExport("csv")} className="yt-btn-secondary py-1.5 px-3 text-xs font-semibold flex items-center gap-1.5"><Download className="w-3.5 h-3.5 text-[#606060]"/> CSV</button>
                    <button onClick={() => handleExport("json")} className="yt-btn-secondary py-1.5 px-3 text-xs font-semibold flex items-center gap-1.5"><Download className="w-3.5 h-3.5 text-[#606060]"/> JSON</button>
                    <button onClick={() => handleExport("xlsx")} className="yt-btn-primary py-1.5 px-3 text-xs font-semibold flex items-center gap-1.5"><Download className="w-3.5 h-3.5"/> Excel</button>
                  </div>
                )}
              </div>

              {conceptStatus === 'NOT_GENERATED' ? (
                <div className="py-16 text-center space-y-2 border border-[#E5E5E5] rounded-xl bg-[#FAFAFA]">
                  <Sparkles className="w-10 h-10 text-[#909090] mx-auto" />
                  <p className="text-sm font-semibold text-[#0F0F0F]">Concepts have not been extracted yet.</p>
                  <p className="text-xs text-[#606060]">Click [ Extract Concepts ] to process the course transcript.</p>
                </div>
              ) : conceptStatus === 'PENDING' || conceptStatus === 'PROCESSING' ? (
                <div className="py-16 text-center space-y-3">
                  <RefreshCw className="w-8 h-8 text-[#FF0000] animate-spin mx-auto" />
                  <p className="text-sm font-semibold text-[#0F0F0F]">Extracting Educational Concepts...</p>
                  <p className="text-xs text-[#606060] font-mono">Running segmentation adapter in background worker.</p>
                </div>
              ) : filteredSegments.length === 0 ? (
                <div className="py-12 text-center text-xs text-[#606060] border border-[#E5E5E5] rounded-xl">
                  No concept segments matching search filter.
                </div>
              ) : (
                <div className="overflow-x-auto rounded-xl border border-[#E5E5E5]">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-[#F9F9F9] border-b border-[#E5E5E5] text-[#606060] text-xs font-semibold uppercase tracking-wider">
                        <th className="p-3.5">Concept Name</th>
                        <th className="p-3.5">Start Time</th>
                        <th className="p-3.5">End Time</th>
                        <th className="p-3.5">Prerequisite</th>
                        <th className="p-3.5">Difficulty</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#E5E5E5] text-[#0F0F0F]">
                      {filteredSegments.map((seg, idx) => (
                        <tr key={idx} className="hover:bg-[#F9F9F9] transition-colors">
                          <td className="p-3.5 font-semibold text-[#0F0F0F]">{seg.Concept}</td>
                          <td className="p-3.5 font-mono text-[#606060]">{seg.ConceptStart}</td>
                          <td className="p-3.5 font-mono text-[#606060]">{seg.ConceptEnd}</td>
                          <td className="p-3.5 text-[#606060]">{seg.Prerequisite || 'None'}</td>
                          <td className="p-3.5">
                            <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                              seg.DifficultyLevel === 'Hard' ? 'bg-[#FFEBEE] text-[#C62828]' :
                              seg.DifficultyLevel === 'Medium' ? 'bg-[#FFF8E1] text-[#F57F17]' :
                              'bg-[#E8F5E9] text-[#2E7D32]'
                            }`}>
                              {seg.DifficultyLevel}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

          </div>
        ) : null}

      </main>
    </div>
  );
}
