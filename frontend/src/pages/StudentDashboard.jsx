import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  GraduationCap, 
  Search, 
  X, 
  LogOut, 
  ShieldCheck, 
  BookOpen, 
  Video, 
  ArrowRight, 
  Calendar,
  Sparkles
} from 'lucide-react';

export default function StudentDashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const [teachers, setTeachers] = useState([]);
  const [loadingTeachers, setLoadingTeachers] = useState(true);

  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);
  const [searchErrorMessage, setSearchErrorMessage] = useState('');

  const debounceTimerRef = useRef(null);

  // Fetch authorized teachers for student's year
  const fetchTeachers = async () => {
    setLoadingTeachers(true);
    const token = localStorage.getItem('cognitrace_token');
    try {
      const res = await fetch('/api/v1/student/teachers', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setTeachers(data);
      }
    } catch (err) {
      console.error('Failed to fetch teachers:', err);
    } finally {
      setLoadingTeachers(false);
    }
  };

  useEffect(() => {
    fetchTeachers();
  }, []);

  // Handle live search with debouncing
  const executeSearch = async (term) => {
    if (!term.trim()) {
      setSearchResults([]);
      setHasSearched(false);
      setIsSearching(false);
      return;
    }

    setIsSearching(true);
    setSearchErrorMessage('');
    const token = localStorage.getItem('cognitrace_token');

    try {
      const res = await fetch(`/api/v1/student/courses/search?query=${encodeURIComponent(term.trim())}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSearchResults(data);
        setHasSearched(true);
      } else {
        setSearchErrorMessage('Search failed. Please try again.');
      }
    } catch (err) {
      setSearchErrorMessage('Network error during search.');
    } finally {
      setIsSearching(false);
    }
  };

  const handleSearchChange = (e) => {
    const val = e.target.value;
    setSearchQuery(val);

    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    if (val.trim()) {
      debounceTimerRef.current = setTimeout(() => {
        executeSearch(val);
      }, 300);
    } else {
      setSearchResults([]);
      setHasSearched(false);
    }
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    setSearchResults([]);
    setHasSearched(false);
    setSearchErrorMessage('');
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
  };

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
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <GraduationCap className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-base text-slate-100 flex items-center gap-2">
                Student Dashboard
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/50">Verified</span>
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

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        
        {/* Profile Card */}
        <section className="glass-panel p-6 sm:p-8 rounded-2xl relative overflow-hidden">
          <div className="absolute -top-24 -right-24 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none"></div>
          
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-2">
              <div className="inline-flex items-center gap-1.5 text-xs font-mono text-cyan-400 bg-cyan-950/60 px-3 py-1 rounded-full border border-cyan-800/50">
                <ShieldCheck className="w-3.5 h-3.5" /> Roll Number: {user?.identifier}
              </div>
              <h2 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
                Welcome, {user?.name}
              </h2>
              <p className="text-xs text-slate-400">
                Academic Year: <strong className="text-white">{user?.year}</strong>
              </p>
            </div>

            <div className="flex items-center gap-2 text-xs font-mono bg-slate-900/60 px-4 py-2 rounded-xl border border-slate-800 text-slate-300">
              <Calendar className="w-4 h-4 text-cyan-400" />
              <span>Year Scoped Access: {user?.year}</span>
            </div>
          </div>
        </section>

        {/* Search Bar Section */}
        <section className="glass-panel p-6 rounded-2xl space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Search className="w-5 h-5 text-cyan-400" /> Search Courses
            </h3>
            <span className="text-[11px] font-mono text-slate-400">Scoped to {user?.year}</span>
          </div>

          <div className="relative">
            <div className="relative flex items-center">
              <Search className="w-5 h-5 text-slate-500 absolute left-4" />
              <input
                type="text"
                value={searchQuery}
                onChange={handleSearchChange}
                placeholder="Search by course name (e.g. Binary Search, Arrays, CPU Scheduling)..."
                className="w-full pl-12 pr-10 py-3 rounded-xl bg-slate-900 border border-slate-700 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-all"
              />
              {searchQuery && (
                <button
                  onClick={handleClearSearch}
                  className="absolute right-3 p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
                  title="Clear Search"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>

          {/* Search Results Display */}
          {hasSearched && (
            <div className="pt-4 border-t border-slate-800 space-y-3">
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>Search Results for "{searchQuery}"</span>
                <span>{searchResults.length} course(s) found</span>
              </div>

              {isSearching ? (
                <div className="py-8 text-center text-xs font-mono text-slate-500">Searching catalog...</div>
              ) : searchResults.length === 0 ? (
                <div className="py-8 text-center bg-slate-900/40 rounded-xl border border-slate-800/60 text-xs text-slate-400">
                  No courses found matching your search.
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {searchResults.map((c) => (
                    <div key={c.id} className="glass-card p-5 rounded-xl border border-slate-800 space-y-3 flex flex-col justify-between hover:border-cyan-500/50 transition-all">
                      <div className="space-y-2">
                        <h4 className="font-bold text-sm text-white line-clamp-1">{c.course_name}</h4>
                        <div className="text-xs text-slate-400 space-y-1">
                          <p>Teacher: <strong className="text-slate-200">{c.teacher_name}</strong></p>
                          <p>Subject: <strong className="text-cyan-400">{c.subject}</strong></p>
                          <p className="text-[11px] font-mono text-slate-500">Year: {c.year}</p>
                        </div>
                      </div>
                      <Link
                        to={`/student/course/${c.id}`}
                        className="inline-flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-300 font-semibold text-xs border border-cyan-500/30 transition-colors w-full"
                      >
                        <span>Open Course</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>

        {/* Available Teachers & Subjects Section */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <BookOpen className="w-5 h-5 text-indigo-400" /> Teachers & Subjects ({user?.year})
            </h3>
            <span className="text-xs text-slate-400">Select a subject to view courses</span>
          </div>

          {loadingTeachers ? (
            <div className="py-12 text-center text-xs font-mono text-slate-500">Loading teacher catalog...</div>
          ) : teachers.length === 0 ? (
            <div className="py-12 text-center space-y-2 glass-panel rounded-2xl border border-slate-800">
              <BookOpen className="w-10 h-10 text-slate-600 mx-auto" />
              <p className="text-sm font-semibold text-slate-300">No teachers or subjects are currently available for your academic year.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {teachers.map((t) => (
                <div key={t.teacher_id} className="glass-card p-6 rounded-2xl border border-slate-800 space-y-4 flex flex-col justify-between hover:border-indigo-500/50 transition-all">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono text-indigo-400 bg-indigo-950/60 px-2.5 py-0.5 rounded border border-indigo-800/50">
                        {t.year}
                      </span>
                    </div>
                    <h4 className="text-lg font-bold text-white">{t.subject}</h4>
                    <p className="text-xs text-slate-400">Teacher: <strong className="text-slate-200">{t.teacher_name}</strong></p>
                  </div>

                  <Link
                    to={`/student/teacher/${t.teacher_id}`}
                    className="inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs transition-colors shadow-lg shadow-indigo-600/20 w-full"
                  >
                    <span>Open Subject</span>
                    <ArrowRight className="w-4 h-4" />
                  </Link>
                </div>
              ))}
            </div>
          )}
        </section>

      </main>
    </div>
  );
}
