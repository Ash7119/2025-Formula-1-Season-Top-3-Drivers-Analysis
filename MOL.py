import os
import warnings
import fastf1
import streamlit as st
import fastf1
from fastf1 import plotting
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('TkAgg')
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime

os.makedirs(".fastf1_cache", exist_ok=True)
fastf1.Cache.enable_cache(".fastf1_cache")

warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="2025 Formula 1 Season Top 3 Drivers Analysis",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #E10600;
        text-align: center;
        margin-bottom: 2rem;
    }
    .stSelectbox label, .stTextInput label {
        font-weight: bold;
        color: #05f2db;
    }
    </style>
""", unsafe_allow_html=True)

DRIVER_CONFIG = {
    'VER': {
        'name': 'Max Verstappen',
        'full_name': 'Max VERSTAPPEN',
        'color': '#0600EF',
        'team': 'Red Bull Racing',
        'number': 1
    },
    'NOR': {
        'name': 'Lando Norris',
        'full_name': 'Lando NORRIS',
        'color': '#FF8700',
        'team': 'McLaren',
        'number': 4
    },
    'PIA': {
        'name': 'Oscar Piastri',
        'full_name': 'Oscar PIASTRI',
        'color': '#47C7FC',  
        'team': 'McLaren',
        'number': 81
    }
}

if 'race_data' not in st.session_state:
    st.session_state.race_data = None
if 'qualifying_data' not in st.session_state:
    st.session_state.qualifying_data = None

def get_2025_season():
    return [2025]

def get_2025_race_schedule(year):
    try:
        schedule = fastf1.get_event_schedule(year)
        return schedule
    except Exception as e:
        st.error(f"Error fetching schedule for {year}: {str(e)}")
        return None
    
def load_race_session(year, race_name_or_round, session_type='R'):
    try:
        if str(race_name_or_round).isdigit():
            round_num = int(race_name_or_round)
            session = fastf1.get_session(year, round_num, session_type)
        else:
            session = fastf1.get_session(year, race_name_or_round, session_type)
        
        session.load()
        return session
    except Exception as e:
        st.error(f"Error loading {session_type} session: {str(e)}")
        return None
  
def load_all_season_data(year, schedule):
    all_results = []
    
    completed_races = schedule[schedule['EventDate'] <= pd.Timestamp.now()]
    
    for idx, race in completed_races.iterrows():
        round_num = race['RoundNumber']
        race_name = race['EventName']
        
        try:
            race_session = fastf1.get_session(year, round_num, 'R')
            race_session.load()
            
            quali_session = fastf1.get_session(year, round_num, 'Q')
            quali_session.load()
            
            sprint_points = {d: 0 for d in DRIVER_CONFIG.keys()}
            
            try:
                sprint_session = fastf1.get_session(year, round_num, 'S')
                sprint_session.load()
                
                sprint_results = sprint_session.results
                
                for driver_code in DRIVER_CONFIG.keys():
                    driver_sprint = sprint_results[
                        sprint_results['Abbreviation'] == driver_code
                    ]
                    if not driver_sprint.empty:
                        sprint_points[driver_code] = float(driver_sprint.iloc[0]['Points'])
                        
            except Exception:
                pass
            
            for driver_code in DRIVER_CONFIG.keys():
                driver_race = race_session.results[
                    race_session.results['Abbreviation'] == driver_code
                ]
                
                driver_quali = quali_session.results[
                    quali_session.results['Abbreviation'] == driver_code
                ]
                
                if not driver_race.empty:
                    race_points = float(driver_race.iloc[0]['Points'])
                    sprint_pts = sprint_points.get(driver_code, 0)
                    total_points = race_points + sprint_pts
                    
                    result = {
                        'round': round_num,
                        'race_name': race_name,
                        'driver': driver_code,
                        'race_position': driver_race.iloc[0]['Position'],
                        'race_points': race_points,
                        'sprint_points': sprint_pts,
                        'points': total_points,  # Total points including sprint
                        'grid_position': driver_race.iloc[0]['GridPosition'],
                        'quali_position': driver_quali.iloc[0]['Position'] if not driver_quali.empty else None,
                        'status': driver_race.iloc[0]['Status'],
                        'is_sprint_weekend': sprint_pts > 0
                    }
                    all_results.append(result)
                    
        except Exception as e:
            st.warning(f"Could not load data for {race_name}: {str(e)}")
            continue
    
    return pd.DataFrame(all_results)

def calculate_championship_standings(results_df):
    standings = results_df.groupby('driver').agg({
        'points': 'sum',
        'race_position': lambda x: (x == 1).sum(),  
        'quali_position': lambda x: (x == 1).sum()   
    }).reset_index()
    
    standings.columns = ['driver', 'total_points', 'wins', 'poles']
    
    podiums = results_df[results_df['race_position'] <= 3].groupby('driver').size()
    standings['podiums'] = standings['driver'].map(podiums).fillna(0).astype(int)
    
    standings = standings.sort_values('total_points', ascending=False).reset_index(drop=True)
    standings['position'] = standings.index + 1
    
    return standings


def calculate_cumulative_points(results_df):
    results_sorted = results_df.sort_values(['driver', 'round'])

    results_sorted['cumulative_points'] = results_sorted.groupby('driver')['points'].cumsum()
    
    return results_sorted


def calculate_avg_positions(results_df):
    avg_positions = results_df.groupby('driver').agg({
        'quali_position': 'mean',
        'race_position': 'mean'
    }).round(2)
    
    return avg_positions

def championship_cards(standings_df):
    col1, col2, col3 = st.columns(3)
    
    for idx, (col, driver_code) in enumerate(zip([col1, col2, col3], ['VER', 'NOR', 'PIA'])):
        driver_data = standings_df[standings_df['driver'] == driver_code].iloc[0]
        config = DRIVER_CONFIG[driver_code]
        
        with col:
            if driver_data['position'] == 1:
                leader_points = driver_data['total_points']
                second_points = standings_df.iloc[1]['total_points']
                delta = f"+{leader_points - second_points} pts ahead"
            else:
                leader_points = standings_df.iloc[0]['total_points']
                delta = f"-{leader_points - driver_data['total_points']} pts"
            
            st.metric(
                label=f"{config['name']} (#{config['number']})",
                value=f"{int(driver_data['total_points'])} pts",
                delta=delta
            )
            
            st.markdown(f"""
            <div style='background-color: {config['color']}15; padding: 10px; border-radius: 5px; margin-top: 10px;'>
                <p style='margin: 5px 0;'><b>Position:</b> P{int(driver_data['position'])}</p>
                <p style='margin: 5px 0;'><b>Wins:</b> {int(driver_data['wins'])}</p>
                <p style='margin: 5px 0;'><b>Podiums:</b> {int(driver_data['podiums'])}</p>
            </div>
            """, unsafe_allow_html=True)


def points_progression_chart(cumulative_df):
    fig = go.Figure()
    
    for driver_code, config in DRIVER_CONFIG.items():
        driver_data = cumulative_df[cumulative_df['driver'] == driver_code]
        
        fig.add_trace(go.Scatter(
            x=driver_data['round'],
            y=driver_data['cumulative_points'],
            mode='lines',  
            name=config['name'],
            line=dict(color=config['color'], width=3),
            hovertemplate=f"<b>{config['name']}</b><br>" +
                         "Round: %{x}<br>" +
                         "Points: %{y}<br>" +
                         "<extra></extra>"
        ))
    
    fig.update_layout(
        title="Championship Points Progression",
        xaxis_title="Race Round",
        yaxis_title="Points",
        hovermode='x unified',
        height=500,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(size=12),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='LightGray')
    
    return fig


def race_results_heatmap(results_df):
    heatmap_data = results_df.pivot(
        index='driver',
        columns='round',
        values='race_position'
    )
    
    heatmap_data = heatmap_data.reindex(['VER', 'NOR', 'PIA'])

    colorscale = [
        [0, '#FFD700'],      
        [0.05, '#C0C0C0'],   
        [0.1, '#CD7F32'],   
        [0.3, '#90EE90'],    
        [0.5, '#FFFF99'],    
        [1, '#FFB6C6']       
    ]
    
    fig = go.Figure(data=go.Heatmap(
        z=heatmap_data.values,
        x=[f"R{int(r)}" for r in heatmap_data.columns],
        y=[DRIVER_CONFIG[d]['name'] for d in heatmap_data.index],
        colorscale=colorscale,
        text=heatmap_data.values.astype(int),
        texttemplate='P%{text}',
        textfont={"size": 12, "color": "black"},
        colorbar=dict(title="Position"),
        hovertemplate='Driver: %{y}<br>Round: %{x}<br>Position: P%{z}<extra></extra>'
    ))
    
    fig.update_layout(
        title="Race Finishing Positions",
        xaxis_title="Race Round",
        yaxis_title="Driver",
        height=300,
    )
    
    return fig


def h2h_stats_table(standings_df):
    display_data = []
    
    for driver_code in ['VER', 'NOR', 'PIA']:
        driver_stats = standings_df[standings_df['driver'] == driver_code].iloc[0]
        display_data.append({
            'Driver': DRIVER_CONFIG[driver_code]['name'],
            'Wins': int(driver_stats['wins']),
            'Podiums': int(driver_stats['podiums']),
            'Poles': int(driver_stats['poles']),
        })
    
    df_display = pd.DataFrame(display_data)
    
    return df_display


def avg_position_chart(avg_positions_df, results_df):
    chart_data = []
    for driver_code in ['VER', 'NOR', 'PIA']:
        if driver_code in avg_positions_df.index:
            chart_data.append({
                'Driver': DRIVER_CONFIG[driver_code]['name'],
                'Avg Qualifying': avg_positions_df.loc[driver_code, 'quali_position'],
                'Avg Race Finish': avg_positions_df.loc[driver_code, 'race_position'],
                'Color': DRIVER_CONFIG[driver_code]['color']
            })
    
    df_chart = pd.DataFrame(chart_data)
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Avg Qualifying Position',
        x=df_chart['Driver'],
        y=df_chart['Avg Qualifying'],
        marker_color='#636EFA',
        text=df_chart['Avg Qualifying'].round(2),
        textposition='outside'
    ))
    
    fig.add_trace(go.Bar(
        name='Avg Race Finish',
        x=df_chart['Driver'],
        y=df_chart['Avg Race Finish'],
        marker_color='#EF553B',
        text=df_chart['Avg Race Finish'].round(2),
        textposition='outside'
    ))
    
    fig.update_layout(
        title="Average Qualifying vs Race Positions",
        xaxis_title="Driver",
        yaxis_title="Position (Lower is Better)",
        barmode='group',
        height=400,
        yaxis=dict(autorange="reversed"),  # Lower position = better
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

with st.sidebar:
    st.header("Dashboard Controls")
    selected_year = 2025  
    
    st.info(f"📅 Analyzing **{selected_year} Season**")
    
    schedule = get_2025_race_schedule(selected_year)

tab1, tab2, tab3, tab4 = st.tabs([
    "Home", 
    "Season Overview", 
    "Qualifying Analysis", 
    "Race Analysis"
])

with tab1:
    st.title("🏎️ Welcome to the 2025 Formula 1 Season Top 3 Drivers Analysis Dashboard")
    st.subheader("Max Verstappen vs Lando Norris vs Oscar Piastri")
    
    st.markdown("""
    This dashboard provides comprehensive analysis of the 2025 F1 season battle between 
    Max Verstappen (Red Bull Racing), Lando Norris (McLaren), and Oscar Piastri (McLaren).
    """)
    
    st.markdown("---")

with tab2:
    st.title("Season Overview")
    st.subheader("Championship Standings and Performance Metrics")
    
    st.markdown("""
    - **Championship Standings**: A table showing the current points and positions of the top 3 drivers.
    - **Performance Metrics**: Key statistics such as wins, podiums, pole positions, and fastest laps.
    """)

    if schedule is None:
        st.error("Unable to load race schedule. Please check your connection.")
    else:
        with st.spinner("Loading season data..."):
            season_results = load_all_season_data(selected_year, schedule)
        
        if season_results.empty:
            st.warning("No race data available yet for the 2025 season.")
        else:
            standings = calculate_championship_standings(season_results)
            cumulative_points = calculate_cumulative_points(season_results)
            avg_positions = calculate_avg_positions(season_results)
            
            st.subheader("🏆 Championship Standings")
            championship_cards(standings)
            
            st.markdown("---")
            
            st.subheader("📈 Points Progression")
            points_chart = points_progression_chart(cumulative_points)
            st.plotly_chart(points_chart, use_container_width=True)
            
            st.markdown("---")
            
            col1, col2 = st.columns([1.5, 1])
            
            with col1:
                st.subheader("🗓️ Race Results Overview")
                heatmap = race_results_heatmap(season_results)
                st.plotly_chart(heatmap, use_container_width=True)
            
            with col2:
                st.subheader("📊 Head-to-Head Stats")
                h2h_table = h2h_stats_table(standings)
                st.dataframe(h2h_table, hide_index=True, use_container_width=True)
    
    st.markdown("---")

    st.subheader("🎯 Average Qualifying & Race Positions")
    avg_pos_chart = avg_position_chart(avg_positions, season_results)
    st.plotly_chart(avg_pos_chart, use_container_width=True)
            
    st.caption("Average Positions:")
    avg_display = avg_positions.copy()
    avg_display.index = [DRIVER_CONFIG[d]['name'] for d in avg_display.index]
    avg_display.columns = ['Avg Qualifying Position', 'Avg Race Finish']
    st.dataframe(avg_display, use_container_width=True)

    
with tab3:
    st.title("Qualifying Analysis")
    st.subheader("An analysis on the drivers performance during Qualifying Sessions across the 2025 F1 Season.")
    
    st.markdown("""
    This section will provide insights into the drivers' qualifying performance, including:
    - Delta Time Chart: Comparing the drivers' fastest lap times in qualifying sessions. This analysis is acompanied by a speed, throttle and delta panel to provide a comprehensive view of the drivers' performance during qualifying sessions.
    - Minisector Plot: A plot of the circuit where it displays the drivers dominance in deifferent parts of the track, showing which driver was faster in each sector of the circuit.
    - Speed Trace with corner annotations: A plot of the drivers speed trace during their fastest qualifying lap, with the x-axis representing the corners and the y axis representing the speed. 
    """)
    
    st.markdown("---")

with tab3:
    st.title("Race Analysis Analysis")
    st.subheader("An analysis on the drivers performance during the Featured Race across the 2025 F1 Season.")
    
    st.markdown("""
    This section will provide insights into the drivers' race performance, including:
    - Race Gap Overtime:
    """)
    
    st.markdown("---")