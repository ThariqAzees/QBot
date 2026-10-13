import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  MessageSquare,
  Plus,
  Trash2,
  Send,
  PanelLeftClose,
  PanelLeft,
  Moon,
  Sun,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  FileText,
  AlertCircle,
  GraduationCap,
  Sparkles,
  Info,
  ExternalLink,
  BookOpen
} from 'lucide-react';

const SUGGESTED_QUESTIONS = [
  {
    title: 'Explain Anna University 2023 regulations',
    desc: 'Key rules, grading system, and credit framework',
    query: 'Explain the Anna University 2023 regulations.'
  },
  {
    title: 'Semester passing requirements',
    desc: 'Minimum internal marks, end-sem cutoffs, and GPA requirements',
    query: 'What are the semester passing requirements in Anna University?'
  },
  {
    title: 'Attendance requirements',
    desc: 'Minimum attendance percentage and condonation criteria',
    query: 'Explain the attendance requirements under Anna University regulations.'
  },
  {
    title: 'Syllabus & Curriculum overview',
    desc: 'B.E. CSE curriculum changes and credit distribution',
    query: 'Summarize the syllabus and curriculum structure for B.E. CSE.'
  }
];

export default function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem('qbot-theme') || 'dark');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [conversations, setConversations] = useState([]);
  const [activeConvId, setActiveConvId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState(null);
  const [systemHealth, setSystemHealth] = useState(null);
  const [showDiagnostics, setShowDiagnostics] = useState(false);
  const [expandedSources, setExpandedSources] = useState({});

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  // Apply theme to document element
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('qbot-theme', theme);
  }, [theme]);

  // Fetch conversations and health check on mount
  useEffect(() => {
    fetchHealth();
    fetchConversations();
    const interval = setInterval(fetchHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  // Auto-scroll when messages change or loading state changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const fetchHealth = async () => {
    try {
      const res = await fetch('/api/health');
      if (res.ok) {
        const data = await res.json();
        setSystemHealth(data);
      }
    } catch (err) {
      setSystemHealth({
        status: 'degraded',
        database: { connected: false, error: 'Cannot connect to backend server' },
        openai: { configured: false, error: 'Backend unreachable' }
      });
    }
  };

  const fetchConversations = async () => {
    try {
      const res = await fetch('/api/conversations');
      if (res.ok) {
        const data = await res.json();
        setConversations(data);
      }
    } catch (err) {
      console.error('Error fetching conversations:', err);
    }
  };

  const loadConversation = async (convId) => {
    setActiveConvId(convId);
    setIsLoading(true);
    try {
      const res = await fetch(`/api/conversations/${convId}`);
      if (res.ok) {
        const data = await res.json();
        setMessages(data.messages || []);
      }
    } catch (err) {
      console.error('Error loading conversation:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const startNewChat = () => {
    setActiveConvId(null);
    setMessages([]);
    setInputMessage('');
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  const handleDeleteConversation = async (convId) => {
    try {
      const res = await fetch(`/api/conversations/${convId}`, { method: 'DELETE' });
      if (res.ok) {
        setConversations((prev) => prev.filter((c) => c.id !== convId));
        if (activeConvId === convId) {
          startNewChat();
        }
      }
    } catch (err) {
      console.error('Error deleting conversation:', err);
    } finally {
      setDeleteConfirmId(null);
    }
  };

  const handleSendMessage = async (customText = null) => {
    const textToSend = (typeof customText === 'string' ? customText : inputMessage).trim();
    if (!textToSend || isLoading) return;

    setInputMessage('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    const userMsg = {
      role: 'user',
      content: textToSend,
      timestamp: new Date().toISOString()
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const payload = {
        message: textToSend,
        conversation_id: activeConvId || undefined
      };

      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await res.json();

      if (!res.ok) {
        // Detailed error message from backend
        const errorDetail = data.detail || 'Failed to generate answer from server.';
        const assistantErrorMsg = {
          role: 'assistant',
          content: `⚠️ **Service Notification:**\n\n${errorDetail}`,
          isError: true,
          sources: [],
          timestamp: new Date().toISOString()
        };
        setMessages((prev) => [...prev, assistantErrorMsg]);
      } else {
        const assistantMsg = {
          role: 'assistant',
          content: data.answer,
          sources: data.sources || [],
          similarity_category: data.similarity_category || 'medium',
          related_questions: data.related_questions || [],
          timestamp: new Date().toISOString()
        };
        setMessages((prev) => [...prev, assistantMsg]);

        // If conversation was new, set active ID and refresh conversation list
        if (!activeConvId && data.conversation_id) {
          setActiveConvId(data.conversation_id);
        }
        fetchConversations();
      }
    } catch (err) {
      const assistantErrorMsg = {
        role: 'assistant',
        content: `⚠️ **Connection Error:** Could not reach the backend API server. Please verify that \`python -m uvicorn server:app\` is running.`,
        isError: true,
        sources: [],
        timestamp: new Date().toISOString()
      };
      setMessages((prev) => [...prev, assistantErrorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleTextareaInput = (e) => {
    setInputMessage(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = Math.min(e.target.scrollHeight, 200) + 'px';
  };

  const handleCopy = (text, index) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const toggleSources = (idx) => {
    setExpandedSources((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const activeTitle = conversations.find((c) => c.id === activeConvId)?.title || 'New Chat';

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? '' : 'collapsed'}`}>
        <div className="sidebar-header">
          <div className="brand">
            <div className="brand-icon">
              <GraduationCap size={18} />
            </div>
            <span>Anna Univ QBot</span>
          </div>
          <button
            className="icon-btn"
            title="Collapse Sidebar"
            onClick={() => setSidebarOpen(false)}
          >
            <PanelLeftClose size={18} />
          </button>
        </div>

        <button className="new-chat-btn" onClick={startNewChat}>
          <Plus size={16} />
          <span>New chat</span>
        </button>

        <div className="sidebar-history">
          <div className="history-label">Recent Conversations</div>
          {conversations.length === 0 ? (
            <div style={{ padding: '16px 8px', fontSize: '13px', color: 'var(--text-muted)' }}>
              No previous chats yet
            </div>
          ) : (
            conversations.map((c) => (
              <div
                key={c.id}
                className={`conversation-item ${activeConvId === c.id ? 'active' : ''}`}
                onClick={() => loadConversation(c.id)}
              >
                <span className="conv-title" title={c.title}>
                  {c.title}
                </span>
                <div className="conv-actions">
                  <button
                    className="icon-btn danger"
                    title="Delete Conversation"
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeleteConfirmId(c.id);
                    }}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="sidebar-footer">
          <div
            className="status-pill"
            style={{ cursor: 'pointer' }}
            onClick={() => setShowDiagnostics(true)}
            title="Click for System Diagnostics"
          >
            <div
              className={`status-dot ${
                systemHealth?.status === 'ok'
                  ? ''
                  : systemHealth?.database?.connected
                  ? 'degraded'
                  : 'error'
              }`}
            />
            <span style={{ flex: 1 }}>
              {systemHealth?.status === 'ok'
                ? 'Atlas & Gemini Ready'
                : systemHealth?.database?.connected && !systemHealth?.gemini?.configured
                ? 'Atlas Ready (Needs Gemini Key)'
                : systemHealth?.database?.connected
                ? 'Atlas Online (Degraded)'
                : 'Configuration Needed'}
            </span>
            <Info size={14} />
          </div>

          <div className="theme-toggle-row">
            <span>Theme</span>
            <button
              className="icon-btn"
              onClick={() => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))}
              title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} mode`}
            >
              {theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
            </button>
          </div>
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="main-chat">
        {/* Chat Header */}
        <header className="chat-header">
          <div className="chat-header-left">
            {!sidebarOpen && (
              <button
                className="icon-btn"
                title="Expand Sidebar"
                onClick={() => setSidebarOpen(true)}
              >
                <PanelLeft size={19} />
              </button>
            )}
            <h1 className="header-title">{activeTitle}</h1>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              className="icon-btn"
              onClick={() => setShowDiagnostics(true)}
              title="System Status & Ingested Docs"
            >
              <BookOpen size={18} />
            </button>
          </div>
        </header>

        {/* Chat Scroll Area */}
        <div className="chat-scroll-container">
          {messages.length === 0 ? (
            <div className="welcome-container">
              <div className="welcome-logo">
                <GraduationCap size={32} />
              </div>
              <h2 className="welcome-title">How can I help you with Anna University?</h2>
              <p className="welcome-subtitle">
                Ask about 2023 Academic Regulations, B.E./B.Tech Curricula (2018, 2024, 2026),
                credits, grades, passing rules, or the CEG calendar.
              </p>

              <div className="suggestions-grid">
                {SUGGESTED_QUESTIONS.map((q, idx) => (
                  <div
                    key={idx}
                    className="suggestion-card"
                    onClick={() => handleSendMessage(q.query)}
                  >
                    <div className="suggestion-text">{q.title}</div>
                    <div className="suggestion-sub">
                      <span>{q.desc}</span>
                      <Sparkles size={12} style={{ color: 'var(--accent)' }} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="message-list">
              {messages.map((msg, idx) => {
                const isUser = msg.role === 'user';
                return (
                  <div key={idx} className={`message-row ${isUser ? 'user' : 'assistant'}`}>
                    {!isUser && (
                      <div className="message-avatar assistant">
                        <GraduationCap size={18} />
                      </div>
                    )}
                    <div className="message-bubble">
                      <div className="markdown-content">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {msg.content}
                        </ReactMarkdown>
                      </div>

                      {/* Source Citations */}
                      {!isUser && msg.sources && msg.sources.length > 0 && (
                        <div className="sources-card">
                          <div className="sources-header" onClick={() => toggleSources(idx)}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <FileText size={14} />
                              <span>
                                Retreived References ({msg.sources.length}{' '}
                                {msg.sources.length === 1 ? 'document' : 'documents'})
                              </span>
                            </div>
                            {expandedSources[idx] ? (
                              <ChevronUp size={16} />
                            ) : (
                              <ChevronDown size={16} />
                            )}
                          </div>
                          {expandedSources[idx] && (
                            <div className="sources-list">
                              {msg.sources.map((s, sIdx) => {
                                const pages =
                                  s.page_start === s.page_end
                                    ? `p. ${s.page_start}`
                                    : `pp. ${s.page_start}-${s.page_end}`;
                                return (
                                  <div key={sIdx} className="source-item">
                                    <span className="doc-name">{s.source_document}</span>
                                    <span className="page-score">
                                      {pages} • score: {s.score}
                                    </span>
                                  </div>
                                );
                              })}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Related Questions */}
                      {!isUser && msg.related_questions && msg.related_questions.length > 0 && (
                        <div className="related-box">
                          <span className="related-label">Related questions:</span>
                          <div className="chips-wrap">
                            {msg.related_questions.map((rq, rqIdx) => (
                              <button
                                key={rqIdx}
                                className="related-chip"
                                onClick={() => handleSendMessage(rq)}
                              >
                                {rq}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Metadata bar for assistant */}
                      {!isUser && !msg.isError && (
                        <div className="message-meta">
                          <button
                            className="icon-btn"
                            title="Copy response"
                            onClick={() => handleCopy(msg.content, idx)}
                          >
                            {copiedIndex === idx ? (
                              <Check size={14} style={{ color: 'var(--accent)' }} />
                            ) : (
                              <Copy size={14} />
                            )}
                          </button>
                          {msg.similarity_category && (
                            <span
                              className={`confidence-badge ${msg.similarity_category}`}
                              title={`Retrieval confidence: ${msg.similarity_category}`}
                            >
                              {msg.similarity_category} confidence
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}

              {/* Generating loading indicator */}
              {isLoading && (
                <div className="message-row assistant">
                  <div className="message-avatar assistant">
                    <GraduationCap size={18} />
                  </div>
                  <div className="message-bubble">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div className="loading-dots">
                        <div className="dot" />
                        <div className="dot" />
                        <div className="dot" />
                      </div>
                      <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
                        Searching Anna University documents & generating response...
                      </span>
                    </div>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Fixed Message Composer */}
        <div className="composer-wrapper">
          <div className="composer-box">
            <textarea
              ref={textareaRef}
              className="chat-textarea"
              placeholder="Ask anything about Anna University regulations or curriculum..."
              rows={1}
              value={inputMessage}
              onChange={handleTextareaInput}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
            />
            <button
              className="send-btn"
              disabled={!inputMessage.trim() || isLoading}
              onClick={() => handleSendMessage()}
              title="Send Message (Enter)"
            >
              <Send size={16} />
            </button>
          </div>
          <div className="disclaimer-text">
            Answers are generated from Anna University academic documents (2018 RUSA, 2023 Regs,
            2024/2026 Curricula, CEG Calendar). Verify against official university publications.
          </div>
        </div>
      </main>

      {/* Delete Confirmation Modal */}
      {deleteConfirmId && (
        <div className="modal-overlay" onClick={() => setDeleteConfirmId(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-title">Delete Conversation?</div>
            <div className="modal-desc">
              This will permanently delete this conversation and its question-answering history from
              the database.
            </div>
            <div className="modal-buttons">
              <button className="btn-secondary" onClick={() => setDeleteConfirmId(null)}>
                Cancel
              </button>
              <button
                className="btn-danger"
                onClick={() => handleDeleteConversation(deleteConfirmId)}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Diagnostics / Ingested Docs Modal */}
      {showDiagnostics && (
        <div className="modal-overlay" onClick={() => setShowDiagnostics(false)}>
          <div
            className="modal-card"
            style={{ maxWidth: '520px' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <GraduationCap size={20} style={{ color: 'var(--accent)' }} />
              System Status & Documents
            </div>
            <div className="modal-desc" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div>
                <strong>MongoDB Atlas:</strong>{' '}
                {systemHealth?.database?.connected ? (
                  <span style={{ color: 'var(--accent)' }}>Connected ({systemHealth?.database?.chunks_count || 0} chunks)</span>
                ) : (
                  <span style={{ color: '#ef4444' }}>
                    {systemHealth?.database?.error || 'Disconnected'}
                  </span>
                )}
              </div>
              <div>
                <strong>Google Gemini (Free Tier):</strong>{' '}
                {systemHealth?.gemini?.configured ? (
                  <span style={{ color: 'var(--accent)' }}>
                    Active (Model: <code>{systemHealth?.gemini?.model}</code>)
                  </span>
                ) : (
                  <span style={{ color: '#ef4444' }}>
                    Key not set — get free key at{' '}
                    <a
                      href="https://aistudio.google.com/app/apikey"
                      target="_blank"
                      rel="noreferrer"
                      style={{ color: 'var(--accent)', textDecoration: 'underline' }}
                    >
                      aistudio.google.com
                    </a>
                  </span>
                )}
              </div>
              <div>
                <strong>Embeddings:</strong>{' '}
                <span>
                  <code>{systemHealth?.embedding?.model}</code> ({systemHealth?.embedding?.dimensions}-dim, 100% Free Local CPU)
                </span>
              </div>
              <div>
                <strong>Included University Documents:</strong>
                <ul style={{ margin: '6px 0 0 18px', fontSize: '12.5px' }}>
                  {systemHealth?.documents?.map((doc, dIdx) => (
                    <li key={dIdx}>{doc}</li>
                  ))}
                </ul>
              </div>
            </div>
            <div className="modal-buttons">
              <button className="btn-secondary" onClick={() => setShowDiagnostics(false)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
