import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import CompareView from './components/CompareView';
import SummaryModal from './components/SummaryModal';
import { 
  getDocuments, 
  uploadDocument, 
  deleteDocument, 
  sendChatMessage, 
  compareDocuments, 
  resetChatHistory,
  getDocumentSummary
} from './api/client';
import './App.css';

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'compare'

  // Summary Modal state
  const [summaryModalDoc, setSummaryModalDoc] = useState(null);
  const [summaryText, setSummaryText] = useState('');
  const [summaryLoading, setSummaryLoading] = useState(false);

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      const res = await getDocuments();
      if (res.data && res.data.documents) {
        setDocuments(res.data.documents);
      }
    } catch (err) {
      console.error('Failed to fetch documents:', err);
    }
  };

  const handleUpload = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('name', file.name.replace(/\.[^/.]+$/, ""));

    setUploading(true);
    try {
      await uploadDocument(formData);
      await fetchDocuments();
    } catch (err) {
      alert(`Upload failed: ${err.response?.data?.error || err.message}`);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId, docName) => {
    if (!window.confirm(`Are you sure you want to delete "${docName}"?`)) return;

    try {
      await deleteDocument(docId);
      if (selectedDoc === docId) {
        setSelectedDoc(null);
      }
      await fetchDocuments();
    } catch (err) {
      alert(`Failed to delete: ${err.message}`);
    }
  };

  const handleSendMessage = async (question, docId, topK) => {
    setMessages(prev => [...prev, { role: 'user', text: question }]);
    setLoading(true);

    try {
      const res = await sendChatMessage(question, docId, topK);
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: res.data.answer,
        sources: res.data.sources
      }]);
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: `Error processing query: ${err.response?.data?.error || err.message}`
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleResetChat = async (docId) => {
    try {
      await resetChatHistory(docId);
      setMessages([]);
    } catch (err) {
      console.error('Reset error:', err);
    }
  };

  const handleCompare = async (question, id1, id2) => {
    setLoading(true);
    try {
      const res = await compareDocuments(question, id1, id2);
      return res.data.comparison;
    } catch (err) {
      alert(`Comparison error: ${err.response?.data?.error || err.message}`);
      return null;
    } finally {
      setLoading(false);
    }
  };

  const handleOpenSummary = async (docId) => {
    const targetDoc = documents.find(d => d.doc_id === docId);
    if (!targetDoc) return;

    setSummaryModalDoc(targetDoc);
    setSummaryLoading(true);
    setSummaryText('');

    try {
      const res = await getDocumentSummary(docId);
      setSummaryText(res.data.summary);
    } catch (err) {
      setSummaryText("Error fetching summary: " + err.message);
    } finally {
      setSummaryLoading(false);
    }
  };

  return (
    <div className="app-layout">
      <Sidebar 
        documents={documents}
        selectedDoc={selectedDoc}
        onSelectDoc={setSelectedDoc}
        onUpload={handleUpload}
        onDelete={handleDelete}
        onOpenSummary={handleOpenSummary}
        uploading={uploading}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
      />

      <main className="main-content">
        {activeTab === 'chat' && (
          <ChatArea 
            selectedDoc={selectedDoc}
            documents={documents}
            messages={messages}
            onSendMessage={handleSendMessage}
            onResetChat={handleResetChat}
            loading={loading}
          />
        )}

        {activeTab === 'compare' && (
          <CompareView 
            documents={documents}
            onCompare={handleCompare}
            loading={loading}
          />
        )}
      </main>

      {summaryModalDoc && (
        <SummaryModal 
          doc={summaryModalDoc}
          summary={summaryText}
          loading={summaryLoading}
          onClose={() => setSummaryModalDoc(null)}
        />
      )}
    </div>
  );
}
