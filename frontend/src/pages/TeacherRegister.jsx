import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { UserCheck, AlertCircle, ArrowLeft, ShieldCheck } from 'lucide-react';

const VALID_YEARS = ["1st Year", "2nd Year", "3rd Year", "4th Year"];

export default function TeacherRegister() {
  const [formData, setFormData] = useState({
    teacher_id: '',
    name: '',
    year: '1st Year',
    subject: '',
    password: '',
    confirm_password: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const { registerTeacher } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');

    const cleanTeacherId = formData.teacher_id.trim().toUpperCase();
    const cleanName = formData.name.trim();
    const cleanSubject = formData.subject.trim();

    if (!cleanTeacherId) {
      setErrorMessage('Teacher ID is required.');
      return;
    }

    if (!/^T[A-Za-z0-9]+$/.test(cleanTeacherId)) {
      setErrorMessage("Teacher ID must start with 'T' followed by alphanumeric characters (e.g. T24A001).");
      return;
    }

    if (!cleanName) {
      setErrorMessage('Teacher Name is required.');
      return;
    }

    if (!cleanSubject) {
      setErrorMessage('Subject is required.');
      return;
    }

    if (!formData.password) {
      setErrorMessage('Password is required.');
      return;
    }

    if (formData.password.length < 6) {
      setErrorMessage('Password must be at least 6 characters long.');
      return;
    }

    if (formData.password !== formData.confirm_password) {
      setErrorMessage('Passwords do not match.');
      return;
    }

    setIsSubmitting(true);
    try {
      await registerTeacher({
        teacher_id: cleanTeacherId,
        name: cleanName,
        year: formData.year,
        subject: cleanSubject,
        password: formData.password,
        confirm_password: formData.confirm_password
      });
      navigate('/teacher/home');
    } catch (err) {
      setErrorMessage(err.message || 'Teacher registration failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative overflow-hidden">
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[500px] h-[500px] bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md space-y-3">
        <Link 
          to="/login"
          className="inline-flex items-center gap-1 text-xs font-medium text-slate-400 hover:text-indigo-400 transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Login
        </Link>
        <h2 className="text-2xl font-bold text-white tracking-tight">Teacher Registration</h2>
        <p className="text-xs text-slate-400">CogniTrace Dataset Collection Platform</p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="glass-panel py-8 px-6 shadow-2xl rounded-2xl sm:px-10 border border-slate-800">
          
          <div className="mb-6 pb-4 border-b border-slate-800/80 flex items-center justify-between">
            <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider">Teacher Credentials</span>
            <span className="inline-flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-indigo-950/60 text-indigo-300 border border-indigo-800/50">
              <ShieldCheck className="w-3 h-3 text-indigo-400" /> Format: T...
            </span>
          </div>

          {errorMessage && (
            <div className="mb-5 p-3 rounded-lg bg-rose-950/60 border border-rose-800/60 flex items-start gap-2.5 text-xs text-rose-300">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Teacher ID</label>
              <input
                type="text"
                name="teacher_id"
                value={formData.teacher_id}
                onChange={handleChange}
                placeholder="e.g. T24A001"
                disabled={isSubmitting}
                className="w-full px-3.5 py-2.5 rounded-lg bg-slate-900/90 border border-slate-700 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all disabled:opacity-50 font-mono uppercase"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Teacher Name</label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                placeholder="e.g. Prof. Sarah Connor"
                disabled={isSubmitting}
                className="w-full px-3.5 py-2.5 rounded-lg bg-slate-900/90 border border-slate-700 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all disabled:opacity-50"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Target Academic Year</label>
              <select
                name="year"
                value={formData.year}
                onChange={handleChange}
                disabled={isSubmitting}
                className="w-full px-3.5 py-2.5 rounded-lg bg-slate-900/90 border border-slate-700 text-white text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all disabled:opacity-50"
              >
                {VALID_YEARS.map(yr => (
                  <option key={yr} value={yr} className="bg-slate-900 text-white">{yr}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Subject</label>
              <input
                type="text"
                name="subject"
                value={formData.subject}
                onChange={handleChange}
                placeholder="e.g. Data Structures & Algorithms"
                disabled={isSubmitting}
                className="w-full px-3.5 py-2.5 rounded-lg bg-slate-900/90 border border-slate-700 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all disabled:opacity-50"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Password</label>
              <input
                type="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="Minimum 6 characters"
                disabled={isSubmitting}
                className="w-full px-3.5 py-2.5 rounded-lg bg-slate-900/90 border border-slate-700 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all disabled:opacity-50"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">Confirm Password</label>
              <input
                type="password"
                name="confirm_password"
                value={formData.confirm_password}
                onChange={handleChange}
                placeholder="Re-enter password"
                disabled={isSubmitting}
                className="w-full px-3.5 py-2.5 rounded-lg bg-slate-900/90 border border-slate-700 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all disabled:opacity-50"
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full flex justify-center items-center gap-2 py-2.5 px-4 rounded-lg text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-all disabled:opacity-50 shadow-lg shadow-indigo-600/20 mt-2"
            >
              {isSubmitting ? (
                <span>Creating Account...</span>
              ) : (
                <>
                  <UserCheck className="w-4 h-4" />
                  <span>Create Teacher Account</span>
                </>
              )}
            </button>
          </form>

        </div>
      </div>
    </div>
  );
}
