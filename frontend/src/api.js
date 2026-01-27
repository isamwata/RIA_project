/**
 * API client for the RIA Assessment backend.
 */

const API_BASE = 'http://localhost:8000';

// ============================================================================
// RIA Assessment API
// ============================================================================

export const riaApi = {
  /**
   * Create a new RIA assessment.
   */
  async createAssessment(proposal, metadata = {}) {
    try {
      console.log('Creating assessment with:', { proposal: proposal.substring(0, 50) + '...', metadata });
      const response = await fetch(`${API_BASE}/api/ria/assessments`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ proposal, metadata }),
      });
      
      console.log('Response status:', response.status, response.statusText);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Error response:', errorText);
        let errorMessage = `Failed to create assessment (${response.status} ${response.statusText})`;
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch (e) {
          errorMessage = errorText || errorMessage;
        }
        throw new Error(errorMessage);
      }
      
      const result = await response.json();
      console.log('Assessment created successfully:', result.assessment_id);
      return result;
    } catch (error) {
      console.error('createAssessment error:', error);
      // If it's a network error, provide more helpful message
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        throw new Error(`Network error: Cannot connect to backend at ${API_BASE}. Please ensure the backend is running.`);
      }
      throw error;
    }
  },

  /**
   * Get an assessment by ID.
   */
  async getAssessment(assessmentId) {
    const response = await fetch(`${API_BASE}/api/ria/assessments/${assessmentId}`);
    if (!response.ok) {
      throw new Error('Failed to get assessment');
    }
    return response.json();
  },

  /**
   * Get assessment status.
   */
  async getAssessmentStatus(assessmentId) {
    const response = await fetch(`${API_BASE}/api/ria/assessments/${assessmentId}/status`);
    if (!response.ok) {
      throw new Error('Failed to get assessment status');
    }
    return response.json();
  },

  /**
   * Stream workflow progress.
   */
  async streamAssessment(assessmentId, onEvent) {
    const response = await fetch(
      `${API_BASE}/api/ria/assessments/${assessmentId}/stream`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}), // Empty body for POST
      }
    );

    if (!response.ok) {
      throw new Error('Failed to stream assessment');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE events are separated by a blank line (\n\n)
      const parts = buffer.split('\n\n');
      buffer = parts.pop() || '';

      for (const part of parts) {
        const lines = part.split('\n');
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const data = line.slice(6).trim();
          if (!data) continue;
          try {
            const event = JSON.parse(data);
            onEvent(event.type, event);
          } catch (e) {
            // If JSON is incomplete (chunk split), put it back into the buffer and retry on next read
            buffer = `${part}\n\n${buffer}`;
            break;
          }
        }
      }
    }
  },

  /**
   * Submit review decision.
   */
  async reviewAssessment(assessmentId, action, comments = '') {
    const response = await fetch(
      `${API_BASE}/api/ria/assessments/${assessmentId}/review`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action, comments }),
      }
    );
    if (!response.ok) {
      throw new Error('Failed to submit review');
    }
    return response.json();
  },

  /**
   * List all assessments.
   */
  async listAssessments(status = null) {
    const url = status
      ? `${API_BASE}/api/ria/assessments?status=${status}`
      : `${API_BASE}/api/ria/assessments`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error('Failed to list assessments');
    }
    return response.json();
  },

  /**
   * Get formatted report.
   */
  async getReport(assessmentId) {
    const response = await fetch(`${API_BASE}/api/ria/assessments/${assessmentId}/report`);
    if (!response.ok) {
      throw new Error('Failed to get report');
    }
    return response.json();
  },
};

// ============================================================================
// Legacy LLM Council API (kept for backward compatibility)
// ============================================================================

export const api = {
  /**
   * List all conversations.
   */
  async listConversations() {
    const response = await fetch(`${API_BASE}/api/conversations`);
    if (!response.ok) {
      throw new Error('Failed to list conversations');
    }
    return response.json();
  },

  /**
   * Create a new conversation.
   */
  async createConversation() {
    const response = await fetch(`${API_BASE}/api/conversations`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({}),
    });
    if (!response.ok) {
      throw new Error('Failed to create conversation');
    }
    return response.json();
  },

  /**
   * Get a specific conversation.
   */
  async getConversation(conversationId) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}`
    );
    if (!response.ok) {
      throw new Error('Failed to get conversation');
    }
    return response.json();
  },

  /**
   * Send a message in a conversation.
   */
  async sendMessage(conversationId, content) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      }
    );
    if (!response.ok) {
      throw new Error('Failed to send message');
    }
    return response.json();
  },

  /**
   * Send a message and receive streaming updates.
   * @param {string} conversationId - The conversation ID
   * @param {string} content - The message content
   * @param {function} onEvent - Callback function for each event: (eventType, data) => void
   * @returns {Promise<void>}
   */
  async sendMessageStream(conversationId, content, onEvent) {
    const response = await fetch(
      `${API_BASE}/api/conversations/${conversationId}/message/stream`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content }),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to send message');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value);
      const lines = chunk.split('\n');

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          try {
            const event = JSON.parse(data);
            onEvent(event.type, event);
          } catch (e) {
            console.error('Failed to parse SSE event:', e);
          }
        }
      }
    }
  },
};
