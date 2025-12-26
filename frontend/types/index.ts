export interface NewsItem {
  id: string;
  title: string;
  url: string;
  category: string;
  source: string;
  language: string;
  summary: string;
  translated_summary: string;
  audio_file: string;
  audio_duration: number;
  published_date: string;
  processed_at: string;
}

export interface Playlist {
  language: string;
  total_items: number;
  items: NewsItem[];
}

export interface Language {
  code: string;
  name: string;
  items: number;
}

export type LanguageCode = 'en' | 'hi' | 'bn';