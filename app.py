# Board of Education election results by precinct

import pandas as pd
import geopandas as gpd
import folium
import streamlit as st
from streamlit_folium import st_folium


st.title("Board of Education Election Results by Precinct")
st.markdown("""
This application presents the results of the Board of Education election by precinct.
""")

# set page config to wide
st.set_page_config(layout="wide", page_title="Board of Education Election Results by Precinct", page_icon=":bar_chart:")

@st.cache_data
def load_data():
    df = pd.read_csv("data.csv")

    # ersb_10 = gpd.read_file(rf"ERSB_10_District_Map_FA1_SB_15.shp")
    # ersb_20 = gpd.read_file(rf"ERSB_20_Sub_District_Map_FA1_SB_15.shp")
    # ward_precinct = gpd.read_file(rf"ward_precinct.geojson")
    # intersection = gpd.read_file(rf"ward_precinct_ersb20_intersection.geojson")


    # Strip whitespace from column names

    df['race_name'] = [xstr.strip() for xstr in df['race_name']]

    df['ward'] = df['ward'].apply(lambda x: str(x).zfill(2))
    df['precinct'] = df['precinct'].apply(lambda x: str(x).zfill(3))
    df['ward_precinct'] = df['ward'] + df['precinct']

    reg_voters = df[df['race_name'].isin(['Total Registered Voters'])]
    ballots_cast = df[df['race_name'].isin(['Ballots Cast'])]
    boe = df[df['race_name'].str.contains('Member of the Chicago Board of Education')]
    pt_relief = df[df['race_name'].isin(['The Property Tax Relief and Fairness Referendum'])]

    reg_voters = reg_voters[["ward_precinct","ward","precinct","votes"]]
    reg_voters.columns = ["ward_precinct","ward","precinct","registered_voters"]
    ballots_cast = ballots_cast[["ward_precinct","ward","precinct","votes"]]
    ballots_cast.columns = ["ward_precinct","ward","precinct","ballots_cast"]

    general = reg_voters.merge(ballots_cast,on=["ward_precinct","ward","precinct"],how="left")

    # District and precinct totals for candidates and BOE races
    boe_district = boe.groupby(['race_name']).agg({
        'votes':'sum'
        }).reset_index()
    boe_precinct = boe.groupby(['race_name','ward','precinct']).agg({
        'votes':'sum'
        }).reset_index()

    boe = boe.merge(boe_district,on="race_name",how="left",suffixes=("","_district"))
    boe = boe.merge(boe_precinct,on=["race_name","ward","precinct"],how="left",suffixes=("","_precinct"))

    # Rename for clarity
    rename = {
        'votes':'ballots_candidate_precinct',
        'votes_district':'ballots_district_total',
        'votes_candidate_district_total':'ballots_candidate_district_total',
        'votes_precinct':'ballots_precinct_total'
    }

    boe = boe.rename(columns=rename)

    boe['candidate_percent_precinct'] = boe['ballots_candidate_precinct'] / boe['ballots_precinct_total']

    # District and precinct totals for candidates and The Property Tax Relief and Fairness Referendum
    boe_join = boe.groupby(['ward','precinct']).agg({
        'race_name':'first'
        }).reset_index()

    # create a ward_precinct field in boe_join for merging with general
    boe_join['ward'] = boe_join['ward'].apply(lambda x: str(x).zfill(2))
    boe_join['precinct'] = boe_join['precinct'].apply(lambda x: str(x).zfill(3))
    boe_join['ward_precinct'] = boe_join['ward'] + boe_join['precinct']
    #drop ward and precinct from boe_join
    boe_join = boe_join.drop(columns=['ward','precinct'])

    # create ward_precinct field

    pt_relief = pt_relief.merge(boe_join,on=['ward_precinct'],how="left",suffixes=("","_boe"))

    pt_relief_district = pt_relief.groupby(['race_name']).agg({
        'votes':'sum'
        }).reset_index()
    pt_relief_choice_total = pt_relief.groupby(['race_name','candidate_name']).agg({
        'votes':'sum'
        }).reset_index()
    pt_relief_precinct = pt_relief.groupby(['race_name','ward','precinct']).agg({
        'votes':'sum'
        }).reset_index()


    pt_relief = pt_relief.merge(pt_relief_district,on="race_name",how="left",suffixes=("","_district"))
    pt_relief = pt_relief.merge(pt_relief_choice_total,on=["race_name","candidate_name"],how="left",suffixes=("","_choice_district_total"))
    pt_relief = pt_relief.merge(pt_relief_precinct,on=["race_name","ward","precinct"],how="left",suffixes=("","_precinct"))

    rename = {
    'votes':'ballots_choice_precinct',
    'votes_district':'ballots_district_total',
    'votes_choice_district_total':'ballots_choice_district_total',
    'votes_precinct':'ballots_ref_precinct_total'
    }

    pt_relief = pt_relief.rename(columns=rename)

    # Strip whitespace from candidate_name to ensure clean pivot column names
    pt_relief['candidate_name'] = pt_relief['candidate_name'].str.strip()

    # pad ward with 1 leading zero and precinct with 2 leading zeros

    pt_relief_totals = pt_relief.groupby('ward_precinct').agg({
        'ballots_ref_precinct_total':'first',
        'ballots_choice_district_total':'first',
        'ballots_district_total':'first'
        }).reset_index()

    pt_relief = pt_relief.pivot_table(
        index='ward_precinct',
        columns='candidate_name',
        values='ballots_choice_precinct',
        aggfunc='sum'
    ).reset_index()

    pt_relief = pt_relief.merge(pt_relief_totals,on="ward_precinct",how="left")


    general = general.merge(pt_relief,on="ward_precinct",how="left")

    general = boe_join.merge(general,on="ward_precinct",how="right")

    general['turnout_percent_precinct'] = general['ballots_cast'] / general['registered_voters']
    general['ref_turnout_percent_precinct'] = general['ballots_ref_precinct_total'] / general['registered_voters']
    general['ref_yes_percent_precinct'] = general['Yes'] / general['ballots_ref_precinct_total']
    general['ref_won_precinct'] = ["Won" if x > 0.5 else "Lost" for x in general['ref_yes_percent_precinct']]

    general.columns = [
    "race_name",
    "ward_precinct",
    "ward",
    "precinct",
    "registered_voters",
    "ballots_cast",
    "ref_no",
    "ref_yes",
    "ballots_ref_precinct_total",
    "ballots_ref_yes_district_total",
    "ballots_ref_district_total",
    "turnout_percent_precinct",
    "ref_turnout_percent_precinct",
    "ref_yes_percent_precinct",
    "ref_won_precinct"]

    return general,boe

