# app.py - Version Streamlit
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time
import json
import csv
from io import StringIO, BytesIO
import base64

from config import Config
from database import FootballDatabase
from scraper import FootballAPIScraper

# Configuration de la page
st.set_page_config(
    page_title="⚽ Football Data Scraper Pro",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Initialisation des composants
@st.cache_resource
def get_database():
    return FootballDatabase(Config.DB_PATH)


@st.cache_resource
def get_scraper():
    return FootballAPIScraper()


db = get_database()
scraper = get_scraper()

# CSS personnalisé
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1a73e8;
        margin-bottom: 1rem;
    }
    .card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border-left: 5px solid #1a73e8;
    }
    .stat-card {
        background-color: white;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #1a73e8;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #666;
    }
    .success {
        color: #34a853;
    }
    .warning {
        color: #fbbc05;
    }
    .error {
        color: #ea4335;
    }
    .championship-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.title("⚽ Football Data Scraper")

    # Sélection du championnat
    st.subheader("📊 Sélection")
    championship = st.selectbox(
        "Championnat",
        list(Config.CHAMPIONSHIP_IDS.keys()),
        index=0
    )

    # Quick stats
    st.subheader("📈 Stats Rapides")

    try:
        stats = db.get_scraping_stats()

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Matches", stats.get('total_matches', 0))
        with col2:
            # Compter les championnats
            champ_count = len(stats.get('matches_by_championship', {}))
            st.metric("Championnats", champ_count)

        # Dernière mise à jour
        if 'last_update' in stats and stats['last_update']:
            st.caption(f"📅 Dernière mise à jour: {stats['last_update'][:10]}")

    except Exception as e:
        st.error(f"Erreur stats: {e}")

    # Navigation
    st.subheader("🧭 Navigation")
    page = st.radio(
        "Pages",
        ["🏠 Dashboard", "📥 Scraping", "⚽ Matches", "📈 Classement",
         "📊 Statistiques", "🔍 Recherche", "💾 Export"]
    )


# Fonction pour scraper avec feedback
def scrape_data(championship, date_from, date_to, save_to_db=True):
    """Fonction de scraping avec feedback Streamlit"""

    with st.status(f"Scraping {championship}...", expanded=True) as status:
        try:
            # 1. Récupération des matches
            status.write("📥 Récupération des matches...")
            matches = scraper.get_matches_by_date_range(championship, date_from, date_to)

            saved_count = 0
            if matches and save_to_db:
                status.write("💾 Sauvegarde dans la base de données...")
                saved_count = db.save_matches_batch(matches)
                db.log_scraping(championship, date_from, date_to, saved_count, 'success')

            # 2. Récupération du classement
            status.write("📊 Récupération du classement...")
            standings = scraper.get_standings(championship)

            if standings:
                db.save_standings(championship, standings)

            # 3. Résumé
            status.write("✅ Scraping terminé!")

            return {
                'matches': matches,
                'standings': standings,
                'saved_count': saved_count,
                'success': True
            }

        except Exception as e:
            status.write(f"❌ Erreur: {e}")
            db.log_scraping(championship, date_from, date_to, 0, 'error', str(e))
            return {'success': False, 'error': str(e)}


