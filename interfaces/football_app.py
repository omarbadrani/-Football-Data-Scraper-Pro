# football_app.py - Code corrigé
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import queue
import time
from datetime import datetime, timedelta
import json
import csv
import sys
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import pandas as pd
from config import Config
from database import FootballDatabase
from scraper import FootballAPIScraper


class FootballScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("⚽ Football Data Scraper Pro - API + SQLite")
        self.root.geometry("1600x900")

        # Style moderne
        self.root.configure(bg='#f0f0f0')

        # Initialisation des composants
        self.db = FootballDatabase(Config.DB_PATH)
        self.scraper = FootballAPIScraper()
        self.queue = queue.Queue()
        self.is_scraping = False
        self.current_matches = []
        self.current_standings = []

        # Variables
        self.current_championship = 'Premier League'
        self.championships = list(Config.CHAMPIONSHIP_IDS.keys())

        # Couleurs modernes
        self.colors = {
            'primary': '#1a73e8',
            'secondary': '#34a853',
            'accent': '#ea4335',
            'bg_light': '#ffffff',
            'bg_dark': '#f8f9fa',
            'text_dark': '#202124',
            'text_light': '#5f6368'
        }

        # Setup UI
        self.setup_styles()
        self.setup_ui()

        # Vérifier API
        self.check_api_status()

        # Charger données initiales
        self.load_initial_data()

        # Démarrer le processeur de queue
        self.process_queue()

    def setup_styles(self):
        """Configurer les styles modernes"""
        style = ttk.Style()
        style.theme_use('clam')

        # Configuration des styles
        style.configure('Title.TLabel',
                        font=('Segoe UI', 16, 'bold'),
                        background=self.colors['bg_light'],
                        foreground=self.colors['primary'])

        style.configure('Header.TLabel',
                        font=('Segoe UI', 12, 'bold'),
                        background=self.colors['bg_light'],
                        foreground=self.colors['text_dark'])

        style.configure('Card.TFrame',
                        background=self.colors['bg_light'],
                        relief='raised',
                        borderwidth=1)

        style.configure('Primary.TButton',
                        font=('Segoe UI', 10, 'bold'),
                        background=self.colors['primary'],
                        foreground='white')

        style.map('Primary.TButton',
                  background=[('active', self.colors['primary']),
                              ('disabled', '#cccccc')])

    def setup_ui(self):
        """Configurer l'interface moderne"""
        # Header
        header_frame = tk.Frame(self.root, bg=self.colors['primary'], height=60)
        header_frame.pack(fill=tk.X)
        header_frame.pack_propagate(False)

        title_label = tk.Label(header_frame,
                               text="⚽ Football Data Scraper Pro",
                               font=('Segoe UI', 20, 'bold'),
                               bg=self.colors['primary'],
                               fg='white')
        title_label.pack(side=tk.LEFT, padx=20, pady=10)

        # Status indicator
        self.status_indicator = tk.Label(header_frame,
                                         text="●",
                                         font=('Segoe UI', 14),
                                         bg=self.colors['primary'],
                                         fg='#34a853')
        self.status_indicator.pack(side=tk.RIGHT, padx=20)

        status_text = tk.Label(header_frame,
                               text="Connecté",
                               font=('Segoe UI', 10),
                               bg=self.colors['primary'],
                               fg='white')
        status_text.pack(side=tk.RIGHT, pady=10)

        # Main container
        main_container = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Left panel (controls) - plus étroit
        left_panel = tk.Frame(main_container, bg=self.colors['bg_dark'])
        main_container.add(left_panel, weight=1)

        # Right panel (data display)
        right_panel = tk.Frame(main_container, bg=self.colors['bg_light'])
        main_container.add(right_panel, weight=3)

        # Setup panels
        self.setup_left_panel(left_panel)
        self.setup_right_panel(right_panel)

        # Status bar
        self.setup_status_bar()

    def setup_left_panel(self, parent):
        """Configurer le panel gauche (contrôles)"""
        # Container avec scroll
        canvas = tk.Canvas(parent, bg=self.colors['bg_dark'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['bg_dark'])

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Frame pour le scraping
        scraping_frame = tk.Frame(scrollable_frame,
                                  bg=self.colors['bg_light'],
                                  relief='raised',
                                  borderwidth=1,
                                  padx=15, pady=15)
        scraping_frame.pack(fill=tk.X, padx=5, pady=5)

        # Titre avec icône
        title_frame = tk.Frame(scraping_frame, bg=self.colors['bg_light'])
        title_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(title_frame,
                 text="📥 Scraping API",
                 font=('Segoe UI', 12, 'bold'),
                 bg=self.colors['bg_light'],
                 fg=self.colors['primary']).pack(side=tk.LEFT)

        # Sélection championnat avec style
        tk.Label(scraping_frame,
                 text="Championnat:",
                 font=('Segoe UI', 10),
                 bg=self.colors['bg_light']).pack(anchor='w', pady=(5, 2))

        self.championship_var = tk.StringVar(value=self.current_championship)

        # Frame pour le combobox avec icône
        combo_frame = tk.Frame(scraping_frame, bg=self.colors['bg_light'])
        combo_frame.pack(fill=tk.X, pady=(0, 10))

        # Icône du championnat
        self.flag_label = tk.Label(combo_frame, text="🏴󠁧󠁢󠁥󠁮󠁧󠁿",
                                   font=('Segoe UI', 14),
                                   bg=self.colors['bg_light'])
        self.flag_label.pack(side=tk.LEFT, padx=(0, 5))

        self.championship_combo = ttk.Combobox(combo_frame,
                                               textvariable=self.championship_var,
                                               values=self.championships,
                                               state='readonly',
                                               width=20,
                                               font=('Segoe UI', 10))
        self.championship_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.championship_combo.bind('<<ComboboxSelected>>', self.on_championship_changed)

        # Période de scraping avec meilleur layout
        period_frame = tk.Frame(scraping_frame, bg=self.colors['bg_light'])
        period_frame.pack(fill=tk.X, pady=10)

        # Date de début
        date_frame = tk.Frame(period_frame, bg=self.colors['bg_light'])
        date_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        tk.Label(date_frame,
                 text="📅 Date de début:",
                 font=('Segoe UI', 9),
                 bg=self.colors['bg_light']).pack(anchor='w')

        self.date_from_var = tk.StringVar(value=(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        self.date_from_entry = ttk.Entry(date_frame,
                                         textvariable=self.date_from_var,
                                         width=12,
                                         font=('Segoe UI', 10))
        self.date_from_entry.pack(fill=tk.X, pady=2)

        # Date de fin
        date_frame = tk.Frame(period_frame, bg=self.colors['bg_light'])
        date_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(date_frame,
                 text="📅 Date de fin:",
                 font=('Segoe UI', 9),
                 bg=self.colors['bg_light']).pack(anchor='w')

        self.date_to_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        self.date_to_entry = ttk.Entry(date_frame,
                                       textvariable=self.date_to_var,
                                       width=12,
                                       font=('Segoe UI', 10))
        self.date_to_entry.pack(fill=tk.X, pady=2)

        # Boutons scraping principaux
        btn_frame = tk.Frame(scraping_frame, bg=self.colors['bg_light'])
        btn_frame.pack(fill=tk.X, pady=10)

        # Bouton principal
        scrape_btn = tk.Button(btn_frame,
                               text="🚀 Scraper la période",
                               command=self.scrape_with_progress,
                               bg=self.colors['primary'],
                               fg='white',
                               font=('Segoe UI', 10, 'bold'),
                               relief='raised',
                               borderwidth=0,
                               padx=20,
                               pady=10,
                               cursor='hand2')
        scrape_btn.pack(fill=tk.X, pady=5)
        scrape_btn.bind("<Enter>", lambda e: scrape_btn.config(bg='#0d62c9'))
        scrape_btn.bind("<Leave>", lambda e: scrape_btn.config(bg=self.colors['primary']))

        # Boutons rapides
        quick_btn_frame = tk.Frame(scraping_frame, bg=self.colors['bg_light'])
        quick_btn_frame.pack(fill=tk.X, pady=5)

        last_30_btn = tk.Button(quick_btn_frame,
                                text="📅 30 derniers jours",
                                command=self.scrape_last_30_days,
                                bg=self.colors['secondary'],
                                fg='white',
                                font=('Segoe UI', 9),
                                relief='flat',
                                padx=10,
                                pady=5,
                                cursor='hand2')
        last_30_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 2))

        season_btn = tk.Button(quick_btn_frame,
                               text="🏆 Saison complète",
                               command=self.scrape_season,
                               bg=self.colors['accent'],
                               fg='white',
                               font=('Segoe UI', 9),
                               relief='flat',
                               padx=10,
                               pady=5,
                               cursor='hand2')
        season_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))

        # Options
        options_frame = tk.Frame(scraping_frame, bg=self.colors['bg_light'])
        options_frame.pack(fill=tk.X, pady=10)

        self.save_to_db_var = tk.BooleanVar(value=True)
        save_cb = tk.Checkbutton(options_frame,
                                 text="💾 Sauvegarder dans SQLite",
                                 variable=self.save_to_db_var,
                                 bg=self.colors['bg_light'],
                                 font=('Segoe UI', 9),
                                 anchor='w')
        save_cb.pack(fill=tk.X)

        # Frame pour la base de données
        db_frame = tk.Frame(scrollable_frame,
                            bg=self.colors['bg_light'],
                            relief='raised',
                            borderwidth=1,
                            padx=15, pady=15)
        db_frame.pack(fill=tk.X, padx=5, pady=10)

        tk.Label(db_frame,
                 text="💾 Base de données",
                 font=('Segoe UI', 12, 'bold'),
                 bg=self.colors['bg_light'],
                 fg=self.colors['primary']).pack(anchor='w', pady=(0, 10))

        # Boutons DB avec icônes
        db_buttons = [
            ("📂 Charger depuis DB", self.load_from_db, self.colors['primary']),
            ("🗑️ Effacer championnat", self.clear_championship_data, self.colors['accent']),
            ("📤 Exporter en CSV", self.export_to_csv, self.colors['secondary']),
            ("📊 Statistiques DB", self.show_db_stats, '#9c27b0'),
            ("🔄 Actualiser", self.refresh_data, '#ff9800')
        ]

        for text, command, color in db_buttons:
            btn = tk.Button(db_frame,
                            text=text,
                            command=command,
                            bg=color,
                            fg='white',
                            font=('Segoe UI', 9),
                            relief='flat',
                            pady=8,
                            cursor='hand2')
            btn.pack(fill=tk.X, pady=2)
            btn.bind("<Enter>", lambda e, b=btn, c=color: b.config(bg=self.darken_color(c)))
            btn.bind("<Leave>", lambda e, b=btn, c=color: b.config(bg=c))

        # Statistiques rapides
        stats_frame = tk.Frame(scrollable_frame,
                               bg=self.colors['bg_light'],
                               relief='raised',
                               borderwidth=1,
                               padx=15, pady=15)
        stats_frame.pack(fill=tk.X, padx=5, pady=10)

        tk.Label(stats_frame,
                 text="📈 Statistiques rapides",
                 font=('Segoe UI', 12, 'bold'),
                 bg=self.colors['bg_light'],
                 fg=self.colors['primary']).pack(anchor='w', pady=(0, 10))

        self.quick_stats_labels = {}

        stats_grid = tk.Frame(stats_frame, bg=self.colors['bg_light'])
        stats_grid.pack(fill=tk.X)

        stats_data = [
            ("Matches", "⚽", "0"),
            ("Équipes", "👥", "0"),
            ("Journées", "📅", "0"),
            ("Mise à jour", "🕒", "N/A")
        ]

        for i, (title, icon, default) in enumerate(stats_data):
            frame = tk.Frame(stats_grid, bg=self.colors['bg_light'])
            frame.grid(row=i // 2, column=i % 2, sticky='nsew', padx=5, pady=5)
            stats_grid.columnconfigure(i % 2, weight=1)

            icon_label = tk.Label(frame, text=icon, font=('Segoe UI', 14),
                                  bg=self.colors['bg_light'])
            icon_label.pack(side=tk.LEFT, padx=(0, 5))

            text_frame = tk.Frame(frame, bg=self.colors['bg_light'])
            text_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

            tk.Label(text_frame, text=title, font=('Segoe UI', 9, 'bold'),
                     bg=self.colors['bg_light'], fg=self.colors['text_light']).pack(anchor='w')

            value_label = tk.Label(text_frame, text=default, font=('Segoe UI', 16, 'bold'),
                                   bg=self.colors['bg_light'], fg=self.colors['text_dark'])
            value_label.pack(anchor='w')

            self.quick_stats_labels[title.lower()] = value_label

        # Frame pour les logs
        log_frame = tk.Frame(scrollable_frame,
                             bg=self.colors['bg_light'],
                             relief='raised',
                             borderwidth=1,
                             padx=15, pady=15)
        log_frame.pack(fill=tk.X, padx=5, pady=10)

        tk.Label(log_frame,
                 text="📝 Journal d'activité",
                 font=('Segoe UI', 12, 'bold'),
                 bg=self.colors['bg_light'],
                 fg=self.colors['primary']).pack(anchor='w', pady=(0, 10))

        # Logs avec fond coloré
        self.log_text = scrolledtext.ScrolledText(log_frame,
                                                  height=8,
                                                  wrap=tk.WORD,
                                                  font=('Consolas', 9),
                                                  bg='#f8f9fa',
                                                  relief='flat',
                                                  borderwidth=1)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Boutons logs
        log_btn_frame = tk.Frame(log_frame, bg=self.colors['bg_light'])
        log_btn_frame.pack(fill=tk.X, pady=10)

        clear_log_btn = tk.Button(log_btn_frame,
                                  text="🗑️ Effacer les logs",
                                  command=self.clear_logs,
                                  bg=self.colors['text_light'],
                                  fg='white',
                                  font=('Segoe UI', 9),
                                  relief='flat',
                                  pady=5,
                                  cursor='hand2')
        clear_log_btn.pack(side=tk.LEFT)

        export_log_btn = tk.Button(log_btn_frame,
                                   text="📤 Exporter logs",
                                   command=self.export_logs,
                                   bg=self.colors['secondary'],
                                   fg='white',
                                   font=('Segoe UI', 9),
                                   relief='flat',
                                   pady=5,
                                   cursor='hand2')
        export_log_btn.pack(side=tk.RIGHT)

    def setup_right_panel(self, parent):
        """Configurer le panel droit avec onglets modernes"""
        # Notebook avec style
        style = ttk.Style()
        style.configure('Custom.TNotebook', background=self.colors['bg_light'])
        style.configure('Custom.TNotebook.Tab',
                        padding=[15, 5],
                        font=('Segoe UI', 10, 'bold'))

        self.notebook = ttk.Notebook(parent, style='Custom.TNotebook')
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Onglet 1: Matches
        self.matches_tab = tk.Frame(self.notebook, bg=self.colors['bg_light'])
        self.notebook.add(self.matches_tab, text='⚽  Matches')
        self.setup_matches_tab(self.matches_tab)

        # Onglet 2: Classement
        self.standings_tab = tk.Frame(self.notebook, bg=self.colors['bg_light'])
        self.notebook.add(self.standings_tab, text='📈  Classement')
        self.setup_standings_tab(self.standings_tab)

        # Onglet 3: Statistiques Avancées
        self.stats_tab = tk.Frame(self.notebook, bg=self.colors['bg_light'])
        self.notebook.add(self.stats_tab, text='📊  Statistiques')
        self.setup_stats_tab(self.stats_tab)

        # Onglet 4: Visualisations
        self.visual_tab = tk.Frame(self.notebook, bg=self.colors['bg_light'])
        self.notebook.add(self.visual_tab, text='📉  Visualisations')
        self.setup_visual_tab(self.visual_tab)

        # Onglet 5: Recherche
        self.search_tab = tk.Frame(self.notebook, bg=self.colors['bg_light'])
        self.notebook.add(self.search_tab, text='🔍  Recherche')
        self.setup_search_tab(self.search_tab)

    def setup_matches_tab(self, parent):
        """Configurer l'onglet matches avec interface moderne"""
        # Contrôles supérieurs
        control_frame = tk.Frame(parent, bg=self.colors['bg_light'], padx=20, pady=15)
        control_frame.pack(fill=tk.X)

        # Filtres
        filter_frame = tk.Frame(control_frame, bg=self.colors['bg_light'])
        filter_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(filter_frame,
                 text="Filtrer par date:",
                 font=('Segoe UI', 10),
                 bg=self.colors['bg_light']).pack(side=tk.LEFT, padx=(0, 10))

        self.filter_date_var = tk.StringVar(value=datetime.now().strftime('%Y-%m-%d'))
        self.filter_date_entry = ttk.Entry(filter_frame,
                                           textvariable=self.filter_date_var,
                                           width=12,
                                           font=('Segoe UI', 10))
        self.filter_date_entry.pack(side=tk.LEFT, padx=(0, 10))

        # Boutons de filtrage
        btn_frame = tk.Frame(filter_frame, bg=self.colors['bg_light'])
        btn_frame.pack(side=tk.LEFT)

        filter_btn = tk.Button(btn_frame,
                               text="🔍 Filtrer",
                               command=self.filter_matches,
                               bg=self.colors['primary'],
                               fg='white',
                               font=('Segoe UI', 9),
                               relief='flat',
                               padx=15,
                               cursor='hand2')
        filter_btn.pack(side=tk.LEFT, padx=2)

        show_all_btn = tk.Button(btn_frame,
                                 text="🔄 Tous les matches",
                                 command=self.show_all_matches,
                                 bg=self.colors['secondary'],
                                 fg='white',
                                 font=('Segoe UI', 9),
                                 relief='flat',
                                 padx=15,
                                 cursor='hand2')
        show_all_btn.pack(side=tk.LEFT, padx=2)

        # Stats rapides
        stats_frame = tk.Frame(control_frame, bg=self.colors['bg_light'])
        stats_frame.pack(side=tk.RIGHT)

        self.matches_stats_label = tk.Label(stats_frame,
                                            text="0 matches chargés",
                                            font=('Segoe UI', 10, 'bold'),
                                            bg=self.colors['bg_light'],
                                            fg=self.colors['text_dark'])
        self.matches_stats_label.pack()

        # Treeview avec style
        tree_container = tk.Frame(parent, bg=self.colors['bg_light'], padx=20,
                                  pady=10)  # CORRIGÉ: pady=10 au lieu de pady=(0, 20)
        tree_container.pack(fill=tk.BOTH, expand=True)

        # Création du treeview avec colonnes colorées
        self.matches_tree = ttk.Treeview(tree_container,
                                         columns=('Date', 'Domicile', 'Score', 'Extérieur',
                                                  'Statut', 'Journée', 'Lieu', 'Arbitre'),
                                         show='headings',
                                         height=20,
                                         style='Custom.Treeview')

        # Configuration des colonnes avec largeurs adaptatives
        columns = [
            ('Date', 150, 'center'),
            ('Domicile', 180, 'w'),
            ('Score', 100, 'center'),
            ('Extérieur', 180, 'w'),
            ('Statut', 120, 'center'),
            ('Journée', 100, 'center'),
            ('Lieu', 180, 'w'),
            ('Arbitre', 150, 'w')
        ]

        for col, width, anchor in columns:
            self.matches_tree.heading(col, text=col)
            self.matches_tree.column(col, width=width, anchor=anchor)

        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.matches_tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_container, orient=tk.HORIZONTAL, command=self.matches_tree.xview)

        self.matches_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # Placement des éléments
        self.matches_tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')

        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

        # Double-clic pour détails
        self.matches_tree.bind('<Double-1>', self.show_match_details)

        # Menu contextuel
        self.matches_menu = tk.Menu(self.root, tearoff=0)
        self.matches_menu.add_command(label="📋 Copier les données", command=self.copy_match_data)
        self.matches_menu.add_command(label="📊 Voir statistiques match", command=self.show_match_stats)
        self.matches_tree.bind('<Button-3>', self.show_matches_context_menu)

    def setup_standings_tab(self, parent):
        """Configurer l'onglet classement"""
        # Header avec informations
        header_frame = tk.Frame(parent, bg=self.colors['bg_light'], padx=20, pady=15)
        header_frame.pack(fill=tk.X)

        self.standings_title = tk.Label(header_frame,
                                        text="Classement - ",
                                        font=('Segoe UI', 14, 'bold'),
                                        bg=self.colors['bg_light'],
                                        fg=self.colors['primary'])
        self.standings_title.pack(side=tk.LEFT)

        self.standings_info = tk.Label(header_frame,
                                       text="Chargement...",
                                       font=('Segoe UI', 10),
                                       bg=self.colors['bg_light'],
                                       fg=self.colors['text_light'])
        self.standings_info.pack(side=tk.RIGHT)

        # Conteneur pour le treeview
        tree_container = tk.Frame(parent, bg=self.colors['bg_light'], padx=20, pady=10)  # CORRIGÉ
        tree_container.pack(fill=tk.BOTH, expand=True)

        self.standings_tree = ttk.Treeview(tree_container,
                                           columns=('Pos', 'Équipe', 'Pts', 'MJ', 'G', 'N', 'P',
                                                    'BP', 'BC', 'Diff', 'Form'),
                                           show='headings',
                                           height=20)

        # Configuration des colonnes
        columns = [
            ('Pos', 50, 'center'),
            ('Équipe', 200, 'w'),
            ('Pts', 50, 'center'),
            ('MJ', 50, 'center'),
            ('G', 40, 'center'),
            ('N', 40, 'center'),
            ('P', 40, 'center'),
            ('BP', 50, 'center'),
            ('BC', 50, 'center'),
            ('Diff', 60, 'center'),
            ('Form', 100, 'center')
        ]

        for col, width, anchor in columns:
            self.standings_tree.heading(col, text=col)
            self.standings_tree.column(col, width=width, anchor=anchor)

        # Scrollbar
        scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.standings_tree.yview)
        self.standings_tree.configure(yscrollcommand=scrollbar.set)

        self.standings_tree.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns')

        tree_container.grid_rowconfigure(0, weight=1)
        tree_container.grid_columnconfigure(0, weight=1)

    def setup_stats_tab(self, parent):
        """Configurer l'onglet statistiques avancées"""
        # Notebook pour différentes catégories de stats
        stats_notebook = ttk.Notebook(parent)
        stats_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Statistiques générales
        general_frame = tk.Frame(stats_notebook, bg=self.colors['bg_light'])
        stats_notebook.add(general_frame, text='📈 Générales')
        self.setup_general_stats(general_frame)

        # Statistiques par équipe
        team_frame = tk.Frame(stats_notebook, bg=self.colors['bg_light'])
        stats_notebook.add(team_frame, text='👥 Par Équipe')
        self.setup_team_stats(team_frame)

        # Statistiques temporelles
        temporal_frame = tk.Frame(stats_notebook, bg=self.colors['bg_light'])
        stats_notebook.add(temporal_frame, text='📅 Temporelles')
        self.setup_temporal_stats(temporal_frame)

    def setup_general_stats(self, parent):
        """Configurer les statistiques générales"""
        # Utiliser un canvas pour le défilement
        canvas = tk.Canvas(parent, bg=self.colors['bg_light'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['bg_light'])

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Titre
        tk.Label(scrollable_frame,
                 text="📊 Statistiques Générales",
                 font=('Segoe UI', 16, 'bold'),
                 bg=self.colors['bg_light'],
                 fg=self.colors['primary']).pack(pady=20)

        # Grille de statistiques
        self.stats_grid = tk.Frame(scrollable_frame, bg=self.colors['bg_light'])
        self.stats_grid.pack(fill=tk.X, padx=20)

        # Les statistiques seront remplies par update_stats_display
        self.stats_labels = {}

    def setup_team_stats(self, parent):
        """Configurer les statistiques par équipe"""
        # Frame pour les contrôles
        control_frame = tk.Frame(parent, bg=self.colors['bg_light'], padx=20, pady=10)
        control_frame.pack(fill=tk.X)

        tk.Label(control_frame,
                 text="Sélectionner une équipe:",
                 font=('Segoe UI', 10),
                 bg=self.colors['bg_light']).pack(side=tk.LEFT, padx=(0, 10))

        self.team_var = tk.StringVar()
        self.team_combo = ttk.Combobox(control_frame,
                                       textvariable=self.team_var,
                                       state='readonly',
                                       width=25,
                                       font=('Segoe UI', 10))
        self.team_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.team_combo.bind('<<ComboboxSelected>>', self.on_team_selected)

        # Zone d'affichage des stats d'équipe
        self.team_stats_text = scrolledtext.ScrolledText(parent,
                                                         wrap=tk.WORD,
                                                         font=('Consolas', 10),
                                                         bg='#f8f9fa',
                                                         height=20)
        self.team_stats_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)  # CORRIGÉ

    def setup_temporal_stats(self, parent):
        """Configurer les statistiques temporelles"""
        container = tk.Frame(parent, bg=self.colors['bg_light'])
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Titre
        tk.Label(container,
                 text="📈 Évolution dans le temps",
                 font=('Segoe UI', 14, 'bold'),
                 bg=self.colors['bg_light'],
                 fg=self.colors['primary']).pack(pady=(0, 20))

        # Frame pour les graphiques
        self.temporal_charts_frame = tk.Frame(container, bg=self.colors['bg_light'])
        self.temporal_charts_frame.pack(fill=tk.BOTH, expand=True)

        # Texte d'information
        self.temporal_info = tk.Label(container,
                                      text="Utilisez les boutons pour générer des graphiques",
                                      font=('Segoe UI', 10),
                                      bg=self.colors['bg_light'],
                                      fg=self.colors['text_light'])
        self.temporal_info.pack(pady=10)

        # Boutons pour générer différents graphiques
        btn_frame = tk.Frame(container, bg=self.colors['bg_light'])
        btn_frame.pack(pady=10)

        chart_buttons = [
            ("📊 Buts par journée", self.show_goals_per_matchday),
            ("⚽ Moyenne de buts", self.show_average_goals),
            ("🏠/✈ Forme à domicile/extérieur", self.show_home_away_stats),
            ("🎯 Distribution des scores", self.show_score_distribution)
        ]

        for text, command in chart_buttons:
            btn = tk.Button(btn_frame,
                            text=text,
                            command=command,
                            bg=self.colors['primary'],
                            fg='white',
                            font=('Segoe UI', 9),
                            relief='flat',
                            padx=15,
                            pady=8,
                            cursor='hand2')
            btn.pack(side=tk.LEFT, padx=5)

    def setup_visual_tab(self, parent):
        """Configurer l'onglet visualisations"""
        container = tk.Frame(parent, bg=self.colors['bg_light'])
        container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Titre
        tk.Label(container,
                 text="📉 Visualisations Graphiques",
                 font=('Segoe UI', 16, 'bold'),
                 bg=self.colors['bg_light'],
                 fg=self.colors['primary']).pack(pady=(0, 20))

        # Sélection du type de graphique
        chart_frame = tk.Frame(container, bg=self.colors['bg_light'])
        chart_frame.pack(fill=tk.X, pady=10)

        tk.Label(chart_frame,
                 text="Type de graphique:",
                 font=('Segoe UI', 11),
                 bg=self.colors['bg_light']).pack(side=tk.LEFT, padx=(0, 10))

        self.chart_type_var = tk.StringVar(value='classement')
        chart_types = [
            ('Classement', 'classement'),
            ('Buts marqués', 'buts'),
            ('Victoires/Défaites', 'victoires'),
            ('Forme des équipes', 'forme'),
            ('Distribution scores', 'distribution')
        ]

        for text, value in chart_types:
            rb = tk.Radiobutton(chart_frame,
                                text=text,
                                variable=self.chart_type_var,
                                value=value,
                                bg=self.colors['bg_light'],
                                font=('Segoe UI', 10),
                                command=self.update_chart)
            rb.pack(side=tk.LEFT, padx=5)

        # Bouton de génération
        generate_btn = tk.Button(container,
                                 text="🔄 Générer Graphique",
                                 command=self.generate_chart,
                                 bg=self.colors['secondary'],
                                 fg='white',
                                 font=('Segoe UI', 11, 'bold'),
                                 relief='flat',
                                 padx=25,
                                 pady=10,
                                 cursor='hand2')
        generate_btn.pack(pady=15)

        # Frame pour le graphique
        self.chart_frame = tk.Frame(container, bg='white', relief='sunken', borderwidth=1)
        self.chart_frame.pack(fill=tk.BOTH, expand=True)

        # Texte d'information
        self.chart_info = tk.Label(container,
                                   text="Sélectionnez un type de graphique et cliquez sur Générer",
                                   font=('Segoe UI', 10),
                                   bg=self.colors['bg_light'],
                                   fg=self.colors['text_light'])
        self.chart_info.pack(pady=10)

    def setup_search_tab(self, parent):
        """Configurer l'onglet recherche avancée"""
        # Frame de recherche
        search_frame = tk.Frame(parent, bg=self.colors['bg_light'], padx=20, pady=20)
        search_frame.pack(fill=tk.X)

        # Titre
        tk.Label(search_frame,
                 text="🔍 Recherche Avancée",
                 font=('Segoe UI', 16, 'bold'),
                 bg=self.colors['bg_light'],
                 fg=self.colors['primary']).pack(pady=(0, 20))

        # Critères de recherche
        criteria_frame = tk.Frame(search_frame, bg=self.colors['bg_light'])
        criteria_frame.pack(fill=tk.X, pady=10)

        # Équipe
        tk.Label(criteria_frame,
                 text="Équipe:",
                 font=('Segoe UI', 10),
                 bg=self.colors['bg_light']).grid(row=0, column=0, sticky='w', padx=(0, 10), pady=5)

        self.search_team_var = tk.StringVar()
        ttk.Entry(criteria_frame,
                  textvariable=self.search_team_var,
                  width=25).grid(row=0, column=1, padx=(0, 20), pady=5, sticky='w')

        # Date
        tk.Label(criteria_frame,
                 text="Date (YYYY-MM-DD):",
                 font=('Segoe UI', 10),
                 bg=self.colors['bg_light']).grid(row=0, column=2, sticky='w', padx=(0, 10), pady=5)

        self.search_date_var = tk.StringVar()
        ttk.Entry(criteria_frame,
                  textvariable=self.search_date_var,
                  width=15).grid(row=0, column=3, pady=5, sticky='w')

        # Statut
        tk.Label(criteria_frame,
                 text="Statut:",
                 font=('Segoe UI', 10),
                 bg=self.colors['bg_light']).grid(row=1, column=0, sticky='w', padx=(0, 10), pady=5)

        self.search_status_var = tk.StringVar(value="Tous")
        status_combo = ttk.Combobox(criteria_frame,
                                    textvariable=self.search_status_var,
                                    values=["Tous", "finished", "scheduled", "live", "postponed"],
                                    width=15,
                                    state='readonly')
        status_combo.grid(row=1, column=1, padx=(0, 20), pady=5, sticky='w')

        # Score minimum
        tk.Label(criteria_frame,
                 text="Buts min par match:",
                 font=('Segoe UI', 10),
                 bg=self.colors['bg_light']).grid(row=1, column=2, sticky='w', padx=(0, 10), pady=5)

        self.search_goals_var = tk.StringVar()
        ttk.Entry(criteria_frame,
                  textvariable=self.search_goals_var,
                  width=5).grid(row=1, column=3, pady=5, sticky='w')

        # Bouton de recherche
        search_btn = tk.Button(search_frame,
                               text="🔍 Lancer la recherche",
                               command=self.advanced_search,
                               bg=self.colors['primary'],
                               fg='white',
                               font=('Segoe UI', 11, 'bold'),
                               relief='flat',
                               padx=30,
                               pady=10,
                               cursor='hand2')
        search_btn.pack(pady=15)

        # Résultats
        results_frame = tk.Frame(parent, bg=self.colors['bg_light'], padx=20, pady=10)  # CORRIGÉ
        results_frame.pack(fill=tk.BOTH, expand=True)

        # En-tête des résultats
        results_header = tk.Frame(results_frame, bg=self.colors['bg_light'])
        results_header.pack(fill=tk.X, pady=(0, 10))

        self.results_count_label = tk.Label(results_header,
                                            text="0 résultats",
                                            font=('Segoe UI', 11, 'bold'),
                                            bg=self.colors['bg_light'],
                                            fg=self.colors['text_dark'])
        self.results_count_label.pack(side=tk.LEFT)

        export_results_btn = tk.Button(results_header,
                                       text="📤 Exporter résultats",
                                       command=self.export_search_results,
                                       bg=self.colors['secondary'],
                                       fg='white',
                                       font=('Segoe UI', 9),
                                       relief='flat',
                                       padx=15,
                                       cursor='hand2')
        export_results_btn.pack(side=tk.RIGHT)

        # Treeview pour les résultats
        self.search_tree = ttk.Treeview(results_frame,
                                        columns=('Date', 'Domicile', 'Score', 'Extérieur',
                                                 'Statut', 'Journée', 'Buts Total'),
                                        show='headings',
                                        height=15)

        columns = [
            ('Date', 120, 'center'),
            ('Domicile', 150, 'w'),
            ('Score', 100, 'center'),
            ('Extérieur', 150, 'w'),
            ('Statut', 100, 'center'),
            ('Journée', 80, 'center'),
            ('Buts Total', 100, 'center')
        ]

        for col, width, anchor in columns:
            self.search_tree.heading(col, text=col)
            self.search_tree.column(col, width=width, anchor=anchor)

        # Scrollbars
        v_scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.search_tree.yview)
        h_scrollbar = ttk.Scrollbar(results_frame, orient=tk.HORIZONTAL, command=self.search_tree.xview)

        self.search_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        self.search_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

    def setup_status_bar(self):
        """Configurer la barre de status moderne"""
        self.status_bar = tk.Frame(self.root,
                                   bg=self.colors['bg_dark'],
                                   height=30,
                                   relief='flat',
                                   borderwidth=1)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.status_bar.pack_propagate(False)

        # Status label
        self.status_label = tk.Label(self.status_bar,
                                     text="Prêt",
                                     font=('Segoe UI', 9),
                                     bg=self.colors['bg_dark'],
                                     fg=self.colors['text_light'],
                                     anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        # Progress bar
        self.progress_bar = ttk.Progressbar(self.status_bar, mode='indeterminate')

        # Memory usage
        self.memory_label = tk.Label(self.status_bar,
                                     text="",
                                     font=('Segoe UI', 9),
                                     bg=self.colors['bg_dark'],
                                     fg=self.colors['text_light'])
        self.memory_label.pack(side=tk.RIGHT, padx=10)

    def darken_color(self, color):
        """Assombrir une couleur hexadécimale"""
        try:
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)

            r = max(0, r - 30)
            g = max(0, g - 30)
            b = max(0, b - 30)

            return f'#{r:02x}{g:02x}{b:02x}'
        except:
            return color

    def check_api_status(self):
        """Vérifier le statut de l'API"""

        def check():
            is_connected = self.scraper.test_connection()
            if is_connected:
                self.queue.put(('status', "✅ API connectée"))
                self.queue.put(('log', "Connexion API réussie"))
            else:
                self.queue.put(('status', "⚠️ API non connectée"))
                self.queue.put(('log', "Échec connexion API", 'warning'))

        threading.Thread(target=check, daemon=True).start()

    def load_initial_data(self):
        """Charger les données initiales"""
        # Charger les statistiques de la DB
        self.show_db_stats()
        self.update_quick_stats()

    def on_championship_changed(self, event=None):
        """Quand le championnat change"""
        self.current_championship = self.championship_var.get()

        # Mettre à jour le drapeau
        emoji = Config.CHAMPIONSHIP_EMOJIS.get(self.current_championship, "🏆")
        self.flag_label.config(text=emoji)

        self.log(f"Championnat sélectionné: {self.current_championship}")

        # Mettre à jour les stats rapides
        self.update_quick_stats()

    def scrape_with_progress(self):
        """Scraper avec progression pour les longues périodes"""
        if self.is_scraping:
            messagebox.showwarning("Attention", "Une opération est déjà en cours!")
            return

        championship = self.championship_var.get()
        date_from = self.date_from_var.get()
        date_to = self.date_to_var.get()

        # Validation des dates
        try:
            start_date = datetime.strptime(date_from, '%Y-%m-%d')
            end_date = datetime.strptime(date_to, '%Y-%m-%d')
            total_days = (end_date - start_date).days + 1
        except ValueError:
            messagebox.showerror("Erreur", "Format de date invalide. Utilisez YYYY-MM-DD")
            return

        # Avertissement pour les longues périodes
        if total_days > 30:
            if not messagebox.askyesno("Confirmation",
                                       f"Vous allez scraper {total_days} jours.\n"
                                       f"Cela peut prendre plusieurs minutes.\n\n"
                                       f"Continuer?"):
                return

        def scraping_task():
            self.is_scraping = True
            self.queue.put(('progress_start', f"Scraping {championship} ({total_days} jours)..."))

            try:
                # 1. Récupérer les matches
                self.queue.put(('log', f"Récupération matches {championship} du {date_from} au {date_to}"))
                self.queue.put(('log', f"Durée: {total_days} jours - Découpage automatique..."))

                matches = self.scraper.get_matches_by_date_range(championship, date_from, date_to)

                # 2. Sauvegarder dans la base
                saved_count = 0
                if matches:
                    if self.save_to_db_var.get():
                        saved_count = self.db.save_matches_batch(matches)
                        self.db.log_scraping(championship, date_from, date_to, saved_count, 'success')

                    self.queue.put(('matches', matches))
                    self.queue.put(('log', f"✅ {len(matches)} matches récupérés"))
                else:
                    self.queue.put(('log', f"⚠️ Aucun match trouvé pour cette période", 'warning'))

                # 3. Récupérer le classement
                self.queue.put(('log', f"Récupération classement {championship}"))
                standings = self.scraper.get_standings(championship)

                if standings:
                    self.db.save_standings(championship, standings)
                    self.queue.put(('standings', standings))
                    self.queue.put(('log', f"✅ Classement: {len(standings)} équipes"))
                else:
                    self.queue.put(('log', f"⚠️ Classement non disponible", 'warning'))

                # 4. Statistiques finales
                if matches:
                    self.queue.put(('log', f"📊 RÉSUMÉ: {len(matches)} matches, {saved_count} sauvegardés"))

                    # Statistiques par statut
                    status_counts = {}
                    for match in matches:
                        status = match.get('status', 'unknown')
                        status_counts[status] = status_counts.get(status, 0) + 1

                    for status, count in status_counts.items():
                        self.queue.put(('log', f"   • {status}: {count} matches"))

                    self.queue.put(('status', f"✅ {championship}: {len(matches)} matches scrapés"))
                else:
                    self.queue.put(('status', f"⚠️ Aucun match trouvé"))
                    self.queue.put(('message', 'Information',
                                    f"Aucun match trouvé pour {championship}\n"
                                    f"Période: {date_from} au {date_to}\n\n"
                                    f"Possibilités:\n"
                                    f"1. Pas de matchs programmés\n"
                                    f"2. Période hors-saison\n"
                                    f"3. Limitation API (essayez une période plus courte)"))

            except Exception as e:
                error_msg = str(e)
                self.queue.put(('log', f"❌ Erreur scraping: {error_msg}", 'error'))
                self.queue.put(('status', "Erreur lors du scraping"))

                # Logger l'erreur dans la base
                self.db.log_scraping(championship, date_from, date_to, 0, 'error', error_msg)

                # Afficher un message utile selon le type d'erreur
                if "429" in error_msg:
                    self.queue.put(('message', 'Erreur API',
                                    "Limite de requêtes API atteinte.\n"
                                    "Attendez 1 minute puis réessayez."))
                elif "403" in error_msg:
                    self.queue.put(('message', 'Erreur API',
                                    "Clé API invalide ou expirée.\n"
                                    "Vérifiez votre clé dans le fichier .env"))
                else:
                    self.queue.put(('message', 'Erreur', f"Erreur: {error_msg}"))

            finally:
                self.queue.put(('progress_stop', ''))
                self.is_scraping = False

        threading.Thread(target=scraping_task, daemon=True).start()

    def scrape_season(self):
        """Scraper une saison complète"""
        championship = self.championship_var.get()

        # Déterminer la saison actuelle
        current_year = datetime.now().year
        season_start = f"{current_year}-08-01"
        season_end = f"{current_year + 1}-05-31"

        # Mettre à jour les champs de date
        self.date_from_var.set(season_start)
        self.date_to_var.set(season_end)

        # Confirmation
        if messagebox.askyesno("Confirmation",
                               f"Scraper la saison complète {current_year}/{current_year + 1} de {championship}?\n\n"
                               f"Cette opération peut prendre plusieurs minutes."):
            self.scrape_with_progress()

    def scrape_last_30_days(self):
        """Scraper les 30 derniers jours"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        self.date_from_var.set(start_date.strftime('%Y-%m-%d'))
        self.date_to_var.set(end_date.strftime('%Y-%m-%d'))

        self.scrape_with_progress()

    def load_from_db(self):
        """Charger les données depuis la base"""
        championship = self.championship_var.get()

        def loading_task():
            self.queue.put(('progress_start', f"Chargement {championship} depuis DB..."))

            try:
                # Charger les matches
                matches = self.db.get_matches(championship=championship, limit=100)
                self.queue.put(('matches', matches))

                # Charger le classement
                standings = self.db.get_standings(championship)
                self.queue.put(('standings', standings))

                self.queue.put(('log', f"✅ Chargé depuis DB: {len(matches)} matches, {len(standings)} équipes"))
                self.queue.put(('status', f"Données {championship} chargées"))

            except Exception as e:
                self.queue.put(('log', f"❌ Erreur chargement DB: {e}", 'error'))

            finally:
                self.queue.put(('progress_stop', ''))

        threading.Thread(target=loading_task, daemon=True).start()

    def clear_championship_data(self):
        """Effacer les données d'un championnat"""
        championship = self.championship_var.get()

        if messagebox.askyesno("Confirmation",
                               f"Effacer toutes les données de {championship}?\nCette action est irréversible!"):
            def clearing_task():
                self.queue.put(('progress_start', f"Effacement {championship}..."))

                try:
                    success = self.db.clear_championship_data(championship)
                    if success:
                        self.queue.put(('log', f"✅ Données {championship} effacées"))
                        self.queue.put(('status', f"Données {championship} effacées"))
                    else:
                        self.queue.put(('log', f"❌ Erreur effacement {championship}", 'error'))

                except Exception as e:
                    self.queue.put(('log', f"❌ Erreur: {e}", 'error'))

                finally:
                    self.queue.put(('progress_stop', ''))

            threading.Thread(target=clearing_task, daemon=True).start()

    def export_to_csv(self):
        """Exporter les données en CSV"""
        championship = self.championship_var.get()
        matches = self.db.get_matches(championship=championship, limit=1000)

        if not matches:
            messagebox.showinfo("Information", "Aucune donnée à exporter")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"football_{championship}_{datetime.now().strftime('%Y%m%d')}.csv"
        )

        if not file_path:
            return

        def export_task():
            self.queue.put(('progress_start', "Export CSV..."))

            try:
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)

                    # En-têtes
                    writer.writerow(['Date', 'Championnat', 'Domicile', 'Score', 'Extérieur',
                                     'Statut', 'Journée', 'Lieu', 'Arbitre'])

                    # Données
                    for match in matches:
                        score = f"{match.get('home_score', '')}-{match.get('away_score', '')}"
                        if match.get('home_score') is None:
                            score = 'VS'

                        writer.writerow([
                            match.get('date', '')[:10],
                            match.get('championship', ''),
                            match.get('home_team', ''),
                            score,
                            match.get('away_team', ''),
                            match.get('status', ''),
                            match.get('matchday', ''),
                            match.get('venue', ''),
                            match.get('referee', '')
                        ])

                self.queue.put(('log', f"✅ Export CSV réussi: {len(matches)} matches"))
                self.queue.put(('status', f"Export {championship} terminé"))
                self.queue.put(('message', 'Succès', f'Exporté {len(matches)} matches vers {file_path}'))

            except Exception as e:
                self.queue.put(('log', f"❌ Erreur export: {e}", 'error'))
                self.queue.put(('message', 'Erreur', f'Erreur export: {e}'))

            finally:
                self.queue.put(('progress_stop', ''))

        threading.Thread(target=export_task, daemon=True).start()

    def show_db_stats(self):
        """Afficher les statistiques de la base"""

        def stats_task():
            self.queue.put(('progress_start', "Calcul statistiques..."))

            try:
                stats = self.db.get_scraping_stats()

                stats_text = "📊 STATISTIQUES DE LA BASE DE DONNÉES\n"
                stats_text += "=" * 50 + "\n\n"

                stats_text += f"📅 Dernière mise à jour: {stats.get('last_update', 'N/A')}\n"
                stats_text += f"⚽ Total matches: {stats.get('total_matches', 0)}\n\n"

                stats_text += "Matches par championnat:\n"
                stats_text += "-" * 30 + "\n"

                for champ, count in stats.get('matches_by_championship', {}).items():
                    stats_text += f"• {champ}: {count} matches\n"

                # Ajouter l'espace disponible
                import os
                db_size = os.path.getsize(Config.DB_PATH) if os.path.exists(Config.DB_PATH) else 0
                stats_text += f"\n💾 Taille DB: {db_size / 1024 / 1024:.2f} MB\n"

                self.queue.put(('stats', stats_text))
                self.queue.put(('log', "Statistiques DB calculées"))

            except Exception as e:
                self.queue.put(('log', f"❌ Erreur stats: {e}", 'error'))

            finally:
                self.queue.put(('progress_stop', ''))

        threading.Thread(target=stats_task, daemon=True).start()

    def filter_matches(self):
        """Filtrer les matches par date"""
        date_str = self.filter_date_var.get()

        def filter_task():
            self.queue.put(('progress_start', "Filtrage matches..."))

            try:
                matches = self.db.get_matches(
                    championship=self.current_championship,
                    date_from=date_str,
                    date_to=date_str,
                    limit=50
                )

                self.queue.put(('matches', matches))
                self.queue.put(('log', f"Filtré: {len(matches)} matches pour {date_str}"))

            except Exception as e:
                self.queue.put(('log', f"❌ Erreur filtrage: {e}", 'error'))

            finally:
                self.queue.put(('progress_stop', ''))

        threading.Thread(target=filter_task, daemon=True).start()

    def show_all_matches(self):
        """Afficher tous les matches"""

        def load_task():
            self.queue.put(('progress_start', "Chargement matches..."))

            try:
                matches = self.db.get_matches(
                    championship=self.current_championship,
                    limit=100
                )

                self.queue.put(('matches', matches))
                self.queue.put(('log', f"Chargé: {len(matches)} matches"))

            except Exception as e:
                self.queue.put(('log', f"❌ Erreur chargement: {e}", 'error'))

            finally:
                self.queue.put(('progress_stop', ''))

        threading.Thread(target=load_task, daemon=True).start()

    def show_match_details(self, event):
        """Afficher les détails d'un match"""
        selection = self.matches_tree.selection()
        if not selection:
            return

        item = self.matches_tree.item(selection[0])
        match_id = item['values'][0]

        # Rechercher le match dans les données chargées
        # (Dans une version complète, on irait chercher dans la DB)
        messagebox.showinfo("Détails Match",
                            f"Détails pour le match ID: {match_id}\n\n"
                            f"Fonctionnalité à implémenter: récupération complète depuis la DB")

    def advanced_search(self):
        """Recherche avancée avec plusieurs critères"""
        team = self.search_team_var.get().strip()
        date = self.search_date_var.get().strip()
        status = self.search_status_var.get()
        min_goals = self.search_goals_var.get().strip()

        def search_task():
            self.queue.put(('progress_start', "Recherche en cours..."))

            try:
                # Récupérer tous les matches du championnat actuel
                matches = self.db.get_matches(championship=self.current_championship, limit=500)

                # Appliquer les filtres
                filtered_matches = []

                for match in matches:
                    include = True

                    # Filtre équipe
                    if team:
                        if team.lower() not in match.get('home_team', '').lower() and \
                                team.lower() not in match.get('away_team', '').lower():
                            include = False

                    # Filtre date
                    if date:
                        match_date = match.get('date', '')[:10]
                        if match_date != date:
                            include = False

                    # Filtre statut
                    if status != "Tous":
                        match_status = match.get('status', '')
                        if match_status != status:
                            include = False

                    # Filtre buts minimum
                    if min_goals and match.get('status') == 'finished':
                        try:
                            min_g = int(min_goals)
                            home = match.get('home_score', 0) or 0
                            away = match.get('away_score', 0) or 0
                            total = home + away
                            if total < min_g:
                                include = False
                        except ValueError:
                            pass

                    if include:
                        filtered_matches.append(match)

                # Mettre à jour l'interface
                self.queue.put(('search_results', filtered_matches))
                self.queue.put(('log', f"Recherche: {len(filtered_matches)} résultats trouvés"))

            except Exception as e:
                self.queue.put(('log', f"❌ Erreur recherche: {e}", 'error'))

            finally:
                self.queue.put(('progress_stop', ''))

        threading.Thread(target=search_task, daemon=True).start()

    def export_search_results(self):
        """Exporter les résultats de recherche"""
        # Vérifier s'il y a des résultats
        items = self.search_tree.get_children()
        if not items:
            messagebox.showinfo("Information", "Aucun résultat à exporter")
            return

        # Demander le fichier de destination
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialfile=f"recherche_{self.current_championship}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        if not file_path:
            return

        def export_task():
            self.queue.put(('progress_start', "Export des résultats..."))

            try:
                # Collecter les données
                data = []
                for item in items:
                    values = self.search_tree.item(item)['values']
                    data.append(values)

                # Exporter selon le format
                if file_path.endswith('.csv'):
                    with open(file_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        writer.writerow(['Date', 'Domicile', 'Score', 'Extérieur',
                                         'Statut', 'Journée', 'Buts Total'])
                        writer.writerows(data)
                elif file_path.endswith('.xlsx'):
                    import pandas as pd
                    df = pd.DataFrame(data, columns=['Date', 'Domicile', 'Score', 'Extérieur',
                                                     'Statut', 'Journée', 'Buts Total'])
                    df.to_excel(file_path, index=False)

                self.queue.put(('log', f"✅ Export réussi: {len(data)} résultats"))
                self.queue.put(('message', 'Succès', f'Exporté vers {file_path}'))

            except Exception as e:
                self.queue.put(('log', f"❌ Erreur export: {e}", 'error'))

            finally:
                self.queue.put(('progress_stop', ''))

        threading.Thread(target=export_task, daemon=True).start()

    def clear_logs(self):
        """Effacer les logs"""
        self.log_text.delete(1.0, tk.END)
        self.log("Logs effacés")

    def export_logs(self):
        """Exporter les logs"""
        logs = self.log_text.get(1.0, tk.END)
        if not logs.strip():
            messagebox.showinfo("Information", "Aucun log à exporter")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("Log files", "*.log"), ("All files", "*.*")],
            initialfile=f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )

        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(logs)
            self.log(f"Logs exportés vers {file_path}")

    def refresh_data(self):
        """Rafraîchir les données"""
        self.load_initial_data()
        self.show_all_matches()
        self.log("Données rafraîchies")

    def copy_match_data(self):
        """Copier les données du match sélectionné"""
        selection = self.matches_tree.selection()
        if selection:
            item = self.matches_tree.item(selection[0])
            data = "\t".join(str(x) for x in item['values'])
            self.root.clipboard_clear()
            self.root.clipboard_append(data)
            self.log("Données copiées dans le presse-papier")

    def show_match_stats(self):
        """Afficher les statistiques détaillées d'un match"""
        selection = self.matches_tree.selection()
        if not selection:
            return

        item = self.matches_tree.item(selection[0])
        match_data = item['values']

        # Créer une fenêtre de détails
        details_window = tk.Toplevel(self.root)
        details_window.title("📊 Statistiques du Match")
        details_window.geometry("600x400")
        details_window.configure(bg=self.colors['bg_light'])

        # Titre
        tk.Label(details_window,
                 text=f"{match_data[1]} vs {match_data[3]}",
                 font=('Segoe UI', 16, 'bold'),
                 bg=self.colors['bg_light'],
                 fg=self.colors['primary']).pack(pady=20)

        # Informations détaillées
        info_frame = tk.Frame(details_window, bg=self.colors['bg_light'], padx=20)
        info_frame.pack(fill=tk.BOTH, expand=True)

        infos = [
            ("📅 Date", match_data[0]),
            ("🏟️ Lieu", match_data[6]),
            ("👨‍⚖️ Arbitre", match_data[7]),
            ("📊 Journée", match_data[5]),
            ("📈 Statut", match_data[4])
        ]

        for label, value in infos:
            frame = tk.Frame(info_frame, bg=self.colors['bg_light'])
            frame.pack(fill=tk.X, pady=5)

            tk.Label(frame, text=label, font=('Segoe UI', 10, 'bold'),
                     bg=self.colors['bg_light'], width=15, anchor='w').pack(side=tk.LEFT)
            tk.Label(frame, text=value, font=('Segoe UI', 10),
                     bg=self.colors['bg_light']).pack(side=tk.LEFT)

    def show_matches_context_menu(self, event):
        """Afficher le menu contextuel pour les matches"""
        try:
            self.matches_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.matches_menu.grab_release()

    def update_quick_stats(self):
        """Mettre à jour les statistiques rapides"""
        try:
            stats = self.db.get_scraping_stats()

            # Mettre à jour les labels
            if 'total_matches' in stats:
                self.quick_stats_labels['matches'].config(text=str(stats['total_matches']))

            # Compter les équipes uniques
            matches = self.db.get_matches(championship=self.current_championship, limit=1000)
            teams = set()
            for match in matches:
                teams.add(match.get('home_team', ''))
                teams.add(match.get('away_team', ''))
            self.quick_stats_labels['équipes'].config(text=str(len(teams)))

            # Compter les journées uniques
            matchdays = set()
            for match in matches:
                matchday = match.get('matchday')
                if matchday:
                    matchdays.add(matchday)
            self.quick_stats_labels['journées'].config(text=str(len(matchdays)))

            # Dernière mise à jour
            if 'last_update' in stats and stats['last_update']:
                last_date = stats['last_update'][:10]
                self.quick_stats_labels['mise à jour'].config(text=last_date)

        except Exception as e:
            self.log(f"Erreur mise à jour stats rapides: {e}", 'error')

    def update_stats_display(self):
        """Mettre à jour l'affichage des statistiques"""
        if not self.current_matches:
            return

        try:
            # Statistiques générales
            total_matches = len(self.current_matches)
            finished_matches = sum(1 for m in self.current_matches if m.get('status') == 'finished')
            scheduled_matches = sum(1 for m in self.current_matches if m.get('status') == 'scheduled')

            # Calcul des buts
            total_goals = 0
            home_goals = 0
            away_goals = 0

            for match in self.current_matches:
                if match.get('status') == 'finished':
                    home = match.get('home_score', 0) or 0
                    away = match.get('away_score', 0) or 0
                    total_goals += home + away
                    home_goals += home
                    away_goals += away

            avg_goals = total_goals / finished_matches if finished_matches > 0 else 0

            # Nettoyer l'ancienne grille
            for widget in self.stats_grid.winfo_children():
                widget.destroy()

            # Créer les cartes de statistiques
            stats_cards = [
                ("Matches Totaux", f"{total_matches}", "📊", self.colors['primary']),
                ("Terminés", f"{finished_matches}", "✅", "#34a853"),
                ("Programmés", f"{scheduled_matches}", "📅", "#fbbc05"),
                ("Buts Totaux", f"{total_goals}", "⚽", "#ea4335"),
                ("Buts Domicile", f"{home_goals}", "🏠", "#9c27b0"),
                ("Buts Extérieur", f"{away_goals}", "✈️", "#00bcd4"),
                ("Moyenne Buts/Match", f"{avg_goals:.2f}", "📈", "#ff9800"),
                ("% Victoire Domicile", "Calcul...", "📊", "#4caf50")
            ]

            # Afficher les cartes
            for i, (title, value, icon, color) in enumerate(stats_cards):
                row = i // 4
                col = i % 4

                card = tk.Frame(self.stats_grid,
                                bg='white',
                                relief='raised',
                                borderwidth=1)
                card.grid(row=row, column=col, padx=5, pady=5, sticky='nsew')
                self.stats_grid.columnconfigure(col, weight=1)

                # Icône
                tk.Label(card, text=icon, font=('Segoe UI', 24),
                         bg='white', fg=color).pack(pady=(10, 5))

                # Valeur
                tk.Label(card, text=value, font=('Segoe UI', 18, 'bold'),
                         bg='white').pack()

                # Titre
                tk.Label(card, text=title, font=('Segoe UI', 9),
                         bg='white', fg=self.colors['text_light']).pack(pady=(0, 10))

        except Exception as e:
            self.log(f"Erreur mise à jour stats: {e}", 'error')

    def on_team_selected(self, event=None):
        """Quand une équipe est sélectionnée dans les stats"""
        team = self.team_var.get()
        if not team:
            return

        # Récupérer les statistiques de l'équipe
        matches = self.db.get_matches(championship=self.current_championship, limit=200)

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

                if team in [home_team, away_team]:
                    team_stats['total_matches'] += 1

                    home_score = match.get('home_score', 0) or 0
                    away_score = match.get('away_score', 0) or 0

                    if team == home_team:
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

                    else:  # team == away_team
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
        self.team_stats_text.delete(1.0, tk.END)

        stats_text = f"📊 STATISTIQUES DE {team}\n"
        stats_text += "=" * 50 + "\n\n"

        if team_stats['total_matches'] > 0:
            win_rate = (team_stats['wins'] / team_stats['total_matches']) * 100
            avg_goals_for = team_stats['goals_for'] / team_stats['total_matches']
            avg_goals_against = team_stats['goals_against'] / team_stats['total_matches']

            stats_text += f"Matches joués: {team_stats['total_matches']}\n"
            stats_text += f"Victoires: {team_stats['wins']} ({win_rate:.1f}%)\n"
            stats_text += f"Nuls: {team_stats['draws']}\n"
            stats_text += f"Défaites: {team_stats['losses']}\n\n"

            stats_text += f"Buts marqués: {team_stats['goals_for']} ({avg_goals_for:.2f}/match)\n"
            stats_text += f"Buts encaissés: {team_stats['goals_against']} ({avg_goals_against:.2f}/match)\n"
            stats_text += f"Différence: {team_stats['goals_for'] - team_stats['goals_against']}\n\n"

            stats_text += f"À domicile: {team_stats['home_matches']} matches\n"
            stats_text += f"  - Victoires: {team_stats['home_wins']}\n"
            stats_text += f"À l'extérieur: {team_stats['away_matches']} matches\n"
            stats_text += f"  - Victoires: {team_stats['away_wins']}\n"
        else:
            stats_text += "Aucune donnée disponible pour cette équipe\n"

        self.team_stats_text.insert(tk.END, stats_text)

    def update_chart(self):
        """Mettre à jour le type de graphique sélectionné"""
        pass  # Cette méthode est appelée par les radiobuttons

    def generate_chart(self):
        """Générer un graphique selon le type sélectionné"""
        chart_type = self.chart_type_var.get()

        if not self.current_standings and chart_type == 'classement':
            messagebox.showinfo("Information", "Aucun classement disponible")
            return

        if not self.current_matches and chart_type != 'classement':
            messagebox.showinfo("Information", "Aucun match disponible")
            return

        try:
            # Nettoyer le frame
            for widget in self.chart_frame.winfo_children():
                widget.destroy()

            fig = Figure(figsize=(12, 8))
            ax = fig.add_subplot(111)

            if chart_type == 'classement':
                self.generate_standings_chart(ax)
            elif chart_type == 'buts':
                self.generate_goals_chart(ax)
            elif chart_type == 'victoires':
                self.generate_wins_chart(ax)
            elif chart_type == 'forme':
                self.generate_form_chart(ax)
            elif chart_type == 'distribution':
                self.generate_distribution_chart(ax)

            # Afficher le graphique
            canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

            self.chart_info.config(text=f"Graphique '{chart_type}' généré avec succès")

        except Exception as e:
            self.log(f"Erreur génération graphique: {e}", 'error')
            self.chart_info.config(text=f"Erreur: {str(e)}")

    def generate_standings_chart(self, ax):
        """Générer un graphique de classement"""
        teams = [s.get('team', '') for s in self.current_standings[:10]]
        points = [s.get('points', 0) for s in self.current_standings[:10]]

        colors = plt.cm.Set3(range(len(teams)))

        bars = ax.barh(teams, points, color=colors)
        ax.set_xlabel('Points')
        ax.set_title(f'Top 10 - Classement {self.current_championship}')

        # Ajouter les valeurs sur les barres
        for bar, point in zip(bars, points):
            width = bar.get_width()
            ax.text(width + 1, bar.get_y() + bar.get_height() / 2,
                    f'{point}', ha='left', va='center')

    def generate_goals_chart(self, ax):
        """Générer un graphique des buts"""
        # Calculer les buts par équipe
        team_goals = {}

        for match in self.current_matches:
            if match.get('status') == 'finished':
                home = match.get('home_team')
                away = match.get('away_team')
                home_score = match.get('home_score', 0) or 0
                away_score = match.get('away_score', 0) or 0

                team_goals[home] = team_goals.get(home, 0) + home_score
                team_goals[away] = team_goals.get(away, 0) + away_score

        # Prendre le top 10
        sorted_teams = sorted(team_goals.items(), key=lambda x: x[1], reverse=True)[:10]
        teams = [t[0] for t in sorted_teams]
        goals = [t[1] for t in sorted_teams]

        ax.bar(teams, goals, color=self.colors['primary'])
        ax.set_xlabel('Équipes')
        ax.set_ylabel('Buts marqués')
        ax.set_title(f'Top 10 - Buts marqués ({self.current_championship})')
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right')

    def generate_wins_chart(self, ax):
        """Générer un graphique des victoires/défaites"""
        team_stats = {}

        for match in self.current_matches:
            if match.get('status') == 'finished':
                home = match.get('home_team')
                away = match.get('away_team')
                home_score = match.get('home_score', 0) or 0
                away_score = match.get('away_score', 0) or 0

                # Initialiser si nécessaire
                if home not in team_stats:
                    team_stats[home] = {'wins': 0, 'draws': 0, 'losses': 0}
                if away not in team_stats:
                    team_stats[away] = {'wins': 0, 'draws': 0, 'losses': 0}

                # Mettre à jour les stats
                if home_score > away_score:
                    team_stats[home]['wins'] += 1
                    team_stats[away]['losses'] += 1
                elif away_score > home_score:
                    team_stats[away]['wins'] += 1
                    team_stats[home]['losses'] += 1
                else:
                    team_stats[home]['draws'] += 1
                    team_stats[away]['draws'] += 1

        # Prendre le top 8
        sorted_teams = sorted(team_stats.items(),
                              key=lambda x: x[1]['wins'],
                              reverse=True)[:8]

        teams = [t[0] for t in sorted_teams]
        wins = [t[1]['wins'] for t in sorted_teams]
        draws = [t[1]['draws'] for t in sorted_teams]
        losses = [t[1]['losses'] for t in sorted_teams]

        x = range(len(teams))
        width = 0.25

        ax.bar([i - width for i in x], wins, width, label='Victoires', color='#4caf50')
        ax.bar(x, draws, width, label='Nuls', color='#ff9800')
        ax.bar([i + width for i in x], losses, width, label='Défaites', color='#f44336')

        ax.set_xlabel('Équipes')
        ax.set_ylabel('Nombre')
        ax.set_title(f'Top 8 - Résultats ({self.current_championship})')
        ax.set_xticks(x)
        ax.set_xticklabels(teams, rotation=45, ha='right')
        ax.legend()

    def generate_form_chart(self, ax):
        """Générer un graphique de la forme des équipes"""
        # Ceci est un exemple simplifié
        if not self.current_standings:
            return

        teams = [s.get('team', '') for s in self.current_standings[:6]]

        # Générer des données de forme aléatoires pour l'exemple
        import random
        form_data = []

        for team in teams:
            # 5 derniers matchs simulés (1=victoire, 0=nul, -1=défaite)
            form = [random.choice([-1, 0, 1]) for _ in range(5)]
            form_data.append(form)

        # Créer un heatmap
        im = ax.imshow(form_data, cmap='RdYlGn', aspect='auto')

        ax.set_xlabel('5 derniers matchs')
        ax.set_ylabel('Équipes')
        ax.set_title(f'Forme des équipes ({self.current_championship})')
        ax.set_yticks(range(len(teams)))
        ax.set_yticklabels(teams)
        ax.set_xticks(range(5))
        ax.set_xticklabels(['J-4', 'J-3', 'J-2', 'J-1', 'J'])

        # Ajouter une colorbar
        plt.colorbar(im, ax=ax, ticks=[-1, 0, 1])

    def generate_distribution_chart(self, ax):
        """Générer un graphique de distribution"""
        # Collecter les scores
        scores = []
        for match in self.current_matches:
            if match.get('status') == 'finished':
                home = match.get('home_score', 0) or 0
                away = match.get('away_score', 0) or 0
                scores.append(f"{home}-{away}")

        # Compter les occurrences
        from collections import Counter
        score_counts = Counter(scores)

        # Prendre les 10 scores les plus fréquents
        common_scores = score_counts.most_common(10)

        if not common_scores:
            ax.text(0.5, 0.5, 'Pas de données disponibles',
                    ha='center', va='center', transform=ax.transAxes)
            return

        labels = [score for score, count in common_scores]
        counts = [count for score, count in common_scores]

        ax.barh(labels, counts, color=plt.cm.Paired(range(len(labels))))
        ax.set_xlabel('Nombre d\'occurrences')
        ax.set_title(f'Scores les plus fréquents ({self.current_championship})')

    def show_goals_per_matchday(self):
        """Afficher un graphique des buts par journée"""
        if not self.current_matches:
            messagebox.showinfo("Information", "Aucune donnée disponible")
            return

        # Calculer les buts par journée
        matchday_goals = {}
        for match in self.current_matches:
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

        if not matchday_goals:
            messagebox.showinfo("Information", "Pas de données de buts disponibles")
            return

        # Créer le graphique
        fig = Figure(figsize=(10, 6))
        ax = fig.add_subplot(111)

        matchdays = sorted(matchday_goals.keys())
        totals = [matchday_goals[m]['total'] for m in matchdays]
        averages = [matchday_goals[m]['total'] / matchday_goals[m]['matches'] for m in matchdays]

        x = range(len(matchdays))

        ax.bar(x, totals, alpha=0.7, label='Buts totaux', color=self.colors['primary'])
        ax.plot(x, averages, 'o-', linewidth=2, markersize=8, label='Moyenne par match', color=self.colors['accent'])

        ax.set_xlabel('Journée')
        ax.set_ylabel('Buts')
        ax.set_title(f'Buts par journée - {self.current_championship}')
        ax.set_xticks(x)
        ax.set_xticklabels([str(m) for m in matchdays])
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Afficher dans l'onglet temporal
        self.show_figure_in_frame(fig, self.temporal_charts_frame)
        self.temporal_info.config(text=f"Graphique généré - {len(matchdays)} journées analysées")

    def show_average_goals(self):
        """Afficher un graphique de la moyenne de buts"""
        if not self.current_matches:
            return

        # Calculer la moyenne de buts par équipe à domicile et à l'extérieur
        team_stats = {}

        for match in self.current_matches:
            if match.get('status') == 'finished':
                home_team = match.get('home_team')
                away_team = match.get('away_team')
                home_score = match.get('home_score', 0) or 0
                away_score = match.get('away_score', 0) or 0

                # Statistiques domicile
                if home_team not in team_stats:
                    team_stats[home_team] = {'home': {'goals': 0, 'matches': 0},
                                             'away': {'goals': 0, 'matches': 0}}
                team_stats[home_team]['home']['goals'] += home_score
                team_stats[home_team]['home']['matches'] += 1

                # Statistiques extérieur
                if away_team not in team_stats:
                    team_stats[away_team] = {'home': {'goals': 0, 'matches': 0},
                                             'away': {'goals': 0, 'matches': 0}}
                team_stats[away_team]['away']['goals'] += away_score
                team_stats[away_team]['away']['matches'] += 1

        # Préparer les données pour le top 10
        teams = list(team_stats.keys())
        home_avgs = []
        away_avgs = []

        for team in teams:
            home_matches = team_stats[team]['home']['matches']
            away_matches = team_stats[team]['away']['matches']

            home_avg = team_stats[team]['home']['goals'] / home_matches if home_matches > 0 else 0
            away_avg = team_stats[team]['away']['goals'] / away_matches if away_matches > 0 else 0

            home_avgs.append(home_avg)
            away_avgs.append(away_avg)

        # Trier par moyenne à domicile
        sorted_data = sorted(zip(teams, home_avgs, away_avgs),
                             key=lambda x: x[1], reverse=True)
        top_teams = [x[0] for x in sorted_data[:10]]
        top_home = [x[1] for x in sorted_data[:10]]
        top_away = [x[2] for x in sorted_data[:10]]

        # Créer le graphique
        fig = Figure(figsize=(12, 6))
        ax = fig.add_subplot(111)

        x = range(len(top_teams))
        width = 0.35

        ax.bar([i - width / 2 for i in x], top_home, width, label='Domicile', color=self.colors['primary'])
        ax.bar([i + width / 2 for i in x], top_away, width, label='Extérieur', color=self.colors['secondary'])

        ax.set_xlabel('Équipes')
        ax.set_ylabel('Moyenne de buts')
        ax.set_title(f'Top 10 - Moyenne de buts par équipe ({self.current_championship})')
        ax.set_xticks(x)
        ax.set_xticklabels(top_teams, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Afficher le graphique
        self.show_figure_in_frame(fig, self.temporal_charts_frame)
        self.temporal_info.config(text=f"Top 10 des équipes - Moyenne de buts à domicile/extérieur")

    def show_home_away_stats(self):
        """Afficher les statistiques domicile/extérieur"""
        if not self.current_matches:
            return

        # Calculer les statistiques
        home_wins = 0
        away_wins = 0
        draws = 0
        total_matches = 0

        for match in self.current_matches:
            if match.get('status') == 'finished':
                total_matches += 1
                home_score = match.get('home_score', 0) or 0
                away_score = match.get('away_score', 0) or 0

                if home_score > away_score:
                    home_wins += 1
                elif away_score > home_score:
                    away_wins += 1
                else:
                    draws += 1

        # Créer le graphique camembert
        fig = Figure(figsize=(8, 8))
        ax = fig.add_subplot(111)

        sizes = [home_wins, away_wins, draws]
        labels = [f'Victoires domicile\n{home_wins}',
                  f'Victoires extérieur\n{away_wins}',
                  f'Matchs nuls\n{draws}']
        colors = [self.colors['primary'], self.colors['accent'], self.colors['secondary']]
        explode = (0.1, 0, 0)  # Mettre en avant les victoires à domicile

        ax.pie(sizes, explode=explode, labels=labels, colors=colors,
               autopct='%1.1f%%', shadow=True, startangle=90)
        ax.axis('equal')
        ax.set_title(f'Résultats domicile/extérieur\n{self.current_championship}')

        # Afficher le graphique
        self.show_figure_in_frame(fig, self.temporal_charts_frame)
        self.temporal_info.config(text=f"Analyse de {total_matches} matchs terminés")

    def show_score_distribution(self):
        """Afficher la distribution des scores"""
        if not self.current_matches:
            return

        # Collecter tous les scores
        scores = []
        for match in self.current_matches:
            if match.get('status') == 'finished':
                home = match.get('home_score', 0) or 0
                away = match.get('away_score', 0) or 0
                scores.append((home, away))

        # Calculer les totaux de buts par match
        total_goals = [home + away for home, away in scores]

        # Créer le graphique d'histogramme
        fig = Figure(figsize=(10, 6))
        ax = fig.add_subplot(111)

        ax.hist(total_goals, bins=range(0, max(total_goals) + 2),
                alpha=0.7, color=self.colors['primary'], edgecolor='black')

        ax.set_xlabel('Nombre total de buts par match')
        ax.set_ylabel('Nombre de matchs')
        ax.set_title(f'Distribution des scores - {self.current_championship}')
        ax.grid(True, alpha=0.3)

        # Ajouter des statistiques
        mean_goals = sum(total_goals) / len(total_goals) if total_goals else 0
        ax.axvline(mean_goals, color='red', linestyle='--', linewidth=2,
                   label=f'Moyenne: {mean_goals:.2f}')
        ax.legend()

        # Afficher le graphique
        self.show_figure_in_frame(fig, self.temporal_charts_frame)
        self.temporal_info.config(text=f"Distribution de {len(scores)} scores - Moyenne: {mean_goals:.2f} buts/match")

    def show_figure_in_frame(self, fig, frame):
        """Afficher une figure matplotlib dans un frame"""
        # Nettoyer le frame
        for widget in frame.winfo_children():
            widget.destroy()

        # Créer le canvas matplotlib
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def log(self, message, level='info'):
        """Ajouter un message au log"""
        timestamp = datetime.now().strftime('%H:%M:%S')

        if level == 'error':
            prefix = f"[{timestamp}] ❌ "
            color = 'red'
        elif level == 'warning':
            prefix = f"[{timestamp}] ⚠️ "
            color = 'orange'
        elif level == 'success':
            prefix = f"[{timestamp}] ✅ "
            color = 'green'
        else:
            prefix = f"[{timestamp}] ℹ️ "
            color = 'black'

        self.log_text.insert(tk.END, prefix + message + "\n")
        self.log_text.see(tk.END)

    def process_queue(self):
        """Traiter les messages de la queue avec mise à jour des statistiques"""
        try:
            while True:
                msg_type, data = self.queue.get_nowait()

                if msg_type == 'log':
                    if isinstance(data, tuple):
                        message, level = data[0], data[1] if len(data) > 1 else 'info'
                        self.log(message, level)
                    else:
                        self.log(str(data))

                elif msg_type == 'status':
                    self.status_label.config(text=data)

                elif msg_type == 'progress_start':
                    self.progress_bar.pack(side=tk.LEFT, padx=(0, 10))
                    self.progress_bar.start()
                    if data:
                        self.status_label.config(text=data)

                elif msg_type == 'progress_stop':
                    self.progress_bar.stop()
                    self.progress_bar.pack_forget()

                elif msg_type == 'matches':
                    self.current_matches = data
                    self.display_matches(data)
                    self.update_stats_display()
                    self.update_quick_stats()

                    # Mettre à jour le compteur de matches
                    count = len(data) if data else 0
                    self.matches_stats_label.config(text=f"{count} matches chargés")

                    # Mettre à jour la liste des équipes pour les statistiques
                    if data:
                        teams = set()
                        for match in data:
                            teams.add(match.get('home_team', ''))
                            teams.add(match.get('away_team', ''))
                        self.team_combo['values'] = list(sorted(teams))

                elif msg_type == 'standings':
                    self.current_standings = data
                    self.display_standings(data)

                    # Mettre à jour le titre
                    if data:
                        self.standings_title.config(
                            text=f"Classement - {self.current_championship}"
                        )
                        self.standings_info.config(
                            text=f"{len(data)} équipes | Dernière mise à jour: {datetime.now().strftime('%H:%M')}"
                        )

                elif msg_type == 'stats':
                    # Pour l'instant, cette méthode est utilisée pour les stats DB
                    pass

                elif msg_type == 'search_results':
                    self.display_search_results(data)

                elif msg_type == 'message':
                    title, message = data[0], data[1]
                    if len(data) == 3 and data[2] == 'error':
                        messagebox.showerror(title, message)
                    else:
                        messagebox.showinfo(title, message)

        except queue.Empty:
            pass

        finally:
            # Mettre à jour l'utilisation mémoire
            try:
                import psutil
                process = psutil.Process()
                mem_info = process.memory_info()
                mem_mb = mem_info.rss / 1024 / 1024
                self.memory_label.config(text=f"Mémoire: {mem_mb:.1f} MB")
            except:
                pass

            self.root.after(100, self.process_queue)

    def display_matches(self, matches):
        """Afficher les matches dans le treeview"""
        # Effacer les anciennes données
        for item in self.matches_tree.get_children():
            self.matches_tree.delete(item)

        # Ajouter les nouveaux matches
        for match in matches:
            date_str = match.get('date', '')
            if date_str:
                display_date = date_str[:10] + " " + date_str[11:16]
            else:
                display_date = ''

            home_score = match.get('home_score')
            away_score = match.get('away_score')

            if home_score is not None and away_score is not None:
                score = f"{home_score}-{away_score}"
            else:
                score = 'VS'

            self.matches_tree.insert('', tk.END, values=(
                display_date,
                match.get('home_team', ''),
                score,
                match.get('away_team', ''),
                match.get('status', ''),
                match.get('matchday', ''),
                match.get('venue', ''),
                match.get('referee', '')
            ))

    def display_standings(self, standings):
        """Afficher le classement"""
        # Effacer les anciennes données
        for item in self.standings_tree.get_children():
            self.standings_tree.delete(item)

        # Ajouter les nouvelles données
        for standing in standings:
            # Calculer la forme (exemple simplifié)
            form = "❓❓❓❓❓"  # Par défaut

            self.standings_tree.insert('', tk.END, values=(
                standing.get('position', ''),
                standing.get('team', ''),
                standing.get('points', ''),
                standing.get('played_games', ''),
                standing.get('won', ''),
                standing.get('draw', ''),
                standing.get('lost', ''),
                standing.get('goals_for', ''),
                standing.get('goals_against', ''),
                standing.get('goal_difference', ''),
                form
            ))

    def display_search_results(self, matches):
        """Afficher les résultats de recherche"""
        # Effacer les anciens résultats
        for item in self.search_tree.get_children():
            self.search_tree.delete(item)

        # Ajouter les nouveaux résultats
        for match in matches:
            date_str = match.get('date', '')[:10]
            home_score = match.get('home_score')
            away_score = match.get('away_score')

            if home_score is not None and away_score is not None:
                score = f"{home_score}-{away_score}"
                total_goals = (home_score or 0) + (away_score or 0)
            else:
                score = 'VS'
                total_goals = 'N/A'

            self.search_tree.insert('', tk.END, values=(
                date_str,
                match.get('home_team', ''),
                score,
                match.get('away_team', ''),
                match.get('status', ''),
                match.get('matchday', ''),
                total_goals
            ))

        # Mettre à jour le compteur
        count = len(matches)
        self.results_count_label.config(text=f"{count} résultat(s) trouvé(s)")


def main():
    root = tk.Tk()
    app = FootballScraperApp(root)

    # Centrer la fenêtre
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')

    root.mainloop()


if __name__ == "__main__":
    main()