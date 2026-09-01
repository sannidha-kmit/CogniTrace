import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { PlusCircle, ArrowLeft, AlertCircle, Video, CheckCircle2, ShieldCheck } from 'lucide-react';

export default function AddCourse() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [courseName, setCourseName] = useState('');
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');

    const cleanName = courseName.trim();
    const cleanUrl = youtubeUrl.trim();

    if (!cleanName) {
      setErrorMessage('Course Name is required.');
      return;
    }

    if (!cleanUrl) {
      setErrorMessage('YouTube Video URL is required.');
      return;
    }

    const ytPattern = /^(https?:\/\/)?(www\.|m\.|music\.)?(youtube\.com\/(watch\?.*v=|embed\/|v\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})/;
    if (!ytPattern.test(cleanUrl)) {
      setErrorMessage('Please enter a valid YouTube single video URL (e.g. https://www.youtube.com/watch?v=... or https://youtu.be/...).');
      return;
    }

    setIsSubmitting(true);
    const token = localStorage.getItem('cognitrace_token');

    try {
      const res = await fetch('/api/v1/courses', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          course_name: cleanName,
          youtube_url: cleanUrl
        })
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || data.message || 'Failed to create course.');
      }

      navigate('/teacher/courses');
    } catch (err) {
      setErrorMessage(err.message || 'Failed to create course.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-950">
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link
            to="/teacher/dashboard"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-400 hover:text-indigo-400 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Dashboard
          </Link>
          <span className="text-xs font-mono text-slate-400 flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" /> Ownership: {user?.identifier}
          </span>
        </div>
      </header>

      <main className="flex-1 max-w-2xl w-full mx-auto px-4 py-12">
        <div className="glass-panel p-8 rounded-2xl border border-slate-800 space-y-6">
          <div>
            <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
              <PlusCircle className="w-6 h-6 text-indigo-400" /> Add New Course
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Add a new course module with a single YouTube video URL for <strong className="text-white">{user?.year}</strong> ({user?.subject}).
            </p>
          </div>

          {errorMessage && (
            <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-800/60 flex items-start gap-2.5 text-xs text-rose-300">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          <form className="space-y-5" onSubmit={handleSubmit}>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">Course Name</label>
              <input
                type="text"
                value={courseName}
                onChange={(e) => setCourseName(e.target.value)}
                placeholder="e.g. Binary Search Trees & Applications"
                disabled={isSubmitting}
                className="w-full px-3.5 py-2.5 rounded-lg bg-slate-900/90 border border-slate-700 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all disabled:opacity-50"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">YouTube Video URL</label>
              <input
                type="url"
                value={youtubeUrl}
                onChange={(e) => setYoutubeUrl(e.target.value)}
                placeholder="https://www.youtube.com/watch?v=..."
                disabled={isSubmitting}
                className="w-full px-3.5 py-2.5 rounded-lg bg-slate-900/90 border border-slate-700 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all disabled:opacity-50 font-mono"
              />
              <p className="text-[11px] text-slate-500 mt-1 flex items-center gap-1">
                <Video className="w-3 h-3 text-cyan-400" /> Must be a single YouTube video watch link. Playlist links are excluded.
              </p>
            </div>

            <div className="bg-slate-900/50 p-4 rounded-xl border border-slate-800/80 text-xs text-slate-400 space-y-1">
              <span className="text-slate-300 font-semibold block">Automatic Backend Ownership Binding:</span>
              <p>Year: <strong className="text-white">{user?.year}</strong> | Subject: <strong className="text-white">{user?.subject}</strong> | Created By: <strong className="text-white">{user?.name}</strong></p>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full flex justify-center items-center gap-2 py-3 px-4 rounded-xl text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-all disabled:opacity-50 shadow-lg shadow-indigo-600/20"
            >
              {isSubmitting ? (
                <span>Publishing Course...</span>
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Add Course</span>
                </>
              )}
            </button>
          </form>

        </div>
      </main>
    </div>
  );
}
