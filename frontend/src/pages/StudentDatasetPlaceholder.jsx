import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Users, ShieldCheck, Activity, LineChart, FileText } from 'lucide-react';

export default function StudentDatasetPlaceholder() {
  const { rollNumber } = useParams();

  return (
    <div className="min-h-screen flex flex-col bg-slate-950">
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link
            to="/teacher/students"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-400 hover:text-cyan-400 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Student List
          </Link>
          <span className="text-xs font-mono text-cyan-400 px-3 py-1 rounded-full bg-cyan-950/60 border border-cyan-800/50">
            Student: {rollNumber}
          </span>
        </div>
      </header>

      <main className="flex-1 max-w-3xl w-full mx-auto px-4 py-12">
        <div className="glass-panel p-8 rounded-2xl border border-slate-800 space-y-6 text-center">
          
          <div className="w-16 h-16 rounded-2xl bg-cyan-950/80 border border-cyan-800/60 flex items-center justify-center text-cyan-400 mx-auto">
            <Activity className="w-8 h-8 animate-pulse" />
          </div>

          <div className="space-y-2">
            <span className="inline-flex items-center gap-1 text-xs font-mono text-cyan-400 bg-slate-900 px-3 py-1 rounded-full border border-slate-800">
              <ShieldCheck className="w-3.5 h-3.5" /> Roll Number: {rollNumber}
            </span>
            <h2 className="text-2xl font-bold text-white tracking-tight">
              Student Learning Interaction Dataset Viewer
            </h2>
            <p className="text-xs text-slate-400 max-w-lg mx-auto">
              Future Dataset Telemetry Placeholder Module
            </p>
          </div>

          <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-300 space-y-3 text-left">
            <h3 className="font-semibold text-white flex items-center gap-2">
              <LineChart className="w-4 h-4 text-cyan-400" /> Module Scope Boundary Notice
            </h3>
            <p className="leading-relaxed text-slate-400">
              This module will visualize real student learning interaction telemetry—including video playback events (plays, pauses, seeks, playback rate adjustments), pause popups, and concept understanding events—when students watch assigned videos in future phases.
            </p>
            <p className="leading-relaxed text-slate-400">
              <strong className="text-white">Strict Research Data Rule:</strong> Zero fake telemetry or synthetic records are generated. Data will populate dynamically only when real student interactions occur.
            </p>
          </div>

          <div className="pt-4">
            <Link
              to="/teacher/students"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 text-xs font-medium transition-colors"
            >
              <Users className="w-4 h-4 text-cyan-400" /> Return to Registered Students
            </Link>
          </div>

        </div>
      </main>
    </div>
  );
}
