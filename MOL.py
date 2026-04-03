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

def load_qualifying_fastest_laps(year, race_round, driver_codes):
    try:
        session = fastf1.get_session(year, race_round, 'Q')
        session.load()
        
        fastest_laps = []
        
        for driver_code in driver_codes:
            driver_laps = session.laps.pick_driver(driver_code)
            
            fastest_lap = driver_laps.pick_fastest()  
            
            if fastest_lap is not None and not fastest_lap.empty:  
                fastest_lap['DriverCode'] = driver_code
                fastest_laps.append(fastest_lap.to_frame().T)  
        
        if fastest_laps:  # 👈 Check if we found any laps
            combined_fastest = pd.concat(fastest_laps, ignore_index=True)
            return combined_fastest
        else:
            return None
        
    except Exception as e:
        st.error(f"Error loading qualifying fastest laps: {str(e)}")
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

    completed_races = completed_races[completed_races['EventFormat'] != 'testing']
    
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
                        'points': total_points,  
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

def load_race_laps(year, race_round, driver_codes):
    try:
        session = fastf1.get_session(year, race_round, 'R')
        session.load()
        
        all_laps = []
        
        for driver_code in driver_codes:
            driver_laps = session.laps.pick_driver(driver_code)
            driver_laps['DriverCode'] = driver_code
            
            all_laps.append(driver_laps)
        
        combined_laps = pd.concat(all_laps, ignore_index=True)
        
        return combined_laps
        
    except Exception as e:
        st.error(f"Error loading lap data: {str(e)}")
        return None

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
        yaxis_title="Position ",
        barmode='group',
        height=550,
        yaxis=dict(autorange="reversed"),  
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

#Minisector Q

#Delta Time Quali 

def tyrestrategy_chart(laps_df, session):
    laps_df = laps_df.copy()

    fig = go.Figure()
    
    compound_colors = {
        'SOFT': '#FF0000',      
        'MEDIUM': '#FFA500',    
        'HARD': '#FFFFFF',      
        'INTERMEDIATE': '#00FF00',  
        'WET': '#0000FF'        
    }

    driver_order = ['VER', 'NOR', 'PIA']

    for driver_code in driver_order:
        if driver_code not in laps_df['DriverCode'].unique():
            continue
        
        driver_laps = laps_df[laps_df['DriverCode'] == driver_code].sort_values('LapNumber')
        driver_name = DRIVER_CONFIG[driver_code]['name']
        
        # Calculate stint information using groupby
        stints = driver_laps[["DriverCode", "Stint", "Compound", "LapNumber"]].copy()
        stints = stints.groupby(["DriverCode", "Stint", "Compound"]).agg(
            stint_length=('LapNumber', 'count'),
            start_lap=('LapNumber', 'min'),
            end_lap=('LapNumber', 'max')
        ).reset_index()
        
        for _, stint in stints.iterrows():
            fig.add_trace(go.Bar(
                name=stint['Compound'],
                x=[stint['stint_length']],
                y=[driver_name],
                orientation='h',
                marker=dict(
                    color=compound_colors.get(stint['Compound'], '#808080'),
                    line=dict(color='black', width=1)
                ),
                hoverinfo='skip',  # No hovering
                showlegend=False
            ))

    fig.update_xaxes(title_text="Lap Number")
    fig.update_yaxes(title_text="Driver")

    fig.update_layout(
        title="Tyre Strategy",
        height=400,  # Shorter since only one chart
        barmode='stack',
        plot_bgcolor='rgba(0,0,0,0)',
    )

    return fig
    
#Degradation

#Minisector R

