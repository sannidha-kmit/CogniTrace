import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { 
  Database, 
  ArrowLeft, 
  Search, 
  Trash2, 
  ChevronLeft, 
  ChevronRight,
  AlertTriangle,
  Loader2
} from 'lucide-react';

const datasetConfig = {
  interactions: { title: 'Interaction Telemetry', color: 'text-blue-400', bg: 'bg-blue-950/80', border: 'border-blue-800/60' },
  transcripts: { title: 'Course Transcripts', color: 'text-emerald-400', bg: 'bg-emerald-950/80', border: 'border-emerald-800/60' },
  concepts: { title: 'Concept Segments', color: 'text-purple-400', bg: 'bg-purple-950/80', border: 'border-purple-800/60' },
  mappings: { title: 'Concept-Event Mappings', color: 'text-amber-400', bg: 'bg-amber-950/80', border: 'border-amber-800/60' },
  difficulty: { title: 'Difficulty Dataset', color: 'text-rose-400', bg: 'bg-rose-950/80', border: 'border-rose-800/60' }
};

export default function TeacherDatasetDetail() {
  const { datasetType } = useParams();
  const navigate = useNavigate();
  const config = datasetConfig[datasetType];

  const [data, setData] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [limit] = useState(50);
  
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [deleteModal, setDeleteModal] = useState({ show: false, item: null, loading: false, error: null });

  useEffect(() => {
    if (!config) navigate('/teacher/datasets');
  }, [config, navigate]);

  const fetchData = async (pageNum = 1, searchQuery = search) => {
    setLoading(true);
    setError(null);
    const token = localStorage.getItem('cognitrace_token');
    try {
      const qs = new URLSearchParams({
        page: pageNum,
        limit,
        ...(searchQuery && { search: searchQuery })
      });
      const res = await fetch(`/api/v1/teacher/datasets/${datasetType}?${qs.toString()}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (!res.ok) throw new Error('Failed to fetch dataset records.');
      const resData = await res.json();
      setData(resData.data);
      setTotal(resData.total);
      setPage(resData.page);
      setTotalPages(resData.total_pages);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [datasetType]); // intentionally exclude page/search to avoid double fetch

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    fetchData(1, search);
  };

  const handleDeleteConfirm = async () => {
    setDeleteModal(prev => ({ ...prev, loading: true, error: null }));
    const token = localStorage.getItem('cognitrace_token');
    try {
      const res = await fetch(`/api/v1/teacher/datasets/${datasetType}/record/${deleteModal.item._id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const resData = await res.json();
      if (!res.ok) {
        throw new Error(resData.detail || 'Failed to delete record.');
      }
      setDeleteModal({ show: false, item: null, loading: false, error: null });
      fetchData(page);
    } catch (err) {
      setDeleteModal(prev => ({ ...prev, loading: false, error: err.message }));
    }
  };

  if (!config) return null;

  // Determine columns based on first item, or predefined
  const getColumns = () => {
    if (datasetType === 'interactions') return ['CourseName', 'StudentID', 'EventType', 'EventTimestamp', 'PauseReason'];
    if (datasetType === 'transcripts') return ['CourseName', 'TranscriptStart', 'TranscriptEnd', 'text'];
    if (datasetType === 'concepts') return ['CourseName', 'Concept', 'ConceptStart', 'Prerequisite', 'DifficultyLevel'];
    if (datasetType === 'mappings') return ['CourseName', 'StudentID', 'EventType', 'Concept', 'EventTimestamp'];
    if (datasetType === 'difficulty') return ['CourseName', 'StudentID', 'Concept', 'DifficultyScore', 'DifficultyLevel'];
    return [];
  };
  const columns = getColumns();

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col pb-12">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/teacher/datasets" className="p-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 hover:text-white transition-colors border border-slate-800">
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <div className="flex items-center gap-3">
              <div className={`w-9 h-9 rounded-xl ${config.bg} border ${config.border} flex items-center justify-center`}>
                <Database className={`w-5 h-5 ${config.color}`} />
              </div>
              <div>
                <h1 className="font-bold text-base text-slate-100">{config.title} Detail</h1>
                <p className="text-xs text-slate-400">Total Records: {total.toLocaleString()}</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 mt-8 space-y-6">
        
        {/* Controls */}
        <div className="glass-panel p-4 rounded-xl flex flex-col md:flex-row gap-4 items-center justify-between">
          <form onSubmit={handleSearchSubmit} className="relative w-full md:w-96">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search dataset..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-4 py-2 text-sm text-slate-200 focus:outline-none focus:border-slate-700 transition-colors"
            />
          </form>
          
          {/* Pagination */}
          <div className="flex items-center gap-3 bg-slate-900 border border-slate-800 rounded-lg p-1">
            <button
              onClick={() => { setPage(p => p - 1); fetchData(page - 1); }}
              disabled={page === 1 || loading}
              className="p-1.5 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-50 transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-xs font-mono text-slate-300 px-2">Page {page} of {totalPages}</span>
            <button
              onClick={() => { setPage(p => p + 1); fetchData(page + 1); }}
              disabled={page === totalPages || loading}
              className="p-1.5 rounded-md text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-50 transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Table */}
        <div className="glass-panel rounded-xl overflow-hidden border border-slate-800">
          {error ? (
            <div className="p-8 text-center text-red-400 text-sm">{error}</div>
          ) : loading ? (
            <div className="p-12 flex justify-center">
              <Loader2 className="w-8 h-8 animate-spin text-slate-600" />
            </div>
          ) : data.length === 0 ? (
            <div className="p-12 text-center text-slate-500 text-sm">No records found.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-900/50 border-b border-slate-800 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                    {columns.map(col => (
                      <th key={col} className="px-4 py-3 whitespace-nowrap">{col}</th>
                    ))}
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50 text-sm text-slate-300">
                  {data.map((row) => (
                    <tr key={row._id} className="hover:bg-slate-900/50 transition-colors group">
                      {columns.map(col => (
                        <td key={col} className="px-4 py-3 max-w-[200px] truncate">
                          {row[col] !== null && row[col] !== undefined ? String(row[col]) : '-'}
                        </td>
                      ))}
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => setDeleteModal({ show: true, item: row, loading: false, error: null })}
                          className="p-1.5 rounded-md text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors opacity-0 group-hover:opacity-100"
                          title="Delete Record"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>

      {/* Delete Modal */}
      {deleteModal.show && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-slate-950 border border-slate-800 rounded-2xl w-full max-w-md shadow-2xl overflow-hidden">
            <div className="p-6">
              <div className="w-12 h-12 rounded-full bg-rose-500/10 border border-rose-500/20 flex items-center justify-center mb-4">
                <AlertTriangle className="w-6 h-6 text-rose-500" />
              </div>
              <h3 className="text-xl font-bold text-white mb-2">Delete Record?</h3>
              <p className="text-sm text-slate-400 mb-4">
                Are you sure you want to delete this dataset record? This action cannot be undone.
              </p>
              
              {deleteModal.error && (
                <div className="mb-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs font-medium">
                  {deleteModal.error}
                </div>
              )}

              <div className="flex items-center justify-end gap-3 mt-6">
                <button
                  onClick={() => setDeleteModal({ show: false, item: null, loading: false, error: null })}
                  disabled={deleteModal.loading}
                  className="px-4 py-2 rounded-xl border border-slate-700 text-slate-300 hover:bg-slate-900 transition-colors text-sm font-semibold"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteConfirm}
                  disabled={deleteModal.loading}
                  className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white shadow-lg shadow-rose-600/20 transition-colors text-sm font-semibold flex items-center gap-2"
                >
                  {deleteModal.loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                  Confirm Delete
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
