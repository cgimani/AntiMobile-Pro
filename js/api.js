/**
 * Antigravity PWA - REST API Client
 */

class ApiService {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const defaultHeaders = {
      'Content-Type': 'application/json',
      'Accept': 'application/json'
    };

    const config = {
      ...options,
      headers: {
        ...defaultHeaders,
        ...(options.headers || {})
      }
    };

    try {
      const response = await fetch(url, config);
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error ${response.status}`);
      }
      return await response.json();
    } catch (err) {
      console.error(`API Error [${endpoint}]:`, err);
      throw err;
    }
  }

  // Get system & daemon status
  async getStatus() {
    return this.request('/api/status');
  }

  // Get available AI models
  async getModels() {
    return this.request('/api/models');
  }

  // List files in workspace
  async getFiles(dirPath = '') {
    const query = dirPath ? `?path=${encodeURIComponent(dirPath)}` : '';
    return this.request(`/api/files${query}`);
  }

  // Read file content
  async getFileContent(filePath) {
    const query = `?path=${encodeURIComponent(filePath)}`;
    return this.request(`/api/file${query}`);
  }

  // Save/Update file
  async saveFile(filePath, content) {
    return this.request('/api/file', {
      method: 'POST',
      body: JSON.stringify({ path: filePath, content })
    });
  }

  // Execute terminal shell command via REST fallback
  async execCommand(command) {
    return this.request('/api/exec', {
      method: 'POST',
      body: JSON.stringify({ cmd: command })
    });
  }

  // Run agy prompt directly
  async runPrompt(prompt, model = '') {
    return this.request('/api/agy/prompt', {
      method: 'POST',
      body: JSON.stringify({ prompt, model })
    });
  }
}

export const api = new ApiService();
