import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Play, LogIn, AlertCircle, ArrowRight, ShieldCheck, GraduationCap, School } from 'lucide-react';

export default function Login() {
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');
    
    if (!identifier.trim()) {
      setErrorMessage('Please enter your Roll Number or Teacher ID.');
      return;
    }
    if (!password) {
      setErrorMessage('Please enter your password.');
      return;
    }

    setIsSubmitting(true);
    try {
      const authenticatedUser = await login(identifier, password);
      if (authenticatedUser.role === 'student') {
        navigate('/student/home');
      } else if (authenticatedUser.role === 'teacher') {
        navigate('/teacher/home');
      }
    } catch (err) {
      setErrorMessage(err.message || 'Login failed. Please verify your credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col justify-center py-12 sm:px-6 lg:px-8 bg-[#F9F9F9]">
      <div className="sm:mx-auto sm:w-full sm:max-w-md space-y-3">
        <div className="flex items-center justify-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-[#0F0F0F] flex items-center justify-center shadow-xs">
            <span className="font-bold text-sm text-[#00C896]">CT</span>
          </div>
          <span className="text-2xl font-bold text-[#0F0F0F] tracking-tight">CogniTrace</span>
        </div>
        <p className="text-center text-sm text-[#606060]">
          Adaptive Video Learning & Assessment Platform
        </p>
      </div>

      <div className="mt-6 sm:mx-auto sm:w-full sm:max-w-md px-4 sm:px-0">
        <div className="bg-[#FFFFFF] border border-[#E5E5E5] rounded-xl py-8 px-6 sm:px-8 shadow-sm">
          
          <div className="mb-6 pb-3 border-b border-[#E5E5E5] flex items-center justify-between">
            <h1 className="text-lg font-semibold text-[#0F0F0F]">Sign In</h1>
            <span className="inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 bg-[#F2F2F2] text-[#606060] rounded-full">
              <ShieldCheck className="w-3.5 h-3.5 text-[#0F0F0F]" /> Auto Role
            </span>
          </div>

          {errorMessage && (
            <div className="mb-5 p-3 rounded-lg bg-[#FFEBEE] border border-[#FFCDD2] flex items-start gap-2.5 text-xs font-medium text-[#C62828]">
              <AlertCircle className="w-4 h-4 text-[#C62828] shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          <form className="space-y-4" onSubmit={handleSubmit}>
            <div>
              <label className="block text-xs font-semibold text-[#0F0F0F] mb-1.5 uppercase tracking-wide">
                Roll Number / Teacher ID
              </label>
              <input
                type="text"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                placeholder="e.g. S24A001 or T24A001"
                disabled={isSubmitting}
                className="w-full px-3.5 py-2.5 rounded-lg bg-[#FFFFFF] border border-[#CCCCCC] text-[#0F0F0F] placeholder-[#909090] text-sm focus:outline-none focus:border-[#0F0F0F] focus:ring-1 focus:ring-[#0F0F0F] transition-all font-mono uppercase"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#0F0F0F] mb-1.5 uppercase tracking-wide">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
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
                <span>Authenticating...</span>
              ) : (
                <>
                  <LogIn className="w-4 h-4" />
                  <span>Sign In</span>
                </>
              )}
            </button>
          </form>

          <div className="mt-7 pt-5 border-t border-[#E5E5E5] space-y-3">
            <p className="text-xs text-[#606060] text-center font-medium">New to CogniTrace? Select your role to register:</p>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <Link
                to="/register/student"
                className="group flex items-center justify-between px-3.5 py-2.5 rounded-lg bg-[#F9F9F9] hover:bg-[#F2F2F2] border border-[#E5E5E5] text-[#0F0F0F] text-xs font-medium transition-colors"
              >
                <div className="flex items-center gap-2">
                  <GraduationCap className="w-4 h-4 text-[#606060] group-hover:text-[#FF0000] transition-colors" />
                  <span>Student</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-[#909090] group-hover:text-[#0F0F0F] transition-transform group-hover:translate-x-0.5" />
              </Link>
              <Link
                to="/register/teacher"
                className="group flex items-center justify-between px-3.5 py-2.5 rounded-lg bg-[#F9F9F9] hover:bg-[#F2F2F2] border border-[#E5E5E5] text-[#0F0F0F] text-xs font-medium transition-colors"
              >
                <div className="flex items-center gap-2">
                  <School className="w-4 h-4 text-[#606060] group-hover:text-[#FF0000] transition-colors" />
                  <span>Teacher</span>
                </div>
                <ArrowRight className="w-3.5 h-3.5 text-[#909090] group-hover:text-[#0F0F0F] transition-transform group-hover:translate-x-0.5" />
              </Link>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

