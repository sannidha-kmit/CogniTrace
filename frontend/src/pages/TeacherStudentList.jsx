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
  Calendar
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
    <div className="min-h-screen flex flex-col bg-slate-950">
      {/* Navbar */}
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link
            to="/teacher/dashboard"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-400 hover:text-cyan-400 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Dashboard
          </Link>
          <span className="text-xs font-mono text-cyan-400 px-3 py-1 rounded-full bg-cyan-950/60 border border-cyan-800/50">
            Target Year: {user?.year}
          </span>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-8 space-y-6">
        
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800">
          <div>
            <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
              <Users className="w-6 h-6 text-cyan-400" /> Registered Students
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Students registered for <strong className="text-white">{user?.year}</strong> sorted alphanumerically by Roll Number.
            </p>
          </div>

          {/* Search filter */}
          <div className="relative max-w-xs w-full">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-3" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search Roll Number / Name..."
              className="w-full pl-9 pr-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-white placeholder-slate-500 text-xs focus:outline-none focus:ring-2 focus:ring-cyan-500"
            />
          </div>
        </div>

        {errorMessage && (
          <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-800/60 flex items-start gap-2.5 text-xs text-rose-300">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <span>{errorMessage}</span>
          </div>
        )}

        {loading ? (
          <div className="py-16 text-center text-xs font-mono text-slate-500">Loading student directory...</div>
        ) : students.length === 0 ? (
          <div className="py-16 text-center space-y-3 glass-panel rounded-2xl border border-slate-800">
            <UserCheck className="w-12 h-12 text-slate-600 mx-auto" />
            <p className="text-base font-semibold text-white">No students registered for this academic year yet.</p>
            <p className="text-xs text-slate-400">When students register for {user?.year}, their accounts will automatically appear here.</p>
          </div>
        ) : (
          <div className="glass-panel rounded-2xl border border-slate-800 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-900/90 text-slate-400 font-mono uppercase text-[11px] border-b border-slate-800">
                  <tr>
                    <th className="py-3.5 px-6">Roll Number</th>
                    <th className="py-3.5 px-6">Student Name</th>
                    <th className="py-3.5 px-6">Academic Year</th>
                    <th className="py-3.5 px-6 text-right">Dataset Module</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80">
                  {filteredStudents.map((s) => (
                    <tr key={s.id || s.roll_number} className="hover:bg-slate-900/50 transition-colors">
                      <td className="p-4 font-mono font-bold text-cyan-400">
                        <Link 
                          to={`/teacher/students/${s.roll_number}`} 
                          className="hover:underline flex items-center gap-1 text-cyan-400 hover:text-cyan-300"
                        >
                          <span>{s.roll_number}</span>
                          <ExternalLink className="w-3 h-3 text-slate-500" />
                        </Link>
                      </td>
                      <td className="p-4 font-semibold text-white">{s.name}</td>
                      <td className="p-4 font-mono text-slate-300">
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-slate-900 text-slate-300 border border-slate-800 text-[11px]">
                          <Calendar className="w-3 h-3 text-slate-500" /> {s.year}
                        </span>
                      </td>
                      <td className="py-4 px-6 text-right font-mono text-[11px]">
                        <Link
                          to={`/teacher/students/${s.roll_number}`}
                          className="text-slate-400 hover:text-cyan-400 transition-colors"
                        >
                          View Future Dataset Placeholder →
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
