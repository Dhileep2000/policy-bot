import { useState } from 'react';
import api from '../api/axios';

export interface Source {
  id: number;
  company?: string;
  filename: string;
  tag: string;
  section: string;
  score: string;
  content: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  isRetrieving?: boolean;
  scanningText?: string;
  sources?: Source[];
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome-message',
      role: 'assistant',
      isRetrieving: false,
      content: 'Hello! I am your Lexis AI Document Intelligence Assistant. ' +
        'Upload your documents (such as price lists, guides, FAQs, or policies) in the **Knowledge Base** tab, ' +
        'and I will help you retrieve and analyze information from them. Ask me anything!',
    }
  ]);
  const [sending, setSending] = useState(false);
  const [indexStatus, setIndexStatus] = useState<'Operational' | 'Searching'>('Operational');

  const sendMessage = async (text: string) => {
    if (!text.trim() || sending) return;

    const userMessageId = `user-${Date.now()}`;
    const assistantMessageId = `assistant-${Date.now()}`;

    // Add user message
    const userMsg: Message = {
      id: userMessageId,
      role: 'user',
      content: text,
    };
    
    // Add temp assistant message with loading state
    const assistantMsg: Message = {
      id: assistantMessageId,
      role: 'assistant',
      isRetrieving: true,
      scanningText: 'Connecting to Index...',
      content: '',
      sources: [],
    };

    setMessages(prev => [...prev, userMsg, assistantMsg]);
    setSending(true);
    setIndexStatus('Searching');

    try {
      // Simulate scanning progression for UI beauty
      setTimeout(() => {
        setMessages(prev =>
          prev.map(m =>
            m.id === assistantMessageId
              ? { ...m, scanningText: 'Searching Vector Embeddings...' }
              : m
          )
        );
      }, 1000);

      setTimeout(() => {
        setMessages(prev =>
          prev.map(m =>
            m.id === assistantMessageId
              ? { ...m, scanningText: 'Synthesizing with Gemini 2.5 Flash...' }
              : m
          )
        );
      }, 2500);

      const res = await api.post('/chat', { message: text });
      
      const { answer, sources, index_names, response_type } = res.data;
      
      // Determine the scanning text based on response type
      let scanText: string;
      if (response_type === 'general_knowledge') {
        scanText = 'Answered from General Knowledge (Gemini 2.5 Flash)';
      } else {
        const indexStr = index_names && index_names.length > 0 
          ? index_names.join(', ') 
          : 'General Policy Index';
        scanText = `Retrieved from Policy Index (${indexStr})`;
      }

      // Update final answer
      setMessages(prev =>
        prev.map(m =>
          m.id === assistantMessageId
            ? {
                ...m,
                isRetrieving: false,
                scanningText: scanText,
                content: answer,
                sources: sources || [],
              }
            : m
        )
      );
    } catch (err) {
      console.error(err);
      const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail;
      setMessages(prev =>
        prev.map(m =>
          m.id === assistantMessageId
            ? {
                ...m,
                isRetrieving: false,
                scanningText: 'Error during retrieval',
                content: detail
                  ? `Sorry, I could not complete that request: ${detail}`
                  : 'Sorry, I could not reach the policy service. Please confirm that the backend is running.',
                sources: [],
              }
            : m
        )
      );
    } finally {
      setSending(false);
      setIndexStatus('Operational');
    }
  };

  const clearChat = () => {
    setMessages([]);
  };

  return {
    messages,
    sending,
    indexStatus,
    sendMessage,
    clearChat,
  };
}
