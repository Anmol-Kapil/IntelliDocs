import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const getHealth = () => api.get('/health');
export const getDocuments = () => api.get('/documents');
export const uploadDocument = (formData) => api.post('/documents', formData, {
  headers: { 'Content-Type': 'multipart/form-data' }
});
export const deleteDocument = (docId) => api.delete(`/documents/${docId}`);
export const getDocumentSummary = (docId) => api.get(`/documents/${docId}/summary`);
export const sendChatMessage = (question, docId = null, topK = 4) => 
  api.post('/chat', { question, doc_id: docId, top_k: topK });
export const compareDocuments = (question, docId1, docId2) => 
  api.post('/compare', { question, doc_id_1: docId1, doc_id_2: docId2 });
export const resetChatHistory = (docId = null) => 
  api.post('/reset', { doc_id: docId });

export default api;
