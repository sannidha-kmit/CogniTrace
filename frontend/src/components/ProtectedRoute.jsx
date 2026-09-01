import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Loader2 } from 'lucide-react';

export default function ProtectedRoute({ children, requiredRole }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950 text-cyan-400">
        <div className="flex flex-col items-center space-y-3">
          <Loader2 className="w-8 h-8 animate-spin" />
          <span className="text-xs font-mono text-slate-400">Verifying session credentials...</span>
        </div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (requiredRole && user.role !== requiredRole) {
    // Redirect unauthorized cross-role attempts to their correct home route
    const fallbackPath = user.role === 'student' ? '/student/home' : '/teacher/home';
    return <Navigate to={fallbackPath} replace />;
  }

  return children;
}