# Page Dashboard
if page == "🏠 Dashboard":
    st.markdown("<h1 class='main-header'>🏠 Dashboard Football</h1>", unsafe_allow_html=True)

    # Métriques principales
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        try:
            stats = db.get_scraping_stats()
            st.metric("Matches Totaux", stats.get('total_matches', 0))
        except:
            st.metric("Matches Totaux", 0)

    with col2:
        try:
            # Charger quelques matches pour compter les équipes
            matches = db.get_matches(limit=100)
            teams = set()
            for match in matches:
                teams.add(match.get('home_team', ''))
                teams.add(match.get('away_team', ''))
            st.metric("Équipes Uniques", len(teams))
        except:
            st.metric("Équipes Uniques", 0)

    with col3:
        try:
            matches = db.get_matches(limit=100)
            finished = sum(1 for m in matches if m.get('status') == 'finished')
            st.metric("Matches Terminés", finished)
        except:
            st.metric("Matches Terminés", 0)

    with col4:
        try:
            matches = db.get_matches(limit=100)
            goals = 0
            for match in matches:
                if match.get('status') == 'finished':
                    goals += (match.get('home_score', 0) or 0) + (match.get('away_score', 0) or 0)
            st.metric("Buts Totaux", goals)
        except:
            st.metric("Buts Totaux", 0)

    # Graphiques
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 Distribution des matches")
        try:
            stats = db.get_scraping_stats()
            if 'matches_by_championship' in stats and stats['matches_by_championship']:
                df = pd.DataFrame.from_dict(
                    stats['matches_by_championship'],
                    orient='index',
                    columns=['matches']
                ).reset_index()
                df.columns = ['championship', 'matches']

                fig = px.pie(df, values='matches', names='championship',
                             title="Matches par championnat")
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.warning(f"Pas assez de données pour le graphique: {e}")

    with col2:
        st.subheader("📈 Derniers matches")
        try:
            matches = db.get_matches(limit=10)
            if matches:
                df = pd.DataFrame(matches)
                if not df.empty:
                    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                    df = df[['date', 'home_team', 'home_score', 'away_score', 'away_team', 'status']]
                    st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"Erreur: {e}")

# Page Scraping
elif page == "📥 Scraping":
    st.markdown("<h1 class='main-header'>📥 Scraping API Football</h1>", unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            date_from = st.date_input(
                "Date de début",
                datetime.now() - timedelta(days=30)
            )

        with col2:
            date_to = st.date_input(
                "Date de fin",
                datetime.now()
            )

        save_to_db = st.checkbox("💾 Sauvegarder dans la base de données", value=True)

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("🚀 Scraper la période", type="primary", use_container_width=True):
                result = scrape_data(
                    championship,
                    date_from.strftime('%Y-%m-%d'),
                    date_to.strftime('%Y-%m-%d'),
                    save_to_db
                )

                if result['success']:
                    st.success(f"✅ Scraping réussi!")
                    if 'matches' in result:
                        st.info(f"📊 {len(result['matches'])} matches récupérés")
                        if 'saved_count' in result:
                            st.info(f"💾 {result['saved_count']} matches sauvegardés")

        with col2:
            if st.button("📅 30 derniers jours", use_container_width=True):
                date_from = datetime.now() - timedelta(days=30)
                date_to = datetime.now()

                result = scrape_data(
                    championship,
                    date_from.strftime('%Y-%m-%d'),
                    date_to.strftime('%Y-%m-%d'),
                    save_to_db
                )

                if result['success']:
                    st.success(f"✅ Scraping des 30 derniers jours réussi!")

        with col3:
            if st.button("🏆 Saison complète", use_container_width=True):
                current_year = datetime.now().year
                date_from = f"{current_year}-08-01"
                date_to = f"{current_year + 1}-05-31"

                result = scrape_data(championship, date_from, date_to, save_to_db)

                if result['success']:
                    st.success(f"✅ Scraping saison complète réussi!")

        st.markdown('</div>', unsafe_allow_html=True)

    # Options avancées
    with st.expander("⚙️ Options avancées"):
        col1, col2 = st.columns(2)

        with col1:
            if st.button("🗑️ Effacer championnat", type="secondary"):
                if st.checkbox("Confirmer l'effacement (irréversible)"):
                    success = db.clear_championship_data(championship)
                    if success:
                        st.success(f"✅ Données de {championship} effacées")
                    else:
                        st.error(f"❌ Erreur lors de l'effacement")

        with col2:
            if st.button("🔄 Charger depuis DB", type="secondary"):
                with st.spinner("Chargement..."):
                    matches = db.get_matches(championship=championship, limit=100)
                    standings = db.get_standings(championship)
                    st.success(f"✅ {len(matches)} matches chargés depuis la base")

                    # Stocker dans la session
                    st.session_state['current_matches'] = matches
                    st.session_state['current_standings'] = standings

# Page Matches
elif page == "⚽ Matches":
    st.markdown("<h1 class='main-header'>⚽ Matches</h1>", unsafe_allow_html=True)

    # Filtres
    col1, col2, col3 = st.columns(3)

    with col1:
        filter_date = st.date_input("Filtrer par date", datetime.now())

    with col2:
        filter_status = st.selectbox(
            "Statut",
            ["Tous", "finished", "scheduled", "live", "postponed"]
        )

    with col3:
        limit = st.slider("Nombre de matches", 10, 200, 50)

    # Boutons d'action
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔍 Appliquer filtres", use_container_width=True):
            matches = db.get_matches(
                championship=championship,
                date_from=filter_date.strftime('%Y-%m-%d'),
                date_to=filter_date.strftime('%Y-%m-%d'),
                limit=limit
            )

            if filter_status != "Tous":
                matches = [m for m in matches if m.get('status') == filter_status]

            st.session_state['current_matches'] = matches

    with col2:
        if st.button("🔄 Tous les matches", use_container_width=True):
            matches = db.get_matches(championship=championship, limit=limit)
            st.session_state['current_matches'] = matches

    # Affichage des matches
    if 'current_matches' in st.session_state and st.session_state['current_matches']:
        matches = st.session_state['current_matches']

        # Convertir en DataFrame
        df = pd.DataFrame(matches)

        if not df.empty:
            # Nettoyer les données
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d %H:%M')
            df['score'] = df.apply(
                lambda x: f"{x['home_score'] or '?'}-{x['away_score'] or '?'}"
                if pd.notna(x['home_score']) and pd.notna(x['away_score'])
                else 'VS',
                axis=1
            )

            # Sélectionner les colonnes à afficher
            display_cols = ['date', 'home_team', 'score', 'away_team', 'status', 'matchday', 'venue']
            display_df = df[display_cols].copy()
            display_df.columns = ['Date', 'Domicile', 'Score', 'Extérieur', 'Statut', 'Journée', 'Lieu']

            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )

            # Statistiques des matches affichés
            st.subheader("📊 Statistiques des matches affichés")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                finished = sum(1 for m in matches if m.get('status') == 'finished')
                st.metric("Terminés", finished)

            with col2:
                scheduled = sum(1 for m in matches if m.get('status') == 'scheduled')
                st.metric("Programmés", scheduled)

            with col3:
                total_goals = 0
                for match in matches:
                    if match.get('status') == 'finished':
                        total_goals += (match.get('home_score', 0) or 0) + (match.get('away_score', 0) or 0)
                st.metric("Buts totaux", total_goals)

            with col4:
                avg_goals = total_goals / finished if finished > 0 else 0
                st.metric("Moyenne buts/match", f"{avg_goals:.2f}")
    else:
        st.info("👆 Utilisez les boutons pour charger des matches")

