'use client';

import type { Language, LanguageCode } from '@/types';

interface LanguageSelectorProps {
  selectedLanguage: LanguageCode;
  languages: Language[]; // Now accepts dynamic list
  onLanguageChange: (language: LanguageCode) => void;
}

export default function LanguageSelector({ 
  selectedLanguage, 
  languages, 
  onLanguageChange 
}: LanguageSelectorProps) {
  return (
    <div className="space-y-2">
      {languages.map((lang) => (
        <button
          key={lang.code}
          onClick={() => onLanguageChange(lang.code)}
          className={`
            w-full flex items-center gap-3 p-3 rounded-lg transition-all
            ${selectedLanguage === lang.code
              ? 'bg-blue-500/30 border-2 border-blue-500 text-white'
              : 'bg-white/5 border-2 border-transparent text-gray-300 hover:bg-white/10'
            }
          `}
        >
          <span className="text-2xl">{lang.flag || '🌐'}</span>
          <div className="flex-1 text-left">
            <div className="font-medium">{lang.name}</div>
            <div className="text-xs opacity-70">{lang.code.toUpperCase()}</div>
          </div>
          {selectedLanguage === lang.code && (
            <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" />
          )}
          
          {/* Item count badge */}
          <div className="px-2 py-1 text-xs rounded-full bg-white/10 text-gray-400">
            {lang.items}
          </div>
        </button>
      ))}
      
      {languages.length === 0 && (
        <div className="text-center p-4 text-gray-400 text-sm">
          Loading languages...
        </div>
      )}
    </div>
  );
}