#    return df,boe,general,pt_relief,ersb_20
#    return ward_precinct
def main():    
    # Load data
#    df,boe,general,pt_relief,ersb_20=load_data()
    general,boe=load_data()


    # Create a select box to select by race_name.unique() and sort alphabetically
    race_names = sorted(general['race_name'].unique())
    selected_race = st.selectbox("Select a race", race_names)
    filtered_general = general[general['race_name'] == selected_race]
    filtered_boe = boe[boe['race_name'] == selected_race]

    # groupby "candidate_name" and sume "ballots_candidate_precinct", "ballots_precinct_total"

    boe_grouped = filtered_boe.groupby(['candidate_name']).agg({
        'ballots_candidate_precinct':'sum',
        'ballots_precinct_total':'sum'
    }).reset_index()

    boe_grouped['candidate_percent_precinct'] = boe_grouped['ballots_candidate_precinct'] / boe_grouped['ballots_precinct_total']

        # Pivot BOE on candidate_name get first of ballots_candiate_precinct, ballots_precinct_total, candidate_percent_precinct
    filtered_boe = filtered_boe.pivot_table(
        index=['ward','precinct'],
        columns='candidate_name',
        values=['ballots_candidate_precinct','ballots_precinct_total','candidate_percent_precinct'],
        aggfunc='first'
    )
    
    # Flatten the MultiIndex columns
    filtered_boe.columns = ['_'.join(col).strip() for col in filtered_boe.columns.values]
    filtered_boe = filtered_boe.reset_index()

    winner = boe_grouped.sort_values('candidate_percent_precinct', ascending=False).iloc[0]['candidate_name']

    second_place = boe_grouped.sort_values('candidate_percent_precinct', ascending=False).iloc[1]['candidate_name']

    # for each column name remove "ballots_candidate_precinct_"
    filtered_boe.columns = [col.replace("ballots_candidate_precinct_", "") for col in filtered_boe.columns]
    # drop columns wiht "ballots_precinct_total"
    filtered_boe = filtered_boe.drop(columns=[col for col in filtered_boe.columns if "ballots_precinct_total" in col])
    # Remove "candidate_percent_precinct_" and add (Percent) to the end of the column name
    filtered_boe.columns = [col.replace("candidate_percent_precinct_", "") + " (Percent)" if "candidate_percent_precinct_" in col else col for col in filtered_boe.columns]

    # if the column name containst "Percent" then format the column as a percentage with 2 decimal places, if it does not contain "Percent" or "ward" or "precinct" then numeric with commas

    filtered_boe = filtered_boe.style.format({
        col: '{:.2%}' if "Percent" in col else '{:,.0f}' for col in filtered_boe.columns if col not in ['ward', 'precinct']
    })


    st.header(f"Voter Turnout and Millionaires Tax Referendum Results for {selected_race}")

    st.subheader("Summary of Results")

    # Write district turnout percent and ballot win percent yes
    # 
    st.markdown(f"""District Turnout Percent: {filtered_general['ballots_cast'].sum() / filtered_general['registered_voters'].sum():.2%}

{winner} Won the BOE Election with {boe_grouped[boe_grouped['candidate_name'] == winner]['ballots_candidate_precinct'].values[0]:,.0f} votes, or {boe_grouped[boe_grouped['candidate_name'] == winner]['candidate_percent_precinct'].values[0]:.2%} of the vote.
    
{second_place} came in second with {boe_grouped[boe_grouped['candidate_name'] == second_place]['ballots_candidate_precinct'].values[0]:,.0f} votes, or {boe_grouped[boe_grouped['candidate_name'] == second_place]['candidate_percent_precinct'].values[0]:.2%} of the vote.

Referendum Yes Percent: {filtered_general['ref_yes'].sum() / filtered_general['ballots_ref_precinct_total'].sum():.2%}

Referendum Result: {"Won" if filtered_general['ref_yes'].sum() / filtered_general['ballots_ref_precinct_total'].sum() > 0.5 else "Lost"}

Referendum Turnout Percent: {filtered_general['ballots_ref_precinct_total'].sum() / filtered_general['registered_voters'].sum():.2%}

The Referendum Won {(filtered_general['ref_won_precinct'] == 'Won').sum()} Precincts out of {filtered_general.shape[0]} Precincts, or {(filtered_general['ref_won_precinct'] == 'Won').sum() / filtered_general.shape[0]:.2%} of Precincts.
    
    """)

    filtered_general = filtered_general[["ward","precinct","registered_voters","ballots_cast","turnout_percent_precinct","ref_yes","ballots_ref_precinct_total","ref_yes_percent_precinct","ref_won_precinct"]] 

    # style so that ref_yes_percent_precinct is shown as a percentage with 2 decimal places and turnout_percent_precinct is shown as a percentage with 2 decimal places
    filtered_general = filtered_general.style.format({
        'registered_voters': '{:,.0f}',
        'ballots_cast': '{:,.0f}',
        'ref_yes': '{:,.0f}',
        'ballots_ref_precinct_total': '{:,.0f}',
        'turnout_percent_precinct': '{:.2%}',
        'ref_yes_percent_precinct': '{:.2%}'
    })

    # bold these titles
    st.write(f"**Detailed Precinct-Level Turnout and Millionaires Tax Referendum Results for {selected_race}**")

    st.dataframe(filtered_general, use_container_width=True, hide_index=True)

    st.write(f"**Detailed Precinct-Level BOE Results for {selected_race}**")
    
    st.dataframe(filtered_boe, use_container_width=True, hide_index=True)



