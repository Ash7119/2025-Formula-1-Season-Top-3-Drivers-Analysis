import os
import warnings
import fastf1
import streamlit as st
import fastf1
from fastf1 import plotting
import pandas as pd
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
        
        if fastest_laps:  
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

def create_minisector_comparison(session, driver_codes, num_minisectors=25):
    laps = session.laps
    telemetry_list = []
    
    for driver_code in driver_codes:
        lap = laps.pick_driver(driver_code).pick_fastest()
        if lap is not None and not lap.empty:
            tel = lap.get_telemetry().add_distance()
            tel['Driver'] = driver_code
            telemetry_list.append(tel)
    
    if not telemetry_list:
        return None
    
    telemetry = pd.concat(telemetry_list)
    
    total_distance = telemetry['Distance'].max()
    minisector_length = total_distance / num_minisectors
    telemetry['Minisector'] = telemetry['Distance'].apply(
        lambda dist: int((dist // minisector_length) + 1)
    )
    
    avg_speed = telemetry.groupby(['Minisector', 'Driver'])['Speed'].mean().reset_index()
    fastest_driver = avg_speed.loc[avg_speed.groupby('Minisector')['Speed'].idxmax()]
    fastest_driver = fastest_driver[['Minisector', 'Driver']].rename(columns={'Driver': 'Fastest_driver'})
    
    telemetry = telemetry.merge(fastest_driver, on='Minisector')
    telemetry = telemetry.sort_values(by='Distance')
    
    fig = go.Figure()
    
    for driver_code in driver_codes:
        driver_tel = telemetry[telemetry['Driver'] == driver_code].copy()
        
        driver_tel['Color'] = driver_tel['Fastest_driver'].map(
            lambda d: DRIVER_CONFIG[d]['color']
        )
        
        for minisector in driver_tel['Minisector'].unique():
            sector_data = driver_tel[driver_tel['Minisector'] == minisector]
            fastest_in_sector = sector_data['Fastest_driver'].iloc[0]
            
            fig.add_trace(go.Scatter(
                x=sector_data['X'],
                y=sector_data['Y'],
                mode='lines',
                line=dict(
                    color=DRIVER_CONFIG[fastest_in_sector]['color'],
                    width=5
                ),
                showlegend=False,
                hovertemplate=f"Minisector {minisector}<br>" +
                             f"Fastest: {DRIVER_CONFIG[fastest_in_sector]['name']}<br>" +
                             "<extra></extra>"
            ))
    
    for driver_code in driver_codes:
        fig.add_trace(go.Scatter(
            x=[None],
            y=[None],
            mode='lines',
            line=dict(color=DRIVER_CONFIG[driver_code]['color'], width=5),
            name=DRIVER_CONFIG[driver_code]['name'],
            showlegend=True
        ))
    
    circuit_info = session.get_circuit_info()  
    corners = circuit_info.corners  
    
    ref_lap = laps.pick_driver(driver_codes[0]).pick_fastest()
    ref_tel = ref_lap.get_telemetry().add_distance()
    
    for _, corner in corners.iterrows():
        corner_distance = corner['Distance']  
        corner_number = corner['Number']      
        corner_letter = corner['Letter']     
        
        closest_idx = (ref_tel['Distance'] - corner_distance).abs().idxmin()
        corner_x = ref_tel.loc[closest_idx, 'X']
        corner_y = ref_tel.loc[closest_idx, 'Y']
        
        corner_label = f"{corner_number}{corner_letter}" if corner_letter else f"{corner_number}"
        
        fig.add_annotation(
            x=corner_x,
            y=corner_y,
            text=corner_label,      
            showarrow=True,          
            arrowhead=2,
            arrowsize=1,
            arrowwidth=1,
            arrowcolor='white',
            font=dict(
                size=10,
                color='white'
            ),
            bgcolor='rgba(0,0,0,0.5)',  
            bordercolor='white',
            borderwidth=1,
            ax=20,   
            ay=-20   
        )
    
    fig.update_layout(
        title="Mini-Sector Speed Comparison",
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            scaleanchor="y",
            scaleratio=1
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False
        ),
        plot_bgcolor='rgba(0,0,0,0)',
        height=600,
        hovermode='closest'
    )
    
    return fig

def create_delta_time_chart(session, driver_codes, ref_driver=None, compare_driver=None):
    
    if ref_driver is None:
        ref_driver = driver_codes[0]
    if compare_driver is None:
        compare_driver = driver_codes[1]
    laps = session.laps
    
    driver_laps = {}
    driver_tel = {}
    
    for driver_code in driver_codes:
        lap = laps.pick_driver(driver_code).pick_fastest()
        if lap is not None and not lap.empty:
            driver_laps[driver_code] = lap
            tel = lap.get_telemetry().add_distance()
            driver_tel[driver_code] = tel
    
    if len(driver_tel) < 2:
        st.error("Need at least 2 drivers with valid laps")
        return None

    if compare_driver and ref_driver in driver_laps and compare_driver in driver_laps:
        delta_time, ref_tel, compare_tel = fastf1.utils.delta_time(
            driver_laps[ref_driver],
            driver_laps[compare_driver]
        )
        show_delta = True
    else:
        show_delta = False

    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=["Speed (km/h)", "Throttle (%)", "Brake", "Delta Time (s)"],
        row_heights=[3, 1, 1, 1]
    )
    
    for driver_code in driver_codes:
        tel = driver_tel[driver_code]
        fig.add_trace(go.Scatter(
            x=tel['Distance'],
            y=tel['Speed'],
            mode='lines',
            name=DRIVER_CONFIG[driver_code]['name'],
            line=dict(color=DRIVER_CONFIG[driver_code]['color'], width=2),
            hovertemplate=f"<b>{DRIVER_CONFIG[driver_code]['name']}</b><br>" +
                         "Distance: %{x:.0f}m<br>" +
                         "Speed: %{y:.0f} km/h<br>" +
                         "<extra></extra>",
            showlegend=True
        ), row=1, col=1)
    
    for driver_code in driver_codes:
        tel = driver_tel[driver_code]
        fig.add_trace(go.Scatter(
            x=tel['Distance'],
            y=tel['Throttle'],
            mode='lines',
            name=DRIVER_CONFIG[driver_code]['name'],
            line=dict(color=DRIVER_CONFIG[driver_code]['color'], width=2),
            hovertemplate=f"<b>{DRIVER_CONFIG[driver_code]['name']}</b><br>" +
                         "Distance: %{x:.0f}m<br>" +
                         "Throttle: %{y:.0f}%<br>" +
                         "<extra></extra>",
            showlegend=False
        ), row=2, col=1)
    
    for driver_code in driver_codes:
        tel = driver_tel[driver_code]
        fig.add_trace(go.Scatter(
            x=tel['Distance'],
            y=tel['Brake'].astype(int),
            mode='lines',
            name=DRIVER_CONFIG[driver_code]['name'],
            line=dict(color=DRIVER_CONFIG[driver_code]['color'], width=2),
            hovertemplate=f"<b>{DRIVER_CONFIG[driver_code]['name']}</b><br>" +
                         "Distance: %{x:.0f}m<br>" +
                         "Braking: %{y}<br>" +
                         "<extra></extra>",
            showlegend=False
        ), row=3, col=1)
    
    if show_delta:
        fig.add_trace(go.Scatter(
            x=ref_tel['Distance'],
            y=delta_time,
            mode='lines',
            name="Delta",
            line=dict(color='white', width=2, dash='dash'),
            customdata=[
                [
                    DRIVER_CONFIG[ref_driver]['name'] if d > 0 else DRIVER_CONFIG[compare_driver]['name'],   
                    DRIVER_CONFIG[compare_driver]['name'] if d > 0 else DRIVER_CONFIG[ref_driver]['name'],   
                    abs(d)  # Absolute gap
                ]
                for d in delta_time
            ],
            hovertemplate=
                "Distance: %{x:.0f}m<br>" +
                "Ahead: <b>%{customdata[0]}</b><br>" +
                "Behind: %{customdata[1]}<br>" +
                "Gap: %{customdata[2]:.3f}s<br>" +
                "<extra></extra>",
            showlegend=True
        ), row=4, col=1)
        
        fig.add_hline(
            y=0,
            line=dict(color='white', width=1),
            row=4, col=1
        )
    else:
        fig.add_annotation(
            text="Select 2 drivers to see delta",
            xref="x4", yref="y4",
            x=0.5, y=0,
            showarrow=False,
            font=dict(color='white', size=12)
        )
    
    fig.update_yaxes(title_text="Speed (km/h)", row=1, col=1)
    fig.update_yaxes(title_text="Throttle (%)", row=2, col=1)
    fig.update_yaxes(title_text="Brake", tickvals=[0, 1], ticktext=['Off', 'On'], row=3, col=1)
    fig.update_yaxes(title_text="Delta (s)", row=4, col=1)
    fig.update_xaxes(title_text="Distance (m)", row=4, col=1)
    
    fig.update_layout(
        title=f"Fastest Lap Comparison - {session.event['EventName']} {session.event.year} Qualifying",
        height=800,
        hovermode='x unified',
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

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
                hoverinfo='skip',  
                showlegend=False
            ))

    fig.update_xaxes(title_text="Lap Number")
    fig.update_yaxes(title_text="Driver")

    fig.update_layout(
        title="Tyre Strategy",
        height=400,  
        barmode='stack',
        plot_bgcolor='rgba(0,0,0,0)',
    )

    return fig
    
