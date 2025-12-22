from services.news_fetcher import NewsFetcher

# Example usage
if __name__ == "__main__":
    fetcher = NewsFetcher()
    
    # Fetch all news
    all_news = fetcher.fetch_all_feeds()
    
    # Print sample
    for item in all_news[:3]:
        print(f"\n{item.source} - {item.category}")
        print(f"Title: {item.title}")
        print(f"URL: {item.url}")
        print(f"Content length: {len(item.content) if item.content else 0} chars")
        print(f"Published: {item.published_date}")