#    ward_precinct=load_data()
#     # if df is None:
#     #     return

#     m = folium.Map(location=[41.8781, -87.6298], zoom_start=10, tiles=None)
#     folium.TileLayer("OpenStreetMap", name="Satellite", control=False).add_to(m)

# #    make fill completely transparent. make city boundaries pink and ersb green.
#     folium.GeoJson(
#         intersection,
#         name="intersection",
#         tooltip=folium.GeoJsonTooltip(fields=['ward', 'precinct']),
#         style_function=lambda x: {'fillColor': 'green', 'color': 'pink', 'fillOpacity': 0.5},
#     ).add_to(m)
#     # folium.GeoJson(
#     #     ward_precinct,
#     #     name="ward_precinct",
#     #     tooltip=folium.GeoJsonTooltip(fields=['ward', 'precinct']),
#     #     style_function=lambda x: {'fillColor': 'green', 'color': 'green', 'fillOpacity': 0},
#     # ).add_to(m)
#     folium.GeoJson(
#     ersb_20,
#     name="ersb_20",
#     interactive=False,
#     style_function=lambda x: {'fillColor': 'green', 'color': 'black', 'fillOpacity': 0},
#     ).add_to(m)

#     folium.LayerControl().add_to(m)

#     st_folium(m,returned_objects=[],use_container_width=True)

    # Embed the saved HTML map directly to avoid iframe pointing at the app root.
    # with open("ward_precinct_ersb20_intersection.html", "r", encoding="utf-8") as html_file:
    #     html = html_file.read()
    # st.components.v1.html(html, height=700, scrolling=True)

    # apply subtext to the markdown language

    st.markdown(
        """<sup>
    I hope you're happy...I lost an hour of free time to this project...

JK! Hope this helps!!</sup>""",
        unsafe_allow_html=True)


if __name__ == "__main__":
    main()