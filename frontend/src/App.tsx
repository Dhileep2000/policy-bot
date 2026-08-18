import { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import UploadModal from './components/UploadModal';
import ChatView from './components/ChatView';
import KnowledgeBaseView from './components/KnowledgeBaseView';

import { useChat } from './hooks/useChat';
import { useDocuments } from './hooks/useDocuments';

function App() {
  const [currentPage, setCurrentPage] = useState<'chat' | 'knowledge_base'>('chat');
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const {
    messages,
    sending,
    indexStatus,
    sendMessage,
    clearChat,
  } = useChat();

  const {
    documents,
    loading: docsLoading,
    fetchDocuments,
    uploadDocument,
    deleteDocument,
  } = useDocuments();

  useEffect(() => {
    fetchDocuments();
  }, [fetchDocuments]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-50 font-sans antialiased text-slate-900">
      {/* Desktop Sidebar Navigation */}
      <Sidebar
        currentPage={currentPage}
        setCurrentPage={setCurrentPage}
        onOpenUpload={() => setIsUploadOpen(true)}
      />

      {/* Main Content View Container */}
      <div className="flex-1 flex flex-col h-full relative md:ml-64 overflow-hidden">
        
        {/* Mobile Header (Visible on <768px screens) */}
        <header className="md:hidden flex justify-between items-center px-4 h-16 w-full sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-slate-200 shadow-xs">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-slate-900 text-white flex items-center justify-center font-bold">
              <span className="material-symbols-outlined text-[18px]">policy</span>
            </div>
            <span className="font-extrabold text-base text-slate-900 tracking-tight">Lexis AI</span>
          </div>
          <button 
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="text-slate-600 p-2 rounded-xl hover:bg-slate-100 transition-colors"
            aria-label="Toggle navigation menu"
          >
            <span className="material-symbols-outlined">{isMobileMenuOpen ? 'close' : 'menu'}</span>
          </button>
        </header>

        {/* Mobile Drawer Menu */}
        {isMobileMenuOpen && (
          <div className="md:hidden absolute top-16 left-0 right-0 bg-white border-b border-slate-200 shadow-xl z-30 flex flex-col p-4 gap-2">
            <button
              onClick={() => {
                setCurrentPage('chat');
                setIsMobileMenuOpen(false);
              }}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl w-full text-left text-xs font-bold transition-all ${
                currentPage === 'chat' ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-100'
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">chat_bubble</span>
              Chat Assistant
            </button>
            <button
              onClick={() => {
                setCurrentPage('knowledge_base');
                setIsMobileMenuOpen(false);
              }}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl w-full text-left text-xs font-bold transition-all ${
                currentPage === 'knowledge_base' ? 'bg-slate-900 text-white' : 'text-slate-700 hover:bg-slate-100'
              }`}
            >
              <span className="material-symbols-outlined text-[18px]">folder_shared</span>
              Knowledge Base
            </button>
            <button
              onClick={() => {
                setIsMobileMenuOpen(false);
                setIsUploadOpen(true);
              }}
              className="flex items-center justify-center gap-2 py-3 border border-slate-200 bg-slate-50 text-slate-900 rounded-xl text-xs font-bold mt-1"
            >
              <span className="material-symbols-outlined text-[18px]">upload_file</span>
              Upload Document
            </button>
          </div>
        )}

        {/* Active Page View */}
        {currentPage === 'chat' ? (
          <ChatView
            messages={messages}
            sending={sending}
            indexStatus={indexStatus}
            onSendMessage={sendMessage}
            onClearChat={clearChat}
            documents={documents}
          />
        ) : (
          <KnowledgeBaseView
            documents={documents}
            loading={docsLoading}
            onOpenUpload={() => setIsUploadOpen(true)}
            onDeleteDocument={deleteDocument}
          />
        )}

        {/* Mobile Bottom Navigation Bar */}
        <nav className="md:hidden fixed bottom-0 left-0 right-0 w-full bg-white/90 backdrop-blur-lg border-t border-slate-200 z-30 px-6 py-2 flex justify-around items-center">
          <button
            onClick={() => setCurrentPage('chat')}
            className={`flex flex-col items-center gap-0.5 cursor-pointer ${currentPage === 'chat' ? 'text-slate-900' : 'text-slate-400'}`}
          >
            <span className="material-symbols-outlined text-[22px]">chat_bubble</span>
            <span className="text-[10px] font-bold">Chat</span>
          </button>
          <button
            onClick={() => setIsUploadOpen(true)}
            className="flex flex-col items-center justify-center w-11 h-11 bg-slate-900 text-white rounded-full shadow-md -translate-y-3 active:scale-95 cursor-pointer"
            aria-label="Upload document"
          >
            <span className="material-symbols-outlined text-[22px]">add</span>
          </button>
          <button
            onClick={() => setCurrentPage('knowledge_base')}
            className={`flex flex-col items-center gap-0.5 cursor-pointer ${currentPage === 'knowledge_base' ? 'text-slate-900' : 'text-slate-400'}`}
          >
            <span className="material-symbols-outlined text-[22px]">folder_shared</span>
            <span className="text-[10px] font-bold">Knowledge</span>
          </button>
        </nav>
      </div>

      {/* Upload Document Modal */}
      <UploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onUpload={uploadDocument}
      />
    </div>
  );
}

export default App;
