import streamlit as st
import pandas as pd
import altair as alt

# Load and preprocess data
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
        .agg({'position': 'mean'})
        .rename(columns={'surname': 'name', 'position': 'avg_qualifying_position'})
    )

    return driver_agg, constructor_agg, constructor_podium_counts, qualifying_avg

# Load data
driver_data, constructor_data, constructor_podiums, qualifying_avg = load_data()

# Sidebar controls
metric = st.sidebar.radio("Select Metric:", ['points', 'wins'])
years = ['All Years'] + sorted(driver_data['year'].unique())
selected_year = st.sidebar.selectbox("Select Year:", years)

# Page Title
st.markdown("""
    <h1 style='text-align: center; white-space: nowrap;'>F1 Dominance Dashboard: 2010–2020</h1>
    """, unsafe_allow_html=True)
st.markdown("Explore which **drivers** and **constructors** dominated Formula 1 in the past decade!")

# Tabs for Driver vs Constructor
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

    area_chart = alt.Chart(driver_data[driver_data['wins'] > 0]).mark_area().encode(
        x=alt.X('year:O', title='Year'),
        y=alt.Y('wins:Q', stack='zero', title='Number of Wins'),
        color=alt.Color('name:N', title='Driver', scale=alt.Scale(scheme='category20')),
        tooltip=['year', 'name', 'wins'],
        opacity=alt.condition(driver_selection, alt.value(1), alt.value(0.15))
    ).add_params(driver_selection).properties(
        title='Driver Dominance by Wins (2010–2020)',
        width=900,
        height=400
    )

    qualifying_filtered = qualifying_avg[qualifying_avg['name'].isin(driver_data[driver_data['wins'] > 0]['name'].unique())]

    line_chart = alt.Chart(qualifying_filtered).mark_line(point=True).encode(
        x=alt.X('year:O', title='Year'),
        y=alt.Y('avg_qualifying_position:Q', title='Avg Qualifying Position'),
        color=alt.Color('name:N', title='Driver', scale=alt.Scale(scheme='category20')),
        tooltip=['year', 'name', 'avg_qualifying_position'],
        opacity=alt.condition(driver_selection, alt.value(1), alt.value(0.1))
    ).add_params(driver_selection).properties(
        title='Driver Dominance by Average Qualifying Position (2010-2020)',
        width=900,
        height=400
    )

    st.altair_chart(bar_chart, use_container_width=True)
    st.altair_chart(area_chart, use_container_width=True)
    st.altair_chart(line_chart, use_container_width=True)

with tab2:
    cdf = constructor_data.copy()
    if selected_year != 'All Years':
        cdf = cdf[cdf['year'] == int(selected_year)]

    selection = alt.selection_point(fields=['name'])

    bar_chart = alt.Chart(cdf).mark_bar().encode(
        x=alt.X(f'{metric}:Q', title=metric.title()),
        y=alt.Y('name:N', sort='-x', title='Constructor'),
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
        color=alt.Color('name:N', title='Constructor'),
        tooltip=['year', 'name', 'podiums'],
        opacity=alt.condition(selection, alt.value(1), alt.value(0.2))
    ).add_params(selection).properties(
        title='Team Dominance by Podium Finishes (2010–2020)',
        width=900,
        height=500
    )

    st.altair_chart(bar_chart, use_container_width=True)
    st.altair_chart(area_chart, use_container_width=True)