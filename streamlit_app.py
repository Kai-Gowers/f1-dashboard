import streamlit as st
import pandas as pd
import altair as alt
import time


@st.cache_data
def load_data():
   results = pd.read_csv("results.csv")
   races = pd.read_csv("races.csv")
   drivers = pd.read_csv("drivers.csv")
   constructors = pd.read_csv("constructors.csv")
   qualifying = pd.read_csv("qualifying.csv")


   races = races[['raceId', 'year']]
   results = results.merge(races, on='raceId')


   # Process drivers
   results_drivers = results.merge(drivers[['driverId', 'surname']], on='driverId')
   driver_agg = (
       results_drivers[(results_drivers['year'] >= 2010) & (results_drivers['year'] <= 2020)]
       .groupby(['year', 'surname'], as_index=False)
       .agg({'points': 'sum', 'positionOrder': lambda x: (x == 1).sum()})
   )
   driver_agg['type'] = 'Driver'
   driver_agg.rename(columns={'surname': 'name', 'positionOrder': 'wins'}, inplace=True)

   # Process constructors
   results_constructors = results.merge(constructors[['constructorId', 'name']], on='constructorId')
   constructor_agg = (
       results_constructors[(results_constructors['year'] >= 2010) & (results_constructors['year'] <= 2020)]
       .groupby(['year', 'name'], as_index=False)
       .agg({'points': 'sum', 'positionOrder': lambda x: (x == 1).sum()})
   )
   constructor_agg['type'] = 'Constructor'
   constructor_agg.rename(columns={'positionOrder': 'wins'}, inplace=True)


   # Podium finishes for constructors
   podiums_constructors = results_constructors[results_constructors['positionOrder'].notna()]
   podiums_constructors['positionOrder'] = podiums_constructors['positionOrder'].astype(int)
   podiums_constructors = podiums_constructors[
       (podiums_constructors['positionOrder'] <= 3) &
       (podiums_constructors['year'] >= 2010) & (podiums_constructors['year'] <= 2020)
   ]
   constructor_podium_counts = (
       podiums_constructors.groupby(['year', 'name']).size().reset_index(name='podiums')
   )


   # Qualifying average position per driver per year
   qualifying = qualifying.merge(races[['raceId', 'year']], on='raceId')
   qualifying = qualifying.merge(drivers[['driverId', 'surname']], on='driverId')
   qualifying = qualifying[
       (qualifying['year'] >= 2010) & (qualifying['year'] <= 2020)
   ]
   qualifying_avg = (
       qualifying.groupby(['year', 'surname'], as_index=False)
       .agg({'position': 'median'})
       .rename(columns={'surname': 'name', 'position': 'avg_qualifying_position'})
   )
   qualifying_avg['avg_qualifying_position'] = qualifying_avg['avg_qualifying_position'].round(1)



   return driver_agg, constructor_agg, constructor_podium_counts, qualifying_avg




# Data time


driver_data, constructor_data, constructor_podiums, qualifying_avg = load_data()


st.sidebar.markdown("### Filters (Apply to Bar Chart Only)")
metric = st.sidebar.radio("Select Metric:", ['points', 'wins'])
years = ['All Years'] + sorted(driver_data['year'].unique())
selected_year = st.sidebar.selectbox("Select Year:", years)

if 'prev_metric' not in st.session_state:
    st.session_state.prev_metric = metric
if 'prev_year' not in st.session_state:
    st.session_state.prev_year = selected_year

filters_changed = (metric != st.session_state.prev_metric) or (selected_year != st.session_state.prev_year)

# Update stored filters
st.session_state.prev_metric = metric
st.session_state.prev_year = selected_year


st.markdown("""
   <h1 style='text-align: center; white-space: nowrap;'>F1 Dominance Dashboard: 2010–2020</h1>
   """, unsafe_allow_html=True)
st.markdown("Explore which **drivers** and **constructors** dominated Formula 1 in the past decade!")

