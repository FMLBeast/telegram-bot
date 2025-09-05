"""Synonym management service."""

import random
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from sqlalchemy import select, and_, func, desc

from ..core.database import db_manager
from ..core.database import User
from ..core.logging import get_logger

logger = get_logger(__name__)


class SynonymService:
    """Service for managing word synonyms and daily features."""
    
    def __init__(self):
        """Initialize the synonym service."""
        self.synonyms_db = {}  # Will load from database/file
        logger.info("Synonym service initialized")
    
    async def add_synonym(
        self,
        word: str,
        synonym: str,
        user_id: int,
        chat_id: int
    ) -> Dict[str, Any]:
        """Add a new synonym to the database."""
        try:
            word = word.lower().strip()
            synonym = synonym.lower().strip()
            
            if not word or not synonym:
                return {
                    'success': False,
                    'message': 'Both word and synonym must be provided'
                }
            
            if word == synonym:
                return {
                    'success': False,
                    'message': 'Word and synonym cannot be the same'
                }
            
            # Initialize synonyms for word if not exists
            if word not in self.synonyms_db:
                self.synonyms_db[word] = set()
            
            # Check if synonym already exists
            if synonym in self.synonyms_db[word]:
                return {
                    'success': False,
                    'message': f'"{synonym}" is already a synonym for "{word}"'
                }
            
            # Add synonym
            self.synonyms_db[word].add(synonym)
            
            # Also add reverse mapping
            if synonym not in self.synonyms_db:
                self.synonyms_db[synonym] = set()
            self.synonyms_db[synonym].add(word)
            
            # Save to persistent storage (you could implement file/database storage here)
            await self._save_synonyms()
            
            logger.info("Synonym added", word=word, synonym=synonym, user_id=user_id)
            
            return {
                'success': True,
                'message': f'Added "{synonym}" as a synonym for "{word}"',
                'word': word,
                'synonym': synonym,
                'total_synonyms': len(self.synonyms_db[word])
            }
            
        except Exception as e:
            logger.error("Error adding synonym", word=word, synonym=synonym, error=str(e), exc_info=True)
            return {
                'success': False,
                'message': f'Error adding synonym: {str(e)}'
            }
    
    async def get_synonyms(self, word: str) -> List[str]:
        """Get all synonyms for a word."""
        try:
            word = word.lower().strip()
            if word in self.synonyms_db:
                return list(self.synonyms_db[word])
            return []
        except Exception as e:
            logger.error("Error getting synonyms", word=word, error=str(e))
            return []
    
    async def get_random_synonym(self, word: str) -> Optional[str]:
        """Get a random synonym for a word."""
        try:
            synonyms = await self.get_synonyms(word)
            if synonyms:
                return random.choice(synonyms)
            return None
        except Exception as e:
            logger.error("Error getting random synonym", word=word, error=str(e))
            return None
    
    async def get_synonym_of_the_day(self) -> Dict[str, Any]:
        """Get the synonym of the day."""
        try:
            # Use current date as seed for consistent daily selection
            today = datetime.now().date()
            random.seed(str(today))
            
            if not self.synonyms_db:
                return {
                    'word': 'awesome',
                    'synonyms': ['amazing', 'fantastic', 'incredible', 'wonderful'],
                    'message': 'No custom synonyms available, showing default.'
                }
            
            # Select random word that has synonyms
            available_words = [word for word, syns in self.synonyms_db.items() if syns]
            
            if not available_words:
                return {
                    'word': 'great',
                    'synonyms': ['excellent', 'superb', 'outstanding'],
                    'message': 'No custom synonyms available, showing default.'
                }
            
            selected_word = random.choice(available_words)
            synonyms = list(self.synonyms_db[selected_word])
            
            # Reset random seed
            random.seed()
            
            return {
                'word': selected_word,
                'synonyms': synonyms,
                'count': len(synonyms),
                'date': today.strftime('%Y-%m-%d'),
                'message': f'Today\'s word is "{selected_word}" with {len(synonyms)} synonyms!'
            }
            
        except Exception as e:
            logger.error("Error getting synonym of the day", error=str(e), exc_info=True)
            return {
                'word': 'error',
                'synonyms': ['mistake', 'problem', 'issue'],
                'message': f'Error getting synonym of the day: {str(e)}'
            }
    
    async def search_synonyms(self, query: str) -> Dict[str, Any]:
        """Search for words and their synonyms."""
        try:
            query = query.lower().strip()
            results = {}
            
            for word, synonyms in self.synonyms_db.items():
                if query in word or any(query in syn for syn in synonyms):
                    results[word] = list(synonyms)
            
            return {
                'query': query,
                'results': results,
                'count': len(results),
                'message': f'Found {len(results)} words matching "{query}"'
            }
            
        except Exception as e:
            logger.error("Error searching synonyms", query=query, error=str(e))
            return {
                'query': query,
                'results': {},
                'count': 0,
                'message': f'Error searching: {str(e)}'
            }
    
    async def get_synonym_stats(self) -> Dict[str, Any]:
        """Get statistics about the synonym database."""
        try:
            total_words = len(self.synonyms_db)
            total_synonyms = sum(len(synonyms) for synonyms in self.synonyms_db.values())
            
            if total_words > 0:
                avg_synonyms = total_synonyms / total_words
                
                # Find word with most synonyms
                most_synonyms_word = max(
                    self.synonyms_db.items(), 
                    key=lambda x: len(x[1])
                )
                
                # Find words with least synonyms (but at least 1)
                words_with_synonyms = {k: v for k, v in self.synonyms_db.items() if v}
                least_synonyms_word = min(
                    words_with_synonyms.items(), 
                    key=lambda x: len(x[1])
                ) if words_with_synonyms else None
                
                return {
                    'total_words': total_words,
                    'total_synonyms': total_synonyms,
                    'average_synonyms_per_word': round(avg_synonyms, 2),
                    'most_synonyms': {
                        'word': most_synonyms_word[0],
                        'count': len(most_synonyms_word[1])
                    },
                    'least_synonyms': {
                        'word': least_synonyms_word[0] if least_synonyms_word else None,
                        'count': len(least_synonyms_word[1]) if least_synonyms_word else 0
                    }
                }
            
            return {
                'total_words': 0,
                'total_synonyms': 0,
                'average_synonyms_per_word': 0,
                'most_synonyms': None,
                'least_synonyms': None
            }
            
        except Exception as e:
            logger.error("Error getting synonym stats", error=str(e), exc_info=True)
            return {
                'error': str(e),
                'total_words': 0,
                'total_synonyms': 0
            }
    
    async def remove_synonym(
        self,
        word: str,
        synonym: str,
        user_id: int
    ) -> Dict[str, Any]:
        """Remove a synonym from the database."""
        try:
            word = word.lower().strip()
            synonym = synonym.lower().strip()
            
            if word not in self.synonyms_db or synonym not in self.synonyms_db[word]:
                return {
                    'success': False,
                    'message': f'"{synonym}" is not a synonym for "{word}"'
                }
            
            # Remove synonym
            self.synonyms_db[word].discard(synonym)
            
            # Remove reverse mapping
            if synonym in self.synonyms_db:
                self.synonyms_db[synonym].discard(word)
                
                # Clean up empty sets
                if not self.synonyms_db[synonym]:
                    del self.synonyms_db[synonym]
            
            # Clean up empty sets
            if not self.synonyms_db[word]:
                del self.synonyms_db[word]
            
            # Save changes
            await self._save_synonyms()
            
            logger.info("Synonym removed", word=word, synonym=synonym, user_id=user_id)
            
            return {
                'success': True,
                'message': f'Removed "{synonym}" as a synonym for "{word}"',
                'word': word,
                'synonym': synonym
            }
            
        except Exception as e:
            logger.error("Error removing synonym", word=word, synonym=synonym, error=str(e))
            return {
                'success': False,
                'message': f'Error removing synonym: {str(e)}'
            }
    
    async def _save_synonyms(self) -> None:
        """Save synonyms to persistent storage."""
        try:
            # Convert sets to lists for JSON serialization
            import json
            import os
            
            synonyms_data = {
                word: list(synonyms) for word, synonyms in self.synonyms_db.items()
            }
            
            # Save to data directory
            os.makedirs('data', exist_ok=True)
            with open('data/synonyms.json', 'w') as f:
                json.dump(synonyms_data, f, indent=2)
            
            logger.debug("Synonyms saved to file")
            
        except Exception as e:
            logger.error("Error saving synonyms", error=str(e))
    
    async def _load_synonyms(self) -> None:
        """Load synonyms from persistent storage."""
        try:
            import json
            import os
            
            if os.path.exists('data/synonyms.json'):
                with open('data/synonyms.json', 'r') as f:
                    synonyms_data = json.load(f)
                
                # Convert lists back to sets
                self.synonyms_db = {
                    word: set(synonyms) for word, synonyms in synonyms_data.items()
                }
                
                logger.info("Synonyms loaded from file", count=len(self.synonyms_db))
            else:
                # Initialize with some default synonyms
                self.synonyms_db = {
                    'happy': {'joyful', 'cheerful', 'glad', 'pleased', 'content'},
                    'sad': {'unhappy', 'depressed', 'melancholy', 'downhearted'},
                    'big': {'large', 'huge', 'enormous', 'massive', 'gigantic'},
                    'small': {'tiny', 'little', 'miniature', 'petite', 'microscopic'},
                    'good': {'excellent', 'great', 'wonderful', 'fantastic', 'superb'},
                    'bad': {'terrible', 'awful', 'horrible', 'dreadful', 'atrocious'}
                }
                await self._save_synonyms()
                logger.info("Default synonyms initialized", count=len(self.synonyms_db))
                
        except Exception as e:
            logger.error("Error loading synonyms", error=str(e))
            self.synonyms_db = {}
    
    async def initialize(self) -> None:
        """Initialize the synonym service by loading data."""
        await self._load_synonyms()


# Global service instance
synonym_service = SynonymService()