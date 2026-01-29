# database.py
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class FootballDatabase:
    def __init__(self, db_path="football_data.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialiser la base de données"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Table des matches
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id TEXT UNIQUE,
            championship TEXT,
            date TEXT,
            home_team TEXT,
            away_team TEXT,
            home_score INTEGER,
            away_score INTEGER,
            status TEXT,
            matchday INTEGER,
            venue TEXT,
            referee TEXT,
            raw_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Table des classements
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS standings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            championship TEXT,
            season TEXT,
            position INTEGER,
            team TEXT,
            team_id INTEGER,
            played_games INTEGER,
            won INTEGER,
            draw INTEGER,
            lost INTEGER,
            points INTEGER,
            goals_for INTEGER,
            goals_against INTEGER,
            goal_difference INTEGER,
            raw_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(championship, season, team_id)
        )
        ''')

        # Table des statistiques d'équipe
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS team_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            championship TEXT,
            team TEXT,
            team_id INTEGER,
            matches_played INTEGER,
            wins INTEGER,
            draws INTEGER,
            losses INTEGER,
            goals_for INTEGER,
            goals_against INTEGER,
            points INTEGER,
            avg_possession REAL,
            avg_shots REAL,
            pass_accuracy REAL,
            raw_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(championship, team_id)
        )
        ''')

        # Table des journées scrapées
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS scraping_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            championship TEXT,
            date_from TEXT,
            date_to TEXT,
            matches_count INTEGER,
            status TEXT,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Index pour optimiser les requêtes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_matches_championship ON matches(championship)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_matches_team ON matches(home_team, away_team)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_standings_championship ON standings(championship)')

        conn.commit()
        conn.close()

        logger.info(f"Base de données initialisée: {self.db_path}")

    def get_connection(self):
        """Obtenir une connexion à la base de données"""
        return sqlite3.connect(self.db_path)

    def save_match(self, match_data: Dict) -> bool:
        """Sauvegarder un match dans la base"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            INSERT OR REPLACE INTO matches 
            (match_id, championship, date, home_team, away_team, home_score, away_score, 
             status, matchday, venue, referee, raw_data, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                match_data.get('id'),
                match_data.get('competition'),
                match_data.get('date'),
                match_data.get('home_team'),
                match_data.get('away_team'),
                match_data.get('home_score'),
                match_data.get('away_score'),
                match_data.get('status'),
                match_data.get('matchday'),
                match_data.get('venue'),
                match_data.get('referee'),
                json.dumps(match_data)
            ))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Erreur sauvegarde match: {e}")
            return False

    def save_matches_batch(self, matches: List[Dict]) -> int:
        """Sauvegarder plusieurs matches en batch"""
        saved_count = 0
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            for match_data in matches:
                try:
                    cursor.execute('''
                    INSERT OR REPLACE INTO matches 
                    (match_id, championship, date, home_team, away_team, home_score, away_score, 
                     status, matchday, venue, referee, raw_data, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ''', (
                        match_data.get('id'),
                        match_data.get('competition'),
                        match_data.get('date'),
                        match_data.get('home_team'),
                        match_data.get('away_team'),
                        match_data.get('home_score'),
                        match_data.get('away_score'),
                        match_data.get('status'),
                        match_data.get('matchday'),
                        match_data.get('venue'),
                        match_data.get('referee'),
                        json.dumps(match_data)
                    ))
                    saved_count += 1
                except Exception as e:
                    logger.error(f"Erreur sauvegarde match {match_data.get('id')}: {e}")

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Erreur batch save: {e}")

        return saved_count

    def save_standings(self, championship: str, standings: List[Dict]):
        """Sauvegarder le classement"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            current_season = datetime.now().year

            for standing in standings:
                cursor.execute('''
                INSERT OR REPLACE INTO standings 
                (championship, season, position, team, team_id, played_games, won, draw, lost,
                 points, goals_for, goals_against, goal_difference, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    championship,
                    str(current_season),
                    standing.get('position'),
                    standing.get('team'),
                    standing.get('team_id'),
                    standing.get('played_games'),
                    standing.get('won'),
                    standing.get('draw'),
                    standing.get('lost'),
                    standing.get('points'),
                    standing.get('goals_for'),
                    standing.get('goals_against'),
                    standing.get('goal_difference'),
                    json.dumps(standing)
                ))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Erreur sauvegarde classement: {e}")
            return False

    def get_matches(self, championship: str = None,
                    date_from: str = None, date_to: str = None,
                    limit: int = 100) -> List[Dict]:
        """Récupérer les matches depuis la base"""
        try:
            conn = self.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM matches WHERE 1=1"
            params = []

            if championship:
                query += " AND championship = ?"
                params.append(championship)

            if date_from:
                query += " AND date >= ?"
                params.append(date_from)

            if date_to:
                query += " AND date <= ?"
                params.append(date_to)

            query += " ORDER BY date DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            matches = []
            for row in rows:
                match_data = dict(row)
                # Parser les données JSON si nécessaire
                if 'raw_data' in match_data and match_data['raw_data']:
                    try:
                        raw = json.loads(match_data['raw_data'])
                        match_data.update(raw)
                    except:
                        pass
                matches.append(match_data)

            conn.close()
            return matches

        except Exception as e:
            logger.error(f"Erreur récupération matches: {e}")
            return []

    def get_standings(self, championship: str) -> List[Dict]:
        """Récupérer le classement depuis la base"""
        try:
            conn = self.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            current_season = datetime.now().year

            cursor.execute('''
            SELECT * FROM standings 
            WHERE championship = ? AND season = ?
            ORDER BY position
            ''', (championship, str(current_season)))

            rows = cursor.fetchall()
            standings = [dict(row) for row in rows]

            conn.close()
            return standings

        except Exception as e:
            logger.error(f"Erreur récupération classement: {e}")
            return []

    def get_team_stats(self, championship: str, team: str = None) -> List[Dict]:
        """Récupérer les statistiques d'équipe"""
        try:
            conn = self.get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if team:
                cursor.execute('''
                SELECT * FROM team_stats 
                WHERE championship = ? AND team = ?
                ORDER BY points DESC
                ''', (championship, team))
            else:
                cursor.execute('''
                SELECT * FROM team_stats 
                WHERE championship = ?
                ORDER BY points DESC
                ''', (championship,))

            rows = cursor.fetchall()
            stats = [dict(row) for row in rows]

            conn.close()
            return stats

        except Exception as e:
            logger.error(f"Erreur récupération stats équipe: {e}")
            return []

    def get_scraping_stats(self) -> Dict:
        """Obtenir des statistiques sur le scraping"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            # Nombre total de matches
            cursor.execute("SELECT COUNT(*) FROM matches")
            total_matches = cursor.fetchone()[0]

            # Nombre de matches par championnat
            cursor.execute('''
            SELECT championship, COUNT(*) as count 
            FROM matches 
            GROUP BY championship
            ''')
            matches_by_champ = dict(cursor.fetchall())

            # Dernière date de mise à jour
            cursor.execute('''
            SELECT MAX(date) FROM matches
            ''')
            last_update = cursor.fetchone()[0]

            conn.close()

            return {
                'total_matches': total_matches,
                'matches_by_championship': matches_by_champ,
                'last_update': last_update
            }

        except Exception as e:
            logger.error(f"Erreur stats scraping: {e}")
            return {}

    def log_scraping(self, championship: str, date_from: str, date_to: str,
                     matches_count: int, status: str = 'success', error: str = None):
        """Logger une opération de scraping"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute('''
            INSERT INTO scraping_log 
            (championship, date_from, date_to, matches_count, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (championship, date_from, date_to, matches_count, status, error))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Erreur log scraping: {e}")

    def clear_championship_data(self, championship: str):
        """Effacer les données d'un championnat"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("DELETE FROM matches WHERE championship = ?", (championship,))
            cursor.execute("DELETE FROM standings WHERE championship = ?", (championship,))
            cursor.execute("DELETE FROM team_stats WHERE championship = ?", (championship,))

            conn.commit()
            conn.close()

            logger.info(f"Données effacées pour {championship}")
            return True

        except Exception as e:
            logger.error(f"Erreur effacement données: {e}")
            return False