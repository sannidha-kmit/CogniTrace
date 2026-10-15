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
  AlertCircle,
  Award,
  CheckCircle2,
  XCircle,
  BarChart3
} from 'lucide-react';
import { getStudentQuizResults } from '../services/teacherQuizService';

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

  const [activeTab, setActiveTab] = useState('telemetry'); // 'telemetry' | 'mapping' | 'difficulty' | 'adaptive_quiz'

  const [courses, setCourses] = useState([]);
  const [selectedCourseId, setSelectedCourseId] = useState("ALL");
  const [selectedEventType, setSelectedEventType] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState('');
  
  const [interactions, setInteractions] = useState([]);
  const [conceptMappings, setConceptMappings] = useState([]);
  const [difficultyData, setDifficultyData] = useState([]);
  const [quizResults, setQuizResults] = useState([]);
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

  const fetchQuizResults = async () => {
    setLoading(true);
    setErrorMessage('');
    try {
      const token = localStorage.getItem('cognitrace_token');
      const data = await getStudentQuizResults(rollNumber, selectedCourseId, token);
      setQuizResults(data);
    } catch (err) {
      setErrorMessage('Network error loading Adaptive Quiz Results.');
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
    } else if (activeTab === 'adaptive_quiz') {
      fetchQuizResults();
    }
  }, [rollNumber, selectedCourseId, selectedEventType, activeTab, searchQuery, selectedDifficultyLevel, selectedNeedsRevision]);

  // Find active course for transcript link
  const activeCourse = courses.find(c => c.id === selectedCourseId);

  return (
    <div className="min-h-screen flex flex-col bg-[#F9F9F9] text-[#0F0F0F]">
      {/* Header */}
      <header className="border-b border-[#E5E5E5] bg-[#FFFFFF] sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <Link
            to="/teacher/students"
            className="inline-flex items-center gap-2 text-sm font-medium text-[#606060] hover:text-[#0F0F0F] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Student Roster
          </Link>
          <span className="text-xs font-semibold px-3 py-1 bg-[#F2F2F2] text-[#606060] rounded-full">
            {user?.subject} ({user?.year})
          </span>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 space-y-6">
        
        {/* Header Panel */}
        <div className="bg-[#FFFFFF] border border-[#E5E5E5] rounded-xl p-6 space-y-5 shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-0.5 bg-[#F2F2F2] text-[#0F0F0F] rounded-md font-mono">
                <User className="w-3.5 h-3.5 text-[#606060]" /> Roll Number: {rollNumber}
              </div>
              <h1 className="text-2xl font-bold text-[#0F0F0F] tracking-tight">
                Student Analytics: {rollNumber}
              </h1>
              <p className="text-xs text-[#606060]">
                Academic Year: <strong className="text-[#0F0F0F]">{user?.year}</strong> | Subject: <strong className="text-[#0F0F0F]">{user?.subject}</strong>
              </p>
            </div>

            {/* Transcript Link Button */}
            {selectedCourseId !== 'ALL' && activeCourse && (
              <Link
                to={`/teacher/courses/${selectedCourseId}/transcript`}
                className="yt-btn-primary text-xs py-2 px-3.5 font-semibold flex items-center gap-2 self-start sm:self-auto"
              >
                <FileText className="w-4 h-4" />
                <span>View Course Transcript</span>
              </Link>
            )}
          </div>

          {/* Dataset Switcher Chips */}
          <div className="pt-3 flex items-center gap-2 border-t border-[#E5E5E5] flex-wrap">
            <button
              onClick={() => setActiveTab('telemetry')}
              className={`inline-flex items-center gap-1.5 py-1.5 px-3.5 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                activeTab === 'telemetry'
                  ? 'bg-[#0F0F0F] text-white'
                  : 'bg-[#F2F2F2] text-[#0F0F0F] hover:bg-[#E5E5E5]'
              }`}
            >
              <Database className="w-3.5 h-3.5" />
              <span>Phase 5: Telemetry</span>
            </button>

            <button
              onClick={() => setActiveTab('mapping')}
              className={`inline-flex items-center gap-1.5 py-1.5 px-3.5 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                activeTab === 'mapping'
                  ? 'bg-[#0F0F0F] text-white'
                  : 'bg-[#F2F2F2] text-[#0F0F0F] hover:bg-[#E5E5E5]'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Phase 7: Concept-Event Mapping</span>
            </button>

            <button
              onClick={() => setActiveTab('difficulty')}
              className={`inline-flex items-center gap-1.5 py-1.5 px-3.5 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                activeTab === 'difficulty'
                  ? 'bg-[#0F0F0F] text-white'
                  : 'bg-[#F2F2F2] text-[#0F0F0F] hover:bg-[#E5E5E5]'
              }`}
            >
              <AlertCircle className="w-3.5 h-3.5" />
              <span>Phase 8: Difficulty Analysis</span>
            </button>

            <button
              onClick={() => setActiveTab('adaptive_quiz')}
              className={`inline-flex items-center gap-1.5 py-1.5 px-3.5 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                activeTab === 'adaptive_quiz'
                  ? 'bg-[#0F0F0F] text-white'
                  : 'bg-[#F2F2F2] text-[#0F0F0F] hover:bg-[#E5E5E5]'
              }`}
            >
              <Award className="w-3.5 h-3.5" />
              <span>Adaptive Quiz Results</span>
            </button>
          </div>

          {/* Filters Bar */}
          <div className="pt-3 border-t border-[#E5E5E5] grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* Course Filter */}
            <div className="space-y-1">
              <label className="text-xs font-semibold text-[#606060] uppercase tracking-wider flex items-center gap-1.5">
                <BookOpen className="w-3.5 h-3.5 text-[#0F0F0F]" /> Filter by Course
              </label>
              <select
                value={selectedCourseId}
                onChange={(e) => setSelectedCourseId(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-[#FFFFFF] border border-[#CCCCCC] text-[#0F0F0F] text-xs focus:outline-none focus:border-[#0F0F0F] cursor-pointer"
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
              <div className="space-y-1">
                <label className="text-xs font-semibold text-[#606060] uppercase tracking-wider flex items-center gap-1.5">
                  <Filter className="w-3.5 h-3.5 text-[#0F0F0F]" /> Filter by Event Type
                </label>
                <select
                  value={selectedEventType}
                  onChange={(e) => setSelectedEventType(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-[#FFFFFF] border border-[#CCCCCC] text-[#0F0F0F] text-xs focus:outline-none focus:border-[#0F0F0F] cursor-pointer"
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
                <div className="space-y-1">
                  <label className="text-xs font-semibold text-[#606060] uppercase tracking-wider flex items-center gap-1.5">
                    <AlertCircle className="w-3.5 h-3.5 text-[#0F0F0F]" /> Difficulty Level
                  </label>
                  <select
                    value={selectedDifficultyLevel}
                    onChange={(e) => setSelectedDifficultyLevel(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-[#FFFFFF] border border-[#CCCCCC] text-[#0F0F0F] text-xs focus:outline-none focus:border-[#0F0F0F] cursor-pointer"
                  >
                    <option value="ALL">All Levels</option>
                    <option value="Easy">Easy</option>
                    <option value="Medium">Medium</option>
                    <option value="High">High</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-semibold text-[#606060] uppercase tracking-wider flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-[#0F0F0F]" /> Needs Revision
                  </label>
                  <select
                    value={selectedNeedsRevision}
                    onChange={(e) => setSelectedNeedsRevision(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-[#FFFFFF] border border-[#CCCCCC] text-[#0F0F0F] text-xs focus:outline-none focus:border-[#0F0F0F] cursor-pointer"
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
              <div className="space-y-1">
                <label className="text-xs font-semibold text-[#606060] uppercase tracking-wider flex items-center gap-1.5">
                  <Search className="w-3.5 h-3.5 text-[#0F0F0F]" /> Search text
                </label>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search transcript or concept..."
                  className="w-full px-3 py-2 rounded-lg bg-[#FFFFFF] border border-[#CCCCCC] text-[#0F0F0F] text-xs placeholder-[#909090] focus:outline-none focus:border-[#0F0F0F]"
                />
              </div>
            )}
          </div>
        </div>

        {/* Error message */}
        {errorMessage && (
          <div className="p-4 rounded-xl bg-[#FFEBEE] border border-[#FFCDD2] flex items-start gap-2.5 text-xs text-[#C62828]">
            <AlertCircle className="w-4 h-4 text-[#C62828] shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* TAB 1: Phase 5 Interaction Telemetry Dataset Table */}
        {activeTab === 'telemetry' && (
          <div className="bg-[#FFFFFF] border border-[#E5E5E5] p-6 rounded-xl space-y-4 shadow-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-[#E5E5E5]">
              <div>
                <h3 className="text-lg font-bold text-[#0F0F0F] flex items-center gap-2">
                  <Database className="w-5 h-5 text-[#FF0000]" /> Interaction Telemetry Log
                </h3>
                <span className="text-xs font-semibold px-2.5 py-0.5 bg-[#F2F2F2] text-[#606060] rounded-full mt-1 inline-block">
                  {interactions.length} event record(s)
                </span>
              </div>
              
              {/* Export Controls */}
              {interactions.length > 0 && (
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-semibold text-[#606060] uppercase tracking-wider">Export:</span>
                  <button onClick={() => handleExport("telemetry", "csv")} className="yt-btn-secondary py-1.5 px-3 text-xs font-semibold flex items-center gap-1.5"><Download className="w-3.5 h-3.5 text-[#606060]"/> CSV</button>
                  <button onClick={() => handleExport("telemetry", "json")} className="yt-btn-secondary py-1.5 px-3 text-xs font-semibold flex items-center gap-1.5"><Download className="w-3.5 h-3.5 text-[#606060]"/> JSON</button>
                  <button onClick={() => handleExport("telemetry", "xlsx")} className="yt-btn-primary py-1.5 px-3 text-xs font-semibold flex items-center gap-1.5"><Download className="w-3.5 h-3.5"/> Excel</button>
                </div>
              )}
            </div>

            {loading ? (
              <div className="py-16 text-center text-sm text-[#606060]">Loading telemetry logs...</div>
            ) : interactions.length === 0 ? (
              <div className="py-16 text-center space-y-2 border border-[#E5E5E5] rounded-xl bg-[#FAFAFA]">
                <Database className="w-10 h-10 text-[#909090] mx-auto" />
                <p className="text-sm font-semibold text-[#0F0F0F]">No interaction telemetry recorded yet.</p>
                <p className="text-xs text-[#606060]">When the student watches course videos, interaction events (play, pause, seek, speed change) will stream here.</p>
              </div>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-[#E5E5E5]">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-[#F9F9F9] border-b border-[#E5E5E5] text-[#606060] text-xs font-semibold uppercase tracking-wider">
                      <th className="p-3.5">Roll No</th>
                      <th className="p-3.5">Student</th>
                      <th className="p-3.5">Subject</th>
                      <th className="p-3.5">Video Name</th>
                      <th className="p-3.5">Event</th>
                      <th className="p-3.5">Timestamp</th>
                      <th className="p-3.5">Duration</th>
                      <th className="p-3.5">Speed</th>
                      <th className="p-3.5">Pause Reason</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E5E5E5] text-[#0F0F0F]">
                    {interactions.map((ev, index) => (
                      <tr key={`${ev.id}-${index}`} className="hover:bg-[#F9F9F9] transition-colors">
                        <td className="p-3.5 font-mono text-[#0F0F0F]">{ev.StudentID}</td>
                        <td className="p-3.5 font-semibold text-[#0F0F0F]">{ev.StudentName}</td>
                        <td className="p-3.5 text-[#606060]">{ev.CourseSubject}</td>
                        <td className="p-3.5 font-medium text-[#0F0F0F]">{ev.CourseName}</td>
                        <td className="p-3.5">
                          <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                            ev.EventType === 'PAUSE' ? 'bg-[#FFF8E1] text-[#F57F17]' :
                            ev.EventType === 'PLAY' ? 'bg-[#E8F5E9] text-[#2E7D32]' :
                            ev.EventType === 'VIDEO_COMPLETE' ? 'bg-[#EDE7F6] text-[#5E35B1]' :
                            'bg-[#F2F2F2] text-[#0F0F0F]'
                          }`}>
                            {ev.EventType}
                          </span>
                        </td>
                        <td className="p-3.5 font-mono font-semibold text-[#FF0000]">{ev.EventTimestamp}</td>
                        <td className="p-3.5 font-mono text-[#606060]">{ev.EventDuration !== null && ev.EventDuration !== undefined ? `${ev.EventDuration}s` : '—'}</td>
                        <td className="p-3.5 font-mono text-[#606060]">{ev.PlaybackSpeed !== null && ev.PlaybackSpeed !== undefined ? `${ev.PlaybackSpeed}x` : '—'}</td>
                        <td className="p-3.5 italic text-[#606060]">{ev.PauseReason || '—'}</td>
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
          <div className="bg-[#FFFFFF] border border-[#E5E5E5] p-6 rounded-xl space-y-4 shadow-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-[#E5E5E5]">
              <div>
                <h3 className="text-lg font-bold text-[#0F0F0F] flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-[#FF0000]" /> Concept-Event Mapping Dataset
                </h3>
                <span className="text-xs font-semibold px-2.5 py-0.5 bg-[#F2F2F2] text-[#606060] rounded-full mt-1 inline-block">
                  {conceptMappings.length} mapped record(s)
                </span>
              </div>
              
              {/* Export Controls */}
              {conceptMappings.length > 0 && (
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-semibold text-[#606060] uppercase tracking-wider">Export:</span>
                  <button onClick={() => handleExport("mapping", "csv")} className="yt-btn-secondary py-1.5 px-3 text-xs font-semibold flex items-center gap-1.5"><Download className="w-3.5 h-3.5 text-[#606060]"/> CSV</button>
                  <button onClick={() => handleExport("mapping", "json")} className="yt-btn-secondary py-1.5 px-3 text-xs font-semibold flex items-center gap-1.5"><Download className="w-3.5 h-3.5 text-[#606060]"/> JSON</button>
                  <button onClick={() => handleExport("mapping", "xlsx")} className="yt-btn-primary py-1.5 px-3 text-xs font-semibold flex items-center gap-1.5"><Download className="w-3.5 h-3.5"/> Excel</button>
                </div>
              )}
            </div>

            {loading ? (
              <div className="py-16 text-center text-sm text-[#606060]">Mapping interaction timestamps to concepts...</div>
            ) : conceptMappings.length === 0 ? (
              <div className="py-16 text-center space-y-2 border border-[#E5E5E5] rounded-xl bg-[#FAFAFA]">
                <Layers className="w-10 h-10 text-[#909090] mx-auto" />
                <p className="text-sm font-semibold text-[#0F0F0F]">No concept-event mappings available yet.</p>
                <p className="text-xs text-[#606060]">Ensure video transcript and concepts have been extracted for this course.</p>
              </div>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-[#E5E5E5]">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-[#F9F9F9] border-b border-[#E5E5E5] text-[#606060] text-xs font-semibold uppercase tracking-wider">
                      <th className="p-3.5">Roll No</th>
                      <th className="p-3.5">Student</th>
                      <th className="p-3.5">Video Name</th>
                      <th className="p-3.5">Event</th>
                      <th className="p-3.5">Timestamp</th>
                      <th className="p-3.5 min-w-[240px]">Transcript Segment</th>
                      <th className="p-3.5">Mapped Concept</th>
                      <th className="p-3.5">Prerequisite</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E5E5E5] text-[#0F0F0F]">
                    {conceptMappings.map((m, index) => {
                      const isExpanded = expandedRows[m.id];
                      const isLong = m.Transcript && m.Transcript.length > 80;
                      return (
                        <tr key={`${m.id}-${index}`} className="hover:bg-[#F9F9F9] transition-colors">
                          <td className="p-3.5 font-mono text-[#0F0F0F]">{m.StudentID}</td>
                          <td className="p-3.5 font-semibold text-[#0F0F0F]">{m.StudentName}</td>
                          <td className="p-3.5 font-medium text-[#0F0F0F]">{m.CourseName}</td>
                          <td className="p-3.5">
                            <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                              m.EventType === 'PAUSE' ? 'bg-[#FFF8E1] text-[#F57F17]' :
                              m.EventType === 'PLAY' ? 'bg-[#E8F5E9] text-[#2E7D32]' :
                              m.EventType === 'VIDEO_COMPLETE' ? 'bg-[#EDE7F6] text-[#5E35B1]' :
                              'bg-[#F2F2F2] text-[#0F0F0F]'
                            }`}>
                              {m.EventType}
                            </span>
                          </td>
                          <td className="p-3.5 font-mono font-semibold text-[#FF0000]">{m.EventTimestamp}</td>
                          
                          {/* Transcript segment with expandable view */}
                          <td className="p-3.5 text-[#0F0F0F] leading-relaxed">
                            {isLong ? (
                              <div>
                                <span>{isExpanded ? m.Transcript : `${m.Transcript.substring(0, 80)}...`}</span>
                                <button
                                  onClick={() => toggleExpand(m.id)}
                                  className="ml-1 text-xs font-semibold text-[#FF0000] hover:underline inline-flex items-center gap-0.5 cursor-pointer"
                                >
                                  {isExpanded ? <>Less <ChevronUp className="w-3 h-3" /></> : <>More <ChevronDown className="w-3 h-3" /></>}
                                </button>
                              </div>
                            ) : (
                              <span>{m.Transcript}</span>
                            )}
                          </td>

                          <td className="p-3.5 font-semibold text-[#0F0F0F] bg-[#F9F9F9]">{m.Concept}</td>
                          <td className="p-3.5 text-[#606060]">{m.Prerequisite || 'None'}</td>
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
          <div className="bg-[#FFFFFF] border border-[#E5E5E5] p-6 rounded-xl space-y-4 shadow-xs">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-[#E5E5E5]">
              <div>
                <h3 className="text-lg font-bold text-[#0F0F0F] flex items-center gap-2">
                  <AlertCircle className="w-5 h-5 text-[#FF0000]" /> Student Difficulty Metrics
                </h3>
                <span className="text-xs font-semibold px-2.5 py-0.5 bg-[#F2F2F2] text-[#606060] rounded-full mt-1 inline-block">
                  {difficultyData.length} concept(s) evaluated
                </span>
              </div>
              
              {/* Export Controls */}
              {difficultyData.length > 0 && (
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-semibold text-[#606060] uppercase tracking-wider">Export:</span>
                  <button onClick={() => handleExport("difficulty", "csv")} className="yt-btn-secondary py-1.5 px-3 text-xs font-semibold flex items-center gap-1.5"><Download className="w-3.5 h-3.5 text-[#606060]"/> CSV</button>
                  <button onClick={() => handleExport("difficulty", "json")} className="yt-btn-secondary py-1.5 px-3 text-xs font-semibold flex items-center gap-1.5"><Download className="w-3.5 h-3.5 text-[#606060]"/> JSON</button>
                  <button onClick={() => handleExport("difficulty", "xlsx")} className="yt-btn-primary py-1.5 px-3 text-xs font-semibold flex items-center gap-1.5"><Download className="w-3.5 h-3.5"/> Excel</button>
                </div>
              )}
            </div>

            {loading ? (
              <div className="py-16 text-center text-sm text-[#606060]">Calculating difficulty metrics...</div>
            ) : difficultyData.length === 0 ? (
              <div className="py-16 text-center space-y-2 border border-[#E5E5E5] rounded-xl bg-[#FAFAFA]">
                <AlertCircle className="w-10 h-10 text-[#909090] mx-auto" />
                <p className="text-sm font-semibold text-[#0F0F0F]">No difficulty metrics computed yet.</p>
                <p className="text-xs text-[#606060]">Difficulty metrics are computed automatically as the student engages with concept segments.</p>
              </div>
            ) : (
              <div className="overflow-x-auto rounded-xl border border-[#E5E5E5]">
                <table className="w-full text-left border-collapse text-xs whitespace-nowrap">
                  <thead>
                    <tr className="bg-[#F9F9F9] border-b border-[#E5E5E5] text-[#606060] text-xs font-semibold uppercase tracking-wider">
                      <th className="p-3.5">Roll No</th>
                      <th className="p-3.5">Student</th>
                      <th className="p-3.5">Video Name</th>
                      <th className="p-3.5">Concept</th>
                      <th className="p-3.5">Replays</th>
                      <th className="p-3.5">Pauses</th>
                      <th className="p-3.5">Seek Back</th>
                      <th className="p-3.5">Seek Fwd</th>
                      <th className="p-3.5">Und Pauses</th>
                      <th className="p-3.5">Diff Score</th>
                      <th className="p-3.5">Diff Level</th>
                      <th className="p-3.5">Needs Rev</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E5E5E5] text-[#0F0F0F]">
                    {difficultyData.map((d, index) => (
                      <tr key={`${d.id}-${index}`} className="hover:bg-[#F9F9F9] transition-colors">
                        <td className="p-3.5 font-mono text-[#0F0F0F]">{d.StudentID}</td>
                        <td className="p-3.5 font-semibold text-[#0F0F0F]">{d.StudentName}</td>
                        <td className="p-3.5 font-medium text-[#0F0F0F]">{d.CourseName}</td>
                        <td className="p-3.5 font-semibold text-[#0F0F0F] bg-[#F9F9F9]">{d.Concept}</td>
                        <td className="p-3.5 font-mono text-[#606060]">{d.ReplayCount}</td>
                        <td className="p-3.5 font-mono text-[#606060]">{d.PauseCount}</td>
                        <td className="p-3.5 font-mono text-[#606060]">{d.SeekBackwardCount}</td>
                        <td className="p-3.5 font-mono text-[#606060]">{d.SeekForwardCount}</td>
                        <td className="p-3.5 font-mono font-semibold text-[#FF0000]">{d.UnderstandPauseCount}</td>
                        <td className="p-3.5 font-mono font-bold text-[#0F0F0F]">{d.DifficultyScore.toFixed(1)}</td>
                        <td className="p-3.5">
                          <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                            d.DifficultyLevel === 'High' ? 'bg-[#FFEBEE] text-[#C62828]' :
                            d.DifficultyLevel === 'Medium' ? 'bg-[#FFF8E1] text-[#F57F17]' :
                            'bg-[#E8F5E9] text-[#2E7D32]'
                          }`}>
                            {d.DifficultyLevel}
                          </span>
                        </td>
                        <td className="p-3.5">
                          {d.NeedsRevision ? (
                            <span className="bg-[#FFEBEE] text-[#C62828] font-semibold px-2.5 py-0.5 rounded-full text-xs">Yes</span>
                          ) : (
                            <span className="text-[#909090]">No</span>
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

        {/* TAB 4: Adaptive Quiz Results */}
        {activeTab === 'adaptive_quiz' && (
          <div className="space-y-6">
            {loading ? (
              <div className="bg-[#FFFFFF] border border-[#E5E5E5] p-6 rounded-xl py-16 text-center text-sm text-[#606060] shadow-xs">
                Loading adaptive quiz results...
              </div>
            ) : quizResults.length === 0 ? (
              <div className="bg-[#FFFFFF] border border-[#E5E5E5] p-6 rounded-xl py-16 text-center space-y-2 shadow-xs">
                <Award className="w-10 h-10 text-[#909090] mx-auto" />
                <p className="text-sm font-semibold text-[#0F0F0F]">No completed adaptive quiz attempts found.</p>
              </div>
            ) : (
              quizResults.map((attempt, idx) => (
                <div key={idx} className="bg-[#FFFFFF] border border-[#E5E5E5] p-6 sm:p-7 rounded-xl space-y-6 shadow-xs">
                  
                  {/* Header */}
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 border-b border-[#E5E5E5] pb-5">
                    <div>
                      <h3 className="text-xl font-bold text-[#0F0F0F] flex items-center gap-2">
                        <Award className="w-5 h-5 text-[#FF0000]" />
                        {attempt.quiz_title} Result
                      </h3>
                      <div className="mt-2 space-y-0.5">
                        <p className="text-xs text-[#606060]">Course: <strong className="text-[#0F0F0F]">{attempt.course_name}</strong></p>
                        <p className="text-xs text-[#606060]">Attempt Date: <strong className="text-[#0F0F0F]">{attempt.attempt_date}</strong></p>
                        {attempt.adaptive_summary && (
                          <p className="text-xs text-[#0F0F0F] mt-2 italic flex items-center gap-1.5"><Sparkles className="w-3.5 h-3.5 text-[#FF0000]"/> {attempt.adaptive_summary}</p>
                        )}
                      </div>
                    </div>

                    {/* Score Badge */}
                    <div className="flex gap-3">
                      <div className="text-center px-4 py-2.5 bg-[#F9F9F9] rounded-xl border border-[#E5E5E5]">
                        <p className="text-[11px] uppercase tracking-wider text-[#606060] mb-0.5 font-semibold">Score</p>
                        <div className="flex items-end justify-center gap-1">
                          <span className="text-xl font-bold text-[#FF0000] leading-none">{attempt.score}</span>
                          <span className="text-xs text-[#606060] leading-none mb-0.5">/ {attempt.total}</span>
                        </div>
                      </div>
                      <div className="text-center px-4 py-2.5 bg-[#F9F9F9] rounded-xl border border-[#E5E5E5]">
                        <p className="text-[11px] uppercase tracking-wider text-[#606060] mb-0.5 font-semibold">Percentage</p>
                        <p className="text-xl font-bold text-[#2E7D32] leading-none">{attempt.percentage}%</p>
                      </div>
                    </div>
                  </div>

                  {/* Concept Performance */}
                  {attempt.concept_performance && attempt.concept_performance.length > 0 && (
                    <div className="space-y-3">
                      <h4 className="text-xs font-semibold text-[#606060] tracking-wider uppercase flex items-center gap-2">
                        <Layers className="w-3.5 h-3.5 text-[#0F0F0F]" /> Concept Performance
                      </h4>
                      <div className="overflow-x-auto rounded-xl border border-[#E5E5E5]">
                        <table className="w-full text-left border-collapse text-xs">
                          <thead>
                            <tr className="bg-[#F9F9F9] border-b border-[#E5E5E5] text-[#606060] text-xs font-semibold">
                              <th className="p-3 font-semibold">Concept</th>
                              <th className="p-3 font-semibold text-center">Questions</th>
                              <th className="p-3 font-semibold text-center text-[#2E7D32]">Correct</th>
                              <th className="p-3 font-semibold text-center text-[#C62828]">Incorrect</th>
                              <th className="p-3 font-semibold text-right">Mastery</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-[#E5E5E5] text-[#0F0F0F]">
                            {attempt.concept_performance.map((cp, cIdx) => (
                              <tr key={cIdx} className="hover:bg-[#F9F9F9] transition-colors">
                                <td className="p-3 font-medium text-[#0F0F0F]">{cp.concept}</td>
                                <td className="p-3 text-center text-[#606060] font-mono">{cp.total}</td>
                                <td className="p-3 text-center text-[#2E7D32] font-mono font-semibold">{cp.correct}</td>
                                <td className="p-3 text-center text-[#C62828] font-mono font-semibold">{cp.total - cp.correct}</td>
                                <td className="p-3 text-right font-mono font-semibold text-[#0F0F0F]">{cp.percentage}%</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* Question-wise Performance */}
                  {attempt.questions && attempt.questions.length > 0 && (
                    <div className="space-y-3">
                      <h4 className="text-xs font-semibold text-[#606060] tracking-wider uppercase flex items-center gap-2">
                        <FileText className="w-3.5 h-3.5 text-[#0F0F0F]" /> Detailed Question Analysis
                      </h4>
                      <div className="space-y-3">
                        {attempt.questions.map((q, qIdx) => (
                          <div key={q.id || qIdx} className="p-4 rounded-xl bg-[#F9F9F9] border border-[#E5E5E5] space-y-3">
                            <div className="flex items-start justify-between gap-3">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="text-xs font-semibold text-[#0F0F0F] font-mono px-2 py-0.5 rounded bg-[#FFFFFF] border border-[#E5E5E5]">
                                  Q{qIdx + 1}
                                </span>
                                {q.concept && (
                                  <span className="text-xs font-medium text-[#606060] px-2 py-0.5 rounded bg-[#FFFFFF] border border-[#E5E5E5]">
                                    {q.concept}
                                  </span>
                                )}
                                {q.difficulty && (
                                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase ${
                                    q.difficulty === 'EASY' ? 'bg-[#E8F5E9] text-[#2E7D32]' :
                                    q.difficulty === 'HARD' ? 'bg-[#FFEBEE] text-[#C62828]' :
                                    'bg-[#FFF8E1] text-[#F57F17]'
                                  }`}>
                                    {q.difficulty}
                                  </span>
                                )}
                              </div>
                              <div className={`px-2.5 py-0.5 rounded-full text-xs font-semibold flex items-center gap-1.5 ${
                                q.is_correct ? 'bg-[#E8F5E9] text-[#2E7D32]' : 'bg-[#FFEBEE] text-[#C62828]'
                              }`}>
                                {q.is_correct ? <CheckCircle2 className="w-3.5 h-3.5"/> : <XCircle className="w-3.5 h-3.5"/>}
                                {q.is_correct ? 'Correct' : 'Incorrect'}
                              </div>
                            </div>

                            <h5 className="text-sm font-semibold text-[#0F0F0F] leading-relaxed">{q.text}</h5>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                              <div className="p-2.5 rounded-lg bg-[#FFFFFF] border border-[#E5E5E5]">
                                <p className="text-[#606060] mb-0.5 font-semibold uppercase tracking-wider text-[10px]">Student's Answer:</p>
                                <p className={q.is_correct ? 'text-[#2E7D32] font-semibold' : 'text-[#C62828] font-semibold'}>
                                  {q.student_answer || 'No answer provided'}
                                </p>
                              </div>
                              <div className="p-2.5 rounded-lg bg-[#FFFFFF] border border-[#E5E5E5]">
                                <p className="text-[#606060] mb-0.5 font-semibold uppercase tracking-wider text-[10px]">Correct Answer:</p>
                                <p className="text-[#2E7D32] font-semibold">{q.correct_answer}</p>
                              </div>
                            </div>

                            {q.explanation && (
                              <div className="p-2.5 rounded-lg bg-[#FFFFFF] border border-[#E5E5E5] text-xs flex items-start gap-2">
                                <AlertCircle className="w-3.5 h-3.5 text-[#FF0000] shrink-0 mt-0.5" />
                                <p className="text-[#606060] leading-relaxed"><strong className="text-[#0F0F0F]">Explanation:</strong> {q.explanation}</p>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        )}

      </main>
    </div>
  );
}
