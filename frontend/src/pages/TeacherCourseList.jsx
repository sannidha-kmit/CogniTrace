import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  PlusCircle, 
  Trash2, 
  ArrowLeft, 
  Video, 
  AlertCircle,
  Calendar,
  FileText,
  Layers,
  Search,
  ExternalLink
} from 'lucide-react';

export default function TeacherCourseList() {
  const { user } = useAuth();
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  const fetchCourses = async () => {
    setLoading(true);
    const token = localStorage.getItem('cognitrace_token');
    try {
      const res = await fetch('/api/v1/courses/my', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setCourses(data);
      } else {
        setErrorMessage('Failed to load courses.');
      }
    } catch (err) {
      setErrorMessage(err.message || 'Error connecting to server.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCourses();
  }, []);

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    const token = localStorage.getItem('cognitrace_token');

    try {
      const res = await fetch(`/api/v1/courses/${deleteTarget.id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || 'Failed to delete course.');
      }

      setCourses(prev => prev.filter(c => c.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch (err) {
      setErrorMessage(err.message || 'Failed to delete course.');
    } finally {
      setIsDeleting(false);
    }
  };

  const filteredCourses = courses.filter(c => 
    c.course_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.subject.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="min-h-screen flex flex-col bg-[#F9F9F9] text-[#0F0F0F]">
      {/* Header */}
      <header className="border-b border-[#E5E5E5] bg-[#FFFFFF] sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <Link
            to="/teacher/dashboard"
            className="inline-flex items-center gap-2 text-sm font-medium text-[#606060] hover:text-[#0F0F0F] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Studio Dashboard
          </Link>
          <Link
            to="/teacher/courses/add"
            className="yt-btn-primary text-xs py-2 px-4 font-semibold flex items-center gap-2"
          >
            <PlusCircle className="w-4 h-4" /> Add Video Course
          </Link>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 space-y-6">
        
        {/* Title and Controls */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[#E5E5E5]">
          <div>
            <h1 className="text-2xl font-bold text-[#0F0F0F] tracking-tight">Channel Content</h1>
            <p className="text-sm text-[#606060] mt-0.5">
              Manage uploaded lectures for <span className="font-semibold text-[#0F0F0F]">{user?.year} ({user?.subject})</span>
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[#909090]" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Filter courses..."
                className="pl-9 pr-3 py-1.5 text-xs bg-[#FFFFFF] border border-[#CCCCCC] rounded-full focus:outline-none focus:border-[#0F0F0F] w-48 sm:w-64 text-[#0F0F0F]"
              />
            </div>
            <span className="text-xs font-semibold px-3 py-1 bg-[#F2F2F2] text-[#606060] rounded-full shrink-0">
              {courses.length} {courses.length === 1 ? 'Video' : 'Videos'}
            </span>
          </div>
        </div>

        {errorMessage && (
          <div className="p-3.5 rounded-xl bg-[#FFEBEE] border border-[#FFCDD2] flex items-start gap-2.5 text-xs text-[#C62828]">
            <AlertCircle className="w-4 h-4 text-[#C62828] shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}

        {loading ? (
          <div className="py-16 text-center text-sm text-[#606060]">Loading your video content...</div>
        ) : courses.length === 0 ? (
          <div className="py-20 text-center space-y-4 bg-[#FFFFFF] border border-[#E5E5E5] rounded-xl max-w-lg mx-auto p-8 shadow-sm">
            <div className="w-16 h-16 rounded-full bg-[#F2F2F2] flex items-center justify-center mx-auto text-[#909090]">
              <Video className="w-8 h-8" />
            </div>
            <div className="space-y-1">
              <h3 className="text-base font-bold text-[#0F0F0F]">No video courses published yet</h3>
              <p className="text-xs text-[#606060]">Publish your first educational video link to automatically generate transcripts and concept maps.</p>
            </div>
            <Link
              to="/teacher/courses/add"
              className="yt-btn-primary text-xs py-2.5 px-5 font-semibold inline-flex items-center gap-2"
            >
              <PlusCircle className="w-4 h-4" /> Add Video Now
            </Link>
          </div>
        ) : filteredCourses.length === 0 ? (
          <div className="py-12 text-center text-sm text-[#606060]">
            No courses match the search query "{searchTerm}".
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredCourses.map((c) => (
              <div key={c.id} className="bg-[#FFFFFF] border border-[#E5E5E5] rounded-xl overflow-hidden shadow-xs hover:border-[#CCCCCC] hover:shadow-sm transition-all flex flex-col justify-between">
                <div className="p-4 space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-semibold text-base text-[#0F0F0F] line-clamp-2 leading-snug">{c.course_name}</h3>
                    <span className="text-[11px] font-semibold px-2 py-0.5 bg-[#F2F2F2] text-[#0F0F0F] rounded-md shrink-0">
                      {c.subject}
                    </span>
                  </div>

                  <div className="text-xs text-[#606060] flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-[#909090]" />
                    <span>Uploaded {new Date(c.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}</span>
                  </div>
                </div>

                <div className="p-4 pt-3 border-t border-[#E5E5E5] bg-[#FAFAFA] space-y-2">
                  <div className="grid grid-cols-2 gap-2">
                    <Link
                      to={`/teacher/courses/${c.id}/transcript`}
                      className="yt-btn-secondary py-1.5 px-3 text-xs font-semibold flex items-center justify-center gap-1.5"
                    >
                      <FileText className="w-3.5 h-3.5 text-[#606060]" />
                      <span>Transcript</span>
                    </Link>
                    <Link
                      to={`/teacher/courses/${c.id}/concepts`}
                      className="yt-btn-secondary py-1.5 px-3 text-xs font-semibold flex items-center justify-center gap-1.5"
                    >
                      <Layers className="w-3.5 h-3.5 text-[#FF0000]" />
                      <span>Concepts</span>
                    </Link>
                  </div>

                  <button
                    onClick={() => setDeleteTarget(c)}
                    className="w-full py-1.5 px-3 rounded-full hover:bg-[#FFEBEE] text-[#C62828] font-semibold text-xs border border-transparent hover:border-[#FFCDD2] transition-colors flex items-center justify-center gap-1.5 cursor-pointer"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Delete Video</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

      </main>

      {/* Delete Confirmation Modal */}
      {deleteTarget && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-[#FFFFFF] p-6 rounded-xl max-w-md w-full space-y-4 border border-[#E5E5E5] shadow-lg">
            <div className="flex items-center space-x-3 text-[#C62828]">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <h3 className="text-base font-bold text-[#0F0F0F]">Permanently delete this video?</h3>
            </div>
            <p className="text-xs text-[#606060] leading-relaxed">
              Are you sure you want to delete <strong className="text-[#0F0F0F]">"{deleteTarget.course_name}"</strong>? This will remove all associated interaction telemetry, transcripts, and concept mappings.
            </p>
            <div className="flex items-center justify-end space-x-2.5 pt-2">
              <button
                onClick={() => setDeleteTarget(null)}
                disabled={isDeleting}
                className="yt-btn-secondary text-xs py-2 px-4"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteConfirm}
                disabled={isDeleting}
                className="py-2 px-4 rounded-full bg-[#FF0000] text-white text-xs font-semibold hover:bg-[#CC0000] transition-all cursor-pointer"
              >
                {isDeleting ? 'Deleting...' : 'Delete Forever'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
