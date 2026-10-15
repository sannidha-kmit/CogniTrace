import React, { useState, useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  Play, 
  Search, 
  X, 
  LogOut, 
  ShieldCheck, 
  BookOpen, 
  ArrowRight, 
  Calendar,
  Compass,
  Video,
  User,
  GraduationCap
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
    <div className="min-h-screen flex flex-col bg-[#FFFFFF] text-[#0F0F0F]">
      {/* YouTube-Inspired Top Navbar */}
      <header className="border-b border-[#E5E5E5] bg-[#FFFFFF] sticky top-0 z-50 h-14">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-full flex items-center justify-between gap-4">
          
          {/* Left: Brand / Logo */}
          <div className="flex items-center gap-3 shrink-0">
            <Link to="/student/dashboard" className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-[#0F0F0F] flex items-center justify-center shadow-xs">
                <span className="font-bold text-xs text-[#00C896]">CT</span>
              </div>
              <span className="font-bold text-lg text-[#0F0F0F] tracking-tight hidden sm:inline">
                CogniTrace
              </span>
            </Link>
            <span className="text-xs font-semibold px-2.5 py-0.5 bg-[#F2F2F2] text-[#606060] rounded-full">
              Student
            </span>
          </div>

          {/* Center: YouTube-style Search Bar */}
          <div className="flex-1 max-w-xl mx-2 hidden sm:block">
            <div className="yt-search-container">
              <input
                type="text"
                value={searchQuery}
                onChange={handleSearchChange}
                placeholder="Search courses, concepts, topics..."
                className="yt-search-input"
              />
              {searchQuery && (
                <button
                  onClick={handleClearSearch}
                  className="px-2 text-[#606060] hover:text-[#0F0F0F] cursor-pointer"
                  title="Clear"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
              <button 
                onClick={() => executeSearch(searchQuery)}
                className="yt-search-btn"
                title="Search"
              >
                <Search className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Right: User profile badge & Logout */}
          <div className="flex items-center gap-3 shrink-0">
            <div className="hidden md:flex items-center gap-2 text-xs font-medium text-[#606060] bg-[#F2F2F2] px-3 py-1.5 rounded-full">
              <GraduationCap className="w-3.5 h-3.5 text-[#0F0F0F]" />
              <span>{user?.year}</span>
              <span className="text-[#CCCCCC]">|</span>
              <span className="font-mono text-[#0F0F0F]">{user?.identifier}</span>
            </div>

            <button
              onClick={handleLogout}
              className="bg-[#F2F2F2] hover:bg-[#E5E5E5] text-[#0F0F0F] text-xs font-semibold py-1.5 px-3.5 rounded-full inline-flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <LogOut className="w-3.5 h-3.5 text-[#606060]" />
              <span>Sign Out</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        
        {/* Mobile Search Bar (visible only on small screens) */}
        <div className="block sm:hidden">
          <div className="yt-search-container">
            <input
              type="text"
              value={searchQuery}
              onChange={handleSearchChange}
              placeholder="Search courses, concepts..."
              className="yt-search-input"
            />
            {searchQuery && (
              <button onClick={handleClearSearch} className="px-2 text-[#606060]">
                <X className="w-4 h-4" />
              </button>
            )}
            <button onClick={() => executeSearch(searchQuery)} className="yt-search-btn">
              <Search className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Welcome Channel Header Card */}
        <section className="bg-[#F9F9F9] border border-[#E5E5E5] rounded-xl p-5 sm:p-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-1">
              <div className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-0.5 bg-[#FFFFFF] border border-[#E5E5E5] text-[#0F0F0F] rounded-full">
                <ShieldCheck className="w-3.5 h-3.5 text-[#FF0000]" /> Student ID: {user?.identifier}
              </div>
              <h1 className="text-xl sm:text-2xl font-bold text-[#0F0F0F] tracking-tight">
                Welcome back, {user?.name}
              </h1>
              <p className="text-xs text-[#606060]">
                Enrolled Tier: <strong className="text-[#0F0F0F] font-semibold">{user?.year}</strong> • Explore video lectures and adaptive mastery quizzes
              </p>
            </div>

            <div className="flex items-center gap-2 text-xs font-medium bg-[#FFFFFF] border border-[#E5E5E5] px-3.5 py-2 rounded-lg text-[#606060] self-start md:self-auto shadow-sm">
              <Calendar className="w-3.5 h-3.5 text-[#FF0000]" />
              <span>Current Term: {user?.year}</span>
            </div>
          </div>
        </section>

        {/* Search Results Display */}
        {hasSearched && (
          <section className="bg-[#FFFFFF] border border-[#E5E5E5] rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between text-xs text-[#606060] font-medium border-b border-[#E5E5E5] pb-3">
              <span>Results for "<strong className="text-[#0F0F0F]">{searchQuery}</strong>"</span>
              <span className="px-2.5 py-0.5 bg-[#F2F2F2] rounded-full text-[#0F0F0F] font-semibold">{searchResults.length} course(s) found</span>
            </div>

            {isSearching ? (
              <div className="py-8 text-center text-xs text-[#606060]">Searching catalog...</div>
            ) : searchResults.length === 0 ? (
              <div className="py-8 text-center bg-[#F9F9F9] rounded-lg border border-[#E5E5E5] text-xs text-[#606060]">
                No courses found matching your query.
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {searchResults.map((c) => (
                  <div key={c.id} className="yt-card p-4 rounded-xl flex flex-col justify-between space-y-3">
                    <div className="space-y-1.5">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] font-semibold px-2 py-0.5 bg-[#F2F2F2] text-[#0F0F0F] rounded">
                          {c.subject}
                        </span>
                        <span className="text-[11px] text-[#606060]">{c.year}</span>
                      </div>
                      <h2 className="font-semibold text-sm text-[#0F0F0F] line-clamp-1">{c.course_name}</h2>
                      <p className="text-xs text-[#606060]">Instructor: <strong className="text-[#0F0F0F] font-medium">{c.teacher_name}</strong></p>
                    </div>
                    <Link
                      to={`/student/course/${c.id}`}
                      className="yt-btn-primary w-full text-xs font-semibold py-2"
                    >
                      <Play className="w-3.5 h-3.5 fill-current" />
                      <span>Open Video Lesson</span>
                    </Link>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* Available Subjects / Video Lectures Section */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-bold text-[#0F0F0F] flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-[#FF0000]" /> Subjects & Faculty ({user?.year})
            </h2>
            <span className="text-xs text-[#606060]">Select a subject to view available video lectures</span>
          </div>

          {loadingTeachers ? (
            <div className="py-12 text-center text-xs text-[#606060]">Loading academic courses...</div>
          ) : teachers.length === 0 ? (
            <div className="py-12 text-center space-y-2 bg-[#F9F9F9] rounded-xl border border-[#E5E5E5] p-6">
              <Video className="w-8 h-8 text-[#909090] mx-auto" />
              <p className="text-xs font-semibold text-[#606060]">No subjects currently registered for your academic year.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {teachers.map((t) => (
                <div key={t.teacher_id} className="yt-card p-5 rounded-xl flex flex-col justify-between space-y-4">
                  <div className="space-y-2.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold px-2.5 py-0.5 bg-[#F2F2F2] text-[#0F0F0F] rounded-full">
                        {t.year}
                      </span>
                      <span className="text-xs font-mono text-[#909090]">
                        {t.teacher_id}
                      </span>
                    </div>
                    <h3 className="text-lg font-bold text-[#0F0F0F] tracking-tight">{t.subject}</h3>
                    <p className="text-xs text-[#606060]">Faculty: <strong className="text-[#0F0F0F] font-semibold">{t.teacher_name}</strong></p>
                  </div>

                  <Link
                    to={`/student/teacher/${t.teacher_id}`}
                    className="yt-btn-primary w-full text-xs font-semibold py-2.5 flex items-center justify-center gap-2"
                  >
                    <Play className="w-3.5 h-3.5 fill-current" />
                    <span>View Video Lessons</span>
                    <ArrowRight className="w-3.5 h-3.5 ml-auto" />
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

