import React from 'react';
import { X, Sparkles, FileText, CheckCircle2 } from 'lucide-react';

export default function SummaryModal({ doc, summary, loading, onClose }) {
  if (!doc) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <header className="modal-header">
          <div className="modal-title">
            <Sparkles size={20} className="modal-icon" />
            <div>
              <h3>Executive Summary</h3>
              <span className="modal-subtitle">{doc.name}</span>
            </div>
          </div>
          <button className="btn-close" onClick={onClose}>
            <X size={18} />
          </button>
        </header>

        <div className="modal-body">
          {loading ? (
            <div className="summary-loading">
              <div className="spinner-lg"></div>
              <p>Analyzing document content & synthesizing executive summary...</p>
            </div>
          ) : (
            <div className="summary-text">
              {summary ? summary.split('\n').map((paragraph, idx) => {
                if (paragraph.startsWith('- **') || paragraph.startsWith('###')) {
                  return (
                    <div key={idx} className="summary-heading">
                      <CheckCircle2 size={16} />
                      <strong>{paragraph.replace(/^[-#*]+/, '').trim()}</strong>
                    </div>
                  );
                }
                return <p key={idx}>{paragraph}</p>;
              }) : (
                <p>Failed to generate summary.</p>
              )}
            </div>
          )}
        </div>

        <footer className="modal-footer">
          <button className="btn-secondary" onClick={onClose}>
            Close
          </button>
        </footer>
      </div>
    </div>
  );
}