def laptimes_scatter(laps_df, selected_drivers):
    
    fig = go.Figure()
    
    compound_colors = {
        'SOFT': '#FF0000',        
        'MEDIUM': '#FFF200',       
        'HARD': '#FFFFFF',        
        'INTERMEDIATE': '#00FF00', 
        'WET': '#0000FF'          
    }
    
    for driver_code in selected_drivers:
        driver_laps = laps_df[laps_df['DriverCode'] == driver_code]
        driver_config = DRIVER_CONFIG[driver_code]
        
        compounds = driver_laps['Compound'].dropna().unique()
        
        for compound in compounds:
            compound_laps = driver_laps[driver_laps['Compound'] == compound]
            
            valid_laps = compound_laps[
                (compound_laps['LapTime'].notna()) &
                (compound_laps['IsAccurate'] == True)  
            ]
            
            if valid_laps.empty:
                continue
            
            lap_times_seconds = valid_laps['LapTime'].dt.total_seconds()
            
            fig.add_trace(go.Scatter(
                x=valid_laps['LapNumber'],
                y=lap_times_seconds,
                mode='markers',
                name=f"{driver_config['name']} - {compound}",
                marker=dict(
                    size=8,
                    color=compound_colors.get(compound, '#CCCCCC'),  
                    line=dict(
                        color=driver_config['color'], 
                        width=2
                    )
                ),
                legendgroup=driver_code,
                hovertemplate=(
                    f"<b>{driver_config['name']}</b><br>"
                    "Lap: %{x}<br>"
                    "Time: %{y:.3f}s<br>"
                    f"Compound: {compound}<br>"
                    "<extra></extra>"
                )
            ))
    
    fig.update_layout(
        title="Lap Times Throughout the Race (by Tire Compound)",
        xaxis_title="Lap Number",
        yaxis_title="Lap Time (seconds)",
        hovermode='closest',
        height=600,
        plot_bgcolor='#1a1a1a',
        paper_bgcolor='#1a1a1a',
        font=dict(color='white', size=12),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            bgcolor='rgba(0,0,0,0.5)',
            title="Driver - Compound"
        ),
        xaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='#333333'
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=1,
            gridcolor='#333333'
        )
    )
    
    return fig

def laptimes_violin(laps_df, selected_drivers):
    laps_df = laps_df[laps_df['DriverCode'].isin(selected_drivers)]
    
    laps_df = laps_df[
        (laps_df['LapTime'].notna()) &
        (laps_df['IsAccurate'] == True)  
    ].copy()
    
    laps_df['LapTimeSeconds'] = laps_df['LapTime'].dt.total_seconds()
    
    laps_df['DriverName'] = laps_df['DriverCode'].apply(lambda code: DRIVER_CONFIG[code]['name'])
    
    compound_colors = {
        'SOFT': '#FF0000',        
        'MEDIUM': '#FFF200',      
        'HARD': '#FFFFFF',        
        'INTERMEDIATE': '#00FF00', 
        'WET': '#0000FF'          
    }
    
    fig = go.Figure()
    
    for driver in selected_drivers:
        driver_data = laps_df[laps_df['DriverCode'] == driver]
        driver_name = DRIVER_CONFIG[driver]['name']
        
        fig.add_trace(go.Violin(
            x=[driver_name] * len(driver_data),
            y=driver_data['LapTimeSeconds'],
            name=driver_name,
            box_visible=False,
            meanline_visible=False,
            fillcolor='rgba(0,0,0,0)', 
            line_color=DRIVER_CONFIG[driver]['color'],  
            opacity=0.6,
            points=False,  
            showlegend=False,
            hoverinfo='skip'
        ))
    
    for compound, color in compound_colors.items():
        compound_data = laps_df[laps_df['Compound'] == compound]
        
        if not compound_data.empty:
            fig.add_trace(go.Scatter(
                x=compound_data['DriverName'],
                y=compound_data['LapTimeSeconds'],
                mode='markers',
                name=compound,  
                marker=dict(
                    color=color,  
                    size=6,
                    opacity=0.7,
                    line=dict(width=0.5, color='white')
                ),
                hovertemplate='<b>%{x}</b><br>' +
                             'Lap Time: %{y:.3f}s<br>' +
                             f'Compound: {compound}<br>' +
                             '<extra></extra>'
            ))
    
    fig.update_layout(
        height=600,
        plot_bgcolor='#1a1a1a',
        paper_bgcolor='#1a1a1a',
        font=dict(color='white', size=12),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            bgcolor='rgba(0,0,0,0.5)',
            title="Tire Compound"
        ),
        xaxis_title="Driver",
        yaxis_title="Lap Time (seconds)",
        title="Lap Time Distribution by Driver and Tire Compound"
    )
    
    return fig

