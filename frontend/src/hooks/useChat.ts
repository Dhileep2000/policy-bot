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
      id: 'default-user',
      role: 'user',
      content: 'What is our corporate remote work policy for international employees? Specifically regarding tax implications and duration limits.',
    },
    {
      id: 'default-assistant',
      role: 'assistant',
      isRetrieving: false,
      scanningText: 'Retrieving from Policy Index (HR-Global, Tax-Compliance)',
      content: 'Based on the current **Global Mobility Policy (v2.4)**, here is the corporate stance on international remote work:\n\n' +
        '#### Duration Limits\n' +
        'Employees are permitted to work remotely from an international location for a maximum of **90 days within a rolling 12-month period** [1]. This limit is strictly enforced to prevent triggering permanent establishment risks for the company.\n\n' +
        '#### Tax & Compliance Implications\n' +
        '- **Personal Income Tax:** The employee is solely responsible for determining and fulfilling any personal income tax obligations in the host country [2].\n' +
        '- **Corporate Tax:** Working beyond the 90-day threshold requires executive VP approval and a formal review by the Global Tax Office to assess corporate tax liabilities [3].\n\n' +
        '*Please consult with your HR Business Partner before finalizing any travel arrangements.*',
      sources: [
        {
          id: 1,
          filename: 'Global Mobility Policy v2.4',
          tag: 'HR-POL-01',
          section: 'Sec 4.1',
          score: '98%',
          content: 'Employees are permitted to work remotely from an international location for a maximum of 90 days within a rolling 12-month period...',
        },
        {
          id: 2,
          filename: 'Cross-Border Tax Guidelines',
          tag: 'FIN-POL-04',
          section: 'Appendix B',
          score: '92%',
          content: 'The employee is solely responsible for determining and fulfilling any personal income tax obligations in the host country...',
        },
      ],
    },
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