# Page Classement
elif page == "📈 Classement":
    st.markdown("<h1 class='main-header'>📈 Classement</h1>", unsafe_allow_html=True)

    # Charger le classement
    standings = db.get_standings(championship)

    if standings:
        # Convertir en DataFrame
        df = pd.DataFrame(standings)

        if not df.empty:
            # Nettoyer les données
            display_cols = ['position', 'team', 'points', 'played_games',
                            'won', 'draw', 'lost', 'goals_for', 'goals_against', 'goal_difference']
            display_df = df[display_cols].copy()
            display_df.columns = ['Pos', 'Équipe', 'Pts', 'MJ', 'G', 'N', 'P', 'BP', 'BC', 'Diff']

            # Mettre en forme
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )

            # Graphique du classement
            st.subheader("📊 Visualisation du classement")

            fig = px.bar(
                display_df.head(10),
                x='Équipe',
                y='Pts',
                color='Pts',
                title=f"Top 10 - {championship}",
                color_continuous_scale='Viridis'
            )
            fig.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)

            # Statistiques détaillées
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("🏆 Meilleures attaques")
                top_attack = display_df.nlargest(5, 'BP')[['Équipe', 'BP']]
                st.dataframe(top_attack, use_container_width=True)

            with col2:
                st.subheader("🛡️ Meilleures défenses")
                top_defense = display_df.nsmallest(5, 'BC')[['Équipe', 'BC']]
                st.dataframe(top_defense, use_container_width=True)
    else:
        st.warning(f"⚠️ Aucun classement disponible pour {championship}")
        if st.button("🔄 Charger le classement"):
            with st.spinner("Chargement..."):
                standings = scraper.get_standings(championship)
                if standings:
                    db.save_standings(championship, standings)
                    st.rerun()