def degradation_chart(laps_df, session):
    laps_df = laps_df.copy()
    
    compound_colors = {
        'SOFT': '#FF0000',      
        'MEDIUM': '#FFA500',    
        'HARD': '#FFFFFF',      
        'INTERMEDIATE': '#00FF00',  
        'WET': '#0000FF'        
    }
    
    fig = go.Figure()
    
    for driver_code in ['VER', 'NOR', 'PIA']:
        if driver_code not in laps_df['DriverCode'].unique():
            continue
            
        driver_laps = laps_df[laps_df['DriverCode'] == driver_code].sort_values('LapNumber')
        driver_name = DRIVER_CONFIG[driver_code]['name']
        
        valid_laps = driver_laps[
            (driver_laps['LapTime'].notna()) &
            (driver_laps['IsAccurate'] == True)
        ].copy()
        
        if valid_laps.empty:
            continue
        
        valid_laps['LapTimeSeconds'] = valid_laps['LapTime'].dt.total_seconds()
        
        stints = valid_laps.groupby(['Stint', 'Compound'])
        
        for (stint_id, compound), stint_laps in stints:
            if len(stint_laps) < 2:
                continue
            
            stint_laps = stint_laps.sort_values('TyreLife').copy()
            
            first_lap_time = stint_laps['LapTimeSeconds'].iloc[0]
            stint_laps['Degradation'] = stint_laps['LapTimeSeconds'] - first_lap_time
            
            compound_color = compound_colors.get(compound, '#808080')
            
            degradation_labels = stint_laps['Degradation'].apply(
                lambda d: f"+{d:.3f}s (slower)" if d > 0 else f"{d:.3f}s (faster)" if d < 0 else "0.000s (same)"
            ).values
            
            fig.add_trace(go.Scatter(
                x=stint_laps['TyreLife'],
                y=stint_laps['Degradation'],
                mode='lines+markers',
                name=f"{driver_name} - {compound} (Stint {int(stint_id)})",
                line=dict(
                    color=DRIVER_CONFIG[driver_code]['color'],
                    width=2,
                    dash='solid' if compound == 'HARD' else
                          'dash' if compound == 'MEDIUM' else
                          'dot'
                ),
                marker=dict(
                    size=6,
                    color=compound_color,
                    line=dict(color='black', width=0.5)
                ),
                customdata=degradation_labels,  
                hovertemplate=f"<b>{driver_name}</b><br>" +
                             f"Compound: {compound}<br>" +
                             f"Stint: {int(stint_id)}<br>" +
                             "Tyre Life: %{x} laps<br>" +
                             "Degradation: %{customdata}<br>" +  
                             "<extra></extra>"
            ))
    
    fig.add_hline(
        y=0,
        line=dict(color='white', width=1, dash='dash'),
        annotation_text="Baseline (Lap 1 of Stint)",
        annotation_font_color='white'
    )
    
    fig.update_layout(
        title="Tyre Degradation by Stint",
        xaxis_title="Tyre Life (Laps)",
        yaxis_title="Degradation (s vs Lap 1)",
        hovermode='closest',
        height=600,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white', size=12),
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            bgcolor='rgba(0,0,0,0.5)',
            title="Driver - Compound - Stint"
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
    
    st.title("🏎️ Welcome to the 2025 Formula 1 Season Top 3 Drivers Analysis")
    st.subheader("Max Verstappen vs Lando Norris vs Oscar Piastri")
   
    st.markdown(""" 
    The 2025 Formula 1 Season was the first time since 2010 where the Championship 
    was decided in the final race of the season with 3 or more title contenders. 
    These 3 drivers being Max Verstappen of Red Bull Racing, Lando Norris of Mclaren F1 
    and Oscar Piastri of Mclaren F1. The title was won by Lando Norris of Mclaren F1 with 
    Max Verstappen of Red Bull Racing coming in second with a point difference of 2 points between then. 
    With Oscar Piastri coming in 3rd with a differnce of 13 points between 1st and 3rd.
    This study provides comprehensive analysis of the 2025 F1 season battle between 
    Max Verstappen (Red Bull Racing), Lando Norris (McLaren), and Oscar Piastri (McLaren).
    """)
    
    st.image("https://coffeecornermotorsport.com/wp-content/uploads/2025/12/SI202512070209.webp",use_container_width=True)
    
    st.markdown("---")

with tab2:
    st.title("Season Overview")
    st.subheader("Championship Standings and Performance Metrics")
    
    st.markdown("""
    - Championship Standings: A table showing the final points and positions of the 3 drivers.
    - Performance Metrics: Key statistics such as wins, podiums, pole positions, and fastest laps.
    """)

    if schedule is None:
        st.error("Unable to load race schedule for 2025 Season.")
    else:
        with st.spinner("Loading season data..."):
            season_results = load_all_season_data(selected_year, schedule)
        
        if season_results.empty:
            st.warning("No race data available for the 2025 season.")
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
    - Delta Time Chart: Comparing the drivers' fastest lap times in qualifying sessions. This analysis is acompanied by a speed, throttle, brake and delta panel to provide a comprehensive view of the drivers' performance during qualifying sessions.
    - Minisector Plot: A plot of the circuit where it displays the drivers dominance in deifferent parts of the track, showing which driver was faster in each sector of the circuit.
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
    with st.expander("Delta Time Comparison", expanded=True):
        st.markdown("""
    This chart compares the drivers' performance during their fastest qualifying lap:
    - The top panel shows the speed of each driver throughout the lap.
    - The middle panels show the throttle and brake application.
    - The bottom panel shows the delta time between the two drivers, with a dashed line indicating when they are equal.
    """)
    
        delta_comparison = st.radio(
            "Delta Comparison",
            options=["VER vs NOR", "VER vs PIA", "NOR vs PIA"],
            horizontal=True
    )
    
        delta_map = {
            "VER vs NOR": ("VER", "NOR"),
            "VER vs PIA": ("VER", "PIA"),
            "NOR vs PIA": ("NOR", "PIA")
        }
    
        ref_driver, compare_driver = delta_map[delta_comparison]  
    
        delta_chart = create_delta_time_chart(quali_session, [ref_driver, compare_driver])
    
        if delta_chart is not None:
            st.plotly_chart(delta_chart, use_container_width=True)
        else:
            st.warning("Could not create delta time chart. Please check the data.")  
    
    #2
    with st.expander("Mini-Sector Performance Comparison", expanded=True):
        st.markdown("""
        This plot compares the drivers' performance in different sections of the track during their fastest qualifying lap:
        - The track is divided into mini-sectors, and each section is colored based on which driver was fastest in that mini-sector.
        """)
        
        minisector_chart = create_minisector_comparison(quali_session, selected_drivers)
        
        if minisector_chart is not None:
            st.plotly_chart(minisector_chart, use_container_width=True)
        else:
            st.warning("Could not create minisector comparison chart. Please check the data.")

with tab4:
    st.title("Race Analysis")
    st.subheader("An analysis on the drivers performance during the Featured Race across the 2025 F1 Season.")
    
    st.markdown("""
    This section will provide insights into the drivers' race performance, including:
    - Tyre Strategy Analysis: A bar chart showing the tyre strategy of each driver during the race, including the type of tyre used and the lap on which they were used.
    - Degradation Analysis: A line plot showing the degradation of the tyres over the course of the race.
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
    with st.expander("Tyre Strategy Analysis", expanded=True):  

        st.markdown("""       
        The stacked bar chart shows the tyre strategy for each driver:
        - Each horizontal bar represents a stint on a particular tyre compound.
        - The color of the bar indicates the tyre compound used (Red=Soft, Yellow=Medium, White=Hard, Green=Intermediate, Blue=Wet).
        """)

        tyrestrat_chart = tyrestrategy_chart(laps_data, race_session)
        st.plotly_chart(tyrestrat_chart, use_container_width=True)

    #2
    with st.expander("Tyre Degradation Analysis", expanded=True):
        st.markdown("""
        The line plot shows the degradation of the tyres over the course of each stint:
        - The x-axis represents the tyre life in laps, while the y-axis represents the degradation in seconds compared to the first lap of the stint.
        - Each line represents a stint on a particular tyre compound, with the color indicating the driver and the line style indicating the tyre compound (solid=Hard, dashed=Medium, dotted=Soft).
        """)
        
        degradation_chart_fig = degradation_chart(laps_data, race_session)
        st.plotly_chart(degradation_chart_fig, use_container_width=True)

        st.markdown("---")

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

    #4
    with st.expander("Lap Time Distribution Violin Plot", expanded=False):
        st.subheader("Lap Time Distribution by Driver and Tire Compound")
        
        st.markdown("""
        This violin plot shows the distribution of lap times for each driver, grouped by tire compound:
        - The width of the violin indicates the density of lap times at different values.
        - The color of the markers indicates the tire compound used for each lap.
        """)
        
        laptimes_violin_chart = laptimes_violin(laps_data, selected_drivers)
        st.plotly_chart(laptimes_violin_chart, use_container_width=True)

    #5
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