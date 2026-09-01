import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  ArrowLeft, 
  Play, 
  Video, 
  BookOpen, 
  ShieldCheck, 
  AlertCircle,
  Calendar
} from 'lucide-react';

export default function StudentCourseDetails() {
  const { courseId } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [course, setCourse] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');

  const fetchCourseDetails = async () => {
    setLoading(true);
    const token = localStorage.getItem('cognitrace_token');
    try {
      const res = await fetch(`/api/v1/student/courses/${courseId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setCourse(data);
      } else {
        const errData = await res.json();
        setErrorMessage(errData.detail || 'Failed to load course details or access denied.');
      }
    } catch (err) {
      setErrorMessage('Network error fetching course details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCourseDetails();
  }, [courseId]);

  return (
    <div className="min-h-screen flex flex-col bg-slate-950">
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link
            to="/student/dashboard"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-400 hover:text-cyan-400 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Dashboard
          </Link>
          <span className="text-xs font-mono text-cyan-400 px-3 py-1 rounded-full bg-cyan-950/60 border border-cyan-800/50">
            Year: {user?.year}
          </span>
        </div>
      </header>

      <main className="flex-1 max-w-3xl w-full mx-auto px-4 py-12">
        {errorMessage ? (
          <div className="p-6 rounded-2xl bg-rose-950/60 border border-rose-800/60 flex items-start gap-3 text-xs text-rose-300">
            <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <div>
              <strong className="text-white block text-sm mb-1">Access Restricted</strong>
              <span>{errorMessage}</span>
            </div>
          </div>
        ) : loading ? (
          <div className="py-16 text-center text-xs font-mono text-slate-500">Loading course overview...</div>
        ) : (
          <div className="glass-panel p-8 rounded-2xl border border-slate-800 space-y-8">
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono px-2.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/50">
                  {course.subject}
                </span>
                <span className="text-xs font-mono px-2.5 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
                  {course.year}
                </span>
              </div>
              <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight leading-tight">
                {course.course_name}
              </h2>
              <p className="text-xs text-slate-400">
                Instructor: <strong className="text-white">{course.teacher_name}</strong> ({course.teacher_id})
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800 space-y-1">
                <span className="text-slate-400 flex items-center gap-1.5">
                  <BookOpen className="w-3.5 h-3.5 text-cyan-400" /> Subject
                </span>
                <p className="text-sm font-semibold text-white">{course.subject}</p>
              </div>
              <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800 space-y-1">
                <span className="text-slate-400 flex items-center gap-1.5">
                  <Calendar className="w-3.5 h-3.5 text-indigo-400" /> Published Date
                </span>
                <p className="text-sm font-semibold text-white">
                  {new Date(course.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}
                </p>
              </div>
            </div>

            <div className="pt-4 border-t border-slate-800">
              <Link
                to={`/student/course/${course.id}/watch`}
                className="inline-flex items-center justify-center gap-2 py-3 px-6 rounded-xl bg-cyan-400 hover:bg-cyan-300 text-slate-950 font-bold text-sm transition-colors shadow-lg shadow-cyan-400/20 w-full sm:w-auto"
              >
                <Play className="w-5 h-5 fill-slate-950" />
                <span>Play Video</span>
              </Link>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
