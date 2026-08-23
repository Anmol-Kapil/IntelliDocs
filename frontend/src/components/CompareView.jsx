import React, { useState } from 'react';
import { Layers, ArrowRight, Sparkles, FileText } from 'lucide-react';

export default function CompareView({ documents, onCompare, loading }) {
  const [docId1, setDocId1] = useState('');
  const [docId2, setDocId2] = useState('');
  const [query, setQuery] = useState('');
  const [result, setResult] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query || !docId1 || !docId2) return;
    if (docId1 === docId2) {
      alert("Please select two different documents to compare.");
      return;
    }

    const output = await onCompare(query, docId1, docId2);
    if (output) {
      setResult(output);
    }
  };

  return (
    <div className="compare-container">
      <header className="compare-header">
        <div className="header-info">
          <div className="scope-badge">
            <Layers size={16} />
            <span>Cross-Document Semantic Comparison</span>
          </div>
          <span className="scope-subtitle">
            Compare statements, differences, and similarities between two documents side-by-side.
          </span>
        </div>
      </header>

      <div className="compare-body">
        <form onSubmit={handleSubmit} className="compare-card">
          <div className="selectors-row">
            <div className="select-group">
              <label><FileText size={14} /> Document 1</label>
              <select value={docId1} onChange={(e) => setDocId1(e.target.value)}>
                <option value="">-- Select First Document --</option>
                {documents.map(d => (
                  <option key={d.doc_id} value={d.doc_id}>{d.name}</option>
                ))}
              </select>
            </div>

            <div className="vs-badge">VS</div>

            <div className="select-group">
              <label><FileText size={14} /> Document 2</label>
              <select value={docId2} onChange={(e) => setDocId2(e.target.value)}>
                <option value="">-- Select Second Document --</option>
                {documents.map(d => (
                  <option key={d.doc_id} value={d.doc_id}>{d.name}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="query-group">
            <label>Comparison Topic / Prompt</label>
            <input 
              type="text" 
              value={query} 
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. Compare pricing models, risk factors, or key deliverables..."
            />
          </div>

          <button 
            type="submit" 
            className="btn-primary compare-btn"
            disabled={loading || !docId1 || !docId2 || !query.trim()}
          >
            {loading ? (
              <>
                <div className="spinner-sm"></div>
                <span>Analyzing Documents...</span>
              </>
            ) : (
              <>
                <Sparkles size={18} />
                <span>Run Matrix Comparison</span>
              </>
            )}
          </button>
        </form>

        {result && (
          <div className="comparison-output">
            <div className="output-header">
              <Sparkles size={18} className="output-icon" />
              <h3>AI Comparison Analysis</h3>
            </div>
            <div className="output-body">
              {result.split('\n').map((line, idx) => {
                if (line.startsWith('###')) {
                  return <h4 key={idx}>{line.replace('###', '').trim()}</h4>;
                }
                return <p key={idx}>{line}</p>;
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
