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
    icon: MousePointer2
  },
  {
    id: 'transcripts',
    title: 'Course Transcripts',
    description: 'NLP-generated transcripts from Faster-Whisper, mapped to precise timestamps.',
    icon: FileText
  },
  {
    id: 'concepts',
    title: 'Concept Segments',
    description: 'Educational concepts automatically extracted from transcripts.',
    icon: BrainCircuit
  },
  {
    id: 'mappings',
    title: 'Concept-Event Mappings',
    description: 'Phase 7 intersection mapping raw telemetry to specific concepts.',
    icon: LinkIcon
  },
  {
    id: 'difficulty',
    title: 'Difficulty Dataset',
    description: 'Phase 8 deterministic difficulty scores based strictly on real interaction data.',
    icon: BarChart
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

      const disposition = res.headers.get('content-disposition');
      let filename = `cognitrace_${datasetId}_dataset.${format}`;
      if (disposition && disposition.indexOf('attachment') !== -1) {
        const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
        const matches = filenameRegex.exec(disposition);
        if (matches != null && matches[1]) {
          filename = matches[1].replace(/['"]/g, '');
        }
      }

      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (err) {
      alert(err.message);
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="min-h-screen bg-[#F9F9F9] text-[#0F0F0F] flex flex-col pb-12">
      {/* Header */}
      <header className="border-b border-[#E5E5E5] bg-[#FFFFFF] sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/teacher/dashboard" className="yt-btn-secondary p-2 flex items-center justify-center">
              <ArrowLeft className="w-4 h-4 text-[#0F0F0F]" />
            </Link>
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-[#FF0000]/10 flex items-center justify-center text-[#FF0000]">
                <Database className="w-4 h-4" />
              </div>
              <div>
                <h1 className="font-bold text-sm text-[#0F0F0F]">Dataset Management</h1>
                <p className="text-xs text-[#606060]">View and Export CogniTrace Datasets</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 mt-6 space-y-6">
        
        {error && (
          <div className="p-3.5 bg-[#FFEBEE] border border-[#FFCDD2] rounded-xl text-[#C62828] text-xs">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {datasetConfig.map(ds => {
            const Icon = ds.icon;
            const count = summary ? summary[ds.id] : 0;
            
            return (
              <div key={ds.id} className="bg-[#FFFFFF] border border-[#E5E5E5] p-5 rounded-xl flex flex-col justify-between shadow-xs hover:border-[#CCCCCC] hover:shadow-sm transition-all">
                <div>
                  <div className="flex items-start justify-between mb-3.5">
                    <div className="w-10 h-10 rounded-full bg-[#F2F2F2] flex items-center justify-center text-[#0F0F0F]">
                      <Icon className="w-5 h-5" />
                    </div>
                    <div className="text-right">
                      <p className="text-[11px] text-[#606060] font-semibold uppercase tracking-wider">Total Records</p>
                      {loading ? (
                        <Loader2 className="w-4 h-4 animate-spin text-[#909090] ml-auto mt-1" />
                      ) : (
                        <p className="text-xl font-bold text-[#0F0F0F] font-mono mt-0.5">{count.toLocaleString()}</p>
                      )}
                    </div>
                  </div>
                  
                  <h3 className="text-base font-bold text-[#0F0F0F] mb-1">{ds.title}</h3>
                  <p className="text-xs text-[#606060] leading-relaxed">{ds.description}</p>
                </div>
                
                <div className="mt-5 pt-3.5 border-t border-[#E5E5E5] flex items-center justify-between gap-2.5">
                  <button
                    onClick={() => navigate(`/teacher/datasets/${ds.id}`)}
                    className="flex-1 yt-btn-secondary py-2 px-3 text-xs font-semibold flex items-center justify-center gap-1.5"
                  >
                    <Eye className="w-3.5 h-3.5 text-[#606060]" />
                    <span>View Data</span>
                  </button>
                  <button
                    onClick={() => handleGlobalExport(ds.id, 'csv')}
                    disabled={exporting === ds.id || count === 0}
                    className={`yt-btn-primary p-2 text-xs font-semibold flex items-center justify-center ${
                      exporting === ds.id || count === 0 ? 'opacity-40 cursor-not-allowed' : ''
                    }`}
                    title="Export as CSV"
                  >
                    {exporting === ds.id ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
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
