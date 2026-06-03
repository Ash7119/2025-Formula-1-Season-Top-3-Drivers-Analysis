# 2025 Formula 1 Season Top 3 Driver Analysis
The 2025 Formula 1 Season was the first time since 2010 where the Championship was decided in the final race of the season with 3 or more title contenders. These 3 drivers being Max Verstappen of Red Bull Racing, Lando Norris of Mclaren F1 and Oscar Piastri of Mclaren F1. The title was won by Lando Norris of Mclaren F1 with Max Verstappen of Red Bull Racing coming in second with a point difference of 2 points between then. With Oscar Piastri coming in 3rd with a differnce of 13 points between 1st and 3rd.  This study provides comprehensive analysis of the 2025 F1 season battle between Max Verstappen (Red Bull Racing), Lando Norris (McLaren), and Oscar Piastri (McLaren). 

The analysis is hosted by a streamlit dashboard with 4 tabs:
- Home Page
- Season Overview
- Qualifying Analysis
- Race Analysis

## How to run it locally
### Step 1: Clone the Repository
git clone https://github.com/Ash7119/2025-Formula-1-Season-Top-3-Drivers-Analysis.git
cd 2025-Formula-1-Season-Top-3-Drivers-Analysis

### Step 2: Install Dependencies
pip install streamlit fastf1 pandas plotly

### Step 3: Run the App
python -m streamlit run MOL.py

### Step 4: Open in Browser
The app will automatically open in your browser

## Data
The data is pulled from the FastF1 api.

Link: https://docs.fastf1.dev/index.html

## Libraries used:
- FastF1
- Streamlit
- Plotly
- Pandas

## Sources
These sources helped me in conducting this project:
- https://docs.streamlit.io/
- https://docs.fastf1.dev/index.html
- https://formula1math.substack.com/p/a-deep-dive-into-tyre-degradation
- https://medium.com/towards-formula-1-analysis/analyzing-formula-1-data-using-python-2021-abu-dhabi-gp-minisector-comparison-3d72aa39e5e8

## Notes
- Accurate Laps were used for the analysis in this project.
- Miami GP not included due to data issues in the session.
- The first time you run the app, FastF1 will download and cache race data locally. This may take a few minutes. Subsequent loads will be much faster as data is cached in the `.fastf1_cache` folder.
