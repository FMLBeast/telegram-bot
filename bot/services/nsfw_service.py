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
        self._api_verified = False
        
        if self.rapidapi_key:
            logger.info("NSFW service initialized with RapidAPI key")
        else:
            logger.warning("NSFW service initialized without RapidAPI key - will use fallback content")
    
    async def initialize_and_verify(self):
        """Initialize and verify API access on startup."""
        if self._api_verified or not self.rapidapi_key:
            return
            
        try:
            verification_results = await self.verify_api_access()
            
            if verification_results.get("video_api"):
                logger.info("✅ Video API (quality-porn.p.rapidapi.com) is accessible")
            else:
                error_msg = verification_results.get("video_api_error", "Unknown error")
                logger.warning(f"❌ Video API (quality-porn.p.rapidapi.com) is not accessible: {error_msg}")
                
            if verification_results.get("image_api"):
                logger.info("✅ Image API (girls-nude-image.p.rapidapi.com) is accessible")
            else:
                error_msg = verification_results.get("image_api_error", "Unknown error")
                logger.warning(f"❌ Image API (girls-nude-image.p.rapidapi.com) is not accessible: {error_msg}")
            
            # Log overall status
            working_apis = sum([verification_results.get("video_api", False), verification_results.get("image_api", False)])
            if working_apis == 0:
                logger.error("⚠️  No NSFW APIs are working. Bot will use fallback content only.")
            elif working_apis == 1:
                logger.warning("⚠️  Only 1 out of 2 NSFW APIs are working. Some features may use fallback content.")
            else:
                logger.info("✅ All NSFW APIs are working correctly")
                
            self._api_verified = True
            
        except Exception as e:
            logger.error(f"Error during API verification: {str(e)}", exc_info=True)
    
    async def get_random_video(self, category: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a random NSFW video from RapidAPI."""
        if not self.rapidapi_key:
            logger.warning("RapidAPI key not configured for NSFW video service")
            return await self._get_fallback_video(category)
        
        try:
            headers = {
                "X-RapidAPI-Key": self.rapidapi_key,
                "X-RapidAPI-Host": "quality-porn.p.rapidapi.com"
            }
            
            # Use working quality-porn API endpoint
            endpoints = [
                "https://quality-porn.p.rapidapi.com/search"
            ]
            
            url = endpoints[0]  # Use the single working endpoint
            params = {"query": category or "hot"}  # quality-porn API expects 'query' parameter
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, 
                    headers=headers, 
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.base_timeout)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        # Handle quality-porn API response format
                        if isinstance(data, dict) and 'data' in data:
                            videos = data.get('data', [])
                            if isinstance(videos, list) and videos:
                                video = random.choice(videos)  # Pick random video from results
                                
                                video_url = (
                                    video.get('video_url') or 
                                    video.get('url') or 
                                    video.get('link') or 
                                    video.get('video') or
                                    video.get('embed_url')
                                )
                                
                                if video_url:
                                    return {
                                        'url': video_url,
                                        'title': video.get('title', 'Random Video'),
                                        'category': video.get('category', category or 'general'),
                                        'duration': video.get('duration'),
                                        'thumbnail': video.get('thumbnail') or video.get('image'),
                                        'source': 'RapidAPI Quality Porn',
                                        'fetched_at': datetime.utcnow().isoformat()
                                    }
                    elif response.status == 403:
                        logger.error(f"NSFW video API authentication failed (403). RapidAPI key may not be subscribed to quality-porn.p.rapidapi.com endpoint")
                        return await self._get_fallback_video(category)
                    else:
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
            return await self._get_fallback_image(category)
        
        try:
            headers = {
                "x-rapidapi-key": self.rapidapi_key,
                "x-rapidapi-host": "girls-nude-image.p.rapidapi.com"
            }
            
            # Map categories to available types on the working API
            category_mapping = {
                'amateur': 'boobs',
                'anal': 'ass', 
                'asian': 'boobs',
                'babe': 'boobs',
                'bbw': 'boobs',
                'big-ass': 'ass',
                'big-tits': 'boobs',
                'blonde': 'boobs',
                'blowjob': 'boobs',
                'brunette': 'boobs',
                'creampie': 'boobs',
                'cumshot': 'boobs',
                'fetish': 'boobs',
                'hardcore': 'boobs',
                'latina': 'boobs',
                'lesbian': 'boobs',
                'milf': 'boobs',
                'pornstar': 'boobs',
                'redhead': 'boobs',
                'teen': 'boobs',
                'threesome': 'boobs',
                'vintage': 'boobs',
                'boobs': 'boobs',
                'ass': 'ass'
            }
            
            # Use the mapped category or default to 'boobs'
            api_category = category_mapping.get(category.lower(), 'boobs')
            
            # Try the working endpoint
            endpoints = [
                "https://girls-nude-image.p.rapidapi.com/"
            ]
            
            for url in endpoints:
                try:
                    params = {"type": api_category}
                    
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            url, 
                            headers=headers,
                            params=params,
                            timeout=aiohttp.ClientTimeout(total=self.base_timeout)
                        ) as response:
                            
                            if response.status == 200:
                                data = await response.json()
                                
                                # Handle the response from girls-nude-image API
                                if isinstance(data, dict):
                                    image_url = (
                                        data.get('url') or 
                                        data.get('image_url') or 
                                        data.get('link') or 
                                        data.get('image')
                                    )
                                    
                                    if image_url:
                                        return {
                                            'url': image_url,
                                            'category': category,
                                            'title': data.get('title', f'{category.title()} Image'),
                                            'source': 'RapidAPI Girls Nude Image',
                                            'fetched_at': datetime.utcnow().isoformat(),
                                            'width': data.get('width'),
                                            'height': data.get('height')
                                        }
                            elif response.status == 403:
                                logger.error(f"NSFW image API authentication failed (403) for category '{category}'. RapidAPI key may not be subscribed to girls-nude-image.p.rapidapi.com endpoint")
                                break  # No point trying other endpoints with same auth issue
                            else:
                                logger.warning(f"NSFW image API returned status {response.status} for category '{category}'")
                            
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
    
    async def verify_api_access(self) -> Dict[str, bool]:
        """Verify API access for different endpoints."""
        if not self.rapidapi_key:
            return {"video_api": False, "image_api": False, "reason": "No API key configured"}
        
        results = {"video_api": False, "image_api": False}
        
        # Test video API (quality-porn)
        try:
            headers = {
                "X-RapidAPI-Key": self.rapidapi_key,
                "X-RapidAPI-Host": "quality-porn.p.rapidapi.com"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://quality-porn.p.rapidapi.com/search",
                    headers=headers,
                    params={"query": "test"},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    results["video_api"] = response.status == 200
                    if response.status == 403:
                        results["video_api_error"] = "Authentication failed - API key may not be subscribed to quality-porn.p.rapidapi.com"
        except Exception as e:
            results["video_api_error"] = str(e)
        
        # Test image API (girls-nude-image)
        try:
            headers = {
                "x-rapidapi-key": self.rapidapi_key,
                "x-rapidapi-host": "girls-nude-image.p.rapidapi.com"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://girls-nude-image.p.rapidapi.com/",
                    headers=headers,
                    params={"type": "boobs"},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    results["image_api"] = response.status == 200
                    if response.status == 403:
                        results["image_api_error"] = "Authentication failed - API key may not be subscribed to girls-nude-image.p.rapidapi.com"
        except Exception as e:
            results["image_api_error"] = str(e)
        
        logger.info(f"API access verification completed: {results}")
        return results


# Global service instance
nsfw_service = NsfwService()