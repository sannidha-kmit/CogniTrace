import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  ArrowLeft, 
  User, 
  BookOpen, 
  FileText, 
  Filter, 
  Database, 
  Search,
  Sparkles,
  Layers,
  ChevronDown,
  ChevronUp,
  Download,
  AlertCircle
} from 'lucide-react';

const EVENT_TYPES = [
  "ALL",
  "PLAY",
  "PAUSE",
  "SEEK_FORWARD",
  "SEEK_BACKWARD",
  "REPLAY",
  "SPEED_CHANGE",
  "VIDEO_COMPLETE"
];

export default function TeacherStudentDatasetView() {
  const { rollNumber } = useParams();
  const { user } = useAuth();

  const [activeTab, setActiveTab] = useState('telemetry'); // 'telemetry' | 'mapping'

  const [courses, setCourses] = useState([]);
  const [selectedCourseId, setSelectedCourseId] = useState("ALL");
  const [selectedEventType, setSelectedEventType] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState('');
  
  const [interactions, setInteractions] = useState([]);
  const [conceptMappings, setConceptMappings] = useState([]);
  const [difficultyData, setDifficultyData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');

  // Difficulty filters
  const [selectedDifficultyLevel, setSelectedDifficultyLevel] = useState("ALL");
  const [selectedNeedsRevision, setSelectedNeedsRevision] = useState("ALL");

  // Expandable row states for long transcript text
  const [expandedRows, setExpandedRows] = useState({});

  const toggleExpand = (rowId) => {
    setExpandedRows(prev => ({ ...prev, [rowId]: !prev[rowId] }));
  };

  // Helper for downloading files securely with auth token
  const handleExport = async (datasetType, format) => {
    const token = localStorage.getItem('cognitrace_token');
    let endpoint = "";
    
    // Construct exact endpoints based on Phase
    if (datasetType === "telemetry") {
      endpoint = `/api/v1/teacher/students/${rollNumber}/interactions/export?format=${format}&course_id=${selectedCourseId}&event_type=${selectedEventType}`;
    } else if (datasetType === "mapping") {
      endpoint = `/api/v1/teacher/students/${rollNumber}/concept-mappings/export?format=${format}&course_id=${selectedCourseId}&event_type=${selectedEventType}&search=${encodeURIComponent(searchQuery)}`;
    } else if (datasetType === "difficulty") {
      endpoint = `/api/v1/teacher/students/${rollNumber}/difficulty/export?format=${format}&course_id=${selectedCourseId}&search=${encodeURIComponent(searchQuery)}`;
      if (selectedDifficultyLevel !== "ALL") {
        endpoint += `&difficulty_level=${selectedDifficultyLevel}`;
      }
      if (selectedNeedsRevision !== "ALL") {
        endpoint += `&needs_revision=${selectedNeedsRevision === "Yes" ? "true" : "false"}`;
      }
    }

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
        
        // Extract filename from content-disposition header if available, else generic name
        const disposition = res.headers.get('content-disposition');
        let filename = `${datasetType}_export.${format}`;
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

  // Fetch available courses for this student
  const fetchStudentCourses = async () => {
    const token = localStorage.getItem('cognitrace_token');
    try {
      const res = await fetch(`/api/v1/teacher/students/${rollNumber}/courses`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setCourses(data);
      } else {
        const errData = await res.json();
        setErrorMessage(errData.detail || 'Access denied or failed to load student details.');
      }
    } catch (err) {
      setErrorMessage('Error connecting to server.');
    }
  };

  // Fetch Phase 5 interaction telemetry
  const fetchInteractions = async () => {
    setLoading(true);
    const token = localStorage.getItem('cognitrace_token');
    let url = `/api/v1/teacher/students/${rollNumber}/interactions?course_id=${selectedCourseId}&event_type=${selectedEventType}`;
    
    try {
      const res = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setInteractions(data);
      } else {
        const errData = await res.json();
        setErrorMessage(errData.detail || 'Failed to load student interaction dataset.');
      }
    } catch (err) {
      setErrorMessage('Network error loading interaction dataset.');
    } finally {
      setLoading(false);
    }
  };

  // Fetch Phase 7 concept-event mappings
  const fetchConceptMappings = async () => {
    setLoading(true);
    const token = localStorage.getItem('cognitrace_token');
    let url = `/api/v1/teacher/students/${rollNumber}/concept-mappings?course_id=${selectedCourseId}&event_type=${selectedEventType}&search=${encodeURIComponent(searchQuery)}`;
    
    try {
      const res = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setConceptMappings(data);
      } else {
        const errData = await res.json();
        setErrorMessage(errData.detail || 'Failed to load Phase 7 concept-event mappings.');
      }
    } catch (err) {
      setErrorMessage('Network error loading Phase 7 mapping dataset.');
    } finally {
      setLoading(false);
    }
  };

  // Fetch Phase 8 Difficulty data
  const fetchDifficulty = async () => {
    setLoading(true);
    const token = localStorage.getItem('cognitrace_token');
    let url = `/api/v1/teacher/students/${rollNumber}/difficulty?course_id=${selectedCourseId}&search=${encodeURIComponent(searchQuery)}`;
    
    if (selectedDifficultyLevel !== "ALL") {
      url += `&difficulty_level=${selectedDifficultyLevel}`;
    }
    if (selectedNeedsRevision !== "ALL") {
      url += `&needs_revision=${selectedNeedsRevision === "Yes" ? "true" : "false"}`;
    }

    try {
      const res = await fetch(url, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setDifficultyData(data);
      } else {
        const errData = await res.json();
        setErrorMessage(errData.detail || 'Failed to load Phase 8 difficulty dataset.');
      }
    } catch (err) {
      setErrorMessage('Network error loading Phase 8 difficulty dataset.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStudentCourses();
  }, [rollNumber]);

  useEffect(() => {
    if (activeTab === 'telemetry') {
      fetchInteractions();
    } else if (activeTab === 'mapping') {
      fetchConceptMappings();
    } else if (activeTab === 'difficulty') {
      fetchDifficulty();
    }
  }, [rollNumber, selectedCourseId, selectedEventType, activeTab, searchQuery, selectedDifficultyLevel, selectedNeedsRevision]);

  // Find active course for transcript link
  const activeCourse = courses.find(c => c.id === selectedCourseId);

  return (
    <div className="min-h-screen flex flex-col bg-slate-950">
      {/* Navbar */}
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link
            to="/teacher/students"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-400 hover:text-indigo-400 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Students
          </Link>
          <span className="text-xs font-mono text-indigo-400 px-3 py-1 rounded-full bg-indigo-950/60 border border-indigo-800/50">
            Subject: {user?.subject} ({user?.year})
          </span>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-8 space-y-6">
        
        {/* Header Panel */}
        <div className="glass-panel p-6 sm:p-8 rounded-2xl border border-slate-800 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="inline-flex items-center gap-1.5 text-xs font-mono text-indigo-400 bg-indigo-950/60 px-3 py-1 rounded-full border border-indigo-800/50">
                <User className="w-3.5 h-3.5" /> Student Roll Number: {rollNumber}
              </div>
              <h2 className="text-2xl font-bold text-white tracking-tight">
                Student Dataset: {rollNumber}
              </h2>
              <p className="text-xs text-slate-400">
                Academic Year: <strong className="text-white">{user?.year}</strong> | Authorized Subject: <strong className="text-indigo-400">{user?.subject}</strong>
              </p>
            </div>

            {/* Transcript Link Button */}
            {selectedCourseId !== 'ALL' && activeCourse && (
              <Link
                to={`/teacher/courses/${selectedCourseId}/transcript`}
                className="inline-flex items-center gap-2 py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs shadow-lg shadow-indigo-600/20 transition-all self-start sm:self-auto"
              >
                <FileText className="w-4 h-4" />
                <span>View Course Transcript</span>
              </Link>
            )}
          </div>

          {/* Dataset Switcher Tabs */}
          <div className="pt-3 flex items-center gap-3 border-t border-slate-800/80">
            <button
              onClick={() => setActiveTab('telemetry')}
              className={`inline-flex items-center gap-2 py-2 px-4 rounded-xl text-xs font-bold transition-all ${
                activeTab === 'telemetry'
                  ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20'
                  : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              <Database className="w-3.5 h-3.5" />
              <span>Phase 5: Interaction Telemetry</span>
            </button>

            <button
              onClick={() => setActiveTab('mapping')}
              className={`inline-flex items-center gap-2 py-2 px-4 rounded-xl text-xs font-bold transition-all ${
                activeTab === 'mapping'
                  ? 'bg-cyan-600 text-white shadow-lg shadow-cyan-600/20'
                  : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5 text-cyan-300" />
              <span>Phase 7: Concept-Event Mapping</span>
            </button>

            <button
              onClick={() => setActiveTab('difficulty')}
              className={`inline-flex items-center gap-2 py-2 px-4 rounded-xl text-xs font-bold transition-all ${
                activeTab === 'difficulty'
                  ? 'bg-rose-600 text-white shadow-lg shadow-rose-600/20'
                  : 'bg-slate-900 text-slate-400 hover:text-white border border-slate-800'
              }`}
            >
              <AlertCircle className="w-3.5 h-3.5 text-rose-300" />
              <span>Phase 8: Difficulty</span>
            </button>
          </div>

          {/* Filters Bar */}
          <div className="pt-3 border-t border-slate-800/60 grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* Course Filter */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
                <BookOpen className="w-3.5 h-3.5 text-indigo-400" /> Filter by Course
              </label>
              <select
                value={selectedCourseId}
                onChange={(e) => setSelectedCourseId(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-white text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="ALL">All Courses ({courses.length})</option>
                {courses.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.course_name} {c.has_events ? '(Watched)' : ''}
                  </option>
                ))}
              </select>
            </div>

            {/* Event Type Filter (Phase 5/7) */}
            {activeTab !== 'difficulty' && (
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
                  <Filter className="w-3.5 h-3.5 text-cyan-400" /> Filter by Event Type
                </label>
                <select
                  value={selectedEventType}
                  onChange={(e) => setSelectedEventType(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-white text-xs focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {EVENT_TYPES.map((et) => (
                    <option key={et} value={et}>{et}</option>
                  ))}
                </select>
              </div>
            )}

            {/* Difficulty Filters (Phase 8) */}
            {activeTab === 'difficulty' && (
              <>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
                    <AlertCircle className="w-3.5 h-3.5 text-rose-400" /> Difficulty Level
                  </label>
                  <select
                    value={selectedDifficultyLevel}
                    onChange={(e) => setSelectedDifficultyLevel(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-white text-xs focus:outline-none focus:ring-2 focus:ring-rose-500"
                  >
                    <option value="ALL">All Levels</option>
                    <option value="Easy">Easy</option>
                    <option value="Medium">Medium</option>
                    <option value="High">High</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-amber-400" /> Needs Revision
                  </label>
                  <select
                    value={selectedNeedsRevision}
                    onChange={(e) => setSelectedNeedsRevision(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-white text-xs focus:outline-none focus:ring-2 focus:ring-amber-500"
                  >
                    <option value="ALL">All</option>
                    <option value="Yes">Yes</option>
                    <option value="No">No</option>
                  </select>
                </div>
              </>
            )}

            {/* Search Filter for Phase 7 & 8 */}
            {(activeTab === 'mapping' || activeTab === 'difficulty') && (
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
                  <Search className="w-3.5 h-3.5 text-amber-400" /> Search text
                </label>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search..."
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-900 border border-slate-700 text-white text-xs placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            )}
          </div>
        </div>

        {/* Error message */}
        {errorMessage && (
          <div className="p-4 rounded-xl bg-rose-950/60 border border-rose-800/60 flex items-start gap-2.5 text-xs text-rose-300">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* TAB 1: Phase 5 Interaction Telemetry Dataset Table */}
        {activeTab === 'telemetry' && (
          <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Database className="w-5 h-5 text-indigo-400" /> Interaction Telemetry Dataset (Phase 5)
                </h3>
                <span className="text-xs font-mono text-slate-400">
                  {interactions.length} record(s) found
                </span>
              </div>
              
              {/* Export Controls */}
              {interactions.length > 0 && (
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Export:</span>
                  <button onClick={() => handleExport("telemetry", "csv")} className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition-colors flex items-center gap-1.5"><Download className="w-3.5 h-3.5"/> CSV</button>
                  <button onClick={() => handleExport("telemetry", "json")} className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition-colors flex items-center gap-1.5"><Download className="w-3.5 h-3.5"/> JSON</button>
                  <button onClick={() => handleExport("telemetry", "xlsx")} className="px-3 py-1.5 rounded-lg bg-indigo-900/60 border border-indigo-700 text-xs font-semibold text-indigo-200 hover:text-white hover:bg-indigo-800 transition-colors flex items-center gap-1.5"><Download className="w-3.5 h-3.5"/> Excel</button>
                </div>
              )}
            </div>

            {loading ? (
              <div className="py-16 text-center text-xs font-mono text-slate-500">Loading student dataset telemetry...</div>
            ) : interactions.length === 0 ? (
              <div className="py-16 text-center space-y-2 border border-slate-800/60 rounded-xl bg-slate-900/40">
                <Database className="w-10 h-10 text-slate-600 mx-auto" />
                <p className="text-sm font-semibold text-slate-300">No interaction data collected yet for this student.</p>
              </div>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-slate-800">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-900/80 border-b border-slate-800 text-slate-400 font-mono text-[11px]">
                      <th className="p-3">StudentID</th>
                      <th className="p-3">StudentName</th>
                      <th className="p-3">CourseSubject</th>
                      <th className="p-3">CourseName</th>
                      <th className="p-3">EventType</th>
                      <th className="p-3">EventTimestamp</th>
                      <th className="p-3">EventDuration</th>
                      <th className="p-3">PlaybackSpeed</th>
                      <th className="p-3">PauseReason</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-200">
                    {interactions.map((ev, index) => (
                      <tr key={`${ev.id}-${index}`} className="hover:bg-slate-900/40 transition-colors">
                        <td className="p-3 font-mono text-cyan-400">{ev.StudentID}</td>
                        <td className="p-3 font-semibold text-white">{ev.StudentName}</td>
                        <td className="p-3">{ev.CourseSubject}</td>
                        <td className="p-3 font-medium text-slate-100">{ev.CourseName}</td>
                        <td className="p-3">
                          <span className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold ${
                            ev.EventType === 'PAUSE' ? 'bg-amber-950 text-amber-400 border border-amber-800/50' :
                            ev.EventType === 'PLAY' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/50' :
                            ev.EventType === 'VIDEO_COMPLETE' ? 'bg-cyan-950 text-cyan-400 border border-cyan-800/50' :
                            'bg-indigo-950 text-indigo-400 border border-indigo-800/50'
                          }`}>
                            {ev.EventType}
                          </span>
                        </td>
                        <td className="p-3 font-mono text-amber-300">{ev.EventTimestamp}</td>
                        <td className="p-3 font-mono">{ev.EventDuration !== null && ev.EventDuration !== undefined ? `${ev.EventDuration}s` : '—'}</td>
                        <td className="p-3 font-mono">{ev.PlaybackSpeed !== null && ev.PlaybackSpeed !== undefined ? `${ev.PlaybackSpeed}x` : '—'}</td>
                        <td className="p-3 italic text-slate-400">{ev.PauseReason || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: Phase 7 Concept-Event Mapping Dataset Table */}
        {activeTab === 'mapping' && (
          <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-cyan-400" /> Concept-Event Mapping Dataset (Phase 7)
                </h3>
                <span className="text-xs font-mono text-slate-400">
                  {conceptMappings.length} record(s) mapped
                </span>
              </div>
              
              {/* Export Controls */}
              {conceptMappings.length > 0 && (
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Export:</span>
                  <button onClick={() => handleExport("mapping", "csv")} className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition-colors flex items-center gap-1.5"><Download className="w-3.5 h-3.5"/> CSV</button>
                  <button onClick={() => handleExport("mapping", "json")} className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition-colors flex items-center gap-1.5"><Download className="w-3.5 h-3.5"/> JSON</button>
                  <button onClick={() => handleExport("mapping", "xlsx")} className="px-3 py-1.5 rounded-lg bg-cyan-900/60 border border-cyan-700 text-xs font-semibold text-cyan-200 hover:text-white hover:bg-cyan-800 transition-colors flex items-center gap-1.5"><Download className="w-3.5 h-3.5"/> Excel</button>
                </div>
              )}
            </div>

            {loading ? (
              <div className="py-16 text-center text-xs font-mono text-slate-500">Mapping interaction timestamps to course transcripts and concepts...</div>
            ) : conceptMappings.length === 0 ? (
              <div className="py-16 text-center space-y-2 border border-slate-800/60 rounded-xl bg-slate-900/40">
                <Layers className="w-10 h-10 text-slate-600 mx-auto" />
                <p className="text-sm font-semibold text-slate-300">No concept-event mappings available yet.</p>
                <p className="text-xs text-slate-500">Ensure course transcript (Phase 4) and concepts (Phase 6) have been generated for this course.</p>
              </div>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-slate-800">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-900/80 border-b border-slate-800 text-slate-400 font-mono text-[11px]">
                      <th className="p-3">StudentID</th>
                      <th className="p-3">StudentName</th>
                      <th className="p-3">CourseSubject</th>
                      <th className="p-3">CourseName</th>
                      <th className="p-3">EventType</th>
                      <th className="p-3">EventTimestamp</th>
                      <th className="p-3 min-w-[240px]">Transcript</th>
                      <th className="p-3">Concept</th>
                      <th className="p-3">Prerequisite</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-200">
                    {conceptMappings.map((m, index) => {
                      const isExpanded = expandedRows[m.id];
                      const isLong = m.Transcript && m.Transcript.length > 80;
                      return (
                        <tr key={`${m.id}-${index}`} className="hover:bg-slate-900/40 transition-colors">
                          <td className="p-3 font-mono text-cyan-400">{m.StudentID}</td>
                          <td className="p-3 font-semibold text-white">{m.StudentName}</td>
                          <td className="p-3">{m.CourseSubject}</td>
                          <td className="p-3 font-medium text-slate-100">{m.CourseName}</td>
                          <td className="p-3">
                            <span className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold ${
                              m.EventType === 'PAUSE' ? 'bg-amber-950 text-amber-400 border border-amber-800/50' :
                              m.EventType === 'PLAY' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/50' :
                              m.EventType === 'VIDEO_COMPLETE' ? 'bg-cyan-950 text-cyan-400 border border-cyan-800/50' :
                              'bg-indigo-950 text-indigo-400 border border-indigo-800/50'
                            }`}>
                              {m.EventType}
                            </span>
                          </td>
                          <td className="p-3 font-mono text-amber-300">{m.EventTimestamp}</td>
                          
                          {/* Transcript segment with expandable view */}
                          <td className="p-3 text-slate-300 leading-relaxed">
                            {isLong ? (
                              <div>
                                <span>{isExpanded ? m.Transcript : `${m.Transcript.substring(0, 80)}...`}</span>
                                <button
                                  onClick={() => toggleExpand(m.id)}
                                  className="ml-1 text-[11px] font-mono text-indigo-400 hover:underline inline-flex items-center gap-0.5"
                                >
                                  {isExpanded ? <>Less <ChevronUp className="w-3 h-3" /></> : <>More <ChevronDown className="w-3 h-3" /></>}
                                </button>
                              </div>
                            ) : (
                              <span>{m.Transcript}</span>
                            )}
                          </td>

                          <td className="p-3 font-semibold text-indigo-300 bg-indigo-950/20">{m.Concept}</td>
                          <td className="p-3 font-mono text-slate-400">{m.Prerequisite || 'None'}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* TAB 3: Phase 8 Difficulty Dataset Table */}
        {activeTab === 'difficulty' && (
          <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <AlertCircle className="w-5 h-5 text-rose-400" /> Difficulty Dataset (Phase 8)
                </h3>
                <span className="text-xs font-mono text-slate-400">
                  {difficultyData.length} concept(s) evaluated
                </span>
              </div>
              
              {/* Export Controls */}
              {difficultyData.length > 0 && (
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Export:</span>
                  <button onClick={() => handleExport("difficulty", "csv")} className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition-colors flex items-center gap-1.5"><Download className="w-3.5 h-3.5"/> CSV</button>
                  <button onClick={() => handleExport("difficulty", "json")} className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-xs font-semibold text-slate-300 hover:text-white hover:bg-slate-800 transition-colors flex items-center gap-1.5"><Download className="w-3.5 h-3.5"/> JSON</button>
                  <button onClick={() => handleExport("difficulty", "xlsx")} className="px-3 py-1.5 rounded-lg bg-rose-900/60 border border-rose-700 text-xs font-semibold text-rose-200 hover:text-white hover:bg-rose-800 transition-colors flex items-center gap-1.5"><Download className="w-3.5 h-3.5"/> Excel</button>
                </div>
              )}
            </div>

            {loading ? (
              <div className="py-16 text-center text-xs font-mono text-slate-500">Deriving difficulty metrics from real interaction telemetry...</div>
            ) : difficultyData.length === 0 ? (
              <div className="py-16 text-center space-y-2 border border-slate-800/60 rounded-xl bg-slate-900/40">
                <AlertCircle className="w-10 h-10 text-slate-600 mx-auto" />
                <p className="text-sm font-semibold text-slate-300">No difficulty data derived yet.</p>
                <p className="text-xs text-slate-500">Difficulty is generated only when Phase 5 interactions map to Phase 6 concepts.</p>
              </div>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-slate-800">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-slate-900/80 border-b border-slate-800 text-slate-400 font-mono text-[11px] whitespace-nowrap">
                      <th className="p-3">StudentID</th>
                      <th className="p-3">StudentName</th>
                      <th className="p-3">CourseSubject</th>
                      <th className="p-3">CourseName</th>
                      <th className="p-3">Concept</th>
                      <th className="p-3">ReplayCount</th>
                      <th className="p-3">PauseCount</th>
                      <th className="p-3">SeekBackCount</th>
                      <th className="p-3">SeekFwdCount</th>
                      <th className="p-3">UndPauseCount</th>
                      <th className="p-3">DiffScore</th>
                      <th className="p-3">DiffLevel</th>
                      <th className="p-3">NeedsRev</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-200">
                    {difficultyData.map((d, index) => (
                      <tr key={`${d.id}-${index}`} className="hover:bg-slate-900/40 transition-colors whitespace-nowrap">
                        <td className="p-3 font-mono text-cyan-400">{d.StudentID}</td>
                        <td className="p-3 font-semibold text-white">{d.StudentName}</td>
                        <td className="p-3">{d.CourseSubject}</td>
                        <td className="p-3 font-medium text-slate-100">{d.CourseName}</td>
                        <td className="p-3 font-semibold text-indigo-300 bg-indigo-950/20">{d.Concept}</td>
                        <td className="p-3 font-mono">{d.ReplayCount}</td>
                        <td className="p-3 font-mono">{d.PauseCount}</td>
                        <td className="p-3 font-mono">{d.SeekBackwardCount}</td>
                        <td className="p-3 font-mono">{d.SeekForwardCount}</td>
                        <td className="p-3 font-mono text-amber-300">{d.UnderstandPauseCount}</td>
                        <td className="p-3 font-mono font-bold text-white">{d.DifficultyScore.toFixed(1)}</td>
                        <td className="p-3">
                          <span className={`px-2 py-0.5 rounded font-mono text-[10px] font-bold ${
                            d.DifficultyLevel === 'High' ? 'bg-rose-950 text-rose-400 border border-rose-800/50' :
                            d.DifficultyLevel === 'Medium' ? 'bg-amber-950 text-amber-400 border border-amber-800/50' :
                            'bg-emerald-950 text-emerald-400 border border-emerald-800/50'
                          }`}>
                            {d.DifficultyLevel}
                          </span>
                        </td>
                        <td className="p-3">
                          {d.NeedsRevision ? (
                            <span className="text-rose-400 font-bold">Yes</span>
                          ) : (
                            <span className="text-slate-500">No</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

      </main>
    </div>
  );
}
