'use client';

import { useState, useRef, useEffect } from 'react';
import { Play, Pause, SkipForward, SkipBack, Volume2, ExternalLink, Repeat, ChevronUp, ChevronDown } from 'lucide-react';
import type { NewsItem } from '@/types';
import { newsApi } from '@/lib/api';

interface AudioPlayerProps {
  currentTrack: NewsItem | null;
  onNext: () => void;
  onPrevious: () => void;
  onEnded?: () => void;
  autoPlay?: boolean;
  onToggleAutoPlay?: () => void;
  isPlaying: boolean;
  setIsPlaying: (playing: boolean) => void;
}

export default function AudioPlayer({ 
  currentTrack, 
  onNext, 
  onPrevious, 
  onEnded,
  autoPlay = false,
  onToggleAutoPlay,
  isPlaying,
  setIsPlaying
}: AudioPlayerProps) {
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(0.7);
  const [isMock, setIsMock] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [dragStartY, setDragStartY] = useState<number | null>(null);
  const [dragCurrentY, setDragCurrentY] = useState<number | null>(null);
  
  const audioRef = useRef<HTMLAudioElement>(null);

  useEffect(() => {
    if (currentTrack && audioRef.current) {
      const audioUrl = newsApi.getAudioUrl(currentTrack.audio_file);
      audioRef.current.src = audioUrl;
      audioRef.current.load();
      
      // Check if it's a mock file by examining Content-Type header
      // Only mock responses return JSON, real audio returns audio/mpeg
      fetch(audioUrl, { method: 'HEAD' })
        .then(res => {
          const contentType = res.headers.get('content-type');
          setIsMock(contentType?.includes('application/json') || false);
        })
        .catch(() => {
          // If HEAD fails, assume it's real audio
          setIsMock(false);
        });
      
      // Auto-play when track changes if isPlaying is true
      if (isPlaying) {
        // Small delay to ensure audio is loaded
        const playTimer = setTimeout(() => {
          audioRef.current?.play().catch(err => console.log('Play error:', err));
        }, 100);
        return () => clearTimeout(playTimer);
      }
    }
  }, [currentTrack, isPlaying]);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = volume;
    }
  }, [volume]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return; // Don't interfere with input fields
      }
      
      switch(e.key) {
        case ' ':
          e.preventDefault();
          togglePlay();
          break;
        case 'ArrowRight':
          e.preventDefault();
          onNext();
          break;
        case 'ArrowLeft':
          e.preventDefault();
          onPrevious();
          break;
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isPlaying, currentTrack]);

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
    if (onEnded) {
      onEnded();
    }
  };

  const formatTime = (seconds: number) => {
    if (isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Touch gesture handlers for mobile drag
  const handleTouchStart = (e: React.TouchEvent) => {
    setDragStartY(e.touches[0].clientY);
    setDragCurrentY(e.touches[0].clientY);
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (dragStartY === null) return;
    setDragCurrentY(e.touches[0].clientY);
  };

  const handleTouchEnd = () => {
    if (dragStartY === null || dragCurrentY === null) return;
    
    const dragDistance = dragCurrentY - dragStartY;
    const threshold = 50; // pixels to trigger expand/collapse
    
    if (!isExpanded && dragDistance < -threshold) {
      // Swipe up to expand
      setIsExpanded(true);
    } else if (isExpanded && dragDistance > threshold) {
      // Swipe down to collapse
      setIsExpanded(false);
    }
    
    setDragStartY(null);
    setDragCurrentY(null);
  };

  if (!currentTrack) {
    return null; // Don't render player if no track
  }

  return (
    <>
      {/* Audio Element */}
      <audio
        ref={audioRef}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={handleEnded}
        preload="metadata"
        aria-label="Audio player"
      />

      {/* Sticky Bottom Player - Spotify Style */}
      <div 
        className="fixed bottom-0 left-0 right-0 bg-black/95 backdrop-blur-md border-t border-white/10 z-50"
        role="region"
        aria-label="Audio player controls"
      >
        {/* Progress Bar - Always visible */}
        <div className="w-full">
          <input
            type="range"
            min="0"
            max={duration || 0}
            value={currentTime}
            onChange={handleSeek}
            aria-label={`Seek slider, current time ${formatTime(currentTime)} of ${formatTime(duration)}`}
            className="w-full h-1 appearance-none cursor-pointer"
            style={{
              background: `linear-gradient(to right, rgb(59, 130, 246) 0%, rgb(59, 130, 246) ${(currentTime / duration) * 100}%, rgb(75, 85, 99) ${(currentTime / duration) * 100}%, rgb(75, 85, 99) 100%)`
            }}
          />
        </div>

        {/* Mobile View - Collapsed */}
        <div 
          className={`lg:hidden ${isExpanded ? 'hidden' : 'block'}`}
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
        >
          <div className="px-4 py-3 flex items-center gap-3">
            {/* Play/Pause */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                togglePlay();
              }}
              className="p-2 bg-blue-500 hover:bg-blue-600 rounded-full transition-colors flex-shrink-0"
              aria-label={isPlaying ? 'Pause' : 'Play'}
              title={isPlaying ? 'Pause (Space)' : 'Play (Space)'}
            >
              {isPlaying ? (
                <Pause className="w-5 h-5 text-white" aria-hidden="true" />
              ) : (
                <Play className="w-5 h-5 text-white" aria-hidden="true" />
              )}
            </button>

            {/* Track Info - Tappable to expand */}
            <button
              onClick={() => setIsExpanded(true)}
              className="flex-1 min-w-0 text-left"
              aria-label="Tap to expand player"
            >
              <h4 className="text-white text-sm font-medium truncate">
                {currentTrack.translated_title || currentTrack.title}
              </h4>
              <p className="text-gray-400 text-xs truncate">{currentTrack.source}</p>
            </button>

            {/* Expand Button */}
            <button
              onClick={() => setIsExpanded(true)}
              className="p-2 hover:bg-white/10 rounded-lg transition-colors flex-shrink-0"
              aria-label="Expand player"
            >
              <ChevronUp className="w-5 h-5 text-gray-400" aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* Mobile View - Expanded */}
        <div 
          className={`lg:hidden ${isExpanded ? 'block' : 'hidden'}`}
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
        >
          <div className="px-4 py-4 space-y-4">
            {/* Header */}
            <div className="flex items-center justify-between">
              <h3 className="text-white font-medium">Now Playing</h3>
              <button
                onClick={() => setIsExpanded(false)}
                className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                aria-label="Collapse player"
              >
                <ChevronDown className="w-5 h-5 text-gray-400" aria-hidden="true" />
              </button>
            </div>

            {/* Track Info - Tappable to collapse */}
            <button
              onClick={() => setIsExpanded(false)}
              className="w-full space-y-2 text-left"
              aria-label="Tap to collapse player"
            >
              <h4 className="text-white font-medium">
                {currentTrack.translated_title || currentTrack.title}
              </h4>
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-sm px-2 py-1 bg-blue-500/20 text-blue-300 rounded">
                  {currentTrack.category}
                </span>
                <span className="text-sm text-gray-400">{currentTrack.source}</span>
              </div>
            </button>

            {/* Time Display */}
            <div className="flex justify-between text-xs text-gray-400">
              <span>{formatTime(currentTime)}</span>
              <span>{formatTime(duration)}</span>
            </div>

            {/* Controls */}
            <div className="flex items-center justify-center gap-6">
              <button
                onClick={onPrevious}
                className="p-2 hover:bg-white/10 rounded-full transition-colors"
                aria-label="Previous track (Left Arrow)"
                title="Previous (← Left Arrow)"
              >
                <SkipBack className="w-6 h-6 text-white" aria-hidden="true" />
              </button>
              
              <button
                onClick={togglePlay}
                className="p-4 bg-blue-500 hover:bg-blue-600 rounded-full transition-colors"
                aria-label={isPlaying ? 'Pause' : 'Play'}
                title={isPlaying ? 'Pause (Space)' : 'Play (Space)'}
              >
                {isPlaying ? (
                  <Pause className="w-7 h-7 text-white" aria-hidden="true" />
                ) : (
                  <Play className="w-7 h-7 text-white" aria-hidden="true" />
                )}
              </button>
              
              <button
                onClick={onNext}
                className="p-2 hover:bg-white/10 rounded-full transition-colors"
                aria-label="Next track (Right Arrow)"
                title="Next (→ Right Arrow)"
              >
                <SkipForward className="w-6 h-6 text-white" aria-hidden="true" />
              </button>
            </div>

            {/* Auto-play Toggle */}
            <div className="space-y-3">
              {onToggleAutoPlay && (
                <button
                  onClick={onToggleAutoPlay}
                  className={`w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                    autoPlay 
                      ? 'bg-blue-500/20 border border-blue-500/50 text-blue-300' 
                      : 'bg-white/5 border border-white/10 text-gray-400 hover:bg-white/10'
                  }`}
                  aria-label={autoPlay ? 'Auto-play enabled' : 'Auto-play disabled'}
                  aria-pressed={autoPlay}
                >
                  <Repeat className="w-4 h-4" aria-hidden="true" />
                  <span className="text-sm">Auto-play {autoPlay ? 'On' : 'Off'}</span>
                </button>
              )}
            </div>

            {/* Link to Article */}
            <a
              href={currentTrack.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 w-full px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg transition-colors text-gray-300 text-sm"
            >
              <ExternalLink className="w-4 h-4" aria-hidden="true" />
              <span>Read Full Article</span>
            </a>

            {isMock && (
              <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3">
                <p className="text-xs text-yellow-200">
                  ⚠️ Development Mode: Mock audio (no actual audio file)
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Desktop View - Full Width Bar */}
        <div className="hidden lg:block">
          <div className="px-6 py-3">
            <div className="flex items-center gap-4">
              {/* Left: Track Info */}
              <div className="flex items-center gap-3 min-w-0 w-1/4">
                <div className="flex-1 min-w-0">
                  <h4 className="text-white text-sm font-medium truncate">
                    {currentTrack.translated_title || currentTrack.title}
                  </h4>
                  <div className="flex items-center gap-2 mt-0.5">
                    <p className="text-gray-400 text-xs truncate">{currentTrack.source}</p>
                    <span className="text-xs px-1.5 py-0.5 bg-blue-500/20 text-blue-300 rounded flex-shrink-0">
                      {currentTrack.category}
                    </span>
                  </div>
                </div>
                <a
                  href={currentTrack.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex-shrink-0 p-1.5 hover:bg-white/10 rounded-lg transition-colors"
                  aria-label="Read full article"
                  title="Read Full Article"
                >
                  <ExternalLink className="w-4 h-4 text-gray-400" aria-hidden="true" />
                </a>
              </div>

              {/* Center: Controls */}
              <div className="flex-1 flex flex-col items-center gap-2 max-w-2xl">
                <div className="flex items-center justify-center gap-4">
                  {onToggleAutoPlay && (
                    <button
                      onClick={onToggleAutoPlay}
                      className={`p-1.5 rounded-lg transition-colors ${
                        autoPlay 
                          ? 'text-blue-400 hover:bg-white/10' 
                          : 'text-gray-400 hover:bg-white/10 hover:text-white'
                      }`}
                      aria-label={autoPlay ? 'Auto-play enabled' : 'Auto-play disabled'}
                      aria-pressed={autoPlay}
                      title={autoPlay ? 'Auto-play: On' : 'Auto-play: Off'}
                    >
                      <Repeat className="w-4 h-4" aria-hidden="true" />
                    </button>
                  )}
                  
                  <button
                    onClick={onPrevious}
                    className="p-1.5 hover:bg-white/10 rounded-full transition-colors"
                    aria-label="Previous track (Left Arrow)"
                    title="Previous (← Left Arrow)"
                  >
                    <SkipBack className="w-5 h-5 text-white" aria-hidden="true" />
                  </button>
                  
                  <button
                    onClick={togglePlay}
                    className="p-3 bg-blue-500 hover:bg-blue-600 rounded-full transition-colors"
                    aria-label={isPlaying ? 'Pause' : 'Play'}
                    title={isPlaying ? 'Pause (Space)' : 'Play (Space)'}
                  >
                    {isPlaying ? (
                      <Pause className="w-5 h-5 text-white" aria-hidden="true" />
                    ) : (
                      <Play className="w-5 h-5 text-white" aria-hidden="true" />
                    )}
                  </button>
                  
                  <button
                    onClick={onNext}
                    className="p-1.5 hover:bg-white/10 rounded-full transition-colors"
                    aria-label="Next track (Right Arrow)"
                    title="Next (→ Right Arrow)"
                  >
                    <SkipForward className="w-5 h-5 text-white" aria-hidden="true" />
                  </button>
                </div>

                {/* Time Display */}
                <div className="flex items-center gap-2 w-full">
                  <span className="text-xs text-gray-400 w-10 text-right">{formatTime(currentTime)}</span>
                  <div className="flex-1" />
                  <span className="text-xs text-gray-400 w-10">{formatTime(duration)}</span>
                </div>
              </div>

              {/* Right: Volume */}
              <div className="w-1/4 flex items-center justify-end gap-3">
                {isMock && (
                  <span className="text-xs text-yellow-400 mr-2" title="Development Mode: Mock audio">
                    ⚠️ Mock
                  </span>
                )}
                <Volume2 className="w-4 h-4 text-gray-400 flex-shrink-0" aria-hidden="true" />
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={volume}
                  onChange={(e) => setVolume(parseFloat(e.target.value))}
                  aria-label={`Volume ${Math.round(volume * 100)}%`}
                  className="w-24 h-1 appearance-none cursor-pointer"
                  style={{
                    background: `linear-gradient(to right, rgb(59, 130, 246) 0%, rgb(59, 130, 246) ${volume * 100}%, rgb(75, 85, 99) ${volume * 100}%, rgb(75, 85, 99) 100%)`
                  }}
                />
                <span className="text-xs text-gray-400 w-8" aria-live="polite">{Math.round(volume * 100)}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}