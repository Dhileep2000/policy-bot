import React, { useState, useRef, useEffect } from 'react';
import { type Message } from '../hooks/useChat';

interface ChatViewProps {
  messages: Message[];
  sending: boolean;
  indexStatus: string;
  onSendMessage: (text: string) => void;
  onClearChat: () => void;
}

export default function ChatView({
  messages,
  sending,
  indexStatus,
  onSendMessage,
  onClearChat,
}: ChatViewProps) {
  const [inputText, setInputText] = useState('');
  const chatEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Scroll to bottom on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Autogrow textarea logic
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputText(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = '56px';
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`;
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    if (!inputText.trim() || sending) return;
    onSendMessage(inputText);
    setInputText('');
    if (textareaRef.current) {
      textareaRef.current.style.height = '56px';
    }
  };

  // Helper to format bold text, lists, and inline citations [X]
  const parseMarkdownAndCitations = (text: string) => {
    if (!text) return null;

    const lines = text.split('\n');
    return lines.map((line, lineIdx) => {
      let trimmed = line.trim();

      if (trimmed.startsWith('####')) {
        return (
          <h4 key={lineIdx} className="text-xs font-bold text-slate-800 mb-2 mt-4 uppercase tracking-wider">
            {parseInlineStyles(trimmed.replace(/^####\s*/, ''))}
          </h4>
        );
      }
      if (trimmed.startsWith('###') || trimmed.startsWith('##') || trimmed.startsWith('#')) {
        return (
          <h3 key={lineIdx} className="text-base font-bold text-slate-900 mb-2 mt-4">
            {parseInlineStyles(trimmed.replace(/^#+\s*/, ''))}
          </h3>
        );
      }

      if (trimmed.startsWith('-') || trimmed.startsWith('*')) {
        return (
          <li key={lineIdx} className="list-disc pl-1 ml-4 mb-2 text-slate-700 text-sm leading-relaxed">
            {parseInlineStyles(trimmed.replace(/^[-*]\s*/, ''))}
          </li>
        );
      }

      if (trimmed === '') {
        return <div key={lineIdx} className="h-2" />;
      }

      return (
        <p key={lineIdx} className="mb-3 text-sm leading-relaxed text-slate-800">
          {parseInlineStyles(line)}
        </p>
      );
    });
  };

  const parseInlineStyles = (text: string) => {
    const regex = /(\*\*.*?\*\*|\[\d+\])/g;
    const parts = text.split(regex);

    return parts.map((part, index) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return <strong key={index} className="font-bold text-slate-950">{part.slice(2, -2)}</strong>;
      }
      if (part.startsWith('[') && part.endsWith(']')) {
        const num = part.slice(1, -1);
        return (
          <button
            key={index}
            onClick={() => {
              const element = document.getElementById(`citation-card-${num}`);
              element?.scrollIntoView({ behavior: 'smooth', block: 'center' });
              element?.classList.add('ring-2', 'ring-slate-900');
              setTimeout(() => {
                element?.classList.remove('ring-2', 'ring-slate-900');
              }, 2000);
            }}
            className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-slate-200 text-slate-900 hover:bg-slate-900 hover:text-white transition-all mx-1 font-bold text-[11px] cursor-pointer shadow-sm align-middle"
          >
            {num}
          </button>
        );
      }
      return part;
    });
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-50/50 relative overflow-hidden">
      
      {/* Chat Canvas */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-8 pt-8 pb-40 flex flex-col items-center">
        <div className="w-full max-w-4xl flex flex-col gap-6">
          
          {/* Security Badge Banner */}
          <div className="flex justify-center my-2">
            <span className="px-4 py-1.5 rounded-full bg-white border border-slate-200 text-slate-600 text-xs font-semibold flex items-center gap-2 shadow-sm">
              <span className="material-symbols-outlined text-[16px] text-emerald-600">verified_user</span>
              Secure Policy Assistant • Gemini RAG Pipeline
            </span>
          </div>

          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center text-slate-500 gap-4">
              <div className="w-16 h-16 rounded-2xl bg-white border border-slate-200 shadow-sm flex items-center justify-center text-slate-800">
                <span className="material-symbols-outlined text-[36px]">policy</span>
              </div>
              <div>
                <h2 className="text-xl font-bold text-slate-900">Welcome to Lexis AI Policy Assistant</h2>
                <p className="text-xs text-slate-500 mt-1 max-w-md leading-relaxed">
                  Ask questions regarding international remote work, travel expenses, data security, compliance directives, and corporate handbooks.
                </p>
              </div>
            </div>
          ) : (
            messages.map(msg => (
              <div key={msg.id} className={`flex w-full ${msg.role === 'user' ? 'justify-end' : 'justify-start gap-4'}`}>
                
                {msg.role === 'assistant' && (
                  <div className="w-9 h-9 rounded-xl bg-slate-900 text-white shrink-0 flex items-center justify-center mt-1 shadow-md">
                    <span className="material-symbols-outlined text-[20px]">smart_toy</span>
                  </div>
                )}

                <div className={`flex flex-col gap-2.5 w-full ${msg.role === 'user' ? 'max-w-[85%] sm:max-w-[70%]' : 'max-w-[88%] sm:max-w-[80%]'}`}>
                  
                  {msg.role === 'user' ? (
                    <div className="bg-slate-900 text-white p-5 rounded-2xl rounded-tr-xs shadow-sm font-medium text-sm leading-relaxed">
                      {msg.content}
                    </div>
                  ) : (
                    <>
                      {/* Scanning Loader Pill */}
                      {msg.scanningText && (
                        <div className={`flex items-center gap-2 text-xs font-medium py-1.5 px-3.5 rounded-lg bg-white border border-slate-200 text-slate-700 self-start shadow-xs ${msg.isRetrieving ? 'rag-scanning' : ''}`}>
                          <span className={`material-symbols-outlined text-[16px] text-sky-600 ${msg.isRetrieving ? 'animate-spin' : ''}`}>
                            {msg.isRetrieving ? 'sync' : 'verified'}
                          </span>
                          {msg.scanningText}
                        </div>
                      )}

                      {/* Assistant Response Body Card */}
                      {msg.content && (
                        <div className="bg-white p-6 rounded-2xl rounded-tl-xs border border-slate-200/90 shadow-sm text-slate-900 border-l-4 border-l-slate-900">
                          <div className="prose max-w-none">
                            {parseMarkdownAndCitations(msg.content)}
                          </div>
                        </div>
                      )}

                      {/* Source Citation Cards */}
                      {msg.sources && msg.sources.length > 0 && (
                        <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-3">
                          {msg.sources.map(src => (
                            <div
                              key={src.id}
                              id={`citation-card-${src.id}`}
                              className="bg-white rounded-xl p-3.5 flex gap-3 items-start border border-slate-200 hover:border-slate-400 transition-all cursor-pointer group shadow-xs relative"
                              title={src.content}
                            >
                              <div className="w-8 h-8 rounded-lg bg-slate-100 border border-slate-200 flex items-center justify-center shrink-0 text-slate-700 group-hover:bg-slate-900 group-hover:text-white transition-colors">
                                <span className="material-symbols-outlined text-[18px]">
                                  {src.filename.toLowerCase().includes('tax') || src.filename.toLowerCase().includes('finance') ? 'gavel' : 'description'}
                                </span>
                              </div>

                              <div className="overflow-hidden flex-1">
                                <h5 className="text-xs font-bold text-slate-900 group-hover:text-sky-700 transition-colors truncate w-full">
                                  {src.filename}
                                </h5>
                                <div className="flex items-center gap-2 mt-1">
                                  <span className="text-[11px] text-slate-500 truncate max-w-[90px]">{src.section}</span>
                                  <span className="w-1 h-1 rounded-full bg-slate-300 shrink-0"></span>
                                  <span className="text-[11px] text-emerald-700 font-bold flex items-center gap-0.5 shrink-0">
                                    <span className="material-symbols-outlined text-[12px]">verified</span>
                                    {src.score} Match
                                  </span>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </>
                  )}

                </div>
              </div>
            ))
          )}
          <div ref={chatEndRef} />
        </div>
      </div>

      {/* Fixed Input Area Footer */}
      <div className="absolute bottom-0 left-0 right-0 p-4 sm:p-6 bg-gradient-to-t from-slate-50 via-slate-50/95 to-transparent pt-8">
        <div className="max-w-4xl mx-auto flex flex-col gap-2 relative">
          
          {/* Action Row */}
          <div className="flex justify-between items-center px-2 mb-1">
            <button
              onClick={onClearChat}
              className="text-xs font-bold text-slate-700 hover:text-slate-950 flex items-center gap-1 transition-colors cursor-pointer"
            >
              <span className="material-symbols-outlined text-[16px]">add_circle</span> Start New Chat
            </button>

            <span className="text-xs text-slate-500 font-medium flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span> Index Status: <strong className="text-slate-800">{indexStatus}</strong>
            </span>
          </div>

          {/* Textarea Input Container */}
          <div className="relative bg-white rounded-2xl border border-slate-200/90 shadow-md focus-within:border-slate-400 focus-within:ring-2 focus-within:ring-slate-900/10 transition-all">
            <textarea
              ref={textareaRef}
              value={inputText}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              className="w-full bg-transparent border-none rounded-2xl py-4 pl-5 pr-14 text-slate-900 text-sm placeholder-slate-400 resize-none focus:outline-none focus:ring-0 font-medium"
              placeholder="Ask a question about corporate remote work policies, travel guidelines, or compliance..."
              rows={1}
              style={{ minHeight: '56px', maxHeight: '150px', overflowY: 'auto' }}
              disabled={sending}
            />

            {/* Send Action Button */}
            <button
              onClick={handleSend}
              className="absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 bg-slate-900 text-white rounded-xl hover:bg-slate-800 transition-all shadow-md active:scale-95 cursor-pointer disabled:opacity-40 flex items-center justify-center"
              disabled={!inputText.trim() || sending}
              aria-label="Send message"
            >
              {sending ? (
                <span className="material-symbols-outlined animate-spin text-[18px]">sync</span>
              ) : (
                <span className="material-symbols-outlined text-[20px]">send</span>
              )}
            </button>
          </div>
          
          <div className="text-center mt-1.5">
            <span className="text-[11px] text-slate-400 font-medium">
              Lexis AI generates answers grounded strictly in internal policy documents.
            </span>
          </div>

        </div>
      </div>

    </div>
  );
}
