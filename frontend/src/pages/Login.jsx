import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Activity, LogIn, AlertCircle, ArrowRight, ShieldCheck } from 'lucide-react';

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
    <div className="min-h-screen flex flex-col justify-center py-12 sm:px-6 lg:px-8 relative overflow-hidden">
      {/* Glow Effects */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[500px] h-[500px] bg-cyan-500/10 rounded-full blur-3xl pointer-events-none"></div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md space-y-4">
        <div className="flex justify-center">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-cyan-500 to-indigo-600 flex items-center justify-center shadow-xl shadow-cyan-500/20">
            <Activity className="w-7 h-7 text-white" />
          </div>
        </div>
        <div className="text-center">
          <h2 className="text-2xl font-bold text-white tracking-tight">CogniTrace Platform</h2>
          <p className="mt-1 text-xs text-slate-400">Educational Learning Interaction Dataset Collection</p>
        </div>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="glass-panel py-8 px-6 shadow-2xl rounded-2xl sm:px-10 border border-slate-800">
          
          <div className="mb-6 pb-4 border-b border-slate-800/80 flex items-center justify-between">
            <span className="text-sm font-semibold text-slate-200">Account Login</span>
            <span className="inline-flex items-center gap-1 text-[11px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
              <ShieldCheck className="w-3 h-3 text-cyan-400" /> Auto Role Detection
            </span>
          </div>

          {errorMessage && (
            <div className="mb-5 p-3 rounded-lg bg-rose-950/60 border border-rose-800/60 flex items-start gap-2.5 text-xs text-rose-300">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          <form className="space-y-5" onSubmit={handleSubmit}>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Roll Number / Teacher ID
              </label>
              <input
                type="text"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                placeholder="e.g. S24A001 or T24A001"
                disabled={isSubmitting}
                className="w-full px-3.5 py-2.5 rounded-lg bg-slate-900/90 border border-slate-700 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-all disabled:opacity-50 font-mono uppercase"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                disabled={isSubmitting}
                className="w-full px-3.5 py-2.5 rounded-lg bg-slate-900/90 border border-slate-700 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-all disabled:opacity-50"
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full flex justify-center items-center gap-2 py-2.5 px-4 rounded-lg text-sm font-semibold text-slate-950 bg-cyan-400 hover:bg-cyan-300 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-cyan-500 transition-all disabled:opacity-50 shadow-lg shadow-cyan-500/20"
            >
              {isSubmitting ? (
                <span>Authenticating...</span>
              ) : (
                <>
                  <LogIn className="w-4 h-4" />
                  <span>Login</span>
                </>
              )}
            </button>
          </form>

          <div className="mt-8 pt-6 border-t border-slate-800/80 space-y-3">
            <p className="text-xs text-slate-400 text-center">New to CogniTrace? Register below:</p>
            <div className="grid grid-cols-2 gap-3 text-xs font-medium">
              <Link
                to="/register/student"
                className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 transition-colors text-center"
              >
                <span>Create Student Account</span>
                <ArrowRight className="w-3 h-3 text-cyan-400" />
              </Link>
              <Link
                to="/register/teacher"
                className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 transition-colors text-center"
              >
                <span>Create Teacher Account</span>
                <ArrowRight className="w-3 h-3 text-indigo-400" />
              </Link>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