with st.expander("Learn How Formula 1 Works!"):
    st.markdown("""
    **🏁 Pole Position**: The first starting position on the grid, earned by the fastest qualifier.  
    **🚗 Constructor**: A team that designs, builds, and races a car (e.g., Ferrari, Mercedes).  
    **👨‍🔧 Drivers per Constructor**: Each constructor fields 2 drivers in every race.  
    **📅 Races per Season**: Typically 20–23 races per year, varying slightly.  
    **⏱️ Qualifying**: A timed session before each race where drivers compete to set the fastest lap. The results determine the starting grid for the race, with the fastest driver earning pole position.  
    **🏆 Points System**: Points are awarded to the top 10 finishers in each race as follows:

    | Position | Points |
    |----------|--------|
    | 1st      | 25     |
    | 2nd      | 18     |
    | 3rd      | 15     |
    | 4th      | 12     |
    | 5th      | 10     |
    | 6th      | 8      |
    | 7th      | 6      |
    | 8th      | 4      |
    | 9th      | 2      |
    | 10th     | 1      |
    """)



tab1, tab2 = st.tabs(["Drivers", "Constructors"])


with tab1:
   ddf = driver_data.copy()
   if selected_year != 'All Years':
       ddf = ddf[ddf['year'] == int(selected_year)]


   ddf = ddf.sort_values(by=metric, ascending=False).head(10 if selected_year != 'All Years' else 50)


   selection = alt.selection_point(fields=['name'])


   bar_chart = alt.Chart(ddf).mark_bar().encode(
       x=alt.X(f'{metric}:Q', title=metric.title()),
       y=alt.Y('name:N', sort='-x', title='Driver'),
       tooltip=['year', 'name', f'{metric}'],
       opacity=alt.condition(selection, alt.value(1), alt.value(0.4))
   ).add_params(selection).properties(
       width=900,
       height=500,
       title=f"Top F1 Drivers by {metric.title()}"
   )
   


   driver_selection = alt.selection_point(name='SelectDriver', fields=['name'], on='click', bind='legend')


   qualifying_filtered = qualifying_avg[qualifying_avg['name'].isin(driver_data[driver_data['wins'] > 0]['name'].unique())]


   driver_data['name'] = driver_data['name'].astype(str)
   qualifying_filtered['name'] = qualifying_filtered['name'].astype(str)


   area_chart = alt.Chart(driver_data[driver_data['wins'] > 0]).mark_area().encode(
       x=alt.X('year:O', title='Year'),
       y=alt.Y('wins:Q', stack='zero', title='Number of Wins'),
       color=alt.Color('name:N', title='Driver', scale=alt.Scale(scheme='category20')),
       tooltip=['year', 'name', 'wins'],
       opacity=alt.condition(driver_selection, alt.value(1), alt.value(0.15))
   ).add_params(driver_selection).properties(
       title='Driver Dominance by Wins (2010–2020)',
       width=400,
       height=250
   )




   line_chart = alt.Chart(qualifying_filtered).mark_line(point=True).encode(
       x=alt.X('year:O', title='Year'),
       y=alt.Y('avg_qualifying_position:Q', title='Avg Qualifying Position'),
       color=alt.Color('name:N', title='Driver', scale=alt.Scale(scheme='category20'), legend=alt.Legend(orient="bottom", columns=7)),
       tooltip=['year', 'name', 'avg_qualifying_position'],
       opacity=alt.condition(driver_selection, alt.value(1), alt.value(0.1))
   ).add_params(driver_selection).properties(
       title='Driver Dominance by Average Qualifying Position (2010-2020)',
       width=400,
       height=250
   )
   
   st.markdown(
    "<div style='text-align:left; font-size:13px; color:gray;'>🔍 Click a driver in the chart to highlight</div>",
    unsafe_allow_html=True
   )

   st.altair_chart(bar_chart, use_container_width=True)
   if filters_changed:
      st.toast("✅ Change applied!")

   
   st.markdown(
    "<div style='text-align:left; font-size:13px; color:gray;'>🔍 Click a driver in the legend or either chart to highlight</div>",
    unsafe_allow_html=True
   )

   combined = area_chart | line_chart
   st.altair_chart(combined, use_container_width=False)
   