def race_pace_comparison(laps_df, selected_drivers):
    laps_df = laps_df[laps_df['DriverCode'].isin(selected_drivers)]
    
    laps_df = laps_df[
        (laps_df['LapTime'].notna()) &
        (laps_df['IsAccurate'] == True)  
    ].copy()
    
    laps_df['LapTimeSeconds'] = laps_df['LapTime'].dt.total_seconds()
    
    laps_df['DriverName'] = laps_df['DriverCode'].apply(lambda code: DRIVER_CONFIG[code]['name'])
    
    fig = go.Figure()
    
    for driver in selected_drivers:
        driver_data = laps_df[laps_df['DriverCode'] == driver]
        driver_name = DRIVER_CONFIG[driver]['name']
        
        fig.add_trace(go.Box(
            y=driver_data['LapTimeSeconds'],
            name=driver_name,
            boxpoints=False,
            marker_color=DRIVER_CONFIG[driver]['color'],
            line_color=DRIVER_CONFIG[driver]['color'],
            fillcolor='rgba(0,0,0,0)',
            opacity=0.7
        ))
    
    fig.update_layout(
        height=600,
        plot_bgcolor='#1a1a1a',
        paper_bgcolor='#1a1a1a',
        font=dict(color='white', size=12),
        xaxis_title="Driver",
        yaxis_title="Lap Time (seconds)")
    
    return fig

