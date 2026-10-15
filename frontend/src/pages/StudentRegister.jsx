import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { UserCheck, AlertCircle, ArrowLeft, ShieldCheck, Play } from 'lucide-react';

const VALID_YEARS = ["1st Year", "2nd Year", "3rd Year", "4th Year"];

export default function StudentRegister() {
  const [formData, setFormData] = useState({
    roll_number: '',
    name: '',
    year: '1st Year',
    password: '',
    confirm_password: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const { registerStudent } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');

    const cleanRoll = formData.roll_number.trim().toUpperCase();
    const cleanName = formData.name.trim();

    if (!cleanRoll) {
      setErrorMessage('Roll Number is required.');
      return;
    }

    if (!/^S[A-Za-z0-9]+$/.test(cleanRoll)) {
      setErrorMessage("Roll Number must start with 'S' followed by alphanumeric characters (e.g. S24A001).");
      return;
    }

    if (!cleanName) {
      setErrorMessage('Student Name is required.');
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
      await registerStudent({
        roll_number: cleanRoll,
        name: cleanName,
        year: formData.year,
        password: formData.password,
        confirm_password: formData.confirm_password
      });
      navigate('/student/home');
    } catch (err) {
      setErrorMessage(err.message || 'Registration failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-center py-12 sm:px-6 lg:px-8 bg-[#F9F9F9]">
      <div className="sm:mx-auto sm:w-full sm:max-w-md space-y-2.5 px-4 sm:px-0">
        <Link 
          to="/login"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#606060] hover:text-[#0F0F0F] transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Login
        </Link>
        <div className="flex items-center gap-2">
          <div className="w-8 h-6 rounded-md bg-[#FF0000] flex items-center justify-center shadow-sm">
            <Play className="w-3.5 h-3.5 text-white fill-white ml-0.5" />
          </div>
          <h1 className="text-2xl font-bold text-[#0F0F0F] tracking-tight">Student Registration</h1>
        </div>
        <p className="text-xs text-[#606060]">Join the CogniTrace Adaptive Learning Platform</p>
      </div>

      <div className="mt-5 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div className="bg-[#FFFFFF] border border-[#E5E5E5] rounded-xl py-7 px-6 sm:px-8 shadow-sm">
          
          <div className="mb-5 pb-3.5 border-b border-[#E5E5E5] flex items-center justify-between">
            <span className="text-xs font-semibold text-[#0F0F0F] uppercase tracking-wide">Student Profile</span>
            <span className="inline-flex items-center gap-1 text-xs font-medium px-2.5 py-0.5 bg-[#F2F2F2] text-[#606060] rounded-full">
              <ShieldCheck className="w-3.5 h-3.5 text-[#0F0F0F]" /> Prefix: S...
            </span>
          </div>

          {errorMessage && (
            <div className="mb-4 p-3 rounded-lg bg-[#FFEBEE] border border-[#FFCDD2] flex items-start gap-2 text-xs font-medium text-[#C62828]">
              <AlertCircle className="w-4 h-4 text-[#C62828] shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label className="block text-xs font-semibold text-[#0F0F0F] mb-1.5 uppercase tracking-wide">Roll Number</label>
              <input
                type="text"
                name="roll_number"
                value={formData.roll_number}
                onChange={handleChange}
                placeholder="e.g. S24A001"
                disabled={isSubmitting}
                className="w-full px-3.5 py-2.5 rounded-lg bg-[#FFFFFF] border border-[#CCCCCC] text-[#0F0F0F] placeholder-[#909090] text-sm focus:outline-none focus:border-[#0F0F0F] focus:ring-1 focus:ring-[#0F0F0F] transition-all font-mono uppercase"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#0F0F0F] mb-1.5 uppercase tracking-wide">Student Name</label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                placeholder="e.g. Alex Johnson"
                disabled={isSubmitting}
                className="w-full px-3.5 py-2.5 rounded-lg bg-[#FFFFFF] border border-[#CCCCCC] text-[#0F0F0F] placeholder-[#909090] text-sm focus:outline-none focus:border-[#0F0F0F] focus:ring-1 focus:ring-[#0F0F0F] transition-all"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#0F0F0F] mb-1.5 uppercase tracking-wide">Academic Year</label>
              <select
                name="year"
                value={formData.year}
                onChange={handleChange}
                disabled={isSubmitting}
                className="w-full px-3.5 py-2.5 rounded-lg bg-[#FFFFFF] border border-[#CCCCCC] text-[#0F0F0F] text-sm focus:outline-none focus:border-[#0F0F0F] focus:ring-1 focus:ring-[#0F0F0F] transition-all"
              >
                {VALID_YEARS.map(yr => (
                  <option key={yr} value={yr} className="bg-white text-[#0F0F0F]">{yr}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#0F0F0F] mb-1.5 uppercase tracking-wide">Password</label>
              <input
                type="password"
                name="password"
                value={formData.password}
                onChange={handleChange}
                placeholder="Minimum 6 characters"
                disabled={isSubmitting}
                className="w-full px-3.5 py-2.5 rounded-lg bg-[#FFFFFF] border border-[#CCCCCC] text-[#0F0F0F] placeholder-[#909090] text-sm focus:outline-none focus:border-[#0F0F0F] focus:ring-1 focus:ring-[#0F0F0F] transition-all"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#0F0F0F] mb-1.5 uppercase tracking-wide">Confirm Password</label>
              <input
                type="password"
                name="confirm_password"
                value={formData.confirm_password}
                onChange={handleChange}
                placeholder="Re-enter password"
                disabled={isSubmitting}
                className="w-full px-3.5 py-2.5 rounded-lg bg-[#FFFFFF] border border-[#CCCCCC] text-[#0F0F0F] placeholder-[#909090] text-sm focus:outline-none focus:border-[#0F0F0F] focus:ring-1 focus:ring-[#0F0F0F] transition-all"
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full bg-[#FF0000] hover:bg-[#CC0000] text-white font-semibold rounded-full py-2.5 text-sm transition-colors duration-150 inline-flex items-center justify-center gap-2 cursor-pointer shadow-sm active:scale-98 mt-2 disabled:bg-[#E5E5E5] disabled:text-[#AAAAAA]"
            >
              {isSubmitting ? (
                <span>Registering Student...</span>
              ) : (
                <>
                  <UserCheck className="w-4 h-4" />
                  <span>Create Student Account</span>
                </>
              )}
            </button>
          </form>

        </div>
      </div>
    </div>
  );
}

