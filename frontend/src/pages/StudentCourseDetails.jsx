import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  ArrowLeft, 
  Play, 
  BookOpen, 
  AlertCircle,
  Calendar,
  User,
  Clock
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
    <div className="min-h-screen flex flex-col bg-[#FFFFFF] text-[#0F0F0F]">
      <header className="border-b border-[#E5E5E5] bg-[#FFFFFF] sticky top-0 z-50 h-14">
        <div className="max-w-4xl mx-auto px-4 h-full flex items-center justify-between">
          <Link
            to="/student/dashboard"
            className="inline-flex items-center gap-2 text-xs font-semibold text-[#0F0F0F] hover:text-[#FF0000] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Dashboard
          </Link>
          <span className="text-xs font-semibold px-2.5 py-0.5 bg-[#F2F2F2] text-[#606060] rounded-full">
            Tier: {user?.year}
          </span>
        </div>
      </header>

      <main className="flex-1 max-w-3xl w-full mx-auto px-4 py-8">
        {errorMessage ? (
          <div className="p-5 rounded-xl bg-[#FFEBEE] border border-[#FFCDD2] flex items-start gap-3 text-xs text-[#C62828]">
            <AlertCircle className="w-5 h-5 text-[#C62828] shrink-0 mt-0.5" />
            <div>
              <strong className="text-[#0F0F0F] block text-sm mb-0.5 font-bold">Access Restricted</strong>
              <span>{errorMessage}</span>
            </div>
          </div>
        ) : loading ? (
          <div className="py-12 text-center text-xs text-[#606060]">Loading course overview...</div>
        ) : (
          <div className="bg-[#FFFFFF] border border-[#E5E5E5] rounded-xl p-6 sm:p-8 space-y-6 shadow-sm">
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold px-2.5 py-0.5 bg-[#F2F2F2] text-[#0F0F0F] rounded-full">
                  {course.subject}
                </span>
                <span className="text-xs font-semibold px-2.5 py-0.5 bg-[#F9F9F9] border border-[#E5E5E5] text-[#606060] rounded-full">
                  {course.year}
                </span>
              </div>
              <h1 className="text-2xl font-bold text-[#0F0F0F] tracking-tight leading-snug">
                {course.course_name}
              </h1>
              <p className="text-xs text-[#606060]">
                Course Faculty: <strong className="text-[#0F0F0F] font-semibold">{course.teacher_name}</strong> ({course.teacher_id})
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              <div className="bg-[#F9F9F9] border border-[#E5E5E5] p-4 rounded-xl space-y-1">
                <span className="text-[#606060] flex items-center gap-1.5 font-medium">
                  <BookOpen className="w-4 h-4 text-[#FF0000]" /> Subject Discipline
                </span>
                <p className="text-sm font-bold text-[#0F0F0F]">{course.subject}</p>
              </div>
              <div className="bg-[#F9F9F9] border border-[#E5E5E5] p-4 rounded-xl space-y-1">
                <span className="text-[#606060] flex items-center gap-1.5 font-medium">
                  <Calendar className="w-4 h-4 text-[#606060]" /> Published Date
                </span>
                <p className="text-sm font-bold text-[#0F0F0F]">
                  {new Date(course.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}
                </p>
              </div>
            </div>

            <div className="pt-4 border-t border-[#E5E5E5]">
              <Link
                to={`/student/course/${course.id}/watch`}
                className="yt-btn-primary py-3 px-6 text-sm font-semibold w-full sm:w-auto inline-flex items-center justify-center gap-2 shadow-sm"
              >
                <Play className="w-4 h-4 fill-current" />
                <span>Start Video Lesson</span>
              </Link>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

