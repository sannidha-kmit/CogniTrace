import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  BookOpen, 
  PlusCircle, 
  Trash2, 
  ArrowLeft, 
  Video, 
  ExternalLink, 
  AlertCircle,
  Calendar,
  FileText,
  Layers
} from 'lucide-react';

export default function TeacherCourseList() {
  const { user } = useAuth();
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

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

  return (
    <div className="min-h-screen flex flex-col bg-slate-950">
      {/* Navbar */}
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link
            to="/teacher/dashboard"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-400 hover:text-indigo-400 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Dashboard
          </Link>
          <Link
            to="/teacher/courses/add"
            className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition-colors shadow-lg shadow-indigo-600/20"
          >
            <PlusCircle className="w-4 h-4" /> Add Course
          </Link>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-8 space-y-6">
        
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
              <BookOpen className="w-6 h-6 text-indigo-400" /> Course Catalog
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Courses created by <strong className="text-white">{user?.name}</strong> for {user?.year} ({user?.subject})
            </p>
          </div>
          <span className="text-xs font-mono px-3 py-1 rounded-full bg-slate-900 text-slate-400 border border-slate-800">
            Total Courses: {courses.length}
          </span>
        </div>

        {errorMessage && (
          <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-800/60 flex items-start gap-2.5 text-xs text-rose-300">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}

        {loading ? (
          <div className="py-16 text-center text-xs font-mono text-slate-500">Loading course list...</div>
        ) : courses.length === 0 ? (
          <div className="py-16 text-center space-y-4 glass-panel rounded-2xl border border-slate-800">
            <Video className="w-12 h-12 text-slate-600 mx-auto" />
            <div className="space-y-1">
              <p className="text-base font-semibold text-white">No courses have been added yet.</p>
              <p className="text-xs text-slate-400">Click "Add Course" to publish your first educational video link.</p>
            </div>
            <Link
              to="/teacher/courses/add"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-all shadow-lg shadow-indigo-600/20"
            >
              <PlusCircle className="w-4 h-4" /> Add Course Now
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {courses.map((c) => (
              <div key={c.id} className="glass-card p-6 rounded-2xl border border-slate-800 flex flex-col justify-between space-y-4 hover:border-slate-700 transition-all">
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-bold text-base text-white line-clamp-2 leading-snug">{c.course_name}</h3>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800/50 shrink-0">
                      {c.subject}
                    </span>
                  </div>

                  <div className="text-[11px] text-slate-500 font-mono flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5" />
                    <span>Added: {new Date(c.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}</span>
                  </div>
                </div>

                <div className="space-y-2 pt-2 border-t border-slate-800/60">
                  <div className="grid grid-cols-2 gap-2">
                    <Link
                      to={`/teacher/courses/${c.id}/transcript`}
                      className="inline-flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl bg-indigo-950/80 hover:bg-indigo-900/80 text-indigo-300 font-semibold text-[10px] border border-indigo-800/60 transition-colors"
                    >
                      <FileText className="w-3.5 h-3.5 text-indigo-400" />
                      <span>Transcript</span>
                    </Link>
                    <Link
                      to={`/teacher/courses/${c.id}/concepts`}
                      className="inline-flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl bg-cyan-950/40 hover:bg-cyan-900/40 text-cyan-400 font-semibold text-[10px] border border-cyan-900/40 transition-colors"
                    >
                      <Layers className="w-3.5 h-3.5 text-cyan-400" />
                      <span>Concepts</span>
                    </Link>
                  </div>

                  <button
                    onClick={() => setDeleteTarget(c)}
                    className="inline-flex items-center justify-center gap-1.5 py-2 px-3 rounded-xl bg-rose-950/40 hover:bg-rose-900/40 text-rose-400 font-semibold text-[10px] border border-rose-900/40 transition-colors w-full"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Delete Course</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

      </main>

      {/* Delete Confirmation Modal */}
      {deleteTarget && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-panel p-6 rounded-2xl max-w-md w-full border border-slate-800 space-y-4">
            <div className="flex items-center space-x-3 text-rose-400">
              <AlertCircle className="w-6 h-6" />
              <h3 className="text-lg font-bold text-white">Delete Course Confirmation</h3>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed">
              Are you sure you want to delete the course <strong className="text-white">"{deleteTarget.course_name}"</strong>? This action cannot be undone.
            </p>
            <div className="flex items-center justify-end space-x-3 pt-2">
              <button
                onClick={() => setDeleteTarget(null)}
                disabled={isDeleting}
                className="px-4 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs font-medium border border-slate-700"
              >
                Cancel
              </button>
              <button
                onClick={handleDeleteConfirm}
                disabled={isDeleting}
                className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold shadow-lg shadow-rose-600/20"
              >
                {isDeleting ? 'Deleting...' : 'Confirm Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
