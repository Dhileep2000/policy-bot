import React, { useState, useRef } from 'react';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUpload: (files: File | File[]) => Promise<any>;
}

export default function UploadModal({ isOpen, onClose, onUpload }: UploadModalProps) {
  const [dragActive, setDragActive] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [status, setStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFiles = Array.from(e.dataTransfer.files);
      validateAndSetFiles(droppedFiles);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFiles(Array.from(e.target.files));
    }
  };

  const validateAndSetFiles = (selectedFiles: File[]) => {
    const invalidFile = selectedFiles.find((file) => {
      const ext = file.name.split('.').pop()?.toLowerCase();
      return ext !== 'pdf' && ext !== 'txt' && ext !== 'md';
    });

    if (invalidFile) {
      setStatus('error');
      setMessage('Invalid file type. Only PDF, TXT, and MD files are supported.');
      setFiles([]);
      return;
    }

    setFiles(selectedFiles);
    setStatus('idle');
    setMessage('');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!files.length) return;

    setUploading(true);
    setUploadProgress(30);
    setStatus('idle');
    try {
      setUploadProgress(65);
      await onUpload(files);
      setUploadProgress(100);
      const countText = files.length > 1 ? `${files.length} documents` : 'Document';
      setStatus('success');
      setMessage(`${countText} successfully uploaded and enqueued for indexing.`);
      setTimeout(() => {
        onClose();
        setFiles([]);
        setStatus('idle');
        setMessage('');
        setUploadProgress(0);
      }, 1800);
    } catch (err: any) {
      setStatus('error');
      setMessage(err.message || 'Failed to upload document.');
      setUploadProgress(0);
    } finally {
      setUploading(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getFileExtension = (name: string) => {
    return name.split('.').pop()?.toUpperCase() || 'FILE';
  };

  return (
    <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-md flex items-center justify-center z-50 p-4 sm:p-6 animate-fade-in">
      <div className="bg-white border border-slate-200 w-full max-w-lg rounded-2xl shadow-modal relative flex flex-col overflow-hidden transition-all duration-300">
        
        {/* Header Bar */}
        <div className="p-6 pb-4 border-b border-slate-100 flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-slate-900 text-white flex items-center justify-center shrink-0 shadow-md">
              <span className="material-symbols-outlined text-[22px]">upload_file</span>
            </div>
            <div>
              <h3 className="text-lg font-bold text-slate-900 tracking-tight">Upload Policy Document</h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Add corporate policies to your Lexis AI knowledge base
              </p>
            </div>
          </div>
          
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-slate-700 rounded-full hover:bg-slate-100 transition-colors cursor-pointer"
            disabled={uploading}
            aria-label="Close modal"
          >
            <span className="material-symbols-outlined text-[20px]">close</span>
          </button>
        </div>

        {/* Modal Form Body */}
        <form onSubmit={handleSubmit} className="p-6 flex flex-col gap-5">
          
          {/* Dropzone Container */}
          {!files.length ? (
            <div
              className={`border-2 border-dashed rounded-xl p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-all duration-200 min-h-55 ${
                dragActive 
                  ? 'border-slate-900 bg-slate-50 scale-[1.01]' 
                  : 'border-slate-200 hover:border-slate-400 bg-slate-50/50 hover:bg-slate-50'
              }`}
              onDragEnter={handleDrag}
              onDragOver={handleDrag}
              onDragLeave={handleDrag}
              onDrop={handleDrop}
              onClick={() => inputRef.current?.click()}
            >
              <input
                ref={inputRef}
                type="file"
                className="hidden"
                accept=".pdf,.txt,.md"
                multiple
                onChange={handleChange}
                disabled={uploading}
              />
              
              <div className="w-14 h-14 rounded-2xl bg-white border border-slate-200 shadow-sm flex items-center justify-center mb-3 text-slate-700">
                <span className="material-symbols-outlined text-[30px]">cloud_upload</span>
              </div>
              
              <p className="text-sm font-semibold text-slate-800">
                Click to upload <span className="text-slate-500 font-normal">or drag and drop</span>
              </p>
              
              <div className="flex items-center gap-1.5 mt-3">
                <span className="px-2 py-0.5 bg-slate-200/70 text-slate-700 text-[10px] font-bold rounded">PDF</span>
                <span className="px-2 py-0.5 bg-slate-200/70 text-slate-700 text-[10px] font-bold rounded">TXT</span>
                <span className="px-2 py-0.5 bg-slate-200/70 text-slate-700 text-[10px] font-bold rounded">MD</span>
                <span className="text-xs text-slate-400 ml-1">• Up to 100 MB</span>
              </div>
            </div>
          ) : (
            <div className="border border-slate-200 rounded-xl p-4 bg-slate-50 flex flex-col gap-3">
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                  <span className="material-symbols-outlined text-[18px]">description</span>
                  {files.length} file{files.length > 1 ? 's' : ''} selected
                </div>

                {!uploading && (
                  <button
                    type="button"
                    onClick={() => setFiles([])}
                    className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-200/60 rounded-lg transition-colors cursor-pointer shrink-0"
                  >
                    Change Files
                  </button>
                )}
              </div>

              <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                {files.map((file, index) => (
                  <div key={`${file.name}-${index}`} className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white p-2.5">
                    <div className="flex items-center gap-3 overflow-hidden">
                      <div className="w-9 h-9 rounded-lg bg-slate-900 text-white flex items-center justify-center shrink-0 font-bold text-[10px]">
                        {getFileExtension(file.name)}
                      </div>
                      <div className="overflow-hidden">
                        <p className="text-xs font-semibold text-slate-900 truncate" title={file.name}>{file.name}</p>
                        <p className="text-[11px] text-slate-500 mt-0.5">{formatFileSize(file.size)}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Upload Progress Bar */}
          {uploading && (
            <div className="flex flex-col gap-2">
              <div className="flex justify-between items-center text-xs text-slate-600 font-medium">
                <span className="flex items-center gap-1.5">
                  <span className="material-symbols-outlined text-[16px] animate-spin text-slate-900">sync</span>
                  Processing and embedding document...
                </span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
                <div 
                  className="bg-slate-900 h-full rounded-full transition-all duration-500 ease-out" 
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* Status Message Notification */}
          {message && (
            <div className={`p-3.5 rounded-xl text-xs font-medium flex items-start gap-2.5 border ${
              status === 'success' 
                ? 'bg-emerald-50 border-emerald-200 text-emerald-800' 
                : 'bg-red-50 border-red-200 text-red-800'
            }`}>
              <span className="material-symbols-outlined text-[18px] shrink-0 mt-0.5">
                {status === 'success' ? 'check_circle' : 'error'}
              </span>
              <span className="leading-relaxed">{message}</span>
            </div>
          )}

          {/* Footer Actions */}
          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 text-xs font-semibold text-slate-700 hover:text-slate-900 hover:bg-slate-100 rounded-xl transition-colors cursor-pointer"
              disabled={uploading}
            >
              Cancel
            </button>
            
            <button
              type="submit"
              className="px-5 py-2.5 bg-slate-900 text-white text-xs font-semibold rounded-xl hover:bg-slate-800 active:scale-95 transition-all shadow-md disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2 cursor-pointer"
              disabled={!files.length || uploading}
            >
              {uploading ? (
                <>
                  <span className="material-symbols-outlined text-[16px] animate-spin">sync</span>
                  Indexing...
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-[16px]">upload</span>
                  Upload & Index
                </>
              )}
            </button>
          </div>
        </form>

      </div>
    </div>
  );
}
