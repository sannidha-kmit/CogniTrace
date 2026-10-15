import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  ArrowLeft, 
  Play, 
  Video, 
  Calendar, 
  AlertCircle,
  User
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
    <div className="min-h-screen flex flex-col bg-[#FFFFFF] text-[#0F0F0F]">
      {/* Top Navbar */}
      <header className="border-b border-[#E5E5E5] bg-[#FFFFFF] sticky top-0 z-50 h-14">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-full flex items-center justify-between">
          <Link
            to="/student/dashboard"
            className="inline-flex items-center gap-2 text-xs font-semibold text-[#0F0F0F] hover:text-[#FF0000] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Back to All Subjects
          </Link>
          <span className="text-xs font-semibold px-2.5 py-0.5 bg-[#F2F2F2] text-[#606060] rounded-full">
            Scope: {user?.year}
          </span>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        
        {/* Channel Banner */}
        <div className="bg-[#F9F9F9] border border-[#E5E5E5] rounded-xl p-5 sm:p-6 space-y-2">
          <div className="flex items-center justify-between">
            <h1 className="text-xl sm:text-2xl font-bold text-[#0F0F0F] tracking-tight">
              {teacherInfo?.subject || 'Subject Courses'}
            </h1>
            <span className="text-xs font-semibold px-2.5 py-0.5 bg-[#FFFFFF] border border-[#E5E5E5] text-[#0F0F0F] rounded-full">
              {teacherInfo?.year || user?.year}
            </span>
          </div>
          <p className="text-xs text-[#606060]">
            Course Faculty: <strong className="text-[#0F0F0F] font-medium">{teacherInfo?.name || teacherId}</strong>
          </p>
        </div>

        {errorMessage && (
          <div className="p-3.5 rounded-lg bg-[#FFEBEE] border border-[#FFCDD2] flex items-start gap-2.5 text-xs text-[#C62828]">
            <AlertCircle className="w-4 h-4 text-[#C62828] shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}

        {loading ? (
          <div className="py-12 text-center text-xs text-[#606060]">Loading video lessons...</div>
        ) : courses.length === 0 ? (
          <div className="py-12 text-center space-y-2 bg-[#F9F9F9] rounded-xl border border-[#E5E5E5] p-6">
            <Video className="w-8 h-8 text-[#909090] mx-auto" />
            <p className="text-sm font-medium text-[#0F0F0F]">No video courses have been added by this instructor yet.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {courses.map((c) => (
              <div key={c.id} className="yt-card p-4 rounded-xl flex flex-col justify-between space-y-3">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-semibold px-2 py-0.5 bg-[#F2F2F2] text-[#0F0F0F] rounded">
                      {c.subject}
                    </span>
                    <span className="text-xs font-mono text-[#909090]">
                      {c.year}
                    </span>
                  </div>
                  <h2 className="font-bold text-base text-[#0F0F0F] leading-snug line-clamp-2">{c.course_name}</h2>
                  <div className="text-xs text-[#606060] flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-[#909090]" />
                    <span>Added {new Date(c.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })}</span>
                  </div>
                </div>

                <Link
                  to={`/student/course/${c.id}`}
                  className="yt-btn-primary w-full text-xs font-semibold py-2.5 flex items-center justify-center gap-2 mt-2"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Start Video Lesson</span>
                </Link>
              </div>
            ))}
          </div>
        )}

      </main>
    </div>
  );
}

