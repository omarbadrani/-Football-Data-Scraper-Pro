# scraper.py (version corrigée)
import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import time
from config import Config

logger = logging.getLogger(__name__)


class FootballAPIScraper:
    def __init__(self):
        self.api_key = Config.FOOTBALL_DATA_API_KEY
        self.base_url = Config.FOOTBALL_DATA_URL
        self.headers = {
            'X-Auth-Token': self.api_key,
            'User-Agent': 'FootballScraper/1.0'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        if not self.api_key:
            logger.warning("Aucune clé API configurée")

    def test_connection(self) -> bool:
        """Tester la connexion à l'API"""
        try:
            response = self.session.get(f"{self.base_url}/competitions/PL", timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Erreur test connexion: {e}")
            return False

    def get_matches_by_date_range(self, championship: str,
                                  date_from: str, date_to: str) -> List[Dict]:
        """Récupérer les matches sur une période (gère les longues périodes)"""
        championship_code = Config.get_championship_code(championship)

        if not championship_code:
            logger.error(f"Championnat inconnu: {championship}")
            return []

        # Convertir les dates en objets datetime
        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d')
            end_date = datetime.strptime(date_to, '%Y-%m-%d')
        except ValueError:
            logger.error(f"Format de date invalide: {date_from} ou {date_to}")
            return []

        # Vérifier si la période est trop longue (> 10 jours)
        total_days = (end_date - start_date).days + 1

        if total_days > 10:
            logger.info(f"Période longue détectée: {total_days} jours. Découpage en lots de 7 jours...")
            return self._get_matches_long_period(championship_code, start_date, end_date, championship)
        else:
            return self._get_matches_single_request(championship_code, date_from, date_to, championship)

    def _get_matches_single_request(self, championship_code: int,
                                    date_from: str, date_to: str,
                                    championship_name: str) -> List[Dict]:
        """Récupérer les matches avec une seule requête API (pour périodes courtes)"""
        matches = []

        try:
            url = f"{self.base_url}/matches"
            params = {
                'competitions': championship_code,
                'dateFrom': date_from,
                'dateTo': date_to
            }

            response = self.session.get(url, params=params, timeout=30)

            if response.status_code != 200:
                logger.error(f"Erreur API: {response.status_code} - {response.text}")
                return matches

            data = response.json()
            matches_data = data.get('matches', [])

            for match_data in matches_data:
                parsed_match = self._parse_match_data(match_data, championship_name)
                if parsed_match:
                    matches.append(parsed_match)

            logger.info(f"Récupéré {len(matches)} matches pour {championship_name}")

        except Exception as e:
            logger.error(f"Erreur récupération matches: {e}")

        return matches

    def _get_matches_long_period(self, championship_code: int,
                                 start_date: datetime, end_date: datetime,
                                 championship_name: str) -> List[Dict]:
        """Récupérer les matches pour une longue période (découpage en lots)"""
        all_matches = []
        current_date = start_date

        # Découper en lots de 7 jours maximum
        batch_size = 7

        while current_date <= end_date:
            batch_end = min(current_date + timedelta(days=batch_size - 1), end_date)

            date_from_str = current_date.strftime('%Y-%m-%d')
            date_to_str = batch_end.strftime('%Y-%m-%d')

            logger.info(f"Récupération lot {date_from_str} à {date_to_str}")

            batch_matches = self._get_matches_single_request(
                championship_code, date_from_str, date_to_str, championship_name
            )

            all_matches.extend(batch_matches)

            # Pause pour respecter les limites de l'API
            time.sleep(1.5)

            # Passer au lot suivant
            current_date = batch_end + timedelta(days=1)

        logger.info(f"Total récupéré: {len(all_matches)} matches pour {championship_name}")
        return all_matches

    def get_matches_by_season(self, championship: str, season_year: int = None) -> List[Dict]:
        """Récupérer tous les matches d'une saison"""
        championship_code = Config.get_championship_code(championship)

        if not championship_code:
            logger.error(f"Championnat inconnu: {championship}")
            return []

        # Déterminer l'année de saison
        if season_year is None:
            season_year = datetime.now().year

        # Dates typiques d'une saison de football (août à mai)
        season_start = f"{season_year}-08-01"
        season_end = f"{season_year + 1}-05-31"

        logger.info(f"Récupération saison {season_year}/{season_year + 1} pour {championship}")

        return self.get_matches_by_date_range(championship, season_start, season_end)

    def get_matches_by_matchday(self, championship: str, matchday: int) -> List[Dict]:
        """Récupérer les matches d'une journée spécifique"""
        championship_id = Config.get_championship_id(championship)

        if not championship_id:
            logger.error(f"Championnat inconnu: {championship}")
            return []

        matches = []

        try:
            url = f"{self.base_url}/competitions/{championship_id}/matches"
            params = {
                'matchday': matchday
            }

            response = self.session.get(url, params=params, timeout=30)

            if response.status_code != 200:
                logger.error(f"Erreur API: {response.status_code}")
                return matches

            data = response.json()
            matches_data = data.get('matches', [])

            for match_data in matches_data:
                parsed_match = self._parse_match_data(match_data, championship)
                if parsed_match:
                    matches.append(parsed_match)

            logger.info(f"Récupéré {len(matches)} matches pour la journée {matchday}")

        except Exception as e:
            logger.error(f"Erreur récupération journée: {e}")

        return matches

    def get_current_matchday(self, championship: str) -> Optional[int]:
        """Récupérer la journée actuelle"""
        championship_id = Config.get_championship_id(championship)

        if not championship_id:
            return None

        try:
            url = f"{self.base_url}/competitions/{championship_id}"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                current_season = data.get('currentSeason', {})
                return current_season.get('currentMatchday')

        except Exception as e:
            logger.error(f"Erreur récupération journée actuelle: {e}")

        return None

    def get_standings(self, championship: str) -> List[Dict]:
        """Récupérer le classement"""
        championship_id = Config.get_championship_id(championship)

        if not championship_id:
            logger.error(f"Championnat inconnu: {championship}")
            return []

        try:
            url = f"{self.base_url}/competitions/{championship_id}/standings"
            response = self.session.get(url, timeout=10)

            if response.status_code != 200:
                logger.error(f"Erreur API standings: {response.status_code}")
                return []

            data = response.json()
            standings_data = []

            for standing in data.get('standings', []):
                if standing.get('type') == 'TOTAL':
                    for table_item in standing.get('table', []):
                        team = table_item.get('team', {})

                        standings_data.append({
                            'position': table_item.get('position'),
                            'team': team.get('name'),
                            'team_id': team.get('id'),
                            'played_games': table_item.get('playedGames'),
                            'won': table_item.get('won'),
                            'draw': table_item.get('draw'),
                            'lost': table_item.get('lost'),
                            'points': table_item.get('points'),
                            'goals_for': table_item.get('goalsFor'),
                            'goals_against': table_item.get('goalsAgainst'),
                            'goal_difference': table_item.get('goalDifference'),
                            'raw_data': table_item
                        })

            logger.info(f"Récupéré classement {championship}: {len(standings_data)} équipes")
            return standings_data

        except Exception as e:
            logger.error(f"Erreur récupération classement: {e}")
            return []

    def get_team_info(self, team_id: int) -> Optional[Dict]:
        """Récupérer les informations d'une équipe"""
        try:
            url = f"{self.base_url}/teams/{team_id}"
            response = self.session.get(url, timeout=10)

            if response.status_code == 200:
                return response.json()

        except Exception as e:
            logger.error(f"Erreur récupération équipe {team_id}: {e}")

        return None

    def get_team_matches(self, team_id: int, limit: int = 10) -> List[Dict]:
        """Récupérer les derniers matches d'une équipe"""
        try:
            url = f"{self.base_url}/teams/{team_id}/matches"
            params = {
                'limit': limit,
                'status': 'FINISHED'
            }

            response = self.session.get(url, params=params, timeout=10)

            if response.status_code != 200:
                logger.error(f"Erreur API team matches: {response.status_code}")
                return []

            data = response.json()
            matches = []

            for match_data in data.get('matches', []):
                competition = match_data.get('competition', {}).get('name', 'Unknown')
                parsed_match = self._parse_match_data(match_data, competition)
                if parsed_match:
                    matches.append(parsed_match)

            return matches

        except Exception as e:
            logger.error(f"Erreur récupération matches équipe: {e}")
            return []

    def _parse_match_data(self, match_data: Dict, championship: str) -> Optional[Dict]:
        """Parser les données d'un match"""
        try:
            match_id = str(match_data.get('id', ''))
            home_team = match_data.get('homeTeam', {}).get('name', '')
            away_team = match_data.get('awayTeam', {}).get('name', '')

            if not home_team or not away_team:
                return None

            # Score
            score_data = match_data.get('score', {})
            full_time = score_data.get('fullTime', {})

            # Statut
            status = match_data.get('status', '')
            status_map = {
                'SCHEDULED': 'scheduled',
                'LIVE': 'live',
                'IN_PLAY': 'live',
                'FINISHED': 'finished',
                'POSTPONED': 'postponed',
                'CANCELLED': 'cancelled'
            }

            parsed_data = {
                'id': match_id,
                'api_id': match_data.get('id'),
                'date': match_data.get('utcDate', ''),
                'home_team': home_team,
                'away_team': away_team,
                'home_score': full_time.get('home'),
                'away_score': full_time.get('away'),
                'status': status_map.get(status, status.lower()),
                'competition': championship,
                'matchday': match_data.get('matchday'),
                'venue': match_data.get('venue', 'Unknown'),
                'referee': match_data.get('referees', [{}])[0].get('name', ''),
                'raw_data': match_data
            }

            # Score à la mi-temps
            half_time = score_data.get('halfTime', {})
            if half_time:
                parsed_data['half_time_home'] = half_time.get('home')
                parsed_data['half_time_away'] = half_time.get('away')

            return parsed_data

        except Exception as e:
            logger.error(f"Erreur parsing match: {e}")
            return None

    def get_available_seasons(self, championship: str) -> List[str]:
        """Récupérer les saisons disponibles"""
        championship_id = Config.get_championship_id(championship)

        if not championship_id:
            return []

        try:
            url = f"{self.base_url}/competitions/{championship_id}"
            response = self.session.get(url, timeout=10)

            if response.status_code != 200:
                return []

            data = response.json()
            seasons = data.get('seasons', [])

            return [season.get('startDate')[:4] for season in seasons if season.get('startDate')]

        except Exception as e:
            logger.error(f"Erreur récupération saisons: {e}")
            return []