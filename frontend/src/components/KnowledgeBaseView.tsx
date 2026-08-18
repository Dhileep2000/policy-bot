import React, { useState } from 'react';
import { type Document } from '../hooks/useDocuments';
import api from '../api/axios';

interface KnowledgeBaseViewProps {
  documents: Document[];
  loading: boolean;
  onOpenUpload: () => void;
  onDeleteDocument: (id: number) => Promise<void>;
}

export default function KnowledgeBaseView({
  documents,
  loading,
  onOpenUpload,
  onDeleteDocument,
}: KnowledgeBaseViewProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeMenuId, setActiveMenuId] = useState<number | null>(null);

  // Filter documents by search query
  const filteredDocs = documents.filter(doc =>
    doc.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (doc.description && doc.description.toLowerCase().includes(searchQuery.toLowerCase())) ||
    (doc.tag && doc.tag.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  // Compute Stats
  const totalDocs = documents.length;
  const activeIndices = documents.filter(doc => doc.status === 'Indexed').length;
  const processingCount = documents.filter(doc => doc.status === 'Processing').length;
  
  const calculateTotalStorage = () => {
    let totalKb = 0;
    documents.forEach(doc => {
      const sizeStr = doc.storage_size || '0 KB';
      const val = parseFloat(sizeStr);
      if (sizeStr.includes('MB')) {
        totalKb += val * 1024;
      } else if (sizeStr.includes('KB')) {
        totalKb += val;
      } else {
        totalKb += val / 1024;
      }
    });
    
    if (totalKb === 0) return '0 KB';
    if (totalKb < 1024) return `${totalKb.toFixed(1)} KB`;
    return `${(totalKb / 1024).toFixed(1)} MB`;
  };

  const totalStorage = calculateTotalStorage();

  const toggleMenu = (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setActiveMenuId(activeMenuId === id ? null : id);
  };

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setActiveMenuId(null);
    if (window.confirm('Are you sure you want to delete this policy document? This will remove all its vector index embeddings.')) {
      try {
        await onDeleteDocument(id);
      } catch (err: any) {
        alert(err.message || 'Failed to delete document.');
      }
    }
  };

  React.useEffect(() => {
    const handleClose = () => setActiveMenuId(null);
    window.addEventListener('click', handleClose);
    return () => window.removeEventListener('click', handleClose);
  }, []);

  return (
    <div className="flex-1 p-6 md:p-10 flex flex-col gap-8 max-w-7xl mx-auto w-full relative bg-slate-50/50 overflow-y-auto min-h-screen">
      
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 w-full pt-2">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full bg-slate-900 text-white text-[11px] font-bold tracking-wider uppercase">
              RAG Knowledge Base
            </span>
            <span className="text-xs text-slate-400">• Active Index Pipeline</span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-slate-900 tracking-tight">
            Policy Knowledge Base
          </h1>
          <p className="text-sm text-slate-600 max-w-2xl mt-1 leading-relaxed">
            Manage, upload, and search authoritative corporate policies for the Lexis AI retrieval system.
          </p>
        </div>
        
        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={onOpenUpload}
            className="flex items-center justify-center gap-2 px-5 py-2.5 bg-slate-900 text-white rounded-xl text-xs font-semibold hover:bg-slate-800 transition-all shadow-md active:scale-95 cursor-pointer"
          >
            <span className="material-symbols-outlined text-[18px]">add</span>
            Upload New Policy
          </button>
        </div>
      </div>

      {/* Search Input Bar */}
      <div className="relative w-full bg-white rounded-2xl flex items-center shadow-sm border border-slate-200/80 focus-within:border-slate-400 focus-within:ring-2 focus-within:ring-slate-900/10 transition-all">
        <span className="material-symbols-outlined text-slate-400 absolute left-4.5 text-[22px]">search</span>
        <input
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          className="w-full bg-transparent border-none text-slate-900 text-sm focus:outline-none focus:ring-0 pl-13 pr-24 py-3.5 placeholder-slate-400 font-medium"
          placeholder="Search by policy title, description, or tag (e.g. HR-POL-01)..."
          type="text"
        />
        {searchQuery && (
          <button 
            onClick={() => setSearchQuery('')}
            className="absolute right-14 text-slate-400 hover:text-slate-700 text-xs font-semibold p-1"
          >
            Clear
          </button>
        )}
        <div className="absolute right-4 hidden sm:flex items-center gap-1">
          <kbd className="text-[11px] font-bold text-slate-400 px-2 py-1 bg-slate-100 border border-slate-200 rounded">⌘K</kbd>
        </div>
      </div>

      {/* Analytics Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 w-full">
        
        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm flex flex-col gap-1">
          <div className="flex justify-between items-center text-slate-500 mb-1">
            <span className="text-[11px] font-bold uppercase tracking-wider">Total Documents</span>
            <span className="material-symbols-outlined text-[20px] text-slate-400">folder_open</span>
          </div>
          <span className="text-2xl md:text-3xl font-extrabold text-slate-900">{totalDocs}</span>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm flex flex-col gap-1">
          <div className="flex justify-between items-center text-slate-500 mb-1">
            <span className="text-[11px] font-bold uppercase tracking-wider text-sky-700">Active Indices</span>
            <span className="material-symbols-outlined text-[20px] text-sky-600">verified</span>
          </div>
          <span className="text-2xl md:text-3xl font-extrabold text-sky-700">{activeIndices}</span>
        </div>

        <div className={`bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm flex flex-col gap-1 relative overflow-hidden ${processingCount > 0 ? 'border-amber-300 bg-amber-50/20' : ''}`}>
          <div className="flex justify-between items-center text-slate-500 mb-1">
            <span className={`text-[11px] font-bold uppercase tracking-wider ${processingCount > 0 ? 'text-amber-700' : ''}`}>
              Processing
            </span>
            <span className={`material-symbols-outlined text-[20px] ${processingCount > 0 ? 'text-amber-600 animate-spin' : 'text-slate-400'}`}>
              sync
            </span>
          </div>
          <span className={`text-2xl md:text-3xl font-extrabold ${processingCount > 0 ? 'text-amber-700' : 'text-slate-900'}`}>
            {processingCount}
          </span>
        </div>

        <div className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm flex flex-col gap-1">
          <div className="flex justify-between items-center text-slate-500 mb-1">
            <span className="text-[11px] font-bold uppercase tracking-wider">Storage Index</span>
            <span className="material-symbols-outlined text-[20px] text-slate-400">hard_drive</span>
          </div>
          <span className="text-2xl md:text-3xl font-extrabold text-slate-900">{totalStorage}</span>
        </div>

      </div>

      {/* Document Grid */}
      {loading && documents.length === 0 ? (
        <div className="flex flex-col justify-center items-center py-24 text-slate-400 gap-3">
          <span className="material-symbols-outlined text-[44px] animate-spin">sync</span>
          <p className="text-xs font-semibold">Loading knowledge base...</p>
        </div>
      ) : filteredDocs.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center text-slate-500 gap-3 border-2 border-dashed border-slate-200 rounded-3xl bg-white/60 p-8">
          <div className="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center text-slate-400 mb-1">
            <span className="material-symbols-outlined text-[36px]">folder_off</span>
          </div>
          <h3 className="text-lg font-bold text-slate-900">No policy documents found</h3>
          <p className="text-xs text-slate-500 max-w-md leading-relaxed">
            {searchQuery 
              ? `No policy matches '${searchQuery}'. Try adjusting your search keywords.` 
              : 'Upload policy files (PDF, TXT, MD) to index them into the Lexis AI RAG vector pipeline.'}
          </p>
          {!searchQuery && (
            <button
              onClick={onOpenUpload}
              className="mt-3 px-5 py-2.5 bg-slate-900 text-white text-xs font-semibold rounded-xl hover:bg-slate-800 transition-all cursor-pointer shadow-md"
            >
              Upload Document
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 w-full pb-16">
          {filteredDocs.map(doc => (
            <div
              key={doc.id}
              className={`bg-white rounded-2xl p-6 flex flex-col gap-4 border border-slate-200/90 hover:border-slate-400 hover:shadow-md transition-all duration-200 relative group justify-between ${
                doc.status === 'Processing' ? 'border-amber-300 bg-amber-50/10' : ''
              }`}
            >
              {/* Card Top Row */}
              <div className="flex justify-between items-start">
                  {(() => {
                    const isImg = doc.filename.toLowerCase().match(/\.(png|jpg|jpeg|gif)$/);
                    return (
                      <div className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 border ${
                        doc.status === 'Processing' 
                          ? 'bg-amber-50 text-amber-600 border-amber-200' 
                          : 'bg-slate-900 text-white border-slate-900'
                      }`}>
                        <span className={`material-symbols-outlined text-[22px] ${doc.status === 'Processing' ? 'animate-spin' : ''}`}>
                          {doc.status === 'Processing'
                            ? 'sync'
                            : isImg
                              ? 'image'
                              : doc.filename.toLowerCase().includes('privacy') || doc.filename.toLowerCase().includes('security')
                                ? 'shield'
                                : 'description'}
                        </span>
                      </div>
                    );
                  })()}
                  <div>
                    {doc.status === 'Indexed' ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-800 text-[10px] font-bold tracking-wide uppercase border border-emerald-200">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-600"></span> Indexed
                      </span>
                    ) : doc.status === 'Processing' ? (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-amber-50 text-amber-800 text-[10px] font-bold tracking-wide uppercase border border-amber-200">
                        <span className="w-1.5 h-1.5 rounded-full bg-amber-600 animate-ping"></span> Indexing
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-red-50 text-red-800 text-[10px] font-bold tracking-wide uppercase border border-red-200">
                        <span className="w-1.5 h-1.5 rounded-full bg-red-600"></span> Failed
                      </span>
                    )}
                  </div>
                </div>

                {/* Dropdown Action Button */}
                <div className="relative">
                  <button
                    onClick={e => toggleMenu(doc.id, e)}
                    className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-100 transition-colors cursor-pointer"
                    aria-label="Document options"
                  >
                    <span className="material-symbols-outlined text-[20px]">more_vert</span>
                  </button>

                  {activeMenuId === doc.id && (
                    <div className="absolute right-0 mt-1 w-36 bg-white border border-slate-200 rounded-xl shadow-lg z-30 py-1 overflow-hidden">
                      <button
                        onClick={e => handleDelete(doc.id, e)}
                        className="w-full px-4 py-2 text-left text-red-600 hover:bg-red-50 text-xs font-semibold flex items-center gap-2 cursor-pointer transition-colors"
                      >
                        <span className="material-symbols-outlined text-[16px]">delete</span>
                        Delete Policy
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Card Center Content */}
              <div className="flex-1 my-1">
                <h3 className="text-base font-bold text-slate-900 group-hover:text-sky-700 transition-colors line-clamp-1 mb-1.5">
                  {doc.filename.split('.')[0]}
                </h3>
                
                {(() => {
                  const isImg = doc.filename.toLowerCase().match(/\.(png|jpg|jpeg|gif)$/);
                  return doc.status === 'Processing' ? (
                    <div className="mt-2">
                      <p className="text-xs text-slate-500 leading-relaxed">
                        Generating Gemini vector embeddings...
                      </p>
                      <div className="w-full bg-slate-100 h-1.5 rounded-full mt-2.5 overflow-hidden">
                        <div className="bg-amber-500 h-full rounded-full w-[65%] animate-pulse"></div>
                      </div>
                    </div>
                  ) : (
                    <div className="flex flex-col gap-2.5 mt-1">
                      {isImg && doc.stored_filename && (
                        <div className="w-full h-24 rounded-lg overflow-hidden border border-slate-200 bg-slate-100 flex items-center justify-center">
                          <img
                            src={`${api.defaults.baseURL || '/api'}/documents/file/${doc.stored_filename}`}
                            alt={doc.filename}
                            className="w-full h-full object-cover"
                            onError={(e) => {
                              (e.target as HTMLElement).style.display = 'none';
                            }}
                          />
                        </div>
                      )}
                      <p className="text-xs text-slate-600 leading-relaxed line-clamp-2" title={doc.description || ''}>
                        {doc.description || 'Policy document indexed into Lexis AI.'}
                      </p>
                    </div>
                  );
                })()}
              </div>

              {/* Card Footer Row */}
              <div className="flex justify-between items-center pt-3.5 border-t border-slate-100 text-xs text-slate-500">
                <div className="flex flex-col">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    {doc.status === 'Processing' ? 'Size' : 'Updated'}
                  </span>
                  <span className="font-medium text-slate-700">
                    {doc.status === 'Processing' ? doc.storage_size : doc.last_updated}
                  </span>
                </div>
                
                <div className="flex items-center gap-1 bg-slate-100 text-slate-700 px-2.5 py-1 rounded-md text-[11px] font-bold font-mono">
                  #{doc.tag || 'GEN-POL'}
                </div>
              </div>

            </div>
          ))}
        </div>
      )}

    </div>
  );
}
