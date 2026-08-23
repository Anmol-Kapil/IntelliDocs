import React, { useRef } from 'react';
import { 
  FileText, 
  UploadCloud, 
  Trash2, 
  Layers, 
  Sparkles, 
  Compass, 
  BrainCircuit,
  Plus
} from 'lucide-react';

export default function Sidebar({ 
  documents, 
  selectedDoc, 
  onSelectDoc, 
  onUpload, 
  onDelete, 
  onOpenSummary,
  uploading,
  activeTab,
  setActiveTab
}) {
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      onUpload(file);
      e.target.value = '';
    }
  };

  return (
    <aside className="sidebar">
      {/* Brand Header */}
      <div className="sidebar-brand">
        <div className="brand-logo">
          <BrainCircuit size={26} className="brand-icon" />
        </div>
        <div className="brand-text">
          <h2>DocMind AI</h2>
          <span className="badge">RAG v1.0</span>
        </div>
      </div>

      {/* Navigation Tabs */}
      <nav className="sidebar-nav">
        <button 
          className={`nav-item ${activeTab === 'chat' ? 'active' : ''}`}
          onClick={() => setActiveTab('chat')}
        >
          <Compass size={18} />
          <span>Chat Workspace</span>
        </button>
        <button 
          className={`nav-item ${activeTab === 'compare' ? 'active' : ''}`}
          onClick={() => setActiveTab('compare')}
        >
          <Layers size={18} />
          <span>Compare Docs</span>
        </button>
      </nav>

      {/* Upload Action */}
      <div className="upload-section">
        <input 
          type="file" 
          ref={fileInputRef} 
          accept=".pdf,.txt,.md" 
          onChange={handleFileChange} 
          hidden 
        />
        <button 
          className="btn-primary upload-btn" 
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
        >
          {uploading ? (
            <>
              <div className="spinner-sm"></div>
              <span>Processing...</span>
            </>
          ) : (
            <>
              <Plus size={18} />
              <span>Upload Document</span>
            </>
          )}
        </button>
      </div>

      {/* Document Catalog */}
      <div className="doc-catalog">
        <div className="catalog-header">
          <span>KNOWLEDGE BASE ({documents.length})</span>
        </div>

        {/* Global Scope Selector */}
        <div 
          className={`doc-card ${!selectedDoc ? 'selected' : ''}`}
          onClick={() => onSelectDoc(null)}
        >
          <div className="doc-icon global-icon">
            <Layers size={16} />
          </div>
          <div className="doc-info">
            <span className="doc-title">All Documents Scope</span>
            <span className="doc-meta">Global RAG Search</span>
          </div>
        </div>

        {documents.length === 0 ? (
          <div className="empty-catalog">
            <UploadCloud size={32} className="empty-icon" />
            <p>No documents uploaded yet.</p>
            <small>Supports PDF, TXT & Markdown</small>
          </div>
        ) : (
          <div className="doc-list">
            {documents.map((doc) => {
              const isSelected = selectedDoc === doc.doc_id;
              return (
                <div 
                  key={doc.doc_id} 
                  className={`doc-card ${isSelected ? 'selected' : ''}`}
                  onClick={() => onSelectDoc(doc.doc_id)}
                >
                  <div className="doc-icon">
                    <FileText size={16} />
                  </div>
                  <div className="doc-info">
                    <span className="doc-title" title={doc.name}>{doc.name}</span>
                    <span className="doc-meta">
                      {doc.pages} page{doc.pages > 1 ? 's' : ''} • {doc.chunks} chunks
                    </span>
                  </div>
                  <div className="doc-actions" onClick={(e) => e.stopPropagation()}>
                    <button 
                      className="btn-icon" 
                      title="Generate Executive Summary"
                      onClick={() => onOpenSummary(doc.doc_id)}
                    >
                      <Sparkles size={14} />
                    </button>
                    <button 
                      className="btn-icon danger" 
                      title="Delete document"
                      onClick={() => onDelete(doc.doc_id, doc.name)}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Footer Info */}
      <div className="sidebar-footer">
        <div className="footer-status">
          <span className="status-dot"></span>
          <span>Engine: Groq LLaMA 3.3 70B</span>
        </div>
      </div>
    </aside>
  );
}
