import requests
from bs4 import BeautifulSoup
from newspaper import Article
import logging
from typing import Optional, Tuple
from urllib.parse import urlparse
import random
import time

logger = logging.getLogger(__name__)


class ContentScraper:
    """Scrapes full article content from URLs with anti-blocking measures"""
    
    # Rotating user agents to avoid blocking
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    ]
    
    # Sites known to block scrapers - use RSS description only
    BLOCKED_DOMAINS = {
        'bloomberg.com',
        'wsj.com',
        'nytimes.com',
        'ft.com',
        'economist.com'
    }
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        # Add retry strategy
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        retry_strategy = Retry(
            total=2,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def _get_headers(self) -> dict:
        """Get random headers to avoid blocking"""
        return {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
    
    def _is_blocked_domain(self, url: str) -> bool:
        """Check if domain is known to block scrapers"""
        try:
            domain = urlparse(url).netloc.lower()
            # Remove 'www.' prefix
            domain = domain.replace('www.', '')
            return any(blocked in domain for blocked in self.BLOCKED_DOMAINS)
        except Exception:
            return False
    
    def scrape_article(self, url: str, fallback_description: str = "") -> Tuple[Optional[str], Optional[str]]:
        """
        Scrape full article content and image from URL
        
        Args:
            url: Article URL
            fallback_description: RSS description to use if scraping fails
        
        Returns:
            Tuple of (content, image_url)
        """
        
        # Check if domain is blocked - use fallback immediately
        if self._is_blocked_domain(url):
            logger.info(f"Known blocked domain, using RSS description: {url}")
            return fallback_description, None
        
        try:
            # Try newspaper3k first (best for news articles)
            content, image = self._scrape_with_newspaper(url)
            if content and len(content) > 200:  # Minimum meaningful content
                return content, image
            
            # Fallback to BeautifulSoup
            content, image = self._scrape_with_beautifulsoup(url)
            if content and len(content) > 200:
                return content, image
            
            # If both fail, use RSS description
            logger.warning(f"Scraping failed, using RSS description for: {url}")
            return fallback_description, image
            
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {str(e)}")
            return fallback_description, None
    
    def _scrape_with_newspaper(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """Use newspaper3k library for article extraction"""
        try:
            # newspaper3k doesn't support custom headers directly
            # So we download with requests first, then parse
            response = self.session.get(
                url,
                headers=self._get_headers(),
                timeout=self.timeout,
                allow_redirects=True
            )
            response.raise_for_status()
            
            # Create article from HTML
            article = Article(url)
            article.download(input_html=response.content)
            article.parse()
            
            content = article.text.strip()
            image = article.top_image
            
            if content and len(content) > 200:
                logger.info(f"✓ Scraped with newspaper3k: {url[:60]}")
                return content, image
            
            return None, None
            
        except Exception as e:
            logger.debug(f"Newspaper3k failed for {url}: {str(e)}")
            return None, None
    
    def _scrape_with_beautifulsoup(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """Fallback scraping with BeautifulSoup"""
        try:
            # Add small delay to be respectful
            time.sleep(0.5)
            
            response = self.session.get(
                url, 
                headers=self._get_headers(), 
                timeout=self.timeout,
                allow_redirects=True
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'iframe', 'noscript']):
                element.decompose()
            
            # Try common article containers
            article_content = None
            selectors = [
                'article',
                '[class*="article-content"]',
                '[class*="article-body"]',
                '[class*="article__body"]',
                '[class*="post-content"]',
                '[class*="entry-content"]',
                '[id*="article-content"]',
                '[id*="article-body"]',
                'main [class*="content"]',
                '[class*="story-body"]',
                'main'
            ]
            
            for selector in selectors:
                container = soup.select_one(selector)
                if container:
                    paragraphs = container.find_all('p')
                    if paragraphs and len(paragraphs) > 2:  # At least 3 paragraphs
                        text_parts = []
                        for p in paragraphs:
                            text = p.get_text().strip()
                            # Filter out short paragraphs (likely navigation/ads)
                            if len(text) > 50:
                                text_parts.append(text)
                        
                        if text_parts:
                            article_content = '\n\n'.join(text_parts)
                            break
            
            # Get first meaningful image
            image_url = None
            img_selectors = [
                'article img',
                '[class*="article"] img',
                '[class*="featured"] img',
                'main img',
                'img[class*="hero"]'
            ]
            
            for selector in img_selectors:
                img = soup.select_one(selector)
                if img and img.get('src'):
                    src = img['src']
                    # Skip tiny images, tracking pixels, icons
                    if any(x in src.lower() for x in ['tracking', 'pixel', 'icon', 'logo', '1x1']):
                        continue
                    
                    image_url = src
                    if not image_url.startswith('http'):
                        domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                        image_url = domain + image_url
                    break
            
            if article_content and len(article_content) > 200:
                logger.info(f"✓ Scraped with BeautifulSoup: {url[:60]}")
                return article_content, image_url
            
            return None, None
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.warning(f"403 Forbidden (paywall/blocking): {url}")
            else:
                logger.error(f"HTTP {e.response.status_code}: {url}")
            return None, None
        except Exception as e:
            logger.error(f"BeautifulSoup scraping failed for {url}: {str(e)}")
            return None, None
    
    def is_scrapable_url(self, url: str) -> bool:
        """Check if URL is likely scrapable"""
        try:
            parsed = urlparse(url)
            # Skip PDFs, videos, etc.
            blocked_extensions = ['.pdf', '.mp4', '.mp3', '.zip', '.exe', '.jpg', '.png', '.gif']
            if any(parsed.path.lower().endswith(ext) for ext in blocked_extensions):
                return False
            
            # Check if it's a blocked domain
            if self._is_blocked_domain(url):
                return False
            
            return True
        except:
            return False