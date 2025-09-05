# casino_db.py

from typing import Dict, List, Optional
import sqlite3
import json
import logging
import os

logger = logging.getLogger(__name__)

class CasinoDBManager:
    def __init__(self, db_conn: sqlite3.Connection):
        self.db_conn = db_conn

    def add_casino(self, name: str, description: str = None, website: str = None) -> Optional[int]:
        """Add a new casino to the database."""
        try:
            with self.db_conn:
                cursor = self.db_conn.cursor()
                cursor.execute('''
                    INSERT INTO casinos (name, description, website)
                    VALUES (?, ?, ?)
                ''', (name, description, website))
                casino_id = cursor.lastrowid
                logger.info(f"Added casino '{name}' with ID {casino_id}.")
                return casino_id
        except sqlite3.IntegrityError:
            logger.error(f"Casino '{name}' already exists.")
            return None
        except Exception as e:
            logger.error(f"Error adding casino '{name}': {e}")
            return None

    def add_casino_tier(self, casino_id: int, tier_name: str, level_range: str) -> Optional[int]:
        """Add a new tier to a casino."""
        try:
            with self.db_conn:
                cursor = self.db_conn.cursor()
                cursor.execute('''
                    INSERT INTO casino_tiers (casino_id, name, level_range)
                    VALUES (?, ?, ?)
                ''', (casino_id, tier_name, level_range))
                tier_id = cursor.lastrowid
                logger.info(f"Added tier '{tier_name}' with ID {tier_id} to casino ID {casino_id}.")
                return tier_id
        except sqlite3.IntegrityError:
            logger.error(f"Tier '{tier_name}' already exists for casino ID {casino_id}.")
            return None
        except Exception as e:
            logger.error(f"Error adding tier '{tier_name}' to casino ID {casino_id}: {e}")
            return None

    def add_casino_level(self, tier_id: int, level_name: str, bonus_amount: float, xp_requirement: int) -> None:
        """Add a level to a casino tier."""
        try:
            with self.db_conn:
                cursor = self.db_conn.cursor()
                cursor.execute('''
                    INSERT INTO casino_levels (tier_id, level_name, bonus_amount, xp_requirement)
                    VALUES (?, ?, ?, ?)
                ''', (tier_id, level_name, bonus_amount, xp_requirement))
                logger.info(f"Added level '{level_name}' to tier ID {tier_id}.")
        except sqlite3.IntegrityError:
            logger.error(f"Level '{level_name}' already exists for tier ID {tier_id}.")
        except Exception as e:
            logger.error(f"Error adding level '{level_name}' to tier ID {tier_id}: {e}")

    def add_casino_feature(self, casino_id: int, feature_name: str, description: str, requirements: str = None, calculation_formula: str = None) -> None:
        """Add a feature to a casino."""
        try:
            with self.db_conn:
                cursor = self.db_conn.cursor()
                cursor.execute('''
                    INSERT INTO casino_features (casino_id, name, description, requirements, calculation_formula)
                    VALUES (?, ?, ?, ?, ?)
                ''', (casino_id, feature_name, description, requirements, calculation_formula))
                logger.info(f"Added feature '{feature_name}' to casino ID {casino_id}.")
        except sqlite3.IntegrityError:
            logger.error(f"Feature '{feature_name}' already exists for casino ID {casino_id}.")
        except Exception as e:
            logger.error(f"Error adding feature '{feature_name}' to casino ID {casino_id}: {e}")

    def add_casino_general_info(self, casino_id: int, info_key: str, info_value: str) -> None:
        """Add general information to a casino."""
        try:
            with self.db_conn:
                cursor = self.db_conn.cursor()
                cursor.execute('''
                    INSERT INTO casino_general_info (casino_id, info_key, info_value)
                    VALUES (?, ?, ?)
                ''', (casino_id, info_key, info_value))
                logger.info(f"Added general info '{info_key}' to casino ID {casino_id}.")
        except sqlite3.IntegrityError:
            logger.error(f"General info '{info_key}' already exists for casino ID {casino_id}.")
        except Exception as e:
            logger.error(f"Error adding general info '{info_key}' to casino ID {casino_id}: {e}")

    def get_casino_data(self, casino_name: str) -> Optional[Dict]:
        """Retrieve complete data for a casino."""
        try:
            with self.db_conn:
                cursor = self.db_conn.cursor()
                cursor.execute('SELECT * FROM casinos WHERE name = ?', (casino_name,))
                casino = cursor.fetchone()
                if not casino:
                    logger.warning(f"Casino '{casino_name}' not found.")
                    return None

                casino_id = casino[0]
                data = {
                    'id': casino_id,
                    'name': casino[1],
                    'description': casino[2],
                    'website': casino[3],
                    'created_at': casino[4],
                    'updated_at': casino[5],
                    'tiers': self._get_casino_tiers(casino_id),
                    'features': self._get_casino_features(casino_id),
                    'general_information': self._get_casino_general_info(casino_id)
                }
                return data
        except Exception as e:
            logger.error(f"Error retrieving data for casino '{casino_name}': {e}")
            return None

    def _get_casino_tiers(self, casino_id: int) -> List[Dict]:
        """Retrieve all tiers for a casino."""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('SELECT id, name, level_range FROM casino_tiers WHERE casino_id = ?', (casino_id,))
            tiers = []
            for tier in cursor.fetchall():
                tier_id, name, level_range = tier
                tiers.append({
                    'id': tier_id,
                    'name': name,
                    'level_range': level_range,
                    'levels': self._get_casino_levels(tier_id)
                })
            return tiers
        except Exception as e:
            logger.error(f"Error retrieving tiers for casino ID {casino_id}: {e}")
            return []

    def _get_casino_levels(self, tier_id: int) -> List[Dict]:
        """Retrieve all levels for a casino tier."""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('SELECT level_name, bonus_amount, xp_requirement FROM casino_levels WHERE tier_id = ?', (tier_id,))
            levels = []
            for level in cursor.fetchall():
                level_name, bonus_amount, xp_requirement = level
                levels.append({
                    'level_name': level_name,
                    'bonus_amount': bonus_amount,
                    'xp_requirement': xp_requirement
                })
            return levels
        except Exception as e:
            logger.error(f"Error retrieving levels for tier ID {tier_id}: {e}")
            return []

    def _get_casino_features(self, casino_id: int) -> List[Dict]:
        """Retrieve all features for a casino."""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('SELECT name, description, requirements, calculation_formula FROM casino_features WHERE casino_id = ?', (casino_id,))
            features = []
            for feature in cursor.fetchall():
                name, description, requirements, calculation_formula = feature
                features.append({
                    'name': name,
                    'description': description,
                    'requirements': requirements,
                    'calculation_formula': calculation_formula
                })
            return features
        except Exception as e:
            logger.error(f"Error retrieving features for casino ID {casino_id}: {e}")
            return []

    def _get_casino_general_info(self, casino_id: int) -> List[Dict]:
        """Retrieve all general information for a casino."""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('SELECT info_key, info_value FROM casino_general_info WHERE casino_id = ?', (casino_id,))
            general_info = []
            for info in cursor.fetchall():
                key, value = info
                general_info.append({
                    'key': key,
                    'value': value
                })
            return general_info
        except Exception as e:
            logger.error(f"Error retrieving general information for casino ID {casino_id}: {e}")
            return []

    def get_all_casinos(self) -> List[Dict]:
        """Retrieve basic information for all casinos."""
        try:
            with self.db_conn:
                cursor = self.db_conn.cursor()
                cursor.execute('SELECT id, name, description FROM casinos')
                casinos = [
                    {'id': row[0], 'name': row[1], 'description': row[2]}
                    for row in cursor.fetchall()
                ]
                return casinos
        except Exception as e:
            logger.error(f"Error retrieving all casinos: {e}")
            return []

    def search_casino_features(self, search_term: str) -> List[Dict]:
        """Search for casino features by name or description."""
        try:
            with self.db_conn:
                cursor = self.db_conn.cursor()
                like_term = f'%{search_term}%'
                cursor.execute('''
                    SELECT c.name, f.name, f.description, f.requirements
                    FROM casino_features f
                    JOIN casinos c ON c.id = f.casino_id
                    WHERE f.name LIKE ? OR f.description LIKE ?
                ''', (like_term, like_term))
                results = [
                    {
                        'casino': row[0],
                        'feature': row[1],
                        'description': row[2],
                        'requirements': row[3]
                    }
                    for row in cursor.fetchall()
                ]
                return results
        except Exception as e:
            logger.error(f"Error searching casino features with term '{search_term}': {e}")
            return []

    def calculate_bonus(self, casino_name: str, level: str, wager: float) -> Optional[Dict]:
        """Calculate bonus based on casino features and wager."""
        try:
            with self.db_conn:
                cursor = self.db_conn.cursor()
                cursor.execute('''
                    SELECT f.name, f.calculation_formula
                    FROM casino_features f
                    JOIN casinos c ON c.id = f.casino_id
                    WHERE c.name = ? AND f.calculation_formula IS NOT NULL
                ''', (casino_name,))
                features = cursor.fetchall()
                if not features:
                    logger.warning(f"No bonus features found for casino '{casino_name}'.")
                    return None

                calculations = {}
                for feature_name, formula in features:
                    try:
                        # Replace placeholders with actual values
                        calculated_value = eval(formula.replace('wager', str(wager)))
                        calculations[feature_name] = calculated_value
                        logger.info(f"Calculated bonus for feature '{feature_name}': {calculated_value}")
                    except Exception as e:
                        logger.error(f"Error calculating bonus for feature '{feature_name}': {e}")
                        calculations[feature_name] = None

                return calculations
        except Exception as e:
            logger.error(f"Error calculating bonuses for casino '{casino_name}': {e}")
            return None

    def load_casino_data_from_json(self, json_file_path: str) -> None:
        """Load and insert casino data from a JSON file into the database."""
        if not os.path.exists(json_file_path):
            logger.error(f"JSON file '{json_file_path}' does not exist.")
            return

        try:
            with open(json_file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                casinos = data.get('casinos', [])
                for casino in casinos:
                    name = casino.get('name')
                    description = casino.get('description')
                    website = casino.get('website')
                    
                    casino_id = self.add_casino(name, description, website)
                    if not casino_id:
                        logger.warning(f"Skipping casino '{name}' due to previous errors.")
                        continue

                    # Add Tiers and Levels
                    tiers = casino.get('tiers', [])
                    for tier in tiers:
                        tier_name = tier.get('name')
                        level_range = tier.get('level_range')
                        tier_id = self.add_casino_tier(casino_id, tier_name, level_range)
                        if not tier_id:
                            logger.warning(f"Skipping tier '{tier_name}' for casino '{name}'.")
                            continue

                        levels = tier.get('levels', [])
                        for level in levels:
                            level_name = level.get('level_name')
                            bonus_amount = level.get('bonus_amount')
                            xp_requirement = level.get('xp_requirement')
                            self.add_casino_level(tier_id, level_name, bonus_amount, xp_requirement)

                    # Add Features
                    features = casino.get('features', [])
                    for feature in features:
                        feature_name = feature.get('name')
                        description = feature.get('description')
                        requirements = feature.get('requirements')
                        calculation_formula = feature.get('calculation_formula')
                        self.add_casino_feature(casino_id, feature_name, description, requirements, calculation_formula)

                    # Add General Information
                    general_info = casino.get('general_information', [])
                    for info in general_info:
                        info_key = info.get('key')
                        info_value = info.get('value')
                        self.add_casino_general_info(casino_id, info_key, info_value)

                logger.info("Casino data loaded successfully from JSON.")
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON file '{json_file_path}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error while loading casino data from JSON: {e}")
