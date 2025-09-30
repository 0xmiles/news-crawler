"""
YouTube crawler for extracting and summarizing video content.
"""

import re
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import pytube
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from news_crawler.crawlers.base import BaseCrawler, CrawledContent


class YouTubeCrawler(BaseCrawler):
    """Crawler for YouTube videos."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        self.formatter = TextFormatter()
    
    async def crawl(self, url: str) -> List[CrawledContent]:
        """Crawl content from a YouTube URL."""
        self.logger.info(f"Starting YouTube crawl for {url}")
        
        try:
            video_id = self._extract_video_id(url)
            if not video_id:
                self.logger.error(f"Could not extract video ID from {url}")
                return []
            
            # Get video information
            video_info = await self._get_video_info(video_id)
            if not video_info:
                return []
            
            # Get transcript
            transcript = await self._get_transcript(video_id)
            
            # Create content object
            content = CrawledContent(
                url=url,
                title=video_info.get('title', ''),
                content=transcript or '',
                author=video_info.get('author', ''),
                published_date=video_info.get('publish_date'),
                tags=video_info.get('keywords', []),
                metadata={
                    'video_id': video_id,
                    'duration': video_info.get('length', 0),
                    'views': video_info.get('views', 0),
                    'description': video_info.get('description', ''),
                    'channel': video_info.get('author', ''),
                    'has_transcript': bool(transcript)
                }
            )
            
            return [content]
            
        except Exception as e:
            self.logger.error(f"Error crawling YouTube video {url}: {e}")
            return []
    
    def _extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL."""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
            r'youtube\.com\/v\/([^&\n?#]+)',
            r'youtube\.com\/shorts\/([^&\n?#]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    async def _get_video_info(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get video information using pytube."""
        try:
            # Create YouTube object
            yt = pytube.YouTube(f"https://www.youtube.com/watch?v={video_id}")
            
            # Get video details
            video_info = {
                'title': yt.title,
                'author': yt.author,
                'length': yt.length,
                'views': yt.views,
                'description': yt.description,
                'keywords': yt.keywords,
                'publish_date': yt.publish_date,
                'thumbnail_url': yt.thumbnail_url,
                'video_url': yt.watch_url
            }
            
            return video_info
            
        except Exception as e:
            self.logger.error(f"Error getting video info for {video_id}: {e}")
            return None
    
    async def _get_transcript(self, video_id: str) -> Optional[str]:
        """Get video transcript."""
        try:
            # Try to get transcript in preferred language
            transcript_language = self.config.get('transcript_language', 'en')
            
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                
                # Try to get transcript in preferred language
                try:
                    transcript = transcript_list.find_transcript([transcript_language])
                    transcript_data = transcript.fetch()
                except:
                    # Fallback to any available transcript
                    transcript = transcript_list.find_generated_transcripts([transcript_language])
                    transcript_data = transcript[0].fetch()
                
                # Format transcript
                formatted_transcript = self.formatter.format_transcript(transcript_data)
                return formatted_transcript
                
            except Exception as e:
                self.logger.warning(f"Could not get transcript for {video_id}: {e}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting transcript for {video_id}: {e}")
            return None
    
    async def crawl_channel(self, channel_url: str) -> List[CrawledContent]:
        """Crawl videos from a YouTube channel."""
        self.logger.info(f"Starting channel crawl for {channel_url}")
        
        try:
            # Extract channel ID or username
            channel_id = self._extract_channel_id(channel_url)
            if not channel_id:
                self.logger.error(f"Could not extract channel ID from {channel_url}")
                return []
            
            # Get channel videos (this would require YouTube API)
            # For now, we'll return empty list as this requires API key
            self.logger.warning("Channel crawling requires YouTube API key")
            return []
            
        except Exception as e:
            self.logger.error(f"Error crawling channel {channel_url}: {e}")
            return []
    
    def _extract_channel_id(self, url: str) -> Optional[str]:
        """Extract channel ID from YouTube channel URL."""
        patterns = [
            r'youtube\.com\/channel\/([^\/\?]+)',
            r'youtube\.com\/c\/([^\/\?]+)',
            r'youtube\.com\/user\/([^\/\?]+)',
            r'youtube\.com\/@([^\/\?]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def get_supported_domains(self) -> List[str]:
        """Get list of supported domains for this crawler."""
        return [
            'youtube.com',
            'youtu.be',
            'm.youtube.com'
        ]
    
    def is_youtube_url(self, url: str) -> bool:
        """Check if URL is a YouTube URL."""
        youtube_domains = self.get_supported_domains()
        parsed_url = urlparse(url)
        return any(domain in parsed_url.netloc for domain in youtube_domains)
    
    def get_video_duration(self, video_id: str) -> Optional[int]:
        """Get video duration in seconds."""
        try:
            yt = pytube.YouTube(f"https://www.youtube.com/watch?v={video_id}")
            return yt.length
        except Exception as e:
            self.logger.error(f"Error getting duration for {video_id}: {e}")
            return None
    
    def is_video_too_long(self, video_id: str) -> bool:
        """Check if video exceeds maximum length limit."""
        max_length = self.config.get('max_video_length', 3600)  # 1 hour default
        duration = self.get_video_duration(video_id)
        
        if duration is None:
            return False  # Assume it's okay if we can't get duration
        
        return duration > max_length
