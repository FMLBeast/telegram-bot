"""OpenAI service for AI-powered features."""

import openai
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from ..core.config import settings
from ..core.logging import LoggerMixin
from ..core.exceptions import APIError


class OpenAIService(LoggerMixin):
    """Service for interacting with OpenAI API."""
    
    def __init__(self) -> None:
        """Initialize the OpenAI service."""
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.conversation_history: Dict[int, List[Dict[str, str]]] = {}
        self.max_history_length = 10
        self.logger.info("OpenAI service initialized")
    
    async def generate_response(
        self,
        message: str,
        user_id: int,
        username: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate an AI response to a user message."""
        
        try:
            # Get or initialize conversation history
            history = self.conversation_history.get(user_id, [])
            
            # Build messages for the API
            messages = []
            
            # Add system prompt
            if not system_prompt:
                system_prompt = (
                    f"You are a helpful, friendly, and knowledgeable AI assistant in a Telegram bot. "
                    f"The user's name is {username}. Be conversational, engaging, and helpful. "
                    f"Keep responses concise but informative. Use emojis appropriately to make "
                    f"conversations more engaging. Current date: {datetime.now().strftime('%Y-%m-%d')}"
                )
            
            messages.append({"role": "system", "content": system_prompt})
            
            # Add conversation history
            messages.extend(history)
            
            # Add current user message
            messages.append({"role": "user", "content": message})
            
            self.logger.info(
                "Generating AI response",
                user_id=user_id,
                username=username,
                message_length=len(message),
                history_length=len(history)
            )
            
            # Make API request
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                max_tokens=1000,
                temperature=0.8,
                presence_penalty=0.6,
                frequency_penalty=0.3,
            )
            
            ai_response = response.choices[0].message.content
            
            if not ai_response:
                raise APIError("Empty response from OpenAI API")
            
            # Update conversation history
            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": ai_response})
            
            # Trim history if too long
            if len(history) > self.max_history_length * 2:
                history = history[-self.max_history_length * 2:]
            
            self.conversation_history[user_id] = history
            
            self.logger.info(
                "AI response generated",
                user_id=user_id,
                response_length=len(ai_response),
                tokens_used=response.usage.total_tokens if response.usage else None
            )
            
            return ai_response
            
        except openai.RateLimitError as e:
            self.logger.error("OpenAI rate limit exceeded", user_id=user_id, error=str(e))
            return "🚫 I'm currently experiencing high demand. Please try again in a moment!"
            
        except openai.AuthenticationError as e:
            self.logger.error("OpenAI authentication error", error=str(e))
            return "🔐 Authentication error. Please contact the bot administrator."
            
        except openai.APIConnectionError as e:
            self.logger.error("OpenAI connection error", error=str(e))
            return "🌐 Connection issue with AI service. Please try again later."
            
        except Exception as e:
            self.logger.error(
                "Error generating AI response",
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            return "🤖 Sorry, I encountered an error while processing your message. Please try again!"
    
    async def generate_image(
        self,
        prompt: str,
        user_id: int,
        size: str = "1024x1024",
        quality: str = "standard"
    ) -> Optional[str]:
        """Generate an image from a text prompt."""
        
        try:
            self.logger.info(
                "Generating image",
                user_id=user_id,
                prompt_length=len(prompt),
                size=size,
                quality=quality
            )
            
            response = await self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality=quality,
                n=1,
            )
            
            image_url = response.data[0].url
            
            self.logger.info(
                "Image generated successfully",
                user_id=user_id,
                image_url=image_url
            )
            
            return image_url
            
        except openai.RateLimitError as e:
            self.logger.error("OpenAI rate limit exceeded for image generation", user_id=user_id, error=str(e))
            raise APIError("Rate limit exceeded for image generation")
            
        except Exception as e:
            self.logger.error(
                "Error generating image",
                user_id=user_id,
                error=str(e),
                exc_info=True
            )
            raise APIError(f"Image generation failed: {str(e)}")
    
    def clear_conversation_history(self, user_id: int) -> None:
        """Clear conversation history for a user."""
        if user_id in self.conversation_history:
            del self.conversation_history[user_id]
            self.logger.info("Conversation history cleared", user_id=user_id)
    
    def get_conversation_length(self, user_id: int) -> int:
        """Get the length of conversation history for a user."""
        return len(self.conversation_history.get(user_id, []))
    
    async def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze the sentiment of text."""
        
        try:
            messages = [
                {
                    "role": "system",
                    "content": (
                        "Analyze the sentiment of the following text. "
                        "Respond with a JSON object containing 'sentiment' (positive/negative/neutral), "
                        "'confidence' (0.0-1.0), and 'explanation' (brief explanation)."
                    )
                },
                {"role": "user", "content": text}
            ]
            
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=200,
                temperature=0.3,
            )
            
            result = response.choices[0].message.content
            
            # Parse JSON response (simplified - in production, use proper JSON parsing)
            import json
            try:
                sentiment_data = json.loads(result)
                return sentiment_data
            except json.JSONDecodeError:
                return {
                    "sentiment": "neutral",
                    "confidence": 0.5,
                    "explanation": "Unable to analyze sentiment"
                }
                
        except Exception as e:
            self.logger.error("Error analyzing sentiment", error=str(e), exc_info=True)
            return {
                "sentiment": "neutral",
                "confidence": 0.0,
                "explanation": f"Analysis error: {str(e)}"
            }