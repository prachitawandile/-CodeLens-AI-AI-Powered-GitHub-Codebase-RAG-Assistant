/**
 * API client service for CodeLens AI backend endpoints.
 */
const API_BASE = window.location.origin;

const ApiService = {
  /**
   * Health check
   */
  async checkHealth() {
    const res = await fetch(`${API_BASE}/api/health`);
    if (!res.ok) throw new Error("Backend server is not reachable.");
    return await res.json();
  },

  /**
   * Trigger repository analysis
   */
  async analyzeRepository(githubUrl, forceReindex = false) {
    const res = await fetch(`${API_BASE}/api/repository/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ github_url: githubUrl, force_reindex: forceReindex }),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to initiate repository analysis.");
    }
    return data;
  },

  /**
   * Poll repository indexing status and progress
   */
  async getStatus() {
    const res = await fetch(`${API_BASE}/api/repository/status`);
    if (!res.ok) throw new Error("Failed to fetch repository status.");
    return await res.json();
  },

  /**
   * Ask natural-language question
   */
  async askQuestion(question, topK = 5) {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, top_k: topK }),
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to process your question.");
    }
    return data;
  },

  /**
   * Get file tree nodes
   */
  async getFileTree() {
    const res = await fetch(`${API_BASE}/api/repository/files`);
    if (!res.ok) throw new Error("Failed to fetch repository files.");
    return await res.json();
  },

  /**
   * Get file content for file viewer
   */
  async getFileContent(filePath) {
    const url = `${API_BASE}/api/repository/file?path=${encodeURIComponent(filePath)}`;
    const res = await fetch(url);
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || `Failed to read file ${filePath}`);
    }
    return data;
  },

  /**
   * Clear repository & ChromaDB
   */
  async clearRepository() {
    const res = await fetch(`${API_BASE}/api/repository/clear`, {
      method: "POST",
    });
    return await res.json();
  },

  /**
   * Get suggested questions
   */
  async getSuggestedQuestions() {
    const res = await fetch(`${API_BASE}/api/chat/suggested-questions`);
    if (!res.ok) return [];
    return await res.json();
  },
};
