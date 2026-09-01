import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  ArrowLeft, 
  BookOpen, 
  Play, 
  Video, 
  Calendar, 
  AlertCircle 
} from 'lucide-react';

export default function StudentTeacherCourses() {
  const { teacherId } = useParams();
  const { user } = useAuth();

  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');
  const [teacherInfo, setTeacherInfo] = useState(null);

  const fetchTeacherCourses = async () => {
    setLoading(true);
    const token = localStorage.getItem('cognitrace_token');
    try {
      const res = await fetch(`/api/v1/student/teachers/${teacherId}/courses`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setCourses(data);
        if (data.length > 0) {
          setTeacherInfo({
            name: data[0].teacher_name,
            subject: data[0].subject,
            year: data[0].year
          });
        }
      } else {
        const errData = await res.json();
        setErrorMessage(errData.detail || 'Access denied or failed to load courses.');
      }
    } catch (err) {
      setErrorMessage('Error connecting to server.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTeacherCourses();
  }, [teacherId]);

  return (
    <div className="min-h-screen flex flex-col bg-slate-950">
      {/* Navbar */}
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
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

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-8 space-y-6">
        
        <div className="glass-panel p-6 sm:p-8 rounded-2xl border border-slate-800 space-y-2">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-bold text-white tracking-tight">
              {teacherInfo?.subject || 'Subject Courses'}
            </h2>
            <span className="text-xs font-mono text-indigo-400 bg-indigo-950/60 px-3 py-1 rounded-full border border-indigo-800/50">
              {teacherInfo?.year || user?.year}
            </span>
          </div>
          <p className="text-xs text-slate-400">
            Teacher: <strong className="text-white">{teacherInfo?.name || teacherId}</strong>
          </p>
        </div>

        {errorMessage && (
          <div className="p-4 rounded-xl bg-rose-950/60 border border-rose-800/60 flex items-start gap-2.5 text-xs text-rose-300">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}

        {loading ? (
          <div className="py-16 text-center text-xs font-mono text-slate-500">Loading courses...</div>
        ) : courses.length === 0 ? (
          <div className="py-16 text-center space-y-3 glass-panel rounded-2xl border border-slate-800">
            <Video className="w-12 h-12 text-slate-600 mx-auto" />
            <p className="text-base font-semibold text-white">No courses have been added by this teacher yet.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {courses.map((c) => (
              <div key={c.id} className="glass-card p-6 rounded-2xl border border-slate-800 space-y-4 flex flex-col justify-between hover:border-cyan-500/50 transition-all">
                <div className="space-y-3">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800/50">
                    {c.subject}
                  </span>
                  <h3 className="font-bold text-base text-white leading-snug line-clamp-2">{c.course_name}</h3>
                  <div className="text-[11px] text-slate-500 font-mono flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5" />
                    <span>Added: {new Date(c.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}</span>
                  </div>
                </div>

                <Link
                  to={`/student/course/${c.id}`}
                  className="inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs transition-colors shadow-lg shadow-cyan-500/20 w-full"
                >
                  <Play className="w-4 h-4 fill-slate-950" />
                  <span>Play</span>
                </Link>
              </div>
            ))}
          </div>
        )}

      </main>
    </div>
  );
}
