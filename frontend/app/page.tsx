'use client';

import { useState, useEffect } from 'react';
import { Radio, RefreshCw, Globe } from 'lucide-react';
import AudioPlayer from '@/components/AudioPlayer';
import LanguageSelector from '@/components/LanguageSelector';
import PlaylistView from '@/components/PlaylistView';
import { newsApi } from '@/lib/api';
import type { NewsItem, LanguageCode } from '@/types';

export default function Home() {
  const [selectedLanguage, setSelectedLanguage] = useState<LanguageCode>('en');
  const [playlist, setPlaylist] = useState<NewsItem[]>([]);
  const [currentTrack, setCurrentTrack] = useState<NewsItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load playlist when language changes
  useEffect(() => {
    loadPlaylist();
  }, [selectedLanguage]);

  const loadPlaylist = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const data = await newsApi.getPlaylist(selectedLanguage, 20);
      setPlaylist(data.items);
      
      // Set first track if none selected
      if (!currentTrack && data.items.length > 0) {
        setCurrentTrack(data.items[0]);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load playlist');
      console.error('Error loading playlist:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    try {
      await newsApi.refreshPlaylist(selectedLanguage);
      await loadPlaylist();
    } catch (err) {
      console.error('Error refreshing playlist:', err);
    }
  };

  const handleTrackSelect = (track: NewsItem) => {
    setCurrentTrack(track);
  };

  const handleNext = () => {
    if (!currentTrack || playlist.length === 0) return;
    
    const currentIndex = playlist.findIndex(item => item.id === currentTrack.id);
    const nextIndex = (currentIndex + 1) % playlist.length;
    setCurrentTrack(playlist[nextIndex]);
  };

  const handlePrevious = () => {
    if (!currentTrack || playlist.length === 0) return;
    
    const currentIndex = playlist.findIndex(item => item.id === currentTrack.id);
    const previousIndex = currentIndex === 0 ? playlist.length - 1 : currentIndex - 1;
    setCurrentTrack(playlist[previousIndex]);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900">
      {/* Header */}
      <header className="bg-black/20 backdrop-blur-sm border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-500/20 rounded-lg">
                <Radio className="w-8 h-8 text-blue-400" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">
                  Multilingual News Radio
                </h1>
                <p className="text-sm text-blue-200">
                  Live news broadcasts in multiple languages
                </p>
              </div>
            </div>
            
            <button
              onClick={handleRefresh}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-blue-500/20 hover:bg-blue-500/30 
                       border border-blue-500/30 rounded-lg text-blue-200 transition-colors
                       disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Language Selector & Player */}
          <div className="lg:col-span-1 space-y-6">
            {/* Language Selector */}
            <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-6">
              <div className="flex items-center gap-2 mb-4">
                <Globe className="w-5 h-5 text-blue-400" />
                <h2 className="text-lg font-semibold text-white">Select Language</h2>
              </div>
              <LanguageSelector
                selectedLanguage={selectedLanguage}
                onLanguageChange={setSelectedLanguage}
              />
            </div>

            {/* Audio Player */}
            <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-6">
              <AudioPlayer
                currentTrack={currentTrack}
                onNext={handleNext}
                onPrevious={handlePrevious}
              />
            </div>

            {/* Stats */}
            <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-6">
              <h3 className="text-sm font-medium text-blue-200 mb-3">Playlist Stats</h3>
              <div className="space-y-2 text-sm text-gray-300">
                <div className="flex justify-between">
                  <span>Total Items:</span>
                  <span className="text-white font-medium">{playlist.length}</span>
                </div>
                <div className="flex justify-between">
                  <span>Language:</span>
                  <span className="text-white font-medium uppercase">{selectedLanguage}</span>
                </div>
                <div className="flex justify-between">
                  <span>Duration:</span>
                  <span className="text-white font-medium">
                    {Math.round(playlist.reduce((sum, item) => sum + item.audio_duration, 0) / 60)} min
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Playlist */}
          <div className="lg:col-span-2">
            <div className="bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-6">
              <h2 className="text-xl font-semibold text-white mb-4">
                Playlist {loading && '(Loading...)'}
              </h2>
              
              {error && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 mb-4">
                  <p className="text-red-200">{error}</p>
                </div>
              )}
              
              <PlaylistView
                items={playlist}
                currentTrack={currentTrack}
                onTrackSelect={handleTrackSelect}
              />
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="text-center text-sm text-blue-200/60">
          <p>AI Partner Catalyst Hackathon 2024</p>
          <p className="mt-1">Powered by Confluent, Gemini & ElevenLabs</p>
        </div>
      </footer>
    </div>
  );
}