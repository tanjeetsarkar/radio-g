# 📡 API Documentation

> Complete REST API reference for Multilingual News Radio

**Base URL**: `http://localhost:8000` (development) | `https://api.yourdomain.com` (production)  
**Version**: 2.0.0  
**Last Updated**: December 28, 2024

---

## 📋 Table of Contents

1. [Overview](#-overview)
2. [Authentication](#-authentication)
3. [Core Endpoints](#-core-endpoints)
4. [Response Formats](#-response-formats)
5. [Error Handling](#-error-handling)
6. [Rate Limiting](#-rate-limiting)
7. [Examples](#-examples)
8. [SDKs & Libraries](#-sdks--libraries)

---

## 🎯 Overview

### API Architecture

```
┌─────────────┐
│   Client    │
│  (Browser)  │
└──────┬──────┘
       │ HTTPS
       ▼
┌─────────────────────┐
│   Load Balancer     │
│   (Cloud Run)       │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│   FastAPI Backend   │
│  (Multiple Pods)    │
│                     │
│  ┌───────────────┐  │
│  │ Fan-Out       │  │
│  │ Kafka Consumer│  │
│  └───────────────┘  │
│                     │
│  ┌───────────────┐  │
│  │ In-Memory     │  │
│  │ Cache         │  │
│  └───────────────┘  │
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│  Kafka Topics       │
│  - news-english     │
│  - news-hindi       │
│  - news-bengali     │
│  - news-*           │
└─────────────────────┘
```

### Key Features

- **RESTful Design**: Standard HTTP methods and status codes
- **JSON Responses**: All responses in JSON format
- **Dynamic Languages**: Language configuration via Redis
- **Health Checks**: K8s-compatible health endpoints
- **Real-time Updates**: Kafka-powered streaming
- **CORS Enabled**: Cross-origin requests supported

---

## 🔐 Authentication

### Current Status

**Public API** - No authentication required (v2.0)

All endpoints are publicly accessible for the MVP release.

### Future Authentication (v2.1+)

Planned authentication methods:

#### API Key Authentication
```bash
curl -H "X-API-Key: your_api_key_here" \
  https://api.yourdomain.com/playlist/en
```

#### JWT Bearer Token
```bash
curl -H "Authorization: Bearer your_jwt_token" \
  https://api.yourdomain.com/playlist/en
```

---

## 🌐 Core Endpoints

### Root Endpoint

#### `GET /`

Get API information and available endpoints.

**Request:**
```bash
curl http://localhost:8000/
```

**Response:**
```json
{
  "name": "Multilingual News Radio API",
  "version": "2.0.0",
  "environment": "development",
  "languages": ["en", "hi", "bn"],
  "endpoints": {
    "health": "/health",
    "playlist": "/playlist/{language}",
    "audio": "/audio/{filename}",
    "languages": "/languages"
  }
}
```

---

### Health Endpoints

#### `GET /health`

Comprehensive health check with all system components.

**Request:**
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-12-28T10:30:00.000Z",
  "version": "2.0.0",
  "environment": "production"
}
```

**Status Values:**
- `healthy` - All systems operational
- `degraded` - Some services experiencing issues
- `unhealthy` - Critical services down

---

#### `GET /ready`

Readiness probe for Kubernetes/Cloud Run.

**Request:**
```bash
curl http://localhost:8000/ready
```

**Success Response (200):**
```json
{
  "status": "ready"
}
```

**Not Ready Response (503):**
```json
{
  "detail": "Service not ready"
}
```

**Use Case:** Load balancer health checks

---

#### `GET /live`

Liveness probe for Kubernetes/Cloud Run.

**Request:**
```bash
curl http://localhost:8000/live
```

**Success Response (200):**
```json
{
  "status": "alive"
}
```

**Not Alive Response (503):**
```json
{
  "detail": "Service not alive"
}
```

**Use Case:** Container restart decisions

---

### Language Endpoints

#### `GET /languages`

Get all available languages with metadata and item counts.

**Request:**
```bash
curl http://localhost:8000/languages
```

**Response:**
```json
{
  "languages": [
    {
      "code": "en",
      "name": "English",
      "flag": "🇬🇧",
      "items": 47
    },
    {
      "code": "hi",
      "name": "Hindi",
      "flag": "🇮🇳",
      "items": 45
    },
    {
      "code": "bn",
      "name": "Bengali",
      "flag": "🇧🇩",
      "items": 43
    }
  ]
}
```

**Response Fields:**
- `code` (string): ISO 639-1 language code
- `name` (string): Language display name
- `flag` (string): Flag emoji or icon
- `items` (integer): Number of available news items

**Notes:**
- Languages are dynamically loaded from Redis
- Only enabled languages are returned
- Item counts are real-time from cache

---

### Playlist Endpoints

#### `GET /playlist/{language}`

Get news playlist for a specific language.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `language` | path | Yes | - | Language code (en, hi, bn, etc.) |
| `limit` | query | No | 20 | Number of items to return (1-50) |
| `category` | query | No | - | Filter by category |

**Request Examples:**

```bash
# Get 20 English articles
curl http://localhost:8000/playlist/en

# Get 10 Hindi articles
curl http://localhost:8000/playlist/hi?limit=10

# Get technology articles in Bengali
curl http://localhost:8000/playlist/bn?category=technology

# Get 5 business articles in English
curl http://localhost:8000/playlist/en?limit=5&category=business
```

**Success Response (200):**
```json
{
  "language": "en",
  "total_items": 20,
  "items": [
    {
      "id": "abc123def456",
      "title": "Major Tech Company Announces AI Breakthrough",
      "url": "https://techcrunch.com/2024/12/28/ai-breakthrough",
      "category": "technology",
      "source": "TechCrunch",
      "language": "en",
      "summary": "Company reveals new AI model with unprecedented capabilities...",
      "translated_summary": "Company reveals new AI model with unprecedented capabilities...",
      "audio_file": "news_abc123def456_en.mp3",
      "audio_duration": 45.5,
      "published_date": "2024-12-28T09:00:00Z",
      "processed_at": "2024-12-28T09:15:00Z"
    }
  ]
}
```

**Error Responses:**

```json
// 404 - Language not found
{
  "detail": "Language 'es' not configured or not found"
}

// 422 - Invalid parameters
{
  "detail": [
    {
      "loc": ["query", "limit"],
      "msg": "ensure this value is less than or equal to 50",
      "type": "value_error.number.not_le"
    }
  ]
}
```

**Categories Available:**
- `general` - General news
- `technology` - Tech news
- `business` - Business news
- `sports` - Sports news

---

#### `GET /refresh/{language}`

Manually trigger playlist refresh for a language.

**Request:**
```bash
curl http://localhost:8000/refresh/en
```

**Response:**
```json
{
  "message": "Refreshed cache (scanned 50 messages)",
  "items_in_cache": 48
}
```

**Use Case:** Force cache update after adding new content

---

### Audio Endpoints

#### `GET /audio/{filename}`

Stream audio file for a news item.

**Request:**
```bash
curl http://localhost:8000/audio/news_abc123_en.mp3
```

**Success Response:**
- **Status:** 200 OK
- **Content-Type:** `audio/mpeg`
- **Body:** Audio file binary data

**Example with Browser:**
```html
<audio controls>
  <source src="http://localhost:8000/audio/news_abc123_en.mp3" type="audio/mpeg">
</audio>
```

**Example with JavaScript:**
```javascript
const audio = new Audio('http://localhost:8000/audio/news_abc123_en.mp3');
audio.play();
```

**Error Response (404):**
```json
{
  "detail": "Audio file not found"
}
```

**Mock Development Response:**
```json
{
  "message": "Mock audio file",
  "filename": "news_abc123_en.mp3",
  "metadata": {
    "language": "en",
    "estimated_duration_seconds": 45.5
  }
}
```

---

## 📊 Response Formats

### NewsItem Object

Complete structure of a news item:

```typescript
interface NewsItem {
  id: string;                    // Unique identifier (MD5 hash)
  title: string;                 // Original article title
  url: string;                   // Source article URL
  category: string;              // Article category
  source: string;                // News source name
  language: string;              // Language code
  summary: string;               // English summary
  translated_summary: string;    // Translated summary
  audio_file: string;            // Audio filename
  audio_duration: number;        // Duration in seconds
  published_date: string;        // ISO 8601 timestamp
  processed_at: string;          // ISO 8601 timestamp
}
```

### Playlist Object

```typescript
interface Playlist {
  language: string;              // Language code
  total_items: number;           // Number of items in response
  items: NewsItem[];             // Array of news items
}
```

### Language Object

```typescript
interface Language {
  code: string;                  // Language code (ISO 639-1)
  name: string;                  // Display name
  flag: string;                  // Flag emoji
  items: number;                 // Available items count
}
```

### Health Object

```typescript
interface Health {
  status: "healthy" | "degraded" | "unhealthy";
  timestamp: string;             // ISO 8601 timestamp
  version: string;               // API version
  environment: string;           // Environment name
}
```

---

## ⚠️ Error Handling

### Standard Error Response

```json
{
  "detail": "Error message describing what went wrong"
}
```

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Successful request |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request parameters |
| 404 | Not Found | Resource not found |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Service temporarily unavailable |

### Validation Errors (422)

```json
{
  "detail": [
    {
      "loc": ["query", "limit"],
      "msg": "ensure this value is less than or equal to 50",
      "type": "value_error.number.not_le",
      "ctx": {
        "limit_value": 50
      }
    }
  ]
}
```

### Error Handling Best Practices

```javascript
async function getPlaylist(language, limit = 20) {
  try {
    const response = await fetch(
      `http://localhost:8000/playlist/${language}?limit=${limit}`
    );
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to fetch playlist');
    }
    
    return await response.json();
  } catch (error) {
    console.error('Error fetching playlist:', error);
    throw error;
  }
}
```

---

## 🚦 Rate Limiting

### Current Limits (v2.0)

**No rate limiting** - All endpoints are unlimited for MVP

### Planned Limits (v2.1+)

| Tier | Requests/Minute | Requests/Hour |
|------|-----------------|---------------|
| Free | 60 | 1,000 |
| Basic | 300 | 10,000 |
| Pro | 1,000 | 100,000 |
| Enterprise | Custom | Custom |

### Rate Limit Headers (Future)

```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1640000000
```

### Rate Limit Error Response

```json
{
  "detail": "Rate limit exceeded. Try again in 42 seconds.",
  "retry_after": 42
}
```

---

## 💡 Examples

### Complete Frontend Integration

```typescript
// api.ts
import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

export const newsApi = {
  // Get all languages
  getLanguages: async () => {
    const response = await api.get('/languages');
    return response.data.languages;
  },

  // Get playlist for language
  getPlaylist: async (language: string, limit: number = 20) => {
    const response = await api.get(`/playlist/${language}`, {
      params: { limit }
    });
    return response.data;
  },

  // Get filtered playlist
  getPlaylistByCategory: async (
    language: string, 
    category: string, 
    limit: number = 20
  ) => {
    const response = await api.get(`/playlist/${language}`, {
      params: { limit, category }
    });
    return response.data;
  },

  // Refresh playlist
  refreshPlaylist: async (language: string) => {
    await api.get(`/refresh/${language}`);
  },

  // Get audio URL
  getAudioUrl: (filename: string) => {
    return `${API_BASE_URL}/audio/${filename}`;
  },

  // Check health
  checkHealth: async () => {
    const response = await api.get('/health');
    return response.data;
  }
};

// Usage example
async function loadNewsData() {
  try {
    // Get available languages
    const languages = await newsApi.getLanguages();
    console.log('Available languages:', languages);

    // Get English playlist
    const playlist = await newsApi.getPlaylist('en', 10);
    console.log('English playlist:', playlist);

    // Get technology articles in Hindi
    const techNews = await newsApi.getPlaylistByCategory('hi', 'technology', 5);
    console.log('Hindi tech news:', techNews);

  } catch (error) {
    console.error('Error loading news:', error);
  }
}
```

### React Component Example

```tsx
import { useState, useEffect } from 'react';
import { newsApi } from './api';

function NewsPlayer() {
  const [languages, setLanguages] = useState([]);
  const [selectedLang, setSelectedLang] = useState('en');
  const [playlist, setPlaylist] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadLanguages();
  }, []);

  useEffect(() => {
    loadPlaylist(selectedLang);
  }, [selectedLang]);

  const loadLanguages = async () => {
    try {
      const langs = await newsApi.getLanguages();
      setLanguages(langs);
    } catch (error) {
      console.error('Failed to load languages:', error);
    }
  };

  const loadPlaylist = async (lang: string) => {
    setLoading(true);
    try {
      const data = await newsApi.getPlaylist(lang, 20);
      setPlaylist(data.items);
    } catch (error) {
      console.error('Failed to load playlist:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    await newsApi.refreshPlaylist(selectedLang);
    await loadPlaylist(selectedLang);
  };

  return (
    <div>
      <div>
        {languages.map(lang => (
          <button
            key={lang.code}
            onClick={() => setSelectedLang(lang.code)}
          >
            {lang.flag} {lang.name} ({lang.items})
          </button>
        ))}
      </div>

      <button onClick={handleRefresh}>Refresh</button>

      {loading ? (
        <div>Loading...</div>
      ) : (
        <div>
          {playlist.map(item => (
            <div key={item.id}>
              <h3>{item.title}</h3>
              <p>{item.translated_summary}</p>
              <audio controls src={newsApi.getAudioUrl(item.audio_file)} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

### Python Client Example

```python
import requests
from typing import List, Dict, Optional

class NewsClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def get_languages(self) -> List[Dict]:
        """Get all available languages"""
        response = self.session.get(f"{self.base_url}/languages")
        response.raise_for_status()
        return response.json()["languages"]
    
    def get_playlist(
        self, 
        language: str, 
        limit: int = 20, 
        category: Optional[str] = None
    ) -> Dict:
        """Get playlist for a language"""
        params = {"limit": limit}
        if category:
            params["category"] = category
        
        response = self.session.get(
            f"{self.base_url}/playlist/{language}",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def refresh_playlist(self, language: str):
        """Refresh playlist for a language"""
        response = self.session.get(f"{self.base_url}/refresh/{language}")
        response.raise_for_status()
        return response.json()
    
    def download_audio(self, filename: str, output_path: str):
        """Download audio file"""
        response = self.session.get(
            f"{self.base_url}/audio/{filename}",
            stream=True
        )
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

# Usage
client = NewsClient()

# Get languages
languages = client.get_languages()
print(f"Available: {[l['name'] for l in languages]}")

# Get English news
playlist = client.get_playlist('en', limit=10)
print(f"English articles: {playlist['total_items']}")

# Download first audio file
if playlist['items']:
    first_item = playlist['items'][0]
    client.download_audio(
        first_item['audio_file'], 
        'news_article.mp3'
    )
```

### cURL Examples

```bash
# Get all languages
curl http://localhost:8000/languages

# Get English playlist (default 20 items)
curl http://localhost:8000/playlist/en

# Get 10 Hindi articles
curl http://localhost:8000/playlist/hi?limit=10

# Get technology articles in Bengali
curl "http://localhost:8000/playlist/bn?category=technology&limit=5"

# Download audio file
curl -O http://localhost:8000/audio/news_abc123_en.mp3

# Check health
curl http://localhost:8000/health

# Refresh playlist
curl http://localhost:8000/refresh/en

# Pretty print JSON with jq
curl http://localhost:8000/languages | jq .
```

---

## 📦 SDKs & Libraries

### Official SDKs (Planned)

- **JavaScript/TypeScript**: `@multilingual-news/client`
- **Python**: `multilingual-news-client`
- **Go**: `github.com/org/multilingual-news-go`
- **Ruby**: `multilingual-news`

### Community Wrappers

Coming soon!

---

## 🔄 Webhooks (Future Feature)

### Planned Webhook Events

```json
{
  "event": "news.published",
  "language": "en",
  "news_item": {
    "id": "abc123",
    "title": "...",
    "category": "technology"
  },
  "timestamp": "2024-12-28T10:30:00Z"
}
```

---

## 📝 API Changelog

### v2.0.0 (2024-12-28)
- ✨ Dynamic language management via Redis
- ✨ Fan-out Kafka consumer architecture
- ✨ Health check endpoints (health/ready/live)
- ✨ Real-time language item counts
- 🔄 Improved error handling

### v1.0.0 (2024-11-28)
- 🎉 Initial release
- ✨ Basic playlist endpoints
- ✨ Audio streaming
- ✨ Three languages (en, hi, bn)

---

## 🤝 Contributing

Found a bug or want to request a feature?

1. Check [GitHub Issues](https://github.com/org/repo/issues)
2. Open a new issue with the `api` label
3. Provide example request/response

---

## 📞 Support

- **Documentation**: [docs.yourdomain.com](https://docs.yourdomain.com)
- **Email**: api-support@yourdomain.com
- **Discord**: [discord.gg/your-server](https://discord.gg/your-server)

---

**API Documentation maintained by**: API Team  
**Last Updated**: December 28, 2024