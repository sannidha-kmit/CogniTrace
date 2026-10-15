import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { PlusCircle, ArrowLeft, AlertCircle, Video, CheckCircle2, ShieldCheck, PlaySquare } from 'lucide-react';

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
      setErrorMessage('Course Title is required.');
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
    <div className="min-h-screen flex flex-col bg-[#F9F9F9] text-[#0F0F0F]">
      <header className="border-b border-[#E5E5E5] bg-[#FFFFFF] sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <Link
            to="/teacher/courses"
            className="inline-flex items-center gap-2 text-sm font-medium text-[#606060] hover:text-[#0F0F0F] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Content
          </Link>
          <span className="text-xs font-medium px-3 py-1 bg-[#F2F2F2] text-[#606060] rounded-full flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-[#2E7D32]" /> {user?.identifier} ({user?.subject})
          </span>
        </div>
      </header>

      <main className="flex-1 max-w-xl w-full mx-auto px-4 py-10">
        <div className="bg-[#FFFFFF] border border-[#E5E5E5] rounded-xl p-6 sm:p-8 space-y-6 shadow-xs">
          <div className="flex items-center gap-3 pb-4 border-b border-[#E5E5E5]">
            <div className="w-10 h-10 rounded-full bg-[#F2F2F2] flex items-center justify-center text-[#0F0F0F] shrink-0">
              <Video className="w-5 h-5" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-[#0F0F0F]">Upload Video Lecture</h1>
              <p className="text-xs text-[#606060] mt-0.5">
                Add an educational YouTube video for <span className="font-semibold text-[#0F0F0F]">{user?.year}</span> ({user?.subject})
              </p>
            </div>
          </div>

          {errorMessage && (
            <div className="p-3.5 rounded-lg bg-[#FFEBEE] border border-[#FFCDD2] flex items-start gap-2.5 text-xs text-[#C62828]">
              <AlertCircle className="w-4 h-4 text-[#C62828] shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label className="block text-xs font-semibold text-[#0F0F0F] mb-1.5">Video Title</label>
              <input
                type="text"
                value={courseName}
                onChange={(e) => setCourseName(e.target.value)}
                placeholder="e.g. Unit 3: Graph Traversal Algorithms & BFS/DFS"
                disabled={isSubmitting}
                className="w-full px-3.5 py-2.5 rounded-lg bg-[#FFFFFF] border border-[#CCCCCC] text-[#0F0F0F] placeholder-[#909090] text-sm focus:outline-none focus:border-[#0F0F0F] transition-colors disabled:opacity-50"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#0F0F0F] mb-1.5">YouTube Video URL</label>
              <input
                type="url"
                value={youtubeUrl}
                onChange={(e) => setYoutubeUrl(e.target.value)}
                placeholder="https://www.youtube.com/watch?v=..."
                disabled={isSubmitting}
                className="w-full px-3.5 py-2.5 rounded-lg bg-[#FFFFFF] border border-[#CCCCCC] text-[#0F0F0F] placeholder-[#909090] text-sm focus:outline-none focus:border-[#0F0F0F] transition-colors disabled:opacity-50 font-mono"
              />
              <p className="text-xs text-[#606060] mt-1.5 flex items-center gap-1.5">
                <Video className="w-3.5 h-3.5 text-[#606060]" /> Accepts standard YouTube watch URLs and shortened youtu.be links.
              </p>
            </div>

            <div className="bg-[#F9F9F9] p-3.5 rounded-lg border border-[#E5E5E5] text-xs text-[#606060] space-y-1">
              <span className="text-[#0F0F0F] font-semibold block">Metadata Binding:</span>
              <p>Target Class: <strong className="text-[#0F0F0F]">{user?.year}</strong> | Subject: <strong className="text-[#0F0F0F]">{user?.subject}</strong> | Instructor: <strong className="text-[#0F0F0F]">{user?.name}</strong></p>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full yt-btn-primary py-2.5 px-4 font-semibold flex justify-center items-center gap-2 text-sm mt-3"
            >
              {isSubmitting ? (
                <span>Publishing Video...</span>
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Publish Video Course</span>
                </>
              )}
            </button>
          </form>

        </div>
      </main>
    </div>
  );
}
