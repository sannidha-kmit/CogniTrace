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
  BookOpen,
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
    <div className="min-h-screen flex flex-col bg-slate-950">
      {/* Navbar */}
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link
            to="/teacher/courses"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-400 hover:text-indigo-400 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Courses
          </Link>
          <div className="flex items-center space-x-2 text-xs font-mono text-indigo-400 px-3 py-1 rounded-full bg-indigo-950/60 border border-indigo-800/50">
            <Layers className="w-3.5 h-3.5" />
            <span>Course Concept Dataset</span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-8 space-y-6">
        
        {loading ? (
          <div className="py-16 text-center text-xs font-mono text-slate-500">Loading course concept details...</div>
        ) : course ? (
          <div className="space-y-6">

            {/* Course Header Banner */}
            <div className="glass-panel p-6 sm:p-8 rounded-2xl border border-slate-800 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="space-y-1">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950 text-indigo-400 border border-indigo-800/50">
                    {course.subject} ({course.year})
                  </span>
                  <h2 className="text-2xl font-bold text-white tracking-tight mt-1">{course.course_name}</h2>
                  <p className="text-xs text-slate-400">
                    Teacher: <strong className="text-white">{course.teacher_name}</strong>
                  </p>
                </div>

                {/* Action Controls */}
                <div className="flex items-center gap-3">
                  <Link
                    to={`/teacher/courses/${courseId}/transcript`}
                    className="inline-flex items-center gap-1.5 py-2 px-3.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 text-xs font-medium transition-colors"
                  >
                    <FileText className="w-3.5 h-3.5 text-indigo-400" />
                    <span>View Transcript</span>
                  </Link>

                  {conceptStatus === 'NOT_GENERATED' || conceptStatus === 'FAILED' ? (
                    <button
                      type="button"
                      onClick={handleExtractConcepts}
                      disabled={actionLoading || transcriptStatus !== 'COMPLETED'}
                      className="inline-flex items-center gap-2 py-2.5 px-4 rounded-xl bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-bold text-xs shadow-lg shadow-indigo-600/20 transition-all"
                    >
                      <Sparkles className="w-4 h-4" />
                      <span>{actionLoading ? 'Queuing Extraction...' : 'Extract Concepts'}</span>
                    </button>
                  ) : conceptStatus === 'PENDING' || conceptStatus === 'PROCESSING' ? (
                    <div className="inline-flex items-center gap-2 py-2 px-3.5 rounded-xl bg-amber-950/60 border border-amber-800/50 text-amber-300 text-xs font-mono">
                      <RefreshCw className="w-3.5 h-3.5 animate-spin text-amber-400" />
                      <span>Concept Extraction: {conceptStatus}...</span>
                    </div>
                  ) : (
                    <div className="inline-flex items-center gap-1.5 py-2 px-3.5 rounded-xl bg-emerald-950/60 border border-emerald-800/50 text-emerald-400 text-xs font-bold font-mono">
                      <CheckCircle2 className="w-4 h-4" />
                      <span>Concepts Extracted</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Status Notice if Transcript is Not Completed */}
              {transcriptStatus !== 'COMPLETED' && (
                <div className="p-3.5 rounded-xl bg-amber-950/40 border border-amber-800/50 flex items-center gap-2 text-xs text-amber-300">
                  <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
                  <span>Transcript required before concept extraction. Please generate transcript first.</span>
                </div>
              )}
            </div>

            {/* Error Banner */}
            {errorMessage && (
              <div className="p-4 rounded-xl bg-rose-950/60 border border-rose-800/60 flex items-start gap-2.5 text-xs text-rose-300">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Search & Filter Bar */}
            {conceptStatus === 'COMPLETED' && (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="relative">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    placeholder="Search concepts..."
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-white placeholder-slate-500 text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div className="flex items-center gap-2">
                  <Filter className="w-4 h-4 text-indigo-400 shrink-0" />
                  <select
                    value={difficultyFilter}
                    onChange={(e) => setDifficultyFilter(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-white text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="ALL">All Content Difficulty Levels</option>
                    <option value="EASY">Easy</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="HARD">Hard</option>
                  </select>
                </div>
              </div>
            )}

            {/* Concept Timeline Visualization */}
            {conceptStatus === 'COMPLETED' && segments.length > 0 && (
              <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-3">
                <h3 className="text-xs font-bold text-slate-400 font-mono flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5 text-indigo-400" /> Concept Sequence Timeline
                </h3>
                <div className="flex items-center gap-2 overflow-x-auto py-2">
                  {segments.map((seg, idx) => (
                    <div 
                      key={idx} 
                      className="shrink-0 px-3.5 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs space-y-0.5 hover:border-indigo-500/50 transition-colors"
                    >
                      <span className="text-[10px] font-mono text-cyan-400 block">{seg.ConceptStart} - {seg.ConceptEnd}</span>
                      <span className="font-semibold text-white block">{seg.Concept}</span>
                      <span className="text-[9px] font-mono text-slate-400 block">Diff: {seg.DifficultyLevel}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Concept Dataset Table */}
            <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h3 className="text-base font-bold text-white flex items-center gap-2">
                    <Layers className="w-5 h-5 text-indigo-400" /> Derived Concept Segments Dataset
                  </h3>
                  <span className="text-xs font-mono text-slate-400">
                    {filteredSegments.length} concept segment(s)
                  </span>
                </div>
                
                {/* Export Controls */}
                {conceptStatus === 'COMPLETED' && segments.length > 0 && (
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Export Concepts:</span>
                    <button onClick={() => handleExport("csv")} className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition-colors flex items-center gap-1.5"><Download className="w-3.5 h-3.5"/> CSV</button>
                    <button onClick={() => handleExport("json")} className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition-colors flex items-center gap-1.5"><Download className="w-3.5 h-3.5"/> JSON</button>
                    <button onClick={() => handleExport("xlsx")} className="px-3 py-1.5 rounded-lg bg-indigo-900/60 border border-indigo-700 text-xs font-semibold text-indigo-200 hover:text-white hover:bg-indigo-800 transition-colors flex items-center gap-1.5"><Download className="w-3.5 h-3.5"/> Excel</button>
                  </div>
                )}
              </div>

              {conceptStatus === 'NOT_GENERATED' ? (
                <div className="py-16 text-center space-y-2 border border-slate-800/60 rounded-xl bg-slate-900/40">
                  <Sparkles className="w-10 h-10 text-slate-600 mx-auto" />
                  <p className="text-sm font-semibold text-slate-300">Concepts have not been extracted yet.</p>
                  <p className="text-xs text-slate-500">Click [ Extract Concepts ] to process the course transcript.</p>
                </div>
              ) : conceptStatus === 'PENDING' || conceptStatus === 'PROCESSING' ? (
                <div className="py-16 text-center space-y-3">
                  <RefreshCw className="w-8 h-8 text-amber-400 animate-spin mx-auto" />
                  <p className="text-sm font-semibold text-white">Extracting Educational Concepts...</p>
                  <p className="text-xs text-slate-400 font-mono">Standby process in concept_worker process.</p>
                </div>
              ) : filteredSegments.length === 0 ? (
                <div className="py-12 text-center text-xs text-slate-400 border border-slate-800 rounded-xl">
                  No concept segments matching search filter.
                </div>
              ) : (
                <div className="overflow-x-auto rounded-xl border border-slate-800">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="bg-slate-900/80 border-b border-slate-800 text-slate-400 font-mono text-[11px]">
                        <th className="p-3">Concept Name</th>
                        <th className="p-3">ConceptStart</th>
                        <th className="p-3">ConceptEnd</th>
                        <th className="p-3">Prerequisite</th>
                        <th className="p-3">DifficultyLevel</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 text-slate-200">
                      {filteredSegments.map((seg, idx) => (
                        <tr key={idx} className="hover:bg-slate-900/40 transition-colors">
                          <td className="p-3 font-semibold text-white">{seg.Concept}</td>
                          <td className="p-3 font-mono text-cyan-400">{seg.ConceptStart}</td>
                          <td className="p-3 font-mono text-cyan-400">{seg.ConceptEnd}</td>
                          <td className="p-3 font-mono text-slate-300">{seg.Prerequisite || 'None'}</td>
                          <td className="p-3">
                            <span className={`px-2.5 py-0.5 rounded font-mono text-[10px] font-bold ${
                              seg.DifficultyLevel === 'Hard' ? 'bg-rose-950 text-rose-400 border border-rose-800/50' :
                              seg.DifficultyLevel === 'Medium' ? 'bg-amber-950 text-amber-400 border border-amber-800/50' :
                              'bg-emerald-950 text-emerald-400 border border-emerald-800/50'
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
