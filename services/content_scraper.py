import requests
from bs4 import BeautifulSoup
from newspaper import Article
import logging
from typing import Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ContentScraper:
    """Scrapes full article content from URLs"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def scrape_article(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Scrape full article content and image from URL
        
        Returns:
            Tuple of (content, image_url)
        """
        try:
            # Try newspaper3k first (best for news articles)
            content, image = self._scrape_with_newspaper(url)
            if content:
                return content, image
            
            # Fallback to BeautifulSoup
            return self._scrape_with_beautifulsoup(url)
            
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {str(e)}")
            return None, None
    
    def _scrape_with_newspaper(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """Use newspaper3k library for article extraction"""
        try:
            article = Article(url)
            article.download()
            article.parse()
            
            content = article.text.strip()
            image = article.top_image
            
            if content and len(content) > 100:  # Minimum content length
                logger.info(f"Successfully scraped with newspaper3k: {url}")
                return content, image
            
            return None, None
            
        except Exception as e:
            logger.debug(f"Newspaper3k failed for {url}: {str(e)}")
            return None, None
    
    def _scrape_with_beautifulsoup(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """Fallback scraping with BeautifulSoup"""
        try:
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                element.decompose()
            
            # Try common article containers
            article_content = None
            selectors = [
                'article',
                '[class*="article-content"]',
                '[class*="article-body"]',
                '[class*="post-content"]',
                '[class*="entry-content"]',
                'main'
            ]
            
            for selector in selectors:
                container = soup.select_one(selector)
                if container:
                    paragraphs = container.find_all('p')
                    if paragraphs:
                        article_content = '\n\n'.join([p.get_text().strip() for p in paragraphs])
                        break
            
            # Get first image
            image_url = None
            img = soup.find('img', {'class': lambda x: x and 'article' in x.lower()}) or soup.find('img')
            if img and img.get('src'):
                image_url = img['src']
                if not image_url.startswith('http'):
                    domain = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
                    image_url = domain + image_url
            
            if article_content and len(article_content) > 100:
                logger.info(f"Successfully scraped with BeautifulSoup: {url}")
                return article_content, image_url
            
            return None, None
            
        except Exception as e:
            logger.error(f"BeautifulSoup scraping failed for {url}: {str(e)}")
            return None, None
    
    def is_scrapable_url(self, url: str) -> bool:
        """Check if URL is likely scrapable"""
        try:
            parsed = urlparse(url)
            # Skip PDFs, videos, etc.
            blocked_extensions = ['.pdf', '.mp4', '.mp3', '.zip', '.exe']
            return not any(parsed.path.endswith(ext) for ext in blocked_extensions)
        except Exception:
            return False