constructor_colors = {
    'Mercedes': '#00D2BE',
    'Ferrari': '#DC0000',
    'Red Bull': '#1E41FF',
    'McLaren': '#FF8700',
    'Renault': '#FFF500',
    'Alpine': '#007FFF',        # Strong Azure Blue
    'AlphaTauri': '#1C2D5A',
    'Alfa Romeo': '#900000',
    'Haas F1 Team': "#3F94D6",
    'Williams': '#3399FF',      # Medium Sky Blue
    'Racing Point': '#F596C8',
    'Toro Rosso': '#6495ED',    # Cornflower Blue
    'Force India': '#F26622',
    'Lotus F1': '#FFD700',
    'Caterham': '#006F62',
    'Marussia': '#B5121B',
    'Manor': '#ED1C24',
    'Sauber': '#4682B4',        # Steel Blue
    'Virgin': '#D70040',
    'HRT': '#A8A8A8'
}

constructor_colors_stacked = {
    'Mercedes': '#00D2BE',      # Teal
    'Ferrari': '#DC0000',       # Red
    'Red Bull': '#1E41FF',      # Deep Royal Blue
    'McLaren': '#FF8700',       # Papaya Orange
    'Renault': '#FFF500',       # Bright Yellow
    'Alpine': '#007FFF',        # Strong Azure Blue
    'AlphaTauri': '#1C2D5A',    # Dark Slate Blue
    'Williams': '#3399FF',      # Medium Sky Blue
    'Racing Point': '#F596C8',  # Pink
    'Toro Rosso': '#6495ED',    # Cornflower Blue
    'Force India': '#F26622',   # Bright Orange
    'Lotus F1': '#FFD700',      # Gold
    'Sauber': '#4682B4'         # Steel Blue
}



with tab2:
   cdf = constructor_data.copy()
   if selected_year != 'All Years':
       cdf = cdf[cdf['year'] == int(selected_year)]


   selection = alt.selection_point(fields=['name'], on='click', bind='legend')


   bar_chart = alt.Chart(cdf).mark_bar().encode(
       x=alt.X(f'{metric}:Q', title=metric.title()),
       y=alt.Y('name:N', sort='-x', title='Constructor'),
       color=alt.Color(
        'name:N',
        scale=alt.Scale(domain=list(constructor_colors.keys()), range=list(constructor_colors.values())),
        title='Constructor',
        legend=None
       ),
       tooltip=['year', 'name', f'{metric}'],
       opacity=alt.condition(selection, alt.value(1), alt.value(0.4))
   ).add_params(selection).properties(
       width=900,
       height=500,
       title=f"Top F1 Constructors by {metric.title()}"
   )


   area_chart = alt.Chart(constructor_podiums).mark_area().encode(
       x=alt.X('year:O', title='Year'),
       y=alt.Y('podiums:Q', stack='zero', title='Number of Podiums'),
       color=alt.Color(
        'name:N',
        scale=alt.Scale(domain=list(constructor_colors_stacked.keys()), range=list(constructor_colors_stacked.values())),
        title='Constructor'
       ),
       tooltip=['year', 'name', 'podiums'],
       opacity=alt.condition(selection, alt.value(1), alt.value(0.2))
   ).add_params(selection).properties(
       title='Team Dominance by Podium Finishes (2010–2020)',
       width=900,
       height=500
   )

   st.markdown(
    "<div style='text-align:left; font-size:13px; color:gray;'>🔍 Click a constructor in the chart to highlight</div>",
    unsafe_allow_html=True
   )

   st.altair_chart(bar_chart, use_container_width=True)

   st.markdown(
    "<div style='text-align:left; font-size:13px; color:gray;'>🔍 Click a constructor in the chart or legend to highlight</div>",
    unsafe_allow_html=True
   )
   st.altair_chart(area_chart, use_container_width=True)

