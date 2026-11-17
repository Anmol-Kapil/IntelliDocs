import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, 
  Trash, 
  Sparkles, 
  FileText, 
  Bot, 
  User, 
  BookOpen, 
  Check, 
  Copy,
  SlidersHorizontal
} from 'lucide-react';

export default function ChatArea({ 
  selectedDoc, 
  documents, 
  messages, 
  onSendMessage, 
  onResetChat, 
  loading 
}) {
  const [inputQuery, setInputQuery] = useState('');
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [topK, setTopK] = useState(4);
  const [showSettings, setShowSettings] = useState(false);
  const chatBottomRef = useRef(null);

  const activeDocObj = selectedDoc ? documents.find(d => d.doc_id === selectedDoc) : null;

  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!inputQuery.trim() || loading) return;
    onSendMessage(inputQuery, selectedDoc, topK);
    setInputQuery('');
  };

  const handleCopy = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const suggestionPills = activeDocObj ? [
    `Summarize key highlights of ${activeDocObj.name}`,
    `What are the main conclusions in ${activeDocObj.name}?`,
    `List all key metrics mentioned in this document`
  ] : [
    "What are the common themes across all documents?",
    "Summarize the main findings across all files",
    "List all action items mentioned in the knowledge base"
  ];

  return (
    <div className="chat-container">
      {/* Workspace Header */}
      <header className="chat-header">
        <div className="header-info">
          <div className="scope-badge">
            {activeDocObj ? <FileText size={16} /> : <BookOpen size={16} />}
            <span>{activeDocObj ? activeDocObj.name : "All Documents Scope"}</span>
          </div>
          <span className="scope-subtitle">
            {activeDocObj 
              ? `${activeDocObj.pages} Pages • ${activeDocObj.chunks} Vector Chunks` 
              : `Searching across ${documents.length} document${documents.length !== 1 ? 's' : ''}`
            }
          </span>
        </div>

        <div className="header-controls">
          <button 
            className={`btn-secondary icon-only ${showSettings ? 'active' : ''}`}
            title="Search Settings"
            onClick={() => setShowSettings(!showSettings)}
          >
            <SlidersHorizontal size={16} />
          </button>
          <button 
            className="btn-secondary danger-hover"
            onClick={() => onResetChat(selectedDoc)}
            title="Clear conversation history"
            disabled={loading}
          >
            <Trash size={16} />
            <span>Clear History</span>
          </button>
        </div>
      </header>

      {/* Settings Bar */}
      {showSettings && (
        <div className="settings-panel">
          <label>Context Retrieval Depth (Top K Chunks): <strong>{topK}</strong></label>
          <input 
            type="range" 
            min="2" 
            max="8" 
            value={topK} 
            onChange={(e) => setTopK(parseInt(e.target.value))} 
          />
        </div>
      )}

      {/* Messages Scroll Area */}
      <div className="chat-scroll-area">
        {messages.length === 0 ? (
          <div className="chat-welcome">
            <div className="welcome-icon">
              <Sparkles size={32} />
            </div>
            <h3>Ask Anything About Your Documents</h3>
            <p>DocMind AI retrieves semantic context and generates accurate responses with source citations.</p>
            
            <div className="suggestions-grid">
              {suggestionPills.map((pill, i) => (
                <button 
                  key={i} 
                  className="suggestion-pill"
                  onClick={() => {
                    setInputQuery(pill);
                  }}
                >
                  <span>"{pill}"</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="messages-list">
            {messages.map((msg, i) => (
              <div key={i} className={`message-bubble ${msg.role}`}>
                <div className="avatar">
                  {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                </div>

                <div className="message-content">
                  <div className="message-header">
                    <span className="author-name">{msg.role === 'user' ? 'You' : 'DocMind AI'}</span>
                    {msg.role === 'assistant' && (
                      <button 
                        className="btn-copy" 
                        onClick={() => handleCopy(msg.text, i)}
                        title="Copy text"
                      >
                        {copiedIndex === i ? <Check size={14} /> : <Copy size={14} />}
                      </button>
                    )}
                  </div>

                  <div className="text-body">
                    {msg.text.split('\n').map((paragraph, pIdx) => (
                      <p key={pIdx}>{paragraph}</p>
                    ))}
                  </div>

                  {/* Sources Citation Bar */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="sources-card">
                      <div className="sources-header">
                        <BookOpen size={12} />
                        <span>Sources Cited ({msg.sources.length})</span>
                      </div>
                      <div className="sources-tags">
                        {msg.sources.map((s, idx) => (
                          <div key={idx} className="source-tag">
                            <span className="source-doc">{s.doc}</span>
                            <span className="source-page">Page {s.page}</span>
                            <span className="source-score">{Math.round(s.relevance * 100)}% match</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="message-bubble assistant loading-bubble">
                <div className="avatar">
                  <Bot size={16} />
                </div>
                <div className="message-content">
                  <div className="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </div>
              </div>
            )}

            <div ref={chatBottomRef} />
          </div>
        )}
      </div>

      {/* Chat Input Bar */}
      <div className="chat-input-area">
        <form onSubmit={handleSubmit} className="input-form">
          <input 
            type="text"
            className="chat-input"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            placeholder={activeDocObj ? `Ask questions about ${activeDocObj.name}...` : "Ask questions across all documents..."}
            disabled={loading}
          />
          <button 
            type="submit" 
            className="btn-send"
            disabled={loading || !inputQuery.trim()}
          >
            <Send size={18} />
          </button>
        </form>
      </div>
    </div>
  );
}
