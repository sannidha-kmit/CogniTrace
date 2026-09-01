import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { 
  Database, 
  ArrowLeft,
  MousePointer2,
  FileText,
  BrainCircuit,
  Link as LinkIcon,
  BarChart,
  Download,
  Eye,
  Loader2
} from 'lucide-react';

const datasetConfig = [
  {
    id: 'interactions',
    title: 'Interaction Telemetry',
    description: 'Raw dataset of student video interactions (Play, Pause, Seek, Speed Changes).',
    icon: MousePointer2,
    color: 'text-blue-400',
    bg: 'bg-blue-950/80',
    border: 'border-blue-800/60',
    hover: 'hover:border-blue-500/50'
  },
  {
    id: 'transcripts',
    title: 'Course Transcripts',
    description: 'NLP-generated transcripts from Faster-Whisper, mapped to timestamps.',
    icon: FileText,
    color: 'text-emerald-400',
    bg: 'bg-emerald-950/80',
    border: 'border-emerald-800/60',
    hover: 'hover:border-emerald-500/50'
  },
  {
    id: 'concepts',
    title: 'Concept Segments',
    description: 'Educational concepts automatically extracted from transcripts.',
    icon: BrainCircuit,
    color: 'text-purple-400',
    bg: 'bg-purple-950/80',
    border: 'border-purple-800/60',
    hover: 'hover:border-purple-500/50'
  },
  {
    id: 'mappings',
    title: 'Concept-Event Mappings',
    description: 'Phase 7 intersection mapping raw telemetry to specific concepts.',
    icon: LinkIcon,
    color: 'text-amber-400',
    bg: 'bg-amber-950/80',
    border: 'border-amber-800/60',
    hover: 'hover:border-amber-500/50'
  },
  {
    id: 'difficulty',
    title: 'Difficulty Dataset',
    description: 'Phase 8 deterministic difficulty scores based strictly on real interaction data.',
    icon: BarChart,
    color: 'text-rose-400',
    bg: 'bg-rose-950/80',
    border: 'border-rose-800/60',
    hover: 'hover:border-rose-500/50'
  }
];

export default function TeacherDatasetManagement() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [exporting, setExporting] = useState(null); // stores dataset id

  const fetchSummary = async () => {
    const token = localStorage.getItem('cognitrace_token');
    if (!token) return;
    try {
      const res = await fetch('/api/v1/teacher/datasets/summary', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Failed to fetch dataset summary');
      const data = await res.json();
      setSummary(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary();
  }, []);

  const handleGlobalExport = async (datasetId, format = 'csv') => {
    const token = localStorage.getItem('cognitrace_token');
    if (!token) return;
    
    setExporting(datasetId);
    try {
      const res = await fetch(`/api/v1/teacher/datasets/${datasetId}/export?format=${format}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!res.ok) {
        throw new Error('Export failed. Please ensure datasets exist.');
      }
      
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = `cognitrace_${datasetId}_dataset.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert(err.message);
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 pb-12">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/teacher/dashboard" className="p-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white transition-colors border border-slate-800">
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-purple-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-purple-500/20">
                <Database className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="font-bold text-base text-slate-100">Dataset Management</h1>
                <p className="text-xs text-slate-400">View and Export CogniTrace Datasets</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-8 space-y-8">
        
        {error && (
          <div className="p-4 bg-red-950/50 border border-red-900 rounded-xl text-red-200 text-sm">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {datasetConfig.map(ds => {
            const Icon = ds.icon;
            const count = summary ? summary[ds.id] : 0;
            
            return (
              <div key={ds.id} className={`glass-card p-6 rounded-2xl flex flex-col border border-slate-800 ${ds.hover} transition-all`}>
                <div className="flex items-start justify-between mb-4">
                  <div className={`w-12 h-12 rounded-xl ${ds.bg} ${ds.border} border flex items-center justify-center ${ds.color}`}>
                    <Icon className="w-6 h-6" />
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-slate-400 font-medium">Total Records</p>
                    {loading ? (
                      <Loader2 className="w-5 h-5 animate-spin text-slate-600 ml-auto mt-1" />
                    ) : (
                      <p className={`text-2xl font-bold ${ds.color} font-mono`}>{count.toLocaleString()}</p>
                    )}
                  </div>
                </div>
                
                <h3 className="text-lg font-bold text-white mb-1">{ds.title}</h3>
                <p className="text-xs text-slate-400 flex-1">{ds.description}</p>
                
                <div className="mt-6 pt-4 border-t border-slate-800/80 flex items-center justify-between gap-3">
                  <button
                    onClick={() => navigate(`/teacher/datasets/${ds.id}`)}
                    className="flex-1 inline-flex items-center justify-center gap-2 px-3 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-200 text-xs font-semibold transition-colors"
                  >
                    <Eye className="w-4 h-4" />
                    View Data
                  </button>
                  <button
                    onClick={() => handleGlobalExport(ds.id, 'csv')}
                    disabled={exporting === ds.id || count === 0}
                    className={`inline-flex items-center justify-center p-2 rounded-xl border text-xs font-semibold transition-colors ${
                      exporting === ds.id || count === 0
                        ? 'bg-slate-900 border-slate-800 text-slate-600 cursor-not-allowed'
                        : `bg-slate-900 hover:${ds.bg} border-slate-700 hover:${ds.border} text-slate-300 hover:${ds.color}`
                    }`}
                    title="Export as CSV"
                  >
                    {exporting === ds.id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            );
          })}
        </div>

      </main>
    </div>
  );
}
