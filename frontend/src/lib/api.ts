const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ApiError {
  detail: string;
}

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem('auth_token', token);
    } else {
      localStorage.removeItem('auth_token');
    }
  }

  getToken(): string | null {
    if (this.token) return this.token;
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('auth_token');
    }
    return this.token;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = this.getToken();
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
      ...options.headers,
    };

    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        detail: 'An unexpected error occurred',
      }));
      
      if (response.status === 401) {
        this.setToken(null);
        if (typeof window !== 'undefined') {
          window.location.href = '/login?error=session_expired';
        }
      }
      
      throw new Error(error.detail);
    }

    return response.json();
  }

  // Auth endpoints
  async getLoginUrl(): Promise<{ auth_url: string }> {
    return this.request('/auth/login');
  }

  async getCurrentUser(): Promise<{
    email: string;
    name: string;
    picture?: string;
  }> {
    return this.request('/auth/me');
  }

  async logout(): Promise<{ message: string }> {
    const result = await this.request<{ message: string }>('/auth/logout', {
      method: 'POST',
    });
    this.setToken(null);
    return result;
  }

  // Email endpoints
  async getEmails(count: number = 5, query?: string): Promise<Email[]> {
    const params = new URLSearchParams({ count: count.toString() });
    if (query) params.append('query', query);
    return this.request(`/emails?${params}`);
  }

  async getEmail(emailId: string): Promise<Email> {
    return this.request(`/emails/${emailId}`);
  }

  async sendEmail(data: {
    to: string;
    subject: string;
    body: string;
    thread_id?: string;
    message_id?: string;
  }): Promise<{ success: boolean; message_id: string }> {
    return this.request('/emails/send', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteEmail(emailId: string): Promise<{ success: boolean; message: string }> {
    return this.request(`/emails/${emailId}`, {
      method: 'DELETE',
    });
  }

  async generateReply(
    emailId: string,
    customInstruction?: string
  ): Promise<{ reply: string; email: Email }> {
    const params = new URLSearchParams();
    if (customInstruction) params.append('custom_instruction', customInstruction);
    return this.request(`/emails/${emailId}/generate-reply?${params}`, {
      method: 'POST',
    });
  }

  // Chat endpoints
  async sendChatMessage(
    message: string,
    conversationHistory: ChatMessage[] = []
  ): Promise<ChatResponse> {
    return this.request('/chat', {
      method: 'POST',
      body: JSON.stringify({
        message,
        conversation_history: conversationHistory,
      }),
    });
  }

  async getDailyDigest(): Promise<{
    digest: string;
    categories: Record<string, number[]>;
    email_count: number;
  }> {
    return this.request('/chat/digest', { method: 'POST' });
  }

  async categorizeEmails(): Promise<{
    emails: Email[];
    categories: Record<string, number[]>;
  }> {
    return this.request('/chat/categorize', { method: 'POST' });
  }
}

// Types
export interface Email {
  id: string;
  thread_id: string;
  sender: string;
  sender_email: string;
  subject: string;
  snippet: string;
  body: string;
  date: string;
  summary?: string;
  suggested_reply?: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
  metadata?: {
    emails?: Email[];
    action?: string;
  };
}

export interface ChatResponse {
  message: string;
  action?: string;
  data?: {
    emails?: Email[];
    email?: Email;
    suggested_reply?: string;
    deleted?: boolean;
    sent?: boolean;
  };
}

export const api = new ApiClient();
