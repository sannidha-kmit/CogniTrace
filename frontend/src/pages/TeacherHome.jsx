import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { BookOpen, LogOut, ShieldCheck, User, Calendar, Book } from 'lucide-react';

export default function TeacherHome() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-950">
      {/* Top Navbar */}
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center">
              <BookOpen className="w-5 h-5 text-indigo-400" />
            </div>
            <div>
              <h1 className="font-bold text-base text-slate-100 flex items-center gap-2">
                Teacher Portal Placeholder
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950 text-indigo-400 border border-indigo-800/50">Authenticated</span>
              </h1>
              <p className="text-xs text-slate-400">CogniTrace Dataset Platform</p>
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

      {/* Main Content */}
      <main className="flex-1 max-w-4xl w-full mx-auto px-4 py-12 space-y-8">
        
        <div className="glass-panel p-8 rounded-2xl border border-slate-800 space-y-6">
          <div className="flex items-center justify-between pb-6 border-b border-slate-800">
            <div className="flex items-center space-x-4">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-white font-bold text-xl shadow-lg shadow-indigo-500/20">
                {user?.name ? user.name.charAt(0) : 'T'}
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">{user?.name}</h2>
                <p className="text-xs font-mono text-indigo-400 flex items-center gap-1 mt-0.5">
                  <ShieldCheck className="w-3.5 h-3.5" /> Teacher ID: {user?.identifier}
                </p>
              </div>
            </div>
            <span className="px-3 py-1 rounded-full bg-indigo-950/80 text-indigo-300 border border-indigo-800/50 text-xs font-mono">
              ROLE: TEACHER
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
            <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800/80 space-y-1">
              <span className="text-slate-400 flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-indigo-400" /> Target Year
              </span>
              <p className="text-sm font-semibold text-white">{user?.year}</p>
            </div>
            <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800/80 space-y-1">
              <span className="text-slate-400 flex items-center gap-1.5">
                <Book className="w-3.5 h-3.5 text-cyan-400" /> Subject
              </span>
              <p className="text-sm font-semibold text-white">{user?.subject || 'N/A'}</p>
            </div>
            <div className="bg-slate-900/60 p-4 rounded-xl border border-slate-800/80 space-y-1">
              <span className="text-slate-400 flex items-center gap-1.5">
                <User className="w-3.5 h-3.5 text-purple-400" /> Status
              </span>
              <p className="text-sm font-semibold text-emerald-400">JWT Authorized</p>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800/60 text-xs text-slate-400 leading-relaxed">
            <strong className="text-white block mb-1">Phase 1 Placeholder Page</strong>
            Teacher authentication and role authorization verified. Video addition, transcript management, and student interaction telemetry views will be added in subsequent phases.
          </div>
        </div>

      </main>
    </div>
  );
}