# Page Statistiques
elif page == "📊 Statistiques":
    st.markdown("<h1 class='main-header'>📊 Statistiques Avancées</h1>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📈 Générales", "👥 Par Équipe", "📅 Temporelles"])

    with tab1:
        st.subheader("📊 Statistiques Générales")

        try:
            # Charger les matches
            matches = db.get_matches(championship=championship, limit=500)

            if matches:
                # Calculer les statistiques
                total_matches = len(matches)
                finished_matches = sum(1 for m in matches if m.get('status') == 'finished')
                scheduled_matches = sum(1 for m in matches if m.get('status') == 'scheduled')

                total_goals = 0
                home_goals = 0
                away_goals = 0

                for match in matches:
                    if match.get('status') == 'finished':
                        home = match.get('home_score', 0) or 0
                        away = match.get('away_score', 0) or 0
                        total_goals += home + away
                        home_goals += home
                        away_goals += away

                avg_goals = total_goals / finished_matches if finished_matches > 0 else 0

                # Afficher les métriques
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("Matches Totaux", total_matches)

                with col2:
                    st.metric("Terminés", finished_matches)

                with col3:
                    st.metric("Buts Totaux", total_goals)

                with col4:
                    st.metric("Moyenne Buts", f"{avg_goals:.2f}")

                # Distribution des statuts
                status_counts = {}
                for match in matches:
                    status = match.get('status', 'unknown')
                    status_counts[status] = status_counts.get(status, 0) + 1

                if status_counts:
                    st.subheader("📊 Distribution par statut")
                    status_df = pd.DataFrame.from_dict(status_counts, orient='index', columns=['count'])
                    status_df = status_df.reset_index()
                    status_df.columns = ['status', 'count']

                    fig = px.pie(status_df, values='count', names='status',
                                 title="Répartition des statuts de match")
                    st.plotly_chart(fig, use_container_width=True)

                # Buts domicile vs extérieur
                st.subheader("⚽ Buts Domicile vs Extérieur")

                goals_data = {
                    'Type': ['Domicile', 'Extérieur'],
                    'Buts': [home_goals, away_goals]
                }

                goals_df = pd.DataFrame(goals_data)
                fig = px.bar(goals_df, x='Type', y='Buts',
                             title="Répartition des buts",
                             color='Type')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune donnée disponible. Scrapez d'abord des matches.")

        except Exception as e:
            st.error(f"Erreur: {e}")

    with tab2:
        st.subheader("👥 Statistiques par Équipe")

        try:
            matches = db.get_matches(championship=championship, limit=500)

            if matches:
                # Collecter toutes les équipes
                teams = set()
                for match in matches:
                    teams.add(match.get('home_team', ''))
                    teams.add(match.get('away_team', ''))

                team_list = sorted(list(teams))
                selected_team = st.selectbox("Sélectionner une équipe", team_list)

                if selected_team:
                    # Calculer les statistiques de l'équipe
                    team_stats = {
                        'total_matches': 0,
                        'wins': 0,
                        'draws': 0,
                        'losses': 0,
                        'goals_for': 0,
                        'goals_against': 0,
                        'home_matches': 0,
                        'away_matches': 0,
                        'home_wins': 0,
                        'away_wins': 0
                    }

                    for match in matches:
                        if match.get('status') == 'finished':
                            home_team = match.get('home_team', '')
                            away_team = match.get('away_team', '')

                            if selected_team in [home_team, away_team]:
                                team_stats['total_matches'] += 1

                                home_score = match.get('home_score', 0) or 0
                                away_score = match.get('away_score', 0) or 0

                                if selected_team == home_team:
                                    team_stats['home_matches'] += 1
                                    team_stats['goals_for'] += home_score
                                    team_stats['goals_against'] += away_score

                                    if home_score > away_score:
                                        team_stats['wins'] += 1
                                        team_stats['home_wins'] += 1
                                    elif home_score < away_score:
                                        team_stats['losses'] += 1
                                    else:
                                        team_stats['draws'] += 1

                                else:  # selected_team == away_team
                                    team_stats['away_matches'] += 1
                                    team_stats['goals_for'] += away_score
                                    team_stats['goals_against'] += home_score

                                    if away_score > home_score:
                                        team_stats['wins'] += 1
                                        team_stats['away_wins'] += 1
                                    elif away_score < home_score:
                                        team_stats['losses'] += 1
                                    else:
                                        team_stats['draws'] += 1

                    # Afficher les statistiques
                    if team_stats['total_matches'] > 0:
                        win_rate = (team_stats['wins'] / team_stats['total_matches']) * 100
                        avg_goals_for = team_stats['goals_for'] / team_stats['total_matches']
                        avg_goals_against = team_stats['goals_against'] / team_stats['total_matches']

                        col1, col2 = st.columns(2)

                        with col1:
                            st.metric("Matches joués", team_stats['total_matches'])
                            st.metric("Victoires", f"{team_stats['wins']} ({win_rate:.1f}%)")
                            st.metric("Nuls", team_stats['draws'])
                            st.metric("Défaites", team_stats['losses'])

                        with col2:
                            st.metric("Buts marqués", f"{team_stats['goals_for']} ({avg_goals_for:.2f}/match)")
                            st.metric("Buts encaissés",
                                      f"{team_stats['goals_against']} ({avg_goals_against:.2f}/match)")
                            st.metric("Différence", team_stats['goals_for'] - team_stats['goals_against'])
                            st.metric("À domicile", f"{team_stats['home_matches']} matches")

                        # Graphique des résultats
                        results_data = {
                            'Résultat': ['Victoires', 'Nuls', 'Défaites'],
                            'Nombre': [team_stats['wins'], team_stats['draws'], team_stats['losses']]
                        }

                        results_df = pd.DataFrame(results_data)
                        fig = px.pie(results_df, values='Nombre', names='Résultat',
                                     title=f"Résultats de {selected_team}")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Aucune donnée disponible pour cette équipe")
            else:
                st.info("Aucune donnée disponible. Scrapez d'abord des matches.")

        except Exception as e:
            st.error(f"Erreur: {e}")

    with tab3:
        st.subheader("📅 Statistiques Temporelles")

        try:
            matches = db.get_matches(championship=championship, limit=500)

            if matches:
                # Buts par journée
                matchday_goals = {}
                for match in matches:
                    if match.get('status') == 'finished':
                        matchday = match.get('matchday')
                        if matchday:
                            home = match.get('home_score', 0) or 0
                            away = match.get('away_score', 0) or 0
                            total = home + away

                            if matchday not in matchday_goals:
                                matchday_goals[matchday] = {'total': 0, 'matches': 0}

                            matchday_goals[matchday]['total'] += total
                            matchday_goals[matchday]['matches'] += 1

                if matchday_goals:
                    # Préparer les données
                    matchdays = sorted(matchday_goals.keys())
                    totals = [matchday_goals[m]['total'] for m in matchdays]
                    averages = [matchday_goals[m]['total'] / matchday_goals[m]['matches'] for m in matchdays]

                    # Créer le graphique
                    fig = go.Figure()

                    fig.add_trace(go.Bar(
                        x=matchdays,
                        y=totals,
                        name='Buts totaux',
                        marker_color='#1a73e8'
                    ))

                    fig.add_trace(go.Scatter(
                        x=matchdays,
                        y=averages,
                        name='Moyenne par match',
                        line=dict(color='#ea4335', width=3),
                        mode='lines+markers'
                    ))

                    fig.update_layout(
                        title="Buts par journée",
                        xaxis_title="Journée",
                        yaxis_title="Buts",
                        hovermode='x unified'
                    )

                    st.plotly_chart(fig, use_container_width=True)

                # Distribution des scores
                st.subheader("🎯 Distribution des scores")

                scores = []
                for match in matches:
                    if match.get('status') == 'finished':
                        home = match.get('home_score', 0) or 0
                        away = match.get('away_score', 0) or 0
                        scores.append(f"{home}-{away}")

                if scores:
                    from collections import Counter

                    score_counts = Counter(scores)

                    # Prendre les 10 scores les plus fréquents
                    common_scores = score_counts.most_common(10)

                    if common_scores:
                        score_labels = [score for score, count in common_scores]
                        score_values = [count for score, count in common_scores]

                        fig = px.bar(
                            x=score_labels,
                            y=score_values,
                            title="Scores les plus fréquents",
                            labels={'x': 'Score', 'y': 'Occurrences'}
                        )
                        fig.update_layout(xaxis_tickangle=-45)
                        st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune donnée disponible. Scrapez d'abord des matches.")

        except Exception as e:
            st.error(f"Erreur: {e}")

