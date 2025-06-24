import streamlit as st
import pandas as pd
import altair as alt

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
    **🚗 Constructor**: A team that designs, builds, and races a car (e.g., Ferrari, Mercedes).  
    **👨‍🔧 Drivers per Constructor**: Each constructor fields the same 2 drivers for every race in a season.   
    **📅 Races per Season**: Typically 20–23 races per year, varying slightly.  
    **⏱️ Qualifying**: A timed session before each race where drivers compete to set the fastest lap. The results determine the starting grid for the race, with the fastest driver earning pole position (1st).   
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
   
   st.markdown("""
    ### Driver Performance Bar Chart

    You can **filter the chart by year, total points, and wins** using the sidebar options.

    - **Points** reflect **cumulative performance** over an entire season (or multiple seasons), accounting for finishing position in every race.
    - **Wins** indicate how many times a driver finished first, but don't consider consistency.

    > For example, a driver with more points but fewer wins may have consistently placed 2nd or 3rd, showing strong overall performance.

    Use the filters to explore different timeframes and compare how different drivers performed.
   """)

   bar_chart = alt.Chart(ddf).mark_bar().encode(
       x=alt.X(f'{metric}:Q', title=metric.title()),
       y=alt.Y('name:N', sort='-x', title='Driver'),
       tooltip=['year', 'name', f'{metric}'],
       order=alt.Order('year:O', sort='ascending'),  # <-- this controls internal stacking
       opacity=alt.condition(selection, alt.value(1), alt.value(0.4))
   ).add_params(selection).properties(
       width=900,
       height=500,
       title=f"Top F1 Drivers by {metric.title()}"
   )
   


   driver_selection = alt.selection_point(name='SelectDriver', fields=['name'], on='click', bind='legend')


   qualifying_filtered = qualifying_avg[qualifying_avg['name'].isin(driver_data[driver_data['wins'] > 0]['name'].unique())]


   driver_data['name'] = driver_data['name'].astype(str)
   qualifying_filtered.loc[:, 'name'] = qualifying_filtered['name'].astype(str)

   annotation_point_1 = pd.DataFrame({
        'year': [2014],  
        'wins': [21.99] 
   })

   annotation_text_1 = alt.Chart(annotation_point_1).mark_text(
        text='⬆️ LARGER AREA = BETTER',
        align='right',
        baseline='top',
        dx=-5,
        dy=5,
        fontSize=13,
        fontWeight='bold'
   ).encode(
        x=alt.X('year:O'),
        y=alt.Y('wins:Q')
   )

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

   annotation_point_2 = pd.DataFrame({
    'year': [2020],  # max year in your chart
    'avg_qualifying_position': [23]  # lowest (best) position
   })

   annotation_text_2 = alt.Chart(annotation_point_2).mark_text(
        text='⬇️ LOWER = BETTER',
        align='right',
        baseline='top',
        dx=-5,
        dy=5,
        fontSize=13,
        fontWeight='bold'
   ).encode(
        x=alt.X('year:O'),
        y=alt.Y('avg_qualifying_position:Q')
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

   st.markdown("""
        ### Driver Dominance Over Time: Wins vs. Qualifying Performance

        This section combines two visualizations to help you understand **driver dominance over time**:

        - The **stacked area chart** shows **total wins per driver** each season, highlighting standout years and shifts in dominance.
        - The **line chart** shows each driver's **average qualifying position**, offering insight into their **single-lap pace and consistency**.

        > While **wins** reflect race-day success, **qualifying position** indicates how competitive a driver is in setting fast laps and securing good starting positions.

        Use this view to compare drivers who not only win races but also consistently start near the front of the grid.
   """)

   st.markdown(
    "<div style='text-align:left; font-size:13px; color:gray;'>🔍 Click a driver in the legend or either chart to highlight</div>",
    unsafe_allow_html=True
   )

   line_chart_annotated = line_chart + annotation_text_2
   area_chart_annotated = area_chart + annotation_text_1

   combined = area_chart_annotated | line_chart_annotated
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
    'HRT': '#A8A8A8',
    'Retired': '#F9F9F9',
    'Inactive': '#F9F9F9'
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

   st.markdown("""
    ### Constructor Performance Bar Chart

    This chart displays **Constructor (team) performance**, and you can **filter it by year, total points, and wins** using the sidebar controls.

    - **Points** represent the **combined performance of both team drivers** across races.
    - **Wins** reflect how often **either of the two drivers** from a constructor won a race.

    > A constructor with high points but fewer wins may have had both drivers consistently finish in the top 5, showing **team-wide reliability and depth**.

    Use this chart to compare how different teams dominated across seasons or sustained strong performance without necessarily always winning.
   """)



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

   annotation_point_3 = pd.DataFrame({
        'year': [2013],  # rightmost year
        'podiums': [64.5]  # highest podium count
   })

   annotation_text_3 = alt.Chart(annotation_point_3).mark_text(
        text='⬆️ LARGER AREA = BETTER',
        align='right',
        baseline='top',
        dx=-5,
        dy=5,
        fontSize=13,
        fontWeight='bold',
   ).encode(
        x=alt.X('year:O'),
        y=alt.Y('podiums:Q')
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

   st.markdown("""
        ### Constructor Dominance Over Time: Podiums

        This stacked area chart highlights **team (constructor) dominance over time** by visualizing the number of **podium finishes** each season.

        - A **podium finish** refers to a driver finishing **in the top 3 positions** of a race — 1st, 2nd, or 3rd place.
        - Since each constructor can have **two drivers**, podiums are a great measure of **overall team competitiveness**, not just individual brilliance.

        > A constructor with frequent podiums — even without many wins — demonstrates **reliable top-tier performance and strong team depth**.

        Use this chart to explore which teams consistently placed at the front of the grid and how team dominance has shifted across seasons.
   """)

   st.markdown(
    "<div style='text-align:left; font-size:13px; color:gray;'>🔍 Click a constructor in the chart or legend to highlight</div>",
    unsafe_allow_html=True
   )

   area_chart_annotated = area_chart + annotation_text_3

   st.altair_chart(area_chart_annotated, use_container_width=True)


st.markdown("### Team Progression of the Top 5 Drivers")
st.markdown("This chart shows how the top 5 drivers switched between teams over the decade.")

# Team progression data for 5 drivers
data = pd.DataFrame([
    *[(year, 'Hamilton', 'McLaren') for year in range(2010, 2013)],
    *[(year, 'Hamilton', 'Mercedes') for year in range(2013, 2021)],

    *[(year, 'Vettel', 'Red Bull') for year in range(2010, 2015)],
    *[(year, 'Vettel', 'Ferrari') for year in range(2015, 2021)],

    *[(year, 'Rosberg', 'Mercedes') for year in range(2010, 2017)],
    *[(year, 'Rosberg', 'Inactive/Retired') for year in range(2017, 2021)],

    *[(year, 'Alonso', 'Ferrari') for year in range(2010, 2015)],
    *[(year, 'Alonso', 'McLaren') for year in range(2015, 2019)],
    *[(year, 'Alonso', 'Inactive/Retired') for year in range(2019, 2021)],

    *[(year, 'Bottas', 'Inactive/Retired') for year in range(2010, 2013)],
    *[(year, 'Bottas', 'Williams') for year in range(2013, 2017)],
    *[(year, 'Bottas', 'Mercedes') for year in range(2017, 2021)],
], columns=['year', 'driver', 'team'])

data['year'] = data['year'].astype(str)

driver_order = ['Hamilton', 'Vettel', 'Bottas', 'Alonso', 'Rosberg']

constructor_colors = {
    'Mercedes': '#00D2BE',
    'Ferrari': '#DC0000',
    'Red Bull': '#1E41FF',
    'McLaren': '#FF8700',
    'Williams': '#3399FF',      # Medium Sky Blue
    'Inactive/Retired': '#F9F9F9',
}

color_scale = alt.Scale(
    domain=list(constructor_colors.keys()),
    range=list(constructor_colors.values())
)

chart = alt.Chart(data).mark_rect().encode(
    x=alt.X('year:O', title='Year'),
    y=alt.Y('driver:N', title='Driver', sort=driver_order),
    color=alt.Color('team:N', scale=color_scale),
    tooltip=['driver', 'year', 'team']
).properties(
    width=750,
    height=300,
    title='Team Progression of Top F1 Drivers (2010–2020)'
)



st.altair_chart(chart, use_container_width=True)




st.markdown("---") 
st.markdown("### Key Insights")

with st.expander("Key Insights: Driver Dominance (2010–2020)"):
    st.markdown("""
        - **Sebastian Vettel** dominated the early 2010s, winning four consecutive world titles with Red Bull from **2010 to 2013**, often combining strong qualifying with race wins.
        - **Lewis Hamilton** took over as the dominant force from **2014 to 2020**, driving for Mercedes. He had the most wins and pole positions during this period, showing both qualifying and race-day excellence.
        - **Nico Rosberg** (2016) briefly disrupted Hamilton’s streak with a title win, despite slightly fewer wins overall.
        - **Fernando Alonso** and **Jenson Button** were competitive early in the decade but gradually faded as their teams struggled.
        - **Max Verstappen** emerged as a serious contender near the end of the decade, becoming a consistent podium finisher and race winner by 2019–2020.
    """)
with st.expander("Key Insights: Constructor Dominance (2010–2020)"):
    st.markdown("""
        - **Red Bull Racing** dominated from **2010 to 2013**, driven largely by Sebastian Vettel’s performance and consistent podium finishes.
        - **Mercedes** began a historic run starting in **2014**, winning **seven consecutive constructor championships** through 2020, with both Lewis Hamilton and Nico Rosberg contributing heavily.
        - Mercedes' success was marked not just by wins but by **consistent double podiums**, showing dominance through both drivers.
        - **Ferrari** remained competitive (especially in 2017–2018 with Vettel), but lacked the consistency to dethrone Mercedes.
        - Teams like **McLaren**, **Lotus**, and **Williams** had intermittent podium appearances but were not long-term title challengers in this era.
    """)

   

