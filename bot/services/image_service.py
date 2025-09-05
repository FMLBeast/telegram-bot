"""Image generation and management service."""

import os
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from PIL import Image
import aiohttp
import base64
from io import BytesIO
from pathlib import Path

from ..core.config import settings
from ..core.logging import LoggerMixin
from ..core.database import db_manager, Base
from ..core.exceptions import APIError, DatabaseError
from ..services.openai_service import OpenAIService
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship


class ImageRequest(Base):
    """Image generation requests model."""
    
    __tablename__ = "image_requests"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    prompt = Column(Text, nullable=False)
    model = Column(String(50), default="dall-e-3")
    size = Column(String(20), default="1024x1024")
    quality = Column(String(20), default="standard")
    style = Column(String(20), nullable=True)
    image_url = Column(Text, nullable=True)
    revised_prompt = Column(Text, nullable=True)
    file_path = Column(String(500), nullable=True)
    is_favorite = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ImageCollection(Base):
    """Image collections model."""
    
    __tablename__ = "image_collections"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=True)  # None for group collections
    chat_id = Column(Integer, nullable=True)  # Group chat ID for group collections
    image_id = Column(Integer, ForeignKey("image_requests.id"), nullable=False)
    collection_name = Column(String(100), default="default")
    added_at = Column(DateTime, default=datetime.utcnow)


