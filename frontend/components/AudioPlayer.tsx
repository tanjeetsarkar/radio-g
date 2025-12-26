'use client';

import { useState, useRef, useEffect } from 'react';
import { Play, Pause, SkipForward, SkipBack, Volume2, ExternalLink } from 'lucide-react';
import type { NewsItem } from '@/types';
import { newsApi } from '@/lib/api';

interface AudioPlayerProps {
  currentTrack: NewsItem | null;
  onNext: () => void;
  onPrevious: () => void;
}

export default function AudioPlayer({ currentTrack, onNext, onPrevious }: AudioPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(0.7);
  const [isMock, setIsMock] = useState(false);
  
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    if (currentTrack && audioRef.current) {
      const audioUrl = newsApi.getAudioUrl(currentTrack.audio_file);
      audioRef.current.src = audioUrl;
      audioRef.current.load();
      
      // Check if it's a mock file
      fetch(audioUrl)
        .then(res => res.json())
        .then(data => {
          if (data.message && data.message.includes('Mock')) {
            setIsMock(true);
          } else {
            setIsMock(false);
          }
        })
        .catch(() => {
          setIsMock(false);
        });
      
      if (isPlaying) {
        audioRef.current.play().catch(err => console.log('Play error:', err));
      }
    }
  }, [currentTrack]);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = volume;
    }
  }, [volume]);

  const togglePlay = () => {
    if (!audioRef.current || !currentTrack) return;

    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play().catch(err => console.log('Play error:', err));
    }
    setIsPlaying(!isPlaying);
  };

  const handleTimeUpdate = () => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration);
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value);
    if (audioRef.current) {
      audioRef.current.currentTime = time;
      setCurrentTime(time);
    }
  };

  const handleEnded = () => {
    setIsPlaying(false);
    onNext();
  };

  const formatTime = (seconds: number) => {
    if (isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (!currentTrack) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-400">No track selected</p>
        <p className="text-sm text-gray-500 mt-2">Select a news item from the playlist</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Now Playing Info */}
      <div className="space-y-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <h3 className="text-white font-medium truncate">
              {currentTrack.title}
            </h3>
            <p className="text-sm text-gray-400 mt-1">{currentTrack.source}</p>
          </div>
          <a
            href={currentTrack.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-shrink-0 p-2 hover:bg-white/10 rounded-lg transition-colors"
            title="Read full article"
          >
            <ExternalLink className="w-4 h-4 text-gray-400" />
          </a>
        </div>
        
        <div className="flex items-center gap-2">
          <span className="text-xs px-2 py-1 bg-blue-500/20 text-blue-300 rounded">
            {currentTrack.category}
          </span>
          <span className="text-xs text-gray-500">
            {formatTime(currentTrack.audio_duration)}
          </span>
        </div>
      </div>

      {/* Mock Warning */}
      {isMock && (
        <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3">
          <p className="text-xs text-yellow-200">
            ⚠️ Development Mode: Mock audio (no actual audio file)
          </p>
        </div>
      )}

      {/* Audio Element */}
      <audio
        ref={audioRef}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={handleEnded}
        preload="metadata"
      />

      {/* Progress Bar */}
      <div className="space-y-2">
        <input
          type="range"
          min="0"
          max={duration || 0}
          value={currentTime}
          onChange={handleSeek}
          className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer 
                   accent-blue-500"
        />
        <div className="flex justify-between text-xs text-gray-400">
          <span>{formatTime(currentTime)}</span>
          <span>{formatTime(duration)}</span>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-center gap-4">
        <button
          onClick={onPrevious}
          className="p-2 hover:bg-white/10 rounded-full transition-colors"
          title="Previous"
        >
          <SkipBack className="w-5 h-5 text-white" />
        </button>
        
        <button
          onClick={togglePlay}
          className="p-4 bg-blue-500 hover:bg-blue-600 rounded-full transition-colors"
          title={isPlaying ? 'Pause' : 'Play'}
        >
          {isPlaying ? (
            <Pause className="w-6 h-6 text-white" />
          ) : (
            <Play className="w-6 h-6 text-white" />
          )}
        </button>
        
        <button
          onClick={onNext}
          className="p-2 hover:bg-white/10 rounded-full transition-colors"
          title="Next"
        >
          <SkipForward className="w-5 h-5 text-white" />
        </button>
      </div>

      {/* Volume Control */}
      <div className="flex items-center gap-3">
        <Volume2 className="w-4 h-4 text-gray-400" />
        <input
          type="range"
          min="0"
          max="1"
          step="0.01"
          value={volume}
          onChange={(e) => setVolume(parseFloat(e.target.value))}
          className="flex-1 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
        />
        <span className="text-xs text-gray-400 w-8">{Math.round(volume * 100)}%</span>
      </div>

      {/* Summary */}
      <div className="pt-4 border-t border-white/10">
        <p className="text-sm text-gray-300 leading-relaxed">
          {currentTrack.translated_summary}
        </p>
      </div>
    </div>
  );
}