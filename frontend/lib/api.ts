import axios from 'axios';
import type { Playlist, Language, LanguageCode } from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

export const newsApi = {
  /**
   * Get playlist for a specific language
   */
  getPlaylist: async (language: LanguageCode, limit: number = 20): Promise<Playlist> => {
    const response = await api.get(`/playlist/${language}`, {
      params: { limit }
    });
    return response.data;
  },

  /**
   * Get audio file URL
   */
  getAudioUrl: (filename: string): string => {
    return `${API_BASE_URL}/audio/${filename}`;
  },

  /**
   * Refresh playlist for a language
   */
  refreshPlaylist: async (language: LanguageCode): Promise<void> => {
    await api.get(`/refresh/${language}`);
  },

  /**
   * Get available languages
   */
  getLanguages: async (): Promise<Language[]> => {
    const response = await api.get('/languages');
    return response.data.languages;
  },

  /**
   * Get health status
   */
  getHealth: async (): Promise<any> => {
    const response = await api.get('/health');
    return response.data;
  },

  /**
   * Get available categories
   */
  getCategories: async (): Promise<string[]> => {
    const response = await api.get('/categories');
    return response.data.categories;
  }
};

export default api;