import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  Play, 
  PlusCircle, 
  Users, 
  LogOut, 
  ShieldCheck, 
  Video,
  ArrowRight, 
  ExternalLink,
  Database,
  Calendar,
  Layers,
  BookOpen
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
    <div className="min-h-screen flex flex-col bg-[#FFFFFF] text-[#0F0F0F]">
      {/* Top Navbar */}
      <header className="border-b border-[#E5E5E5] bg-[#FFFFFF] sticky top-0 z-50 h-14">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-full flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Link to="/teacher/dashboard" className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-[#0F0F0F] flex items-center justify-center shadow-xs">
                <span className="font-bold text-xs text-[#00C896]">CT</span>
              </div>
              <span className="font-bold text-lg text-[#0F0F0F] tracking-tight hidden sm:inline">
                CogniTrace Studio
              </span>
            </Link>
            <span className="text-xs font-semibold px-2.5 py-0.5 bg-[#F2F2F2] text-[#606060] rounded-full">
              Teacher
            </span>
          </div>

          <div className="flex items-center gap-3">
            <Link
              to="/teacher/courses/add"
              className="yt-btn-primary text-xs font-semibold py-1.5 px-3.5"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              <span>Add Course</span>
            </Link>

            <button
              onClick={handleLogout}
              className="yt-btn-secondary text-xs py-1.5 px-3.5 font-semibold"
            >
              <LogOut className="w-3.5 h-3.5 text-[#606060]" />
              <span>Sign Out</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        
        {/* Welcome Channel Banner Card */}
        <section className="bg-[#F9F9F9] border border-[#E5E5E5] rounded-xl p-5 sm:p-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-0.5 bg-[#FFFFFF] border border-[#E5E5E5] text-[#0F0F0F] rounded-full">
                <ShieldCheck className="w-3.5 h-3.5 text-[#FF0000]" /> Teacher ID: {user?.identifier}
              </div>
              <h1 className="text-xl sm:text-2xl font-bold text-[#0F0F0F] tracking-tight">
                Welcome, {user?.name}
              </h1>
              <p className="text-xs text-[#606060]">
                Assigned Year: <strong className="text-[#0F0F0F] font-semibold">{user?.year}</strong> • Subject: <strong className="text-[#0F0F0F] font-semibold">{user?.subject}</strong>
              </p>
            </div>

            <div className="flex items-center gap-2.5 flex-wrap">
              <Link
                to="/teacher/students"
                className="yt-btn-secondary text-xs py-2 px-3.5 font-semibold"
              >
                <Users className="w-4 h-4 text-[#0F0F0F]" />
                <span>View Students</span>
              </Link>
              <Link
                to="/teacher/datasets"
                className="yt-btn-secondary text-xs py-2 px-3.5 font-semibold"
              >
                <Database className="w-4 h-4 text-[#0F0F0F]" />
                <span>Datasets</span>
              </Link>
              <Link
                to="/teacher/research"
                className="yt-btn-primary text-xs py-2 px-3.5 font-semibold"
              >
                <Layers className="w-4 h-4" />
                <span>Research Analytics</span>
              </Link>
            </div>
          </div>
        </section>

        {/* Action / Studio Navigation Cards */}
        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          
          {/* Card 1: Add Course */}
          <Link
            to="/teacher/courses/add"
            className="group yt-card p-5 rounded-xl flex flex-col justify-between space-y-3 block cursor-pointer"
          >
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-full bg-[#FFEBEE] flex items-center justify-center text-[#FF0000]">
                <PlusCircle className="w-5 h-5" />
              </div>
              <ArrowRight className="w-4 h-4 text-[#909090] transition-transform group-hover:translate-x-0.5 group-hover:text-[#0F0F0F]" />
            </div>
            <div>
              <h2 className="text-base font-bold text-[#0F0F0F] group-hover:text-[#FF0000] transition-colors">Create Video Lesson</h2>
              <p className="text-xs text-[#606060] mt-1 leading-relaxed">
                Add an educational YouTube video lesson module for students in {user?.year}.
              </p>
            </div>
          </Link>

          {/* Card 2: View Students */}
          <Link
            to="/teacher/students"
            className="group yt-card p-5 rounded-xl flex flex-col justify-between space-y-3 block cursor-pointer"
          >
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-full bg-[#F2F2F2] flex items-center justify-center text-[#0F0F0F]">
                <Users className="w-5 h-5" />
              </div>
              <ArrowRight className="w-4 h-4 text-[#909090] transition-transform group-hover:translate-x-0.5 group-hover:text-[#0F0F0F]" />
            </div>
            <div>
              <h2 className="text-base font-bold text-[#0F0F0F] group-hover:text-[#FF0000] transition-colors">Enrolled Students</h2>
              <p className="text-xs text-[#606060] mt-1 leading-relaxed">
                View student interaction telemetry and video watching behavior for {user?.year}.
              </p>
            </div>
          </Link>

          {/* Card 3: Dataset Viewer */}
          <Link
            to="/teacher/datasets"
            className="group yt-card p-5 rounded-xl flex flex-col justify-between space-y-3 block cursor-pointer"
          >
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-full bg-[#F2F2F2] flex items-center justify-center text-[#0F0F0F]">
                <Database className="w-5 h-5" />
              </div>
              <ArrowRight className="w-4 h-4 text-[#909090] transition-transform group-hover:translate-x-0.5 group-hover:text-[#0F0F0F]" />
            </div>
            <div>
              <h2 className="text-base font-bold text-[#0F0F0F] group-hover:text-[#FF0000] transition-colors">Dataset Management</h2>
              <p className="text-xs text-[#606060] mt-1 leading-relaxed">
                Inspect, export, and analyze learning telemetry datasets and difficulty ratings.
              </p>
            </div>
          </Link>

          {/* Card 4: Research Analytics */}
          <Link
            to="/teacher/research"
            className="group yt-card p-5 rounded-xl flex flex-col justify-between space-y-3 block cursor-pointer bg-[#FFEBEE]/30 border-[#FFCDD2]"
          >
            <div className="flex items-center justify-between">
              <div className="w-10 h-10 rounded-full bg-[#FFEBEE] flex items-center justify-center text-[#FF0000]">
                <Layers className="w-5 h-5" />
              </div>
              <ArrowRight className="w-4 h-4 text-[#FF0000] transition-transform group-hover:translate-x-0.5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-[#0F0F0F] group-hover:text-[#FF0000] transition-colors">Research & Evidence</h2>
              <p className="text-xs text-[#606060] mt-1 leading-relaxed">
                Configure ablation experiments, weights, temporal decay, and evaluate learning gains.
              </p>
            </div>
          </Link>

        </section>

        {/* Course Summary Section */}
        <section className="bg-[#FFFFFF] border border-[#E5E5E5] rounded-xl p-5 sm:p-6 space-y-4 shadow-sm">
          <div className="flex items-center justify-between border-b border-[#E5E5E5] pb-3">
            <h2 className="text-base font-bold text-[#0F0F0F] flex items-center gap-2">
              <Video className="w-4 h-4 text-[#FF0000]" /> Published Course Lessons ({courses.length})
            </h2>
            <Link
              to="/teacher/courses"
              className="text-xs font-semibold text-[#0F0F0F] hover:text-[#FF0000] flex items-center gap-1 transition-colors cursor-pointer"
            >
              <span>Manage All Courses</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {loading ? (
            <div className="py-8 text-center text-xs text-[#606060]">Loading course library...</div>
          ) : courses.length === 0 ? (
            <div className="py-8 text-center space-y-2 bg-[#F9F9F9] rounded-xl border border-[#E5E5E5] p-6">
              <Video className="w-8 h-8 text-[#909090] mx-auto" />
              <p className="text-xs font-semibold text-[#0F0F0F]">No courses published yet.</p>
              <p className="text-xs text-[#606060]">Click "Add Course" to publish your first video lecture module.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {courses.slice(0, 6).map((c) => (
                <div key={c.id} className="bg-[#F9F9F9] p-4 rounded-xl border border-[#E5E5E5] space-y-2.5 hover:border-[#CCCCCC] transition-colors">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-bold text-xs text-[#0F0F0F] line-clamp-1">{c.course_name}</h3>
                    <span className="text-[10px] font-semibold px-2 py-0.5 bg-[#FFFFFF] border border-[#E5E5E5] text-[#0F0F0F] rounded shrink-0">
                      {c.subject}
                    </span>
                  </div>
                  <div className="text-xs text-[#606060] flex items-center gap-1.5 truncate">
                    <Video className="w-3.5 h-3.5 text-[#FF0000] shrink-0" />
                    <span className="truncate">{c.youtube_url}</span>
                  </div>
                  <div className="pt-2 border-t border-[#E5E5E5] flex items-center justify-between text-xs text-[#606060]">
                    <span>{new Date(c.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}</span>
                    <a
                      href={c.youtube_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[#0F0F0F] hover:text-[#FF0000] flex items-center gap-1 font-semibold transition-colors"
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