class ImageService(LoggerMixin):
    """Service for handling image generation and management."""
    
    def __init__(self) -> None:
        """Initialize the image service."""
        self.openai_service = OpenAIService()
        self.daily_limit = 25
        self.images_dir = Path("data/images")
        self.images_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("Image service initialized")
    
    async def check_daily_limit(self, user_id: int) -> bool:
        """Check if user has reached daily image generation limit."""
        try:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            async with db_manager.get_session() as session:
                from sqlalchemy import select, func
                
                stmt = (
                    select(func.count(ImageRequest.id))
                    .where(
                        ImageRequest.user_id == user_id,
                        ImageRequest.created_at >= today_start
                    )
                )
                result = await session.execute(stmt)
                count = result.scalar() or 0
                
                return count < self.daily_limit
                
        except Exception as e:
            self.logger.error("Error checking daily limit", user_id=user_id, error=str(e), exc_info=True)
            return False
    
    async def generate_image(
        self,
        user_id: int,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
        style: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Generate an image using DALL-E."""
        
        try:
            # Check daily limit
            if not await self.check_daily_limit(user_id):
                raise APIError("Daily image generation limit reached (25/day)")
            
            # Generate image
            image_url = await self.openai_service.generate_image(
                prompt=prompt,
                user_id=user_id,
                size=size,
                quality=quality
            )
            
            if not image_url:
                raise APIError("Failed to generate image")
            
            # Download and save image
            file_path = await self._download_and_save_image(image_url, user_id)
            
            # Save to database
            async with db_manager.get_session() as session:
                image_request = ImageRequest(
                    user_id=user_id,
                    prompt=prompt,
                    size=size,
                    quality=quality,
                    style=style,
                    image_url=image_url,
                    file_path=str(file_path) if file_path else None,
                )
                session.add(image_request)
                await session.flush()
                
                image_id = image_request.id
            
            self.logger.info(
                "Image generated successfully",
                user_id=user_id,
                image_id=image_id,
                prompt_length=len(prompt),
                file_path=file_path
            )
            
            return {
                "id": image_id,
                "url": image_url,
                "file_path": str(file_path) if file_path else None,
                "prompt": prompt,
                "size": size,
                "quality": quality,
                "style": style,
            }
            
        except Exception as e:
            self.logger.error("Error generating image", user_id=user_id, error=str(e), exc_info=True)
            raise
    
    async def generate_multiple_images(
        self,
        user_id: int,
        prompt: str,
        count: int = 2,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Generate multiple images concurrently."""
        
        if count > 4:
            raise APIError("Cannot generate more than 4 images at once")
        
        # Check if user has enough daily quota
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        async with db_manager.get_session() as session:
            from sqlalchemy import select, func
            
            stmt = (
                select(func.count(ImageRequest.id))
                .where(
                    ImageRequest.user_id == user_id,
                    ImageRequest.created_at >= today_start
                )
            )
            result = await session.execute(stmt)
            used_today = result.scalar() or 0
        
        if used_today + count > self.daily_limit:
            raise APIError(f"Not enough daily quota. Used: {used_today}/25, Requested: {count}")
        
        # Generate images concurrently
        tasks = []
        for i in range(count):
            task = self.generate_image(user_id, f"{prompt} (variation {i+1})", **kwargs)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and return successful results
        successful_results = []
        for result in results:
            if isinstance(result, Exception):
                self.logger.error("Error in batch generation", error=str(result))
            else:
                successful_results.append(result)
        
        return successful_results
    
    async def _download_and_save_image(self, image_url: str, user_id: int) -> Optional[Path]:
        """Download image from URL and save to local storage."""
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        self.logger.error("Failed to download image", status=response.status)
                        return None
                    
                    image_data = await response.read()
            
            # Create filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{user_id}_{timestamp}.png"
            file_path = self.images_dir / filename
            
            # Save image
            with open(file_path, "wb") as f:
                f.write(image_data)
            
            self.logger.info("Image saved", file_path=str(file_path), size=len(image_data))
            
            return file_path
            
        except Exception as e:
            self.logger.error("Error downloading image", error=str(e), exc_info=True)
            return None
    
    async def set_favorite(self, user_id: int, image_id: int, is_favorite: bool = True) -> bool:
        """Set an image as favorite or unfavorite."""
        
        try:
            async with db_manager.get_session() as session:
                from sqlalchemy import update
                
                stmt = (
                    update(ImageRequest)
                    .where(
                        ImageRequest.id == image_id,
                        ImageRequest.user_id == user_id
                    )
                    .values(is_favorite=is_favorite)
                )
                result = await session.execute(stmt)
                
                success = result.rowcount > 0
                
                self.logger.info(
                    "Image favorite status updated",
                    user_id=user_id,
                    image_id=image_id,
                    is_favorite=is_favorite,
                    success=success
                )
                
                return success
                
        except Exception as e:
            self.logger.error("Error setting favorite", user_id=user_id, image_id=image_id, error=str(e), exc_info=True)
            return False
    
    async def add_to_collection(
        self,
        user_id: int,
        image_id: int,
        collection_name: str = "default",
        chat_id: Optional[int] = None
    ) -> bool:
        """Add image to a collection."""
        
        try:
            async with db_manager.get_session() as session:
                collection_item = ImageCollection(
                    user_id=user_id if chat_id is None else None,
                    chat_id=chat_id,
                    image_id=image_id,
                    collection_name=collection_name,
                )
                session.add(collection_item)
                await session.flush()
                
                self.logger.info(
                    "Image added to collection",
                    user_id=user_id,
                    image_id=image_id,
                    collection_name=collection_name,
                    chat_id=chat_id
                )
                
                return True
                
        except Exception as e:
            self.logger.error("Error adding to collection", user_id=user_id, image_id=image_id, error=str(e), exc_info=True)
            return False
    
    async def get_user_images(
        self,
        user_id: int,
        favorites_only: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get user's generated images."""
        
        try:
            async with db_manager.get_session() as session:
                from sqlalchemy import select
                
                stmt = (
                    select(ImageRequest)
                    .where(ImageRequest.user_id == user_id)
                    .order_by(ImageRequest.created_at.desc())
                    .limit(limit)
                )
                
                if favorites_only:
                    stmt = stmt.where(ImageRequest.is_favorite == True)
                
                result = await session.execute(stmt)
                images = result.scalars().all()
                
                return [
                    {
                        "id": img.id,
                        "prompt": img.prompt,
                        "url": img.image_url,
                        "file_path": img.file_path,
                        "is_favorite": img.is_favorite,
                        "created_at": img.created_at.isoformat() if img.created_at else None,
                        "size": img.size,
                        "quality": img.quality,
                    }
                    for img in images
                ]
                
        except Exception as e:
            self.logger.error("Error getting user images", user_id=user_id, error=str(e), exc_info=True)
            return []
    
    async def get_collection_images(
        self,
        user_id: Optional[int] = None,
        chat_id: Optional[int] = None,
        collection_name: str = "default"
    ) -> List[Dict[str, Any]]:
        """Get images from a collection."""
        
        try:
            async with db_manager.get_session() as session:
                from sqlalchemy import select
                
                stmt = (
                    select(ImageRequest, ImageCollection)
                    .join(ImageCollection, ImageRequest.id == ImageCollection.image_id)
                    .where(ImageCollection.collection_name == collection_name)
                    .order_by(ImageCollection.added_at.desc())
                )
                
                if user_id is not None:
                    stmt = stmt.where(ImageCollection.user_id == user_id)
                if chat_id is not None:
                    stmt = stmt.where(ImageCollection.chat_id == chat_id)
                
                result = await session.execute(stmt)
                rows = result.all()
                
                return [
                    {
                        "id": img.id,
                        "prompt": img.prompt,
                        "url": img.image_url,
                        "file_path": img.file_path,
                        "is_favorite": img.is_favorite,
                        "created_at": img.created_at.isoformat() if img.created_at else None,
                        "added_to_collection": collection.added_at.isoformat() if collection.added_at else None,
                    }
                    for img, collection in rows
                ]
                
        except Exception as e:
            self.logger.error("Error getting collection images", user_id=user_id, chat_id=chat_id, error=str(e), exc_info=True)
            return []
    
    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user's image generation statistics."""
        
        try:
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            async with db_manager.get_session() as session:
                from sqlalchemy import select, func
                
                # Total images
                total_stmt = select(func.count(ImageRequest.id)).where(ImageRequest.user_id == user_id)
                total_result = await session.execute(total_stmt)
                total_images = total_result.scalar() or 0
                
                # Today's images
                today_stmt = (
                    select(func.count(ImageRequest.id))
                    .where(
                        ImageRequest.user_id == user_id,
                        ImageRequest.created_at >= today_start
                    )
                )
                today_result = await session.execute(today_stmt)
                today_images = today_result.scalar() or 0
                
                # Favorites
                favorites_stmt = (
                    select(func.count(ImageRequest.id))
                    .where(
                        ImageRequest.user_id == user_id,
                        ImageRequest.is_favorite == True
                    )
                )
                favorites_result = await session.execute(favorites_stmt)
                favorites_count = favorites_result.scalar() or 0
                
                return {
                    "total_images": total_images,
                    "today_images": today_images,
                    "daily_limit": self.daily_limit,
                    "remaining_today": max(0, self.daily_limit - today_images),
                    "favorites_count": favorites_count,
                }
                
        except Exception as e:
            self.logger.error("Error getting user stats", user_id=user_id, error=str(e), exc_info=True)
            return {
                "total_images": 0,
                "today_images": 0,
                "daily_limit": self.daily_limit,
                "remaining_today": self.daily_limit,
                "favorites_count": 0,
            }


# Global image service instance
image_service = ImageService()