# Page Recherche
elif page == "🔍 Recherche":
    st.markdown("<h1 class='main-header'>🔍 Recherche Avancée</h1>", unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            search_team = st.text_input("Rechercher une équipe")

        with col2:
            search_date = st.date_input("Date spécifique", value=None)

        col3, col4 = st.columns(2)

        with col3:
            search_status = st.selectbox(
                "Statut du match",
                ["Tous", "finished", "scheduled", "live", "postponed"]
            )

        with col4:
            min_goals = st.number_input("Buts minimum par match", min_value=0, value=0)

        if st.button("🔍 Lancer la recherche", type="primary", use_container_width=True):
            with st.spinner("Recherche en cours..."):
                # Récupérer tous les matches
                matches = db.get_matches(championship=championship, limit=500)

                # Appliquer les filtres
                filtered_matches = []

                for match in matches:
                    include = True

                    # Filtre équipe
                    if search_team:
                        if search_team.lower() not in match.get('home_team', '').lower() and \
                                search_team.lower() not in match.get('away_team', '').lower():
                            include = False

                    # Filtre date
                    if search_date:
                        match_date = match.get('date', '')[:10]
                        if match_date != search_date.strftime('%Y-%m-%d'):
                            include = False

                    # Filtre statut
                    if search_status != "Tous":
                        match_status = match.get('status', '')
                        if match_status != search_status:
                            include = False

                    # Filtre buts minimum
                    if min_goals > 0 and match.get('status') == 'finished':
                        home = match.get('home_score', 0) or 0
                        away = match.get('away_score', 0) or 0
                        total = home + away
                        if total < min_goals:
                            include = False

                    if include:
                        filtered_matches.append(match)

                # Stocker les résultats
                st.session_state['search_results'] = filtered_matches

        st.markdown('</div>', unsafe_allow_html=True)

    # Afficher les résultats
    if 'search_results' in st.session_state:
        results = st.session_state['search_results']

        st.subheader(f"📋 Résultats ({len(results)} matches)")

        if results:
            # Convertir en DataFrame
            df = pd.DataFrame(results)

            if not df.empty:
                # Nettoyer les données
                df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
                df['score'] = df.apply(
                    lambda x: f"{x['home_score'] or '?'}-{x['away_score'] or '?'}"
                    if pd.notna(x['home_score']) and pd.notna(x['away_score'])
                    else 'VS',
                    axis=1
                )

                # Ajouter le total de buts
                df['total_goals'] = df.apply(
                    lambda x: (x['home_score'] or 0) + (x['away_score'] or 0)
                    if pd.notna(x['home_score']) and pd.notna(x['away_score'])
                    else None,
                    axis=1
                )

                # Sélectionner les colonnes à afficher
                display_cols = ['date', 'home_team', 'score', 'away_team', 'status', 'matchday', 'total_goals']
                display_df = df[display_cols].copy()
                display_df.columns = ['Date', 'Domicile', 'Score', 'Extérieur', 'Statut', 'Journée', 'Buts Total']

                st.dataframe(
                    display_df,
                    use_container_width=True,
                    hide_index=True
                )

                # Bouton d'export
                csv = display_df.to_csv(index=False)
                st.download_button(
                    label="📥 Télécharger les résultats (CSV)",
                    data=csv,
                    file_name=f"recherche_{championship}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        else:
            st.info("Aucun résultat trouvé")

# Page Export
elif page == "💾 Export":
    st.markdown("<h1 class='main-header'>💾 Export de Données</h1>", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["📤 Exporter Données", "📊 Statistiques DB"])

    with tab1:
        st.subheader("📤 Exporter les données")

        col1, col2 = st.columns(2)

        with col1:
            export_format = st.selectbox(
                "Format d'export",
                ["CSV", "Excel", "JSON"]
            )

        with col2:
            export_limit = st.slider("Nombre maximum d'enregistrements", 10, 1000, 100)

        if st.button("🚀 Exporter les données", type="primary", use_container_width=True):
            with st.spinner("Préparation de l'export..."):
                try:
                    # Récupérer les données
                    matches = db.get_matches(championship=championship, limit=export_limit)

                    if matches:
                        # Convertir en DataFrame
                        df = pd.DataFrame(matches)

                        if not df.empty:
                            # Nettoyer les données
                            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d %H:%M:%S')
                            df['score'] = df.apply(
                                lambda x: f"{x['home_score'] or ''}-{x['away_score'] or ''}"
                                if pd.notna(x['home_score']) and pd.notna(x['away_score'])
                                else 'VS',
                                axis=1
                            )

                            # Sélectionner les colonnes
                            export_cols = ['date', 'championship', 'home_team', 'score', 'away_team',
                                           'status', 'matchday', 'venue', 'referee']
                            export_df = df[export_cols].copy()
                            export_df.columns = ['Date', 'Championnat', 'Domicile', 'Score', 'Extérieur',
                                                 'Statut', 'Journée', 'Lieu', 'Arbitre']

                            # Préparer le fichier selon le format
                            if export_format == "CSV":
                                csv_data = export_df.to_csv(index=False)
                                st.download_button(
                                    label="📥 Télécharger CSV",
                                    data=csv_data,
                                    file_name=f"football_{championship}_{datetime.now().strftime('%Y%m%d')}.csv",
                                    mime="text/csv"
                                )

                            elif export_format == "Excel":
                                buffer = BytesIO()
                                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                                    export_df.to_excel(writer, index=False, sheet_name='Matches')

                                st.download_button(
                                    label="📥 Télécharger Excel",
                                    data=buffer.getvalue(),
                                    file_name=f"football_{championship}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                                )

                            elif export_format == "JSON":
                                json_data = export_df.to_json(orient='records', indent=2)
                                st.download_button(
                                    label="📥 Télécharger JSON",
                                    data=json_data,
                                    file_name=f"football_{championship}_{datetime.now().strftime('%Y%m%d')}.json",
                                    mime="application/json"
                                )

                            # Aperçu des données
                            st.subheader("👁️ Aperçu des données")
                            st.dataframe(export_df.head(10), use_container_width=True)

                        else:
                            st.warning("Aucune donnée à exporter")
                    else:
                        st.warning("Aucune donnée à exporter")

                except Exception as e:
                    st.error(f"Erreur lors de l'export: {e}")

    with tab2:
        st.subheader("📊 Statistiques de la base de données")

        try:
            stats = db.get_scraping_stats()

            if stats:
                col1, col2 = st.columns(2)

                with col1:
                    st.metric("Matches Totaux", stats.get('total_matches', 0))

                    # Taille de la DB
                    import os

                    db_size = os.path.getsize(Config.DB_PATH) if os.path.exists(Config.DB_PATH) else 0
                    st.metric("Taille DB", f"{db_size / 1024 / 1024:.2f} MB")

                with col2:
                    if 'last_update' in stats and stats['last_update']:
                        st.metric("Dernière mise à jour", stats['last_update'][:10])

                # Matches par championnat
                if 'matches_by_championship' in stats and stats['matches_by_championship']:
                    st.subheader("📊 Matches par championnat")

                    champ_df = pd.DataFrame.from_dict(
                        stats['matches_by_championship'],
                        orient='index',
                        columns=['matches']
                    ).reset_index()
                    champ_df.columns = ['championnat', 'matches']

                    # Graphique
                    fig = px.bar(champ_df, x='championnat', y='matches',
                                 title="Distribution des matches par championnat")
                    st.plotly_chart(fig, use_container_width=True)

                    # Tableau
                    st.dataframe(champ_df, use_container_width=True, hide_index=True)
            else:
                st.info("Aucune statistique disponible")

        except Exception as e:
            st.error(f"Erreur: {e}")

# Pied de page
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
    <p>⚽ Football Data Scraper Pro • Utilise l'API football-data.org • Développé avec Streamlit</p>
    <p>Version 1.0 • © 2026</p>
    </div>
    """,
    unsafe_allow_html=True
)