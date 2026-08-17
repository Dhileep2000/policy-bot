interface SidebarProps {
  currentPage: 'chat' | 'knowledge_base';
  setCurrentPage: (page: 'chat' | 'knowledge_base') => void;
  onOpenUpload: () => void;
}

export default function Sidebar({ currentPage, setCurrentPage, onOpenUpload }: SidebarProps) {
  return (
    <aside className="h-full w-64 fixed left-0 top-0 bg-white border-r border-slate-200/90 flex flex-col p-5 gap-6 z-40 hidden md:flex shadow-xs">
      
      {/* Brand Header */}
      <div className="flex items-center gap-3 px-1 py-1">
        <div className="w-10 h-10 rounded-xl bg-slate-900 text-white flex items-center justify-center shrink-0 shadow-md">
          <span className="material-symbols-outlined text-[22px]">policy</span>
        </div>
        <div>
          <h1 className="text-base font-extrabold text-slate-900 tracking-tight leading-none">Lexis AI</h1>
          <p className="text-[11px] font-semibold text-slate-500 mt-1">Policy Intelligence</p>
        </div>
      </div>

      {/* Primary Navigation Links */}
      <div className="flex-1 flex flex-col gap-1.5 mt-2">
        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-3 mb-1">
          Navigation
        </div>

        <button
          onClick={() => setCurrentPage('chat')}
          className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all cursor-pointer w-full text-left ${
            currentPage === 'chat'
              ? 'bg-slate-900 text-white shadow-sm'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <span className="material-symbols-outlined text-[18px]">chat_bubble</span>
          Chat Assistant
        </button>

        <button
          onClick={() => setCurrentPage('knowledge_base')}
          className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all cursor-pointer w-full text-left ${
            currentPage === 'knowledge_base'
              ? 'bg-slate-900 text-white shadow-sm'
              : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
          }`}
        >
          <span className="material-symbols-outlined text-[18px]">folder_shared</span>
          Knowledge Base
        </button>
      </div>

      {/* Upload Action CTA Button */}
      <button
        onClick={onOpenUpload}
        className="w-full py-3 px-4 rounded-xl border border-slate-200 bg-slate-50 hover:bg-slate-100 hover:border-slate-300 text-slate-900 transition-all flex items-center justify-center gap-2 text-xs font-bold cursor-pointer active:scale-95 shadow-xs"
      >
        <span className="material-symbols-outlined text-[18px] text-slate-800">upload_file</span>
        Upload Document
      </button>

      {/* Footer Utilities */}
      <div className="flex flex-col gap-1 border-t border-slate-100 pt-3 mt-auto text-slate-500">
        <button className="flex items-center gap-3 px-3.5 py-2 text-xs font-medium hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors w-full text-left cursor-pointer">
          <span className="material-symbols-outlined text-[18px]">verified</span>
          v2.4 Production RAG
        </button>
      </div>
    </aside>
  );
}
