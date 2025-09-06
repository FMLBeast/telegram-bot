"""NSFW content service for fetching videos and images from RapidAPI endpoints."""

import asyncio
import aiohttp
import random
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class NsfwService:
    """Service for fetching NSFW content from various RapidAPI endpoints."""
    
    def __init__(self):
        """Initialize the NSFW service."""
        self.rapidapi_key = settings.rapidapi_key
        self.base_timeout = 15
        logger.info("NSFW service initialized")
    
    async def get_random_video(self, category: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a random NSFW video from RapidAPI."""
        if not self.rapidapi_key:
            logger.warning("RapidAPI key not configured for NSFW video service")
            return None
        
        try:
            headers = {
                "X-RapidAPI-Key": self.rapidapi_key,
                "X-RapidAPI-Host": "nsfw-api.p.rapidapi.com"
            }
            
            # Try different endpoints for better variety
            endpoints = [
                "https://nsfw-api.p.rapidapi.com/random",
                "https://nsfw-api.p.rapidapi.com/videos/random",
                "https://nsfw-api.p.rapidapi.com/content/random"
            ]
            
            url = random.choice(endpoints)
            params = {}
            if category:
                params["category"] = category
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, 
                    headers=headers, 
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.base_timeout)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        # Normalize response structure
                        if isinstance(data, list) and data:
                            data = data[0]
                        
                        if isinstance(data, dict):
                            video_url = (
                                data.get('video_url') or 
                                data.get('url') or 
                                data.get('link') or 
                                data.get('mp4')
                            )
                            
                            if video_url:
                                return {
                                    'url': video_url,
                                    'title': data.get('title', 'Random Video'),
                                    'category': data.get('category', category or 'general'),
                                    'duration': data.get('duration'),
                                    'thumbnail': data.get('thumbnail'),
                                    'source': 'RapidAPI NSFW',
                                    'fetched_at': datetime.utcnow().isoformat()
                                }
                    
                    logger.warning(f"NSFW video API returned status {response.status}")
                    
        except asyncio.TimeoutError:
            logger.error("Timeout fetching random video from RapidAPI")
        except Exception as e:
            logger.error(f"Error fetching random video: {str(e)}", exc_info=True)
        
        # Return fallback mock data if API fails
        return await self._get_fallback_video(category)
    
    async def get_image_by_category(self, category: str) -> Optional[Dict[str, Any]]:
        """Get NSFW image by category from RapidAPI."""
        if not self.rapidapi_key:
            logger.warning("RapidAPI key not configured for NSFW image service")
            return None
        
        try:
            headers = {
                "X-RapidAPI-Key": self.rapidapi_key,
                "X-RapidAPI-Host": "nsfw-images.p.rapidapi.com"
            }
            
            # Try different image endpoints
            endpoints = [
                f"https://nsfw-images.p.rapidapi.com/{category}",
                f"https://nsfw-images.p.rapidapi.com/category/{category}",
                f"https://nsfw-images.p.rapidapi.com/random/{category}"
            ]
            
            for url in endpoints:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            url, 
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=self.base_timeout)
                        ) as response:
                            
                            if response.status == 200:
                                data = await response.json()
                                
                                # Normalize response structure
                                if isinstance(data, list) and data:
                                    data = data[0]
                                
                                if isinstance(data, dict):
                                    image_url = (
                                        data.get('image_url') or 
                                        data.get('url') or 
                                        data.get('link') or 
                                        data.get('image')
                                    )
                                    
                                    if image_url:
                                        return {
                                            'url': image_url,
                                            'category': category,
                                            'title': data.get('title', f'{category.title()} Image'),
                                            'source': 'RapidAPI NSFW Images',
                                            'fetched_at': datetime.utcnow().isoformat(),
                                            'width': data.get('width'),
                                            'height': data.get('height')
                                        }
                            
                except Exception as e:
                    logger.debug(f"Failed endpoint {url}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error fetching image by category {category}: {str(e)}", exc_info=True)
        
        # Return fallback mock data if API fails
        return await self._get_fallback_image(category)
    
    async def get_available_categories(self) -> List[str]:
        """Get available NSFW categories."""
        if not self.rapidapi_key:
            return self._get_default_categories()
        
        try:
            headers = {
                "X-RapidAPI-Key": self.rapidapi_key,
                "X-RapidAPI-Host": "nsfw-api.p.rapidapi.com"
            }
            
            url = "https://nsfw-api.p.rapidapi.com/categories"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, 
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.base_timeout)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        if isinstance(data, list):
                            return data
                        elif isinstance(data, dict) and 'categories' in data:
                            return data['categories']
                    
        except Exception as e:
            logger.error(f"Error fetching categories: {str(e)}", exc_info=True)
        
        return self._get_default_categories()
    
    async def _get_fallback_video(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Get fallback video data when API fails."""
        fallback_videos = [
            "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4",
            "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
            "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4"
        ]
        
        return {
            'url': random.choice(fallback_videos),
            'title': f'Sample Video ({category or "Random"})',
            'category': category or 'sample',
            'duration': '00:30',
            'source': 'Fallback Sample',
            'fetched_at': datetime.utcnow().isoformat()
        }
    
    async def _get_fallback_image(self, category: str) -> Dict[str, Any]:
        """Get fallback image data when API fails."""
        # Use placeholder service for fallback
        size = random.choice(['400x400', '500x300', '600x400'])
        
        return {
            'url': f'https://picsum.photos/{size}?random={random.randint(1, 1000)}',
            'category': category,
            'title': f'{category.title()} Placeholder',
            'source': 'Placeholder Service',
            'fetched_at': datetime.utcnow().isoformat()
        }
    
    def _get_default_categories(self) -> List[str]:
        """Get default NSFW categories when API is unavailable."""
        return [
            'amateur', 'anal', 'asian', 'babe', 'bbw', 'big-ass', 'big-tits',
            'blonde', 'blowjob', 'brunette', 'creampie', 'cumshot', 'fetish',
            'hardcore', 'latina', 'lesbian', 'milf', 'pornstar', 'redhead',
            'teen', 'threesome', 'vintage'
        ]


# Global service instance
nsfw_service = NsfwService()