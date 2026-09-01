import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  BookOpen, 
  PlusCircle, 
  Users, 
  LogOut, 
  ShieldCheck, 
  Calendar, 
  Book, 
  Video,
  ArrowRight,
  Sparkles,
  ExternalLink,
  Database
} from 'lucide-react';

export default function TeacherDashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [courses, setCourses] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchRecentCourses = async () => {
    const token = localStorage.getItem('cognitrace_token');
    if (!token) return;
    try {
      const res = await fetch('/api/v1/courses/my', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setCourses(data);
      }
    } catch (err) {
      console.error('Failed to fetch courses:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRecentCourses();
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-950">
      {/* Navbar */}
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <BookOpen className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-base text-slate-100 flex items-center gap-2">
                Teacher Dashboard
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950 text-indigo-400 border border-indigo-800/50">Verified</span>
              </h1>
              <p className="text-xs text-slate-400">CogniTrace Course Management</p>
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-700 text-xs font-medium transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Logout</span>
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        
        {/* Welcome Profile Card */}
        <section className="glass-panel p-6 sm:p-8 rounded-2xl relative overflow-hidden">
          <div className="absolute -top-24 -right-24 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>
          
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="space-y-2">
              <div className="inline-flex items-center gap-1.5 text-xs font-mono text-indigo-400 bg-indigo-950/60 px-3 py-1 rounded-full border border-indigo-800/50">
                <ShieldCheck className="w-3.5 h-3.5" /> Teacher ID: {user?.identifier}
              </div>
              <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
                Welcome, {user?.name}
              </h2>
              <p className="text-xs text-slate-400">
                Academic Year: <strong className="text-white">{user?.year}</strong> &nbsp;|&nbsp; Subject: <strong className="text-white">{user?.subject}</strong>
              </p>
            </div>

            <div className="flex items-center gap-3">
              <Link
                to="/teacher/courses/add"
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs shadow-lg shadow-indigo-600/20 transition-all"
              >
                <PlusCircle className="w-4 h-4" />
                <span>Add Course</span>
              </Link>
              <Link
                to="/teacher/students"
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 font-semibold text-xs transition-colors"
              >
                <Users className="w-4 h-4 text-cyan-400" />
                <span>View Students</span>
              </Link>
            </div>
          </div>
        </section>

        {/* Action Grid */}
        <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          {/* Card 1: Add Course */}
          <Link
            to="/teacher/courses/add"
            className="glass-card p-6 rounded-2xl space-y-4 group block cursor-pointer border border-slate-800 hover:border-indigo-500/50 transition-all"
          >
            <div className="flex items-center justify-between">
              <div className="w-12 h-12 rounded-xl bg-indigo-950/80 border border-indigo-800/60 flex items-center justify-center text-indigo-400 group-hover:scale-105 transition-transform">
                <PlusCircle className="w-6 h-6" />
              </div>
              <ArrowRight className="w-5 h-5 text-slate-500 group-hover:text-indigo-400 transition-colors" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white group-hover:text-indigo-300 transition-colors">Add New Course</h3>
              <p className="text-xs text-slate-400 mt-1">
                Add an educational course with a single YouTube video link for your students in {user?.year}.
              </p>
            </div>
          </Link>

          {/* Card 2: View Students */}
          <Link
            to="/teacher/students"
            className="glass-card p-6 rounded-2xl space-y-4 group block cursor-pointer border border-slate-800 hover:border-cyan-500/50 transition-all"
          >
            <div className="flex items-center justify-between">
              <div className="w-12 h-12 rounded-xl bg-cyan-950/80 border border-cyan-800/60 flex items-center justify-center text-cyan-400 group-hover:scale-105 transition-transform">
                <Users className="w-6 h-6" />
              </div>
              <ArrowRight className="w-5 h-5 text-slate-500 group-hover:text-cyan-400 transition-colors" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white group-hover:text-cyan-300 transition-colors">View Registered Students</h3>
              <p className="text-xs text-slate-400 mt-1">
                View students registered for {user?.year} sorted alphanumerically by Roll Number.
              </p>
            </div>
          </Link>

          {/* Card 3: Dataset Viewer */}
          <Link
            to="/teacher/datasets"
            className="glass-card p-6 rounded-2xl space-y-4 group block cursor-pointer border border-slate-800 hover:border-purple-500/50 transition-all md:col-span-2"
          >
            <div className="flex items-center justify-between">
              <div className="w-12 h-12 rounded-xl bg-purple-950/80 border border-purple-800/60 flex items-center justify-center text-purple-400 group-hover:scale-105 transition-transform">
                <Database className="w-6 h-6" />
              </div>
              <ArrowRight className="w-5 h-5 text-slate-500 group-hover:text-purple-400 transition-colors" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white group-hover:text-purple-300 transition-colors">Dataset Management</h3>
              <p className="text-xs text-slate-400 mt-1">
                View, download, and manage the derived CogniTrace research datasets (Interactions, Transcripts, Concepts, Mappings, Difficulty).
              </p>
            </div>
          </Link>

        </section>

        {/* Course Summary Section */}
        <section className="glass-panel p-6 rounded-2xl space-y-5">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Video className="w-5 h-5 text-indigo-400" /> Your Courses ({courses.length})
            </h3>
            <Link
              to="/teacher/courses"
              className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition-colors"
            >
              <span>Manage All Courses</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {loading ? (
            <div className="py-8 text-center text-xs font-mono text-slate-500">Loading courses...</div>
          ) : courses.length === 0 ? (
            <div className="py-12 text-center space-y-3 bg-slate-900/40 rounded-xl border border-slate-800/60">
              <BookOpen className="w-10 h-10 text-slate-600 mx-auto" />
              <p className="text-sm font-medium text-slate-300">No courses have been added yet.</p>
              <p className="text-xs text-slate-500">Click "Add Course" to publish your first educational video module.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {courses.slice(0, 6).map((c) => (
                <div key={c.id} className="bg-slate-900/70 p-4 rounded-xl border border-slate-800 space-y-3 hover:border-slate-700 transition-colors">
                  <div className="flex items-start justify-between gap-2">
                    <h4 className="font-bold text-sm text-white line-clamp-1">{c.course_name}</h4>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800/50 shrink-0">
                      {c.subject}
                    </span>
                  </div>
                  <div className="text-xs text-slate-400 flex items-center gap-1 font-mono truncate">
                    <Video className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                    <span className="truncate">{c.youtube_url}</span>
                  </div>
                  <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-500">
                    <span>{new Date(c.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}</span>
                    <a
                      href={c.youtube_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-medium"
                    >
                      <span>Watch</span>
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

      </main>
    </div>
  );
}
