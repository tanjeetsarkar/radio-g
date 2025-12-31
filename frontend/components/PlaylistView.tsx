'use client';

import { Clock, Play, ExternalLink } from 'lucide-react';
import type { NewsItem } from '@/types';

interface PlaylistViewProps {
  items: NewsItem[];
  currentTrack: NewsItem | null;
  onTrackSelect: (track: NewsItem) => void;
}

export default function PlaylistView({ items, currentTrack, onTrackSelect }: PlaylistViewProps) {
  if (items.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-400">No news items available</p>
        <p className="text-sm text-gray-500 mt-2">Try refreshing the playlist</p>
      </div>
    );
  }

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="space-y-2 max-h-[600px] overflow-y-auto pr-2 custom-scrollbar">
      {items.map((item, index) => {
        const isCurrentTrack = currentTrack?.id === item.id;
        
        return (
          <button
            key={item.id}
            onClick={() => onTrackSelect(item)}
            className={`
              w-full text-left p-4 rounded-lg transition-all group
              ${isCurrentTrack
                ? 'bg-blue-500/20 border border-blue-500/50'
                : 'bg-white/5 border border-white/10 hover:bg-white/10 hover:border-white/20'
              }
            `}
          >
            <div className="flex gap-4">
              {/* Index/Play Icon */}
              <div className="flex-shrink-0 w-8 flex items-center justify-center">
                {isCurrentTrack ? (
                  <div className="flex flex-col gap-0.5">
                    <div className="w-0.5 h-3 bg-blue-400 animate-pulse" />
                    <div className="w-0.5 h-3 bg-blue-400 animate-pulse" style={{ animationDelay: '0.2s' }} />
                    <div className="w-0.5 h-3 bg-blue-400 animate-pulse" style={{ animationDelay: '0.4s' }} />
                  </div>
                ) : (
                  <span className="text-gray-500 group-hover:hidden">{index + 1}</span>
                )}
                <Play className={`w-4 h-4 text-blue-400 ${isCurrentTrack ? 'hidden' : 'hidden group-hover:block'}`} />
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <h4 className={`font-medium truncate ${isCurrentTrack ? 'text-blue-300' : 'text-white'}`}>
                      {item.translated_title || item.title}
                    </h4>
                    <p className="text-sm text-gray-400 mt-1 line-clamp-2">
                      {item.translated_summary}
                    </p>
                  </div>
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={(e) => e.stopPropagation()}
                    className="flex-shrink-0 p-1.5 hover:bg-white/10 rounded-lg transition-colors"
                    aria-label="Read full article"
                    title="Read Full Article"
                  >
                    <ExternalLink className="w-4 h-4 text-gray-400 hover:text-blue-400" />
                  </a>
                </div>

                <div className="flex flex-wrap items-center gap-2 text-xs">
                  <span className="px-2 py-1 bg-white/10 text-gray-300 rounded">
                    {item.source}
                  </span>
                  <span className="px-2 py-1 bg-white/10 text-gray-300 rounded">
                    {item.category}
                  </span>
                  <div className="flex items-center gap-1 text-gray-400">
                    <Clock className="w-3 h-3" />
                    <span>{formatDuration(item.audio_duration)}</span>
                  </div>
                  <span className="text-gray-500">
                    {formatDate(item.published_date)}
                  </span>
                </div>
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}