import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  Users, 
  ArrowLeft, 
  UserCheck, 
  ExternalLink, 
  AlertCircle,
  Search,
  Calendar,
  ChevronRight
} from 'lucide-react';

export default function TeacherStudentList() {
  const { user } = useAuth();
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  const fetchStudents = async () => {
    setLoading(true);
    const token = localStorage.getItem('cognitrace_token');
    try {
      const res = await fetch('/api/v1/students/my-year', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setStudents(data);
      } else {
        setErrorMessage('Failed to load registered student list.');
      }
    } catch (err) {
      setErrorMessage(err.message || 'Error connecting to server.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStudents();
  }, []);

  const filteredStudents = students.filter(s => 
    s.roll_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
    s.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="min-h-screen flex flex-col bg-[#F9F9F9] text-[#0F0F0F]">
      {/* Header */}
      <header className="border-b border-[#E5E5E5] bg-[#FFFFFF] sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <Link
            to="/teacher/dashboard"
            className="inline-flex items-center gap-2 text-sm font-medium text-[#606060] hover:text-[#0F0F0F] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Studio Dashboard
          </Link>
          <span className="text-xs font-semibold px-3 py-1 bg-[#F2F2F2] text-[#606060] rounded-full">
            Target Year: {user?.year}
          </span>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 space-y-6">
        
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-[#E5E5E5]">
          <div>
            <h1 className="text-2xl font-bold text-[#0F0F0F] tracking-tight flex items-center gap-2.5">
              <Users className="w-6 h-6 text-[#FF0000]" /> Student Roster
            </h1>
            <p className="text-sm text-[#606060] mt-0.5">
              Students registered for <strong className="text-[#0F0F0F]">{user?.year}</strong> sorted alphanumerically by Roll Number.
            </p>
          </div>

          {/* Search filter */}
          <div className="relative max-w-xs w-full">
            <Search className="w-4 h-4 text-[#909090] absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search Roll No or Name..."
              className="w-full pl-10 pr-4 py-2 rounded-full bg-[#FFFFFF] border border-[#CCCCCC] text-[#0F0F0F] placeholder-[#909090] text-xs focus:outline-none focus:border-[#0F0F0F]"
            />
          </div>
        </div>

        {errorMessage && (
          <div className="p-3.5 rounded-xl bg-[#FFEBEE] border border-[#FFCDD2] flex items-start gap-2.5 text-xs text-[#C62828]">
            <AlertCircle className="w-4 h-4 text-[#C62828] shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}

        {loading ? (
          <div className="py-16 text-center text-sm text-[#606060]">Loading student roster...</div>
        ) : students.length === 0 ? (
          <div className="py-20 text-center space-y-3 bg-[#FFFFFF] border border-[#E5E5E5] rounded-xl max-w-lg mx-auto p-8 shadow-xs">
            <div className="w-16 h-16 rounded-full bg-[#F2F2F2] flex items-center justify-center mx-auto text-[#909090]">
              <UserCheck className="w-8 h-8" />
            </div>
            <h3 className="text-base font-bold text-[#0F0F0F]">No students registered yet</h3>
            <p className="text-xs text-[#606060]">When students sign up for academic year {user?.year}, their interaction records will appear here.</p>
          </div>
        ) : (
          <div className="bg-[#FFFFFF] border border-[#E5E5E5] rounded-xl overflow-hidden shadow-xs">
            <div className="overflow-x-auto custom-scrollbar">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#F9F9F9] text-[#606060] font-semibold uppercase text-xs border-b border-[#E5E5E5]">
                  <tr>
                    <th className="py-3.5 px-5">Roll Number</th>
                    <th className="py-3.5 px-5">Student Name</th>
                    <th className="py-3.5 px-5">Academic Year</th>
                    <th className="py-3.5 px-5 text-right">Analytics & Telemetry</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E5E5E5]">
                  {filteredStudents.map((s) => (
                    <tr key={s.id || s.roll_number} className="hover:bg-[#F9F9F9] transition-colors">
                      <td className="p-4 font-mono font-semibold text-[#0F0F0F]">
                        <Link 
                          to={`/teacher/students/${s.roll_number}`} 
                          className="hover:text-[#FF0000] inline-flex items-center gap-1.5 transition-colors"
                        >
                          <span>{s.roll_number}</span>
                          <ExternalLink className="w-3.5 h-3.5 text-[#909090]" />
                        </Link>
                      </td>
                      <td className="p-4 font-semibold text-[#0F0F0F]">{s.name}</td>
                      <td className="p-4">
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#F2F2F2] text-[#606060] text-xs font-medium">
                          <Calendar className="w-3 h-3 text-[#909090]" /> {s.year}
                        </span>
                      </td>
                      <td className="py-4 px-5 text-right">
                        <Link
                          to={`/teacher/students/${s.roll_number}`}
                          className="yt-btn-secondary py-1.5 px-3.5 text-xs font-semibold inline-flex items-center gap-1.5"
                        >
                          <span>View Dataset Telemetry</span>
                          <ChevronRight className="w-3.5 h-3.5 text-[#606060]" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

      </main>
    </div>
  );
}
