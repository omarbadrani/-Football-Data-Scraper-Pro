# config.py
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # API Configuration
    FOOTBALL_DATA_API_KEY = os.getenv('FOOTBALL_DATA_API_KEY', 'a85cd28d53094b7b9fceb53d1f8f3943')
    FOOTBALL_DATA_URL = "https://api.football-data.org/v4"

    # Database
    DB_PATH = "football_data.db"

    # Championships IDs (football-data.org)
    CHAMPIONSHIP_IDS = {
        'Premier League': {'id': 'PL', 'code': 2021},
        'Ligue 1': {'id': 'FL1', 'code': 2015},
        'La Liga': {'id': 'PD', 'code': 2014},
        'Serie A': {'id': 'SA', 'code': 2019},
        'Bundesliga': {'id': 'BL1', 'code': 2002}
    }

    # Colors for each championship
    CHAMPIONSHIP_COLORS = {
        'Premier League': {'bg': '#38003C', 'fg': '#FFFFFF', 'accent': '#00FF85'},
        'Ligue 1': {'bg': '#12233F', 'fg': '#FFFFFF', 'accent': '#E31E24'},
        'La Liga': {'bg': '#FFD700', 'fg': '#000000', 'accent': '#C60B1E'},
        'Serie A': {'bg': '#009246', 'fg': '#FFFFFF', 'accent': '#FFFFFF'},
        'Bundesliga': {'bg': '#D3010C', 'fg': '#FFFFFF', 'accent': '#FFFFFF'}
    }

    CHAMPIONSHIP_EMOJIS = {
        'Premier League': '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
        'Ligue 1': '🇫🇷',
        'La Liga': '🇪🇸',
        'Serie A': '🇮🇹',
        'Bundesliga': '🇩🇪'
    }

    @classmethod
    def get_championship_code(cls, championship):
        return cls.CHAMPIONSHIP_IDS.get(championship, {}).get('code')

    @classmethod
    def get_championship_id(cls, championship):
        return cls.CHAMPIONSHIP_IDS.get(championship, {}).get('id')