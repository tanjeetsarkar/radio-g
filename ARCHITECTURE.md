# 🏛️ System Architecture

> Comprehensive architectural overview of Multilingual News Radio

**Version**: 2.0.0  
**Last Updated**: December 28, 2024

---

## 📋 Table of Contents

1. [High-Level Architecture](#-high-level-architecture)
2. [Component Details](#-component-details)
3. [Data Flow](#-data-flow)
4. [Technology Stack](#-technology-stack)
5. [Scalability & Performance](#-scalability--performance)
6. [Security Architecture](#-security-architecture)
7. [Deployment Architecture](#-deployment-architecture)
8. [Design Decisions](#-design-decisions)

---

## 🎯 High-Level Architecture

### System Overview Diagram

```mermaid
graph TB
    subgraph "External Sources"
        RSS1[BBC RSS]
        RSS2[TechCrunch RSS]
        RSS3[Bloomberg RSS]
        RSS4[12+ RSS Feeds]
    end

    subgraph "Ingestion Layer"
        Fetcher[News Fetcher<br/>Scheduled/15min]
        Scraper[Content Scraper<br/>BeautifulSoup]
    end

    subgraph "Deduplication Layer"
        Redis[(Redis Cache<br/>24h TTL)]
        Dedup[Deduplicator<br/>SHA256 Hashing]
    end

    subgraph "Streaming Layer"
        Kafka1[Kafka: raw-news-feed]
        Kafka2[Kafka: news-english]
        Kafka3[Kafka: news-hindi]
        Kafka4[Kafka: news-bengali]
        KafkaX[Kafka: news-*<br/>Dynamic Topics]
    end

    subgraph "Processing Layer"
        Processor1[Processing Consumer 1<br/>Translation + TTS]
        Processor2[Processing Consumer 2<br/>Translation + TTS]
        ProcessorN[Processing Consumer N<br/>Translation + TTS]
        Gemini[Google Gemini<br/>Translation]
        ElevenLabs[ElevenLabs<br/>Text-to-Speech]
    end

    subgraph "Configuration Layer"
        RedisConfig[(Redis<br/>Language Config)]
        LangMgr[Language Manager<br/>Singleton]
    end

    subgraph "API Layer"
        API1[FastAPI Instance 1<br/>Fan-Out Consumer]
        API2[FastAPI Instance 2<br/>Fan-Out Consumer]
        APIN[FastAPI Instance N<br/>Fan-Out Consumer]
        Cache1[In-Memory Cache 1]
        Cache2[In-Memory Cache 2]
        CacheN[In-Memory Cache N]
    end

    subgraph "Storage Layer"
        AudioStore[(Cloud Storage<br/>Audio Files)]
    end

    subgraph "Frontend"
        NextJS[Next.js Frontend<br/>React 19]
    end

    RSS1 --> Fetcher
    RSS2 --> Fetcher
    RSS3 --> Fetcher
    RSS4 --> Fetcher
    
    Fetcher --> Scraper
    Scraper --> Dedup
    Dedup --> Redis
    Dedup --> Kafka1
    
    Kafka1 --> Processor1
    Kafka1 --> Processor2
    Kafka1 --> ProcessorN
    
    Processor1 --> Gemini
    Processor1 --> ElevenLabs
    Processor2 --> Gemini
    Processor2 --> ElevenLabs
    ProcessorN --> Gemini
    ProcessorN --> ElevenLabs
    
    RedisConfig --> LangMgr
    LangMgr --> Processor1
    LangMgr --> Processor2
    LangMgr --> ProcessorN
    
    Processor1 --> Kafka2
    Processor1 --> Kafka3
    Processor1 --> Kafka4
    Processor1 --> KafkaX
    Processor2 --> Kafka2
    Processor2 --> Kafka3
    Processor2 --> Kafka4
    ProcessorN --> KafkaX
    
    ElevenLabs --> AudioStore
    
    Kafka2 --> API1
    Kafka3 --> API1
    Kafka4 --> API1
    KafkaX --> API1
    Kafka2 --> API2
    Kafka3 --> API2
    Kafka4 --> API2
    KafkaX --> API2
    Kafka2 --> APIN
    Kafka3 --> APIN
    Kafka4 --> APIN
    KafkaX --> APIN
    
    API1 --> Cache1
    API2 --> Cache2
    APIN --> CacheN
    
    AudioStore --> API1
    AudioStore --> API2
    AudioStore --> APIN
    
    API1 --> NextJS
    API2 --> NextJS
    APIN --> NextJS
    
    RedisConfig --> API1
    RedisConfig --> API2
    RedisConfig --> APIN

    style Redis fill:#ff6b6b
    style RedisConfig fill:#ff6b6b
    style Kafka1 fill:#4ecdc4
    style Kafka2 fill:#4ecdc4
    style Kafka3 fill:#4ecdc4
    style Kafka4 fill:#4ecdc4
    style KafkaX fill:#4ecdc4
    style Gemini fill:#ffe66d
    style ElevenLabs fill:#ffe66d
    style AudioStore fill:#95e1d3
```

---

## 🔧 Component Details

### 1. Ingestion Layer

#### News Fetcher
- **Language**: Python 3.13
- **Framework**: Custom with feedparser
- **Schedule**: Every 15 minutes (configurable)
- **Sources**: 12+ RSS feeds across 4 categories
- **Concurrency**: Single instance with sequential fetching
- **Rate Limiting**: 2-second delay between feeds

**Key Features:**
- Retry logic (3 attempts)
- Content scraping with fallback
- Published date parsing
- Image extraction

**Code Location:** `services/news_fetcher.py`

#### Content Scraper
- **Libraries**: BeautifulSoup4, Newspaper3k
- **Strategy**: Multi-layer extraction
  1. Try newspaper3k (best for news)
  2. Fallback to BeautifulSoup
  3. Use RSS description as last resort
- **Anti-blocking**: Rotating user agents
- **Timeout**: 30 seconds per article

**Code Location:** `services/content_scraper.py`

---

### 2. Deduplication Layer

#### Redis Cache
- **Version**: Redis 7
- **TTL**: 24 hours (configurable)
- **Key Format**: `news:seen:{hash}`
- **Hash Algorithm**: SHA256(url + title)
- **Purpose**: Prevent duplicate articles across sources

**Memory Estimates:**
- ~100 bytes per cached article
- ~500 articles/day = 50KB
- ~15,000 articles/month = 1.5MB

**Code Location:** `services/deduplicator.py`

---

### 3. Streaming Layer

#### Apache Kafka
- **Version**: Confluent Platform 7.5.0
- **Protocol**: SASL_SSL (production)
- **Replication**: 3 replicas (production)
- **Partitions**: 3 per topic

**Topics:**

| Topic | Partitions | Retention | Purpose |
|-------|------------|-----------|---------|
| `raw-news-feed` | 3 | 7 days | Untranslated articles |
| `news-english` | 3 | 30 days | English broadcasts |
| `news-hindi` | 3 | 30 days | Hindi broadcasts |
| `news-bengali` | 3 | 30 days | Bengali broadcasts |
| `news-*` | 3 | 30 days | Dynamic language topics |

**Message Format:**
```json
{
  "id": "abc123",
  "title": "Article Title",
  "content": "Full content...",
  "url": "https://...",
  "category": "technology",
  "source": "TechCrunch",
  "published_date": "2024-12-28T10:00:00Z"
}
```

**Producer Configuration:**
- `acks=all` - Wait for all replicas
- `compression=gzip` - Reduce bandwidth
- `batch.size=32KB` - Batch messages
- `linger.ms=100` - Wait 100ms for batching

**Consumer Configuration:**
- `auto.offset.reset=earliest` - Start from beginning
- `enable.auto.commit=true` - Auto-commit offsets
- `session.timeout.ms=6000` - 6 second timeout

---

### 4. Processing Layer

#### Processing Consumer
- **Instances**: 2-5 (auto-scaling)
- **Consumer Group**: `news-processing-group`
- **Concurrency**: Multi-threaded per instance
- **Throughput**: ~100 articles/hour per instance

**Processing Pipeline:**
```mermaid
graph LR
    A[Consume Message] --> B[Parse Article]
    B --> C{For Each Language}
    C --> D[Translate + Summarize]
    D --> E[Generate Audio]
    E --> F[Store Audio File]
    F --> G[Produce to Language Topic]
    G --> C
    C --> H[Mark Complete]
```

**Code Location:** `processing_consumer.py`

#### Google Gemini
- **Model**: gemini-2.5-flash
- **Purpose**: Translation + Summarization
- **Input**: Original article (up to 5000 chars)
- **Output**: 
  - English summary (~150 chars)
  - Translated summary in target language
- **Latency**: ~2-3 seconds per article
- **Cost**: $0.00003/1K chars

**Code Location:** `services/translation_service.py`

#### ElevenLabs TTS
- **Model**: eleven_multilingual_v2
- **Voices**: Custom per language
  - English: George (natural, clear)
  - Hindi: Fin (multilingual)
  - Bengali: Fin (multilingual)
- **Input**: Translated summary (150-200 chars)
- **Output**: MP3 audio file (~30-60 seconds)
- **Latency**: ~3-5 seconds per file
- **Cost**: $0.30/1K characters

**Code Location:** `services/tts_service.py`

---

### 5. Configuration Layer

#### Language Manager
- **Type**: Singleton Pattern
- **Storage**: Redis (`config:languages`)
- **Refresh**: On-demand (no caching within instance)
- **Format**:
```json
{
  "en": {
    "name": "English",
    "flag": "🇬🇧",
    "voice_id": "JBFqnCBsd6RMkjVDRZzb",
    "enabled": true
  },
  "hi": {
    "name": "Hindi",
    "flag": "🇮🇳",
    "voice_id": "zs7UfyHqCCmny7uTxCYi",
    "enabled": true
  }
}
```

**Dynamic Features:**
- Add/remove languages without code changes
- Enable/disable languages on-the-fly
- Change voice assignments
- Auto-creates Kafka topics

**Code Location:** `services/language_manager.py`

---

### 6. API Layer

#### FastAPI Backend
- **Framework**: FastAPI 0.100+
- **Python**: 3.13+
- **ASGI Server**: Uvicorn
- **Instances**: 1-10 (auto-scaling)
- **Memory**: 2GB per instance
- **CPU**: 2 cores per instance

**Architecture Pattern:** Fan-Out Consumer

Each API instance:
1. Creates unique consumer group: `api-consumer-{uuid}`
2. Subscribes to all `news-*` topics using regex
3. Builds independent in-memory cache
4. Serves requests from local cache

**Why Fan-Out?**
- ✅ Every instance has complete data
- ✅ No cache coordination needed
- ✅ Fast local reads (no network calls)
- ✅ Horizontally scalable
- ❌ Higher memory usage (acceptable trade-off)

**In-Memory Cache:**
- **Structure**: `Dict[language_code, List[ProcessedNewsItem]]`
- **Size**: ~50 articles per language × 3 languages = ~150 articles
- **Memory**: ~5MB per instance
- **TTL**: Items sorted by date, keep latest 50

**Endpoints:** See [API.md](API.md) for details

**Code Location:** `main.py`

---

### 7. Storage Layer

#### Cloud Storage (Audio Files)
- **Type**: Google Cloud Storage (production)
- **Bucket**: Public read, private write
- **Lifecycle**: Delete after 30 days
- **CDN**: Cloud CDN (optional)
- **Format**: MP3 files
- **Size**: ~50KB per file
- **Daily Volume**: ~500 files = 25MB/day

**Alternative for Development:**
- Local filesystem: `audio_output/`

---

### 8. Frontend Layer

#### Next.js Application
- **Version**: Next.js 15
- **React**: React 19
- **Styling**: Tailwind CSS v4
- **Deployment**: Vercel or Cloud Run
- **Features**:
  - Server-side rendering
  - Dynamic language selector
  - Audio streaming player
  - Real-time playlist updates

**Code Location:** `frontend/`

---

## 🔄 Data Flow

### Complete Article Journey

```mermaid
sequenceDiagram
    participant RSS as RSS Feeds
    participant Fetcher as News Fetcher
    participant Redis as Redis Cache
    participant K1 as Kafka: raw-news
    participant Proc as Processing Consumer
    participant Gemini as Google Gemini
    participant ElevenLabs as ElevenLabs
    participant K2 as Kafka: news-en
    participant API as FastAPI
    participant Frontend as Next.js Frontend
    participant User as User

    RSS->>Fetcher: Poll every 15 min
    Fetcher->>Fetcher: Scrape content
    Fetcher->>Redis: Check duplicate (SHA256)
    
    alt Not Duplicate
        Fetcher->>K1: Produce raw article
        K1->>Proc: Consume article
        
        loop For each language
            Proc->>Gemini: Translate + Summarize
            Gemini-->>Proc: Translated summary
            Proc->>ElevenLabs: Generate audio
            ElevenLabs-->>Proc: Audio file
            Proc->>K2: Produce processed item
        end
        
        K2->>API: Consume (fan-out)
        API->>API: Update in-memory cache
        
        User->>Frontend: Visit website
        Frontend->>API: GET /languages
        API-->>Frontend: [en, hi, bn]
        
        Frontend->>API: GET /playlist/en
        API-->>Frontend: Playlist with audio files
        
        Frontend->>User: Display news + play audio
    else Duplicate
        Fetcher->>Fetcher: Skip article
    end
```

### Request Flow (API)

```mermaid
sequenceDiagram
    participant Client as Client
    participant LB as Load Balancer
    participant API1 as API Instance 1
    participant API2 as API Instance 2
    participant Cache as In-Memory Cache
    participant Kafka as Kafka

    Client->>LB: GET /playlist/en
    LB->>API1: Route request
    
    API1->>Kafka: Poll for new messages
    Kafka-->>API1: New articles
    API1->>Cache: Update cache
    
    API1->>Cache: Query cache
    Cache-->>API1: Cached articles
    API1-->>LB: JSON response
    LB-->>Client: 200 OK + articles
    
    Note over API1,API2: Each instance has independent cache
    Note over API1,API2: Fan-out pattern ensures data consistency
```

---

## 🛠️ Technology Stack

### Backend

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Runtime | Python | 3.13+ | Application runtime |
| Package Manager | uv | Latest | Dependency management |
| API Framework | FastAPI | 0.100+ | REST API |
| ASGI Server | Uvicorn | Latest | HTTP server |
| Message Queue | Apache Kafka | 7.5.0 | Event streaming |
| Cache | Redis | 7.0 | Deduplication + Config |
| HTTP Client | Requests | Latest | Web scraping |
| HTML Parser | BeautifulSoup4 | Latest | Content extraction |
| Article Parser | Newspaper3k | Latest | News extraction |

### AI/ML

| Service | Purpose | Model | Cost |
|---------|---------|-------|------|
| Google Gemini | Translation + Summarization | gemini-2.5-flash | $0.00003/1K chars |
| ElevenLabs | Text-to-Speech | eleven_multilingual_v2 | $0.30/1K chars |

### Frontend

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Framework | Next.js | 15 | React framework |
| UI Library | React | 19 | UI components |
| Styling | Tailwind CSS | 4 | Utility-first CSS |
| Icons | Lucide React | Latest | Icon library |
| HTTP Client | Axios | Latest | API requests |
| Language | TypeScript | 5+ | Type safety |

### Infrastructure

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Containers | Docker | Development isolation |
| Orchestration | Docker Compose | Local development |
| Cloud Platform | GCP | Production hosting |
| Compute | Cloud Run | Serverless containers |
| Message Queue | Confluent Cloud | Managed Kafka |
| Cache | Memorystore | Managed Redis |
| Storage | Cloud Storage | Audio files |
| Logging | Cloud Logging | Centralized logs |
| Monitoring | Cloud Monitoring | Metrics & alerts |

---

## 📈 Scalability & Performance

### Current Performance (MVP)

| Metric | Value | Notes |
|--------|-------|-------|
| Articles/Day | ~500 | 12 sources × 10 articles × 15-min intervals |
| Audio Generated/Day | ~1500 | 500 articles × 3 languages |
| API Latency (p95) | ~200ms | In-memory cache |
| Processing Latency | ~10s | Per article (translation + TTS) |
| Storage Used/Day | ~25MB | Audio files |

### Scaling Strategy

#### Horizontal Scaling

**News Fetcher:**
- Single instance (scheduled job)
- Not a bottleneck (~2min to fetch all)

**Processing Consumer:**
```
1 instance  = 100 articles/hour
5 instances = 500 articles/hour
10 instances = 1000 articles/hour
```
- Scale based on consumer lag
- Auto-scale in Cloud Run

**API Backend:**
```
1 instance  = 1000 req/sec
5 instances = 5000 req/sec
10 instances = 10000 req/sec
```
- Scale based on CPU/memory
- Auto-scale in Cloud Run

#### Vertical Scaling

**Processing Consumer:**
- Memory: 2GB → 4GB (more concurrent processing)
- CPU: 2 cores → 4 cores (parallel TTS generation)

**API Backend:**
- Memory: 2GB → 4GB (larger cache)
- CPU: 2 cores → 4 cores (more concurrent requests)

### Bottleneck Analysis

| Component | Bottleneck | Solution |
|-----------|------------|----------|
| Gemini API | Rate limits (60 req/min) | Batch requests, add retry |
| ElevenLabs | Rate limits (50 req/min) | Queue system, add retry |
| Kafka | Consumer lag | Scale consumers |
| Redis | Memory limits | Increase instance size |
| API Cache | Stale data | Reduce Kafka poll interval |

### Optimization Opportunities

1. **Batch AI Requests**: Group multiple articles per API call
2. **Pre-warm Cache**: Cache popular categories
3. **CDN for Audio**: Reduce API load
4. **Database for Metadata**: Move from cache to persistent store
5. **GraphQL API**: Reduce over-fetching

---

## 🔒 Security Architecture

### Current Security (MVP)

```mermaid
graph TB
    subgraph "Public Internet"
        User[User]
    end
    
    subgraph "Frontend Layer"
        NextJS[Next.js<br/>HTTPS Only]
    end
    
    subgraph "API Layer"
        API[FastAPI<br/>CORS Enabled]
    end
    
    subgraph "Internal Network"
        Kafka[Kafka<br/>SASL_SSL]
        Redis[Redis<br/>AUTH Enabled]
        Secrets[Secret Manager]
    end
    
    User -->|HTTPS| NextJS
    NextJS -->|HTTPS| API
    API -->|TLS| Kafka
    API -->|TLS| Redis
    API -->|TLS| Secrets
    
    style User fill:#ff6b6b
    style Secrets fill:#51cf66
```

### Security Measures

#### 1. API Security

**Implemented:**
- ✅ HTTPS only (TLS 1.2+)
- ✅ CORS configuration
- ✅ Input validation (Pydantic)
- ✅ Rate limiting (planned)

**Planned:**
- 🔄 API key authentication
- 🔄 JWT bearer tokens
- 🔄 Request signing
- 🔄 IP whitelist

#### 2. Data Security

**In Transit:**
- TLS 1.2+ for all connections
- SASL_SSL for Kafka
- Redis AUTH password

**At Rest:**
- Cloud Storage encryption (AES-256)
- Redis encryption at rest (Memorystore)

**Secrets Management:**
- GCP Secret Manager
- Environment variables for development
- No secrets in code or Git

#### 3. Network Security

**Firewall Rules:**
```
Frontend → API: Allow HTTPS (443)
API → Kafka: Allow 9092, 9093
API → Redis: Allow 6379
API → Gemini: Allow HTTPS (443)
API → ElevenLabs: Allow HTTPS (443)
Everything else: Deny
```

**Internal Network:**
- VPC peering for GCP services
- Private IPs for Redis
- No public IP for processing consumers

#### 4. Application Security

**Code Security:**
- Dependency scanning (uv pip audit)
- Regular updates
- Input sanitization
- SQL injection prevention (N/A - no SQL)
- XSS prevention (React auto-escapes)

**Logging Security:**
- No sensitive data in logs
- Structured logging (JSON)
- Log retention (30 days)

---

## 🚀 Deployment Architecture

### Local Development

```mermaid
graph TB
    subgraph "Developer Machine"
        Docker[Docker Compose<br/>Redis + Kafka]
        Backend[Python Services<br/>Local Environment]
        Frontend[Next.js Dev Server<br/>Port 3000]
    end
    
    Backend --> Docker
    Frontend --> Backend
    
    style Docker fill:#4ecdc4
    style Backend fill:#ffe66d
    style Frontend fill:#95e1d3
```

### Production Deployment (GCP)

```mermaid
graph TB
    subgraph "Global"
        User[Users Worldwide]
        CDN[Cloud CDN]
    end
    
    subgraph "GCP Region: us-central1"
        subgraph "Cloud Run"
            API1[API Instance 1]
            API2[API Instance N]
            Proc1[Processor 1]
            Proc2[Processor N]
        end
        
        subgraph "Managed Services"
            Redis[(Memorystore Redis)]
            Storage[(Cloud Storage<br/>Audio Files)]
            Logging[Cloud Logging]
            Monitoring[Cloud Monitoring]
        end
        
        Scheduler[Cloud Scheduler]
    end
    
    subgraph "Confluent Cloud"
        Kafka[Managed Kafka Cluster<br/>Multi-Region]
    end
    
    subgraph "External Services"
        Gemini[Google Gemini]
        ElevenLabs[ElevenLabs]
    end
    
    User --> CDN
    CDN --> API1
    CDN --> API2
    
    Scheduler --> Proc1
    Scheduler --> Proc2
    
    API1 --> Kafka
    API2 --> Kafka
    Proc1 --> Kafka
    Proc2 --> Kafka
    
    API1 --> Redis
    API2 --> Redis
    Proc1 --> Redis
    Proc2 --> Redis
    
    Proc1 --> Gemini
    Proc2 --> Gemini
    Proc1 --> ElevenLabs
    Proc2 --> ElevenLabs
    
    Proc1 --> Storage
    Proc2 --> Storage
    API1 --> Storage
    API2 --> Storage
    
    API1 --> Logging
    API2 --> Logging
    Proc1 --> Logging
    Proc2 --> Logging
    
    API1 --> Monitoring
    API2 --> Monitoring
    Proc1 --> Monitoring
    Proc2 --> Monitoring
    
    style Kafka fill:#4ecdc4
    style Redis fill:#ff6b6b
    style Storage fill:#95e1d3
    style CDN fill:#51cf66
```

---

## 🤔 Design Decisions

### 1. Why Kafka over Redis Streams?

**Decision:** Apache Kafka

**Reasoning:**
- ✅ Better horizontal scalability
- ✅ Long-term message retention
- ✅ Multi-consumer support
- ✅ Industry standard
- ✅ Rich ecosystem (Connect, Streams)
- ❌ More complex to operate

**Alternatives Considered:**
- Redis Streams: Simpler but less scalable
- RabbitMQ: Good but less suited for streaming
- AWS SQS: Cloud lock-in

---

### 2. Why Fan-Out Consumer Pattern?

**Decision:** Each API instance builds independent cache

**Reasoning:**
- ✅ Fast reads (no network calls)
- ✅ Simple implementation
- ✅ No cache coordination needed
- ✅ Scales horizontally
- ❌ Higher memory usage (acceptable)

**Alternatives Considered:**
- Shared Redis cache: Network latency, complexity
- Database: Slower, added complexity
- External cache service: More dependencies

---

### 3. Why Redis for Language Config?

**Decision:** Redis key-value store

**Reasoning:**
- ✅ Fast reads (<1ms)
- ✅ Already in architecture
- ✅ Simple data structure
- ✅ No schema migrations
- ✅ Atomic updates
- ❌ Not persistent (but backed up)

**Alternatives Considered:**
- PostgreSQL: Overkill for key-value
- Config files: Requires deployment to update
- Environment variables: Not dynamic

---

### 4. Why Google Gemini over OpenAI?

**Decision:** Google Gemini 2.5 Flash

**Reasoning:**
- ✅ Better multilingual support
- ✅ Faster (flash model)
- ✅ Cheaper ($0.00003 vs $0.0005/1K)
- ✅ Structured output support
- ❌ Newer, less battle-tested

**Alternatives Considered:**
- OpenAI GPT-4: More expensive
- Claude: Good but more expensive
- Open-source models: Lower quality

---

### 5. Why ElevenLabs over Google TTS?

**Decision:** ElevenLabs Multilingual v2

**Reasoning:**
- ✅ Superior voice quality
- ✅ Natural-sounding speech
- ✅ Good multilingual support
- ✅ Custom voice options
- ❌ More expensive ($0.30 vs $0.004/1K)

**Alternatives Considered:**
- Google Cloud TTS: Cheaper but robotic
- AWS Polly: Good but less natural
- Azure TTS: Similar quality, similar price

---

## 📊 System Metrics

### Resource Requirements

| Component | CPU | Memory | Storage | Network |
|-----------|-----|--------|---------|---------|
| News Fetcher | 1 core | 512MB | 1GB | 10 Mbps |
| Processing Consumer | 2 cores | 2GB | 5GB | 20 Mbps |
| API Backend | 2 cores | 2GB | 1GB | 50 Mbps |
| Frontend | 1 core | 512MB | 1GB | 10 Mbps |

### Cost Estimates (Monthly)

| Service | Usage | Cost/Month |
|---------|-------|------------|
| Cloud Run (API) | 1M requests | ~$10 |
| Cloud Run (Processor) | 15K hours | ~$30 |
| Confluent Kafka | Basic cluster | ~$360 |
| Memorystore Redis | 1GB instance | ~$40 |
| Cloud Storage | 50GB + bandwidth | ~$10 |
| Gemini API | 15M chars/month | ~$0.45 |
| ElevenLabs | 50K chars/month | ~$15 |
| **Total** | | **~$465/month** |

---

## 🔮 Future Architecture

### Planned Improvements

1. **Database Layer**
   - Add PostgreSQL for persistent storage
   - Store article metadata, user data
   - Enable complex queries

2. **Caching Layer**
   - Add Redis cluster for API caching
   - Implement cache warming
   - Edge caching with CDN

3. **Search Layer**
   - Add Elasticsearch for full-text search
   - Enable semantic search with embeddings
   - Category and tag filtering

4. **Analytics Layer**
   - Add BigQuery for analytics
   - User behavior tracking
   - Content performance metrics

5. **Real-time Updates**
   - WebSocket support for live updates
   - Server-sent events for notifications
   - Real-time article count updates

---

**Architecture Document maintained by**: Engineering Team  
**Last Updated**: December 28, 2024  
**Next Review**: January 28, 2025