with st.sidebar:
    st.header("Dashboard Controls")
    selected_year = 2025  
    
    st.info(f"📅 Analyzing **{selected_year} Season**")
    
    schedule = get_2025_race_schedule(selected_year)
    
    st.markdown("---")
    
    st.subheader("🏎️ Driver Selection")
    st.caption("Applies to: Qualifying & Race Analysis tabs")
    
    selected_drivers = st.multiselect(
        "Select Drivers to Compare",
        options=['VER', 'NOR', 'PIA'],
        default=['VER', 'NOR', 'PIA'],
        format_func=lambda x: DRIVER_CONFIG[x]['name']
    )
    
    if len(selected_drivers) == 0:
        st.warning("⚠️ Please select at least one driver")
    
    st.markdown("---")
    
    st.subheader("🏁 Race Selection")
    st.caption("Applies to: Qualifying & Race Analysis tabs")
    
    if schedule is not None:
        completed_races = schedule[
            (schedule['EventDate'] <= pd.Timestamp.now()) &
            (schedule['RoundNumber'] > 0) &
            (schedule['EventFormat'] != 'testing') &
            (schedule['EventName'] != "Miami Grand Prix")
        ].copy()
        
        if len(completed_races) == 0:
            st.warning("No completed races yet")
            selected_race_round = None
            selected_race_name = None
        else:
            race_options = []
            race_round_map = {}
            
            for idx, race in completed_races.iterrows():
                race_label = f"{race['EventName']} (Round {race['RoundNumber']})"
                race_options.append(race_label)
                race_round_map[race_label] = race['RoundNumber']
            
            selected_race_name = st.selectbox(
                "Select Race",
                options=race_options,
                index=len(race_options) - 1
            )
            
            selected_race_round = race_round_map[selected_race_name]
    else:
        st.error("Could not load race schedule")
        selected_race_round = None
        selected_race_name = None

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
    - Championship Standings: A table showing the current points and positions of the top 3 drivers.
    - Performance Metrics: Key statistics such as wins, podiums, pole positions, and fastest laps.
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
            
            st.subheader("Championship Standings")
            championship_cards(standings)
            
            st.markdown("---")
            
            st.subheader("Points Progression")
            points_chart = points_progression_chart(cumulative_points)
            st.plotly_chart(points_chart, use_container_width=True)
            
            st.markdown("---")
            
            col1, col2 = st.columns([1.5, 1])
            
            with col1:
                st.subheader("Race Results Overview")
                heatmap = race_results_heatmap(season_results)
                st.plotly_chart(heatmap, use_container_width=True)
            
            with col2:
                st.subheader("Head-to-Head Stats")
                h2h_table = h2h_stats_table(standings)
                st.dataframe(h2h_table, hide_index=True, use_container_width=True)
    
    st.markdown("---")

    st.subheader("Average Qualifying & Average Race Positions")
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
    - Speed Trace with Corner Annotations: A plot of the drivers speed trace during their fastest qualifying lap, with the x-axis representing the corners and the y axis representing the speed. 
    """)
    
    st.markdown("---")

    if len(selected_drivers) == 0:
        st.warning("⚠️ Please select at least one driver from the sidebar")
        st.stop()
    st.caption(f"**Analyzing:** {', '.join([DRIVER_CONFIG[d]['name'] for d in selected_drivers])} | **Race:** {selected_race_name}")

    st.markdown("---")

    with st.spinner(f"Loading qualifying data for {selected_race_name}..."):
        quali_session = load_race_session(selected_year, selected_race_round, 'Q')
        quali_laps = load_race_laps(selected_year, selected_race_round, selected_drivers)
    
    if quali_session is None or quali_laps is None or quali_laps.empty:
        st.error("Could not load qualifying data for this race. Please try another race.")
        st.stop()
    
    #1

    #2

with tab4:
    st.title("Race Analysis")
    st.subheader("An analysis on the drivers performance during the Featured Race across the 2025 F1 Season.")
    
    st.markdown("""
    This section will provide insights into the drivers' race performance, including:
    - Tyre Strategy Analysis: A bar chart showing the tyre strategy of each driver during the race, including the type of tyre used and the lap on which they were used.
    - Degradation Analysis: A line plot showing the degradation of the tyres over the course of the race.
    - Minisection Plot: A plot of the circuit where it displays the drivers dominance in deifferent parts of the track, showing which driver was faster in each sector of the circuit.
    - Lap Time Scatter Plot: A scatter plot of the lap times of each driver during the race, with the x-axis representing the lap number and the y-axis representing the lap time grouped by tyre compound. This plot can be used to identify trends in the drivers' performance throughout the race.
    - Lap Time Violin PLot: A violin plot of the lap times of each driver during the race, with the x-axis representing the driver and the y-axis representing the lap time grouped by tyre compound. This plot can be used to identify trends in the drivers' performance throughout the race.
    - Race Pace Comparision: A box plot comparing the race pace of the drivers.
    """)
    
    st.markdown("---")

    if len(selected_drivers) == 0:
        st.warning("⚠️ Please select at least one driver from the sidebar")
        st.stop()
    st.caption(f"**Analyzing:** {', '.join([DRIVER_CONFIG[d]['name'] for d in selected_drivers])} | **Race:** {selected_race_name}")
    
    st.markdown("---")
    
    with st.spinner(f"Loading race data for {selected_race_name}..."):
        laps_data = load_race_laps(selected_year, selected_race_round, selected_drivers)
        race_session = load_race_session(selected_year, selected_race_round, 'R')
    
    if laps_data is None or laps_data.empty:
        st.error("Could not load race data for this race. Please try another race.")
        st.stop()
    
    #1
    with st.expander("Race Gap and Tyre Strategy Analysis", expanded=True):
        st.subheader("Race Gap Over Time and Tyre Strategy")    

        st.markdown("""       
        The stacked bar chart shows the tyre strategy for each driver:
        - Each horizontal bar represents a stint on a particular tyre compound.
        - The color of the bar indicates the tyre compound used (Red=Soft, Yellow=Medium, White=Hard, Green=Intermediate, Blue=Wet).
        """)

        tyrestrat_chart = tyrestrategy_chart(laps_data, race_session)
        st.plotly_chart(tyrestrat_chart, use_container_width=True)

    #2

    #3

    with st.expander("Lap Time Scatter Plot (by Tire Compound))", expanded=True):
        st.subheader("Lap Time Progression Throughout the Race")
        
        st.markdown("""
        This scatter plot shows every lap time during the race, color-coded by tire compound:
        - Dot fill color = Tire compound (Red=Soft, Yellow=Medium, White=Hard).
        - Dot outline color = Driver's team color.
        """)
        
        laptimes_chart = laptimes_scatter(laps_data, selected_drivers)
        st.plotly_chart(laptimes_chart, use_container_width=True)
        
        st.markdown("---")

    with st.expander("Lap Time Distribution Violin Plot", expanded=False):
        st.subheader("Lap Time Distribution by Driver and Tire Compound")
        
        st.markdown("""
        This violin plot shows the distribution of lap times for each driver, grouped by tire compound:
        - Each violin represents the distribution of lap times for a specific driver and tire compound.
        - The width of the violin indicates the density of lap times at different values.
        - The box plot inside the violin shows the interquartile range and median lap time.
        """)
        
        laptimes_violin_chart = laptimes_violin(laps_data, selected_drivers)
        st.plotly_chart(laptimes_violin_chart, use_container_width=True)

    with st.expander("Race Pace Comparison Box Plot", expanded=False):
        st.subheader("Race Pace Comparison")
        
        st.markdown("""
        This box plot compares the race pace of the selected drivers:
        - Each box represents the distribution of lap times for a specific driver.
        - The whiskers indicate the range of lap times, excluding outliers.
        - The median lap time is shown as a horizontal line within each box.
        """)
        
        race_pace_chart = race_pace_comparison(laps_data, selected_drivers)
        st.plotly_chart(race_pace_chart, use_container_width=True)