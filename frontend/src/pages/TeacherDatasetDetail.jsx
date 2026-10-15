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
  interactions: { title: 'Interaction Telemetry' },
  transcripts: { title: 'Course Transcripts' },
  concepts: { title: 'Concept Segments' },
  mappings: { title: 'Concept-Event Mappings' },
  difficulty: { title: 'Difficulty Dataset' }
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
  }, [datasetType]);

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

  // Determine columns based on dataset type
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
    <div className="min-h-screen bg-[#F9F9F9] text-[#0F0F0F] flex flex-col pb-12">
      {/* Header */}
      <header className="border-b border-[#E5E5E5] bg-[#FFFFFF] sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link to="/teacher/datasets" className="yt-btn-secondary p-2 flex items-center justify-center">
              <ArrowLeft className="w-4 h-4 text-[#0F0F0F]" />
            </Link>
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-full bg-[#FF0000]/10 flex items-center justify-center text-[#FF0000]">
                <Database className="w-4 h-4" />
              </div>
              <div>
                <h1 className="font-bold text-sm text-[#0F0F0F]">{config.title} Table</h1>
                <p className="text-xs text-[#606060]">Total Records: {total.toLocaleString()}</p>
              </div>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 mt-6 space-y-4">
        
        {/* Controls */}
        <div className="bg-[#FFFFFF] border border-[#E5E5E5] p-4 rounded-xl flex flex-col md:flex-row gap-4 items-center justify-between shadow-xs">
          <form onSubmit={handleSearchSubmit} className="relative w-full md:w-80">
            <Search className="w-4 h-4 text-[#909090] absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search dataset..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full bg-[#FFFFFF] border border-[#CCCCCC] rounded-full pl-10 pr-4 py-1.5 text-xs text-[#0F0F0F] placeholder-[#909090] focus:outline-none focus:border-[#0F0F0F]"
            />
          </form>
          
          {/* Pagination */}
          <div className="flex items-center gap-2 bg-[#F2F2F2] rounded-full p-1 border border-[#E5E5E5]">
            <button
              onClick={() => { setPage(p => p - 1); fetchData(page - 1); }}
              disabled={page === 1 || loading}
              className="p-1 rounded-full text-[#0F0F0F] hover:bg-[#E5E5E5] disabled:opacity-30 transition-colors cursor-pointer"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-xs font-semibold text-[#0F0F0F] px-2">Page {page} of {totalPages}</span>
            <button
              onClick={() => { setPage(p => p + 1); fetchData(page + 1); }}
              disabled={page === totalPages || loading}
              className="p-1 rounded-full text-[#0F0F0F] hover:bg-[#E5E5E5] disabled:opacity-30 transition-colors cursor-pointer"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Table */}
        <div className="bg-[#FFFFFF] border border-[#E5E5E5] rounded-xl overflow-hidden shadow-xs">
          {error ? (
            <div className="p-8 text-center text-[#C62828] text-xs font-mono">{error}</div>
          ) : loading ? (
            <div className="p-12 flex justify-center">
              <Loader2 className="w-7 h-7 animate-spin text-[#FF0000]" />
            </div>
          ) : data.length === 0 ? (
            <div className="p-12 text-center text-[#606060] text-xs">No records found.</div>
          ) : (
            <div className="overflow-x-auto custom-scrollbar">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-[#F9F9F9] border-b border-[#E5E5E5] text-xs font-semibold text-[#606060] uppercase tracking-wider">
                    {columns.map(col => (
                      <th key={col} className="px-4 py-3 whitespace-nowrap">{col}</th>
                    ))}
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#E5E5E5] text-[#0F0F0F]">
                  {data.map((row) => (
                    <tr key={row._id} className="hover:bg-[#F9F9F9] transition-colors group">
                      {columns.map(col => (
                        <td key={col} className="px-4 py-3 max-w-[220px] truncate font-medium">
                          {row[col] !== null && row[col] !== undefined ? String(row[col]) : '-'}
                        </td>
                      ))}
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => setDeleteModal({ show: true, item: row, loading: false, error: null })}
                          className="p-1.5 rounded-full text-[#909090] hover:text-[#C62828] hover:bg-[#FFEBEE] transition-colors opacity-0 group-hover:opacity-100 cursor-pointer"
                          title="Delete Record"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="bg-[#FFFFFF] border border-[#E5E5E5] rounded-xl w-full max-w-md overflow-hidden shadow-lg">
            <div className="p-6">
              <div className="w-10 h-10 rounded-full bg-[#FFEBEE] flex items-center justify-center mb-3.5 text-[#C62828]">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <h3 className="text-lg font-bold text-[#0F0F0F] mb-1">Delete Record?</h3>
              <p className="text-xs text-[#606060] mb-4 leading-relaxed">
                Are you sure you want to delete this dataset record? This action cannot be undone.
              </p>
              
              {deleteModal.error && (
                <div className="mb-4 p-3 rounded-lg bg-[#FFEBEE] border border-[#FFCDD2] text-[#C62828] text-xs font-medium">
                  {deleteModal.error}
                </div>
              )}

              <div className="flex items-center justify-end gap-2.5 mt-5">
                <button
                  onClick={() => setDeleteModal({ show: false, item: null, loading: false, error: null })}
                  disabled={deleteModal.loading}
                  className="yt-btn-secondary py-2 px-3.5 text-xs font-semibold"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteConfirm}
                  disabled={deleteModal.loading}
                  className="py-2 px-4 rounded-full bg-[#FF0000] text-white text-xs font-semibold hover:bg-[#CC0000] transition-all flex items-center gap-1.5 cursor-pointer"
                >
                  {deleteModal.loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
                  <span>Confirm Delete</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
