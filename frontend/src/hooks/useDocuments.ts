import { useState, useEffect, useRef, useCallback } from 'react';
import api from '../api/axios';

export interface Document {
  id: number;
  filename: string;
  stored_filename?: string | null;
  tag: string | null;
  status: 'Processing' | 'Indexed' | 'Failed';
  storage_size: string;
  last_updated: string;
  description: string | null;
}

export function useDocuments() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollingRef = useRef<any | null>(null);

  const fetchDocuments = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get<Document[]>('/documents');
      setDocuments(res.data);
      setError(null);
    } catch (err: any) {
      console.error(err);
      setError('Failed to fetch documents.');
    } finally {
      setLoading(false);
    }
  }, []);

  const uploadDocument = async (files: File | File[]) => {
    const fileList = Array.isArray(files) ? files : [files];
    const formData = new FormData();

    fileList.forEach((file) => {
      formData.append('files', file);
    });

    try {
      const res = await api.post('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      await fetchDocuments();
      return res.data;
    } catch (err: any) {
      console.error(err);
      const msg = err.response?.data?.detail || 'Failed to upload document.';
      throw new Error(msg);
    }
  };

  const deleteDocument = async (id: number) => {
    try {
      await api.delete(`/documents/${id}`);
      setDocuments(prev => prev.filter(doc => doc.id !== id));
    } catch (err: any) {
      console.error(err);
      throw new Error('Failed to delete document.');
    }
  };

  // Poll for document status if there are any 'Processing' documents
  useEffect(() => {
    const hasProcessing = documents.some(doc => doc.status === 'Processing');
    
    if (hasProcessing && !pollingRef.current) {
      pollingRef.current = setInterval(async () => {
        try {
          const res = await api.get<Document[]>('/documents');
          setDocuments(res.data);
          
          const stillProcessing = res.data.some(doc => doc.status === 'Processing');
          if (!stillProcessing && pollingRef.current) {
            clearInterval(pollingRef.current);
            pollingRef.current = null;
          }
        } catch (err) {
          console.error('Error during document polling:', err);
        }
      }, 3000);
    }

    return () => {
      if (!hasProcessing && pollingRef.current) {
        clearInterval(pollingRef.current);
        pollingRef.current = null;
      }
    };
  }, [documents]);

  // Clean up timer on unmount
  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  return {
    documents,
    loading,
    error,
    fetchDocuments,
    uploadDocument,
    deleteDocument,
  };
}
