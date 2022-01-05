import streamlit as st

import gpxpy
import gpxpy.gpx
import altair as alt

from pacer_calc import evaluate_model_parameters, load_reference_data, load_target_data, predict_pace

st.set_page_config(
     page_title="Pacer - A pace prediction for trails that actually works",
     page_icon="🏔",
     layout="wide",
     initial_sidebar_state="expanded",
     menu_items={
         'Get Help': 'https://nttdata-dach.github.io/posts/ok-pacer/',
         'Report a bug': "https://github.com/oliver-koeth/pacer-lit/issues",
         'About': """
# Pacer Project
This project predicts the pace for a given trail-run gps track based on a
base pace plus the uphill/downhill "penalties" from the base pace based on the
elevation per 100m. The pace prediction is based on a regression model which
is trained with a "reference run". The closer the reference run is to the 
predicted run (duration, elevation, technicality) the better the prediction.
         """
     }
)

st.write("""
# Pacer Project
This project predicts the pace for a given trail-run gps track based on a
base pace plus the uphill/downhill "penalties" from the base pace based on the
elevation per 100m. The pace prediction is based on a regression model which
is trained with a "reference run". The closer the reference run is to the 
predicted run (duration, elevation, technicality) the better the prediction.
"""
)

reference, target = st.columns(2)

reference_data = None 
target_data = None

st.sidebar.header("Input")
reference_run = st.sidebar.file_uploader(
    label="Choose a reference file",type=['gpx'])

if reference_run is not None:
    reference.subheader("Reference Profile")
    reference_data = load_reference_data(reference_run.getvalue())


    reference_chart_base = alt.Chart(reference_data).encode(
        x=alt.X(
            field="distance_sum", type="quantitative", 
            axis=alt.Axis(labels=False,grid=False,title=None,ticks=False,domainOpacity=0)
            ),
    )

    reference_chart_elevation = reference_chart_base.mark_area(opacity=0.5, color="grey").encode(
        y=alt.Y(
            field="elevation", type="quantitative", 
            axis=alt.Axis(labels=False,grid=False,title=None,ticks=False,domainOpacity=0),
            scale=alt.Scale(domain=[reference_data["elevation"].min().values[0], reference_data["elevation"].max().values[0]])
            ),
    )

    reference_chart_pace = reference_chart_base.mark_line(opacity=0.7, color='grey').encode(
        y=alt.Y(
            field="pace_segment", type="quantitative", 
            axis=alt.Axis(labels=False,grid=False,title=None,ticks=False,domainOpacity=0),
            #scale=alt.Scale(domain=[0, reference_data["pace_segment"].max().values[0]])
            ),
    )

    c = alt.layer(reference_chart_elevation, reference_chart_pace).resolve_scale(
        y = 'independent'
    ).configure_view(
        strokeOpacity=0
    )

    reference.altair_chart(c, use_container_width=True)
else:
    reference.write("")

target_run = st.sidebar.file_uploader(
    label="Choose a target file",type=['gpx'])

if target_run is not None:
    target.subheader("Target Profile")
    target_data = load_target_data(target_run.getvalue())

    c = alt.Chart(target_data).mark_area(opacity=0.5,color="grey").encode(
        x=alt.X(
            field="distance_sum", type="quantitative", 
            axis=alt.Axis(labels=False,grid=False,title=None,ticks=False,domainOpacity=0)
            ),
        y=alt.Y(
            field="elevation", type="quantitative", 
            axis=alt.Axis(labels=False,grid=False,title=None,ticks=False,domainOpacity=0),
            scale=alt.Scale(domain=[target_data["elevation"].min().values[0], target_data["elevation"].max().values[0]])
            ),
    ).configure_view(
        strokeOpacity=0
    )

    target.altair_chart(c, use_container_width=True)
else:
    target.write("")

model = st.sidebar.selectbox(
     'Chose prediction model:',
     ('linear', 'parabolic', 'hybrid', 'manual'), index=0)

base_pace = st.sidebar.slider(
    'Select your base pace (for manual model)?', 3.5, 10.0, 5.0)

if reference_data is not None and target_data is not None:
    st.subheader("Predicted Pace and Time")
    model_parameters = evaluate_model_parameters(reference_data)

    target_data['pace_segment'] = target_data.apply(
        lambda row: predict_pace(model_parameters, row[('elevation_delta','sum')], base_pace, model), axis=1)

    target_data['time_delta'] = target_data[('distance_delta','sum')]/(16.7/target_data['pace_segment'])
    target_data['time_sum'] = target_data['time_delta'].cumsum(axis = 0)/3600

    result_chart_base = alt.Chart(target_data).encode(
        x=alt.X(
            field="distance_sum", type="quantitative", 
            axis=alt.Axis(title="Distance")
        ),
    )

    result_chart_elevation = result_chart_base.mark_area(opacity=0.5).encode(
        y=alt.Y(
            field="elevation", type="quantitative", 
            axis=alt.Axis(title="Elevation [m]"),
            scale=alt.Scale(domain=[target_data["elevation"].min().values[0], target_data["elevation"].max().values[0]])
        ),
    )

    result_chart_pace = result_chart_base.mark_line(opacity=0.3, color='green').encode(
        y=alt.Y(
            field="pace_segment", type="quantitative", 
            axis=alt.Axis(title="Pace [min/km]"),
        ),
    )

    result_chart_time = result_chart_base.mark_line(opacity=0.3, color='red').encode(
        y=alt.Y(
            field="time_sum", type="quantitative", 
            axis=alt.Axis(title="Time [h]",offset=40),
            #axis=alt.Axis(labels=False,grid=False,title=None,ticks=False,domainOpacity=0),
        ),
    )

    c = alt.layer(result_chart_elevation, result_chart_pace, result_chart_time).resolve_scale(
        y = 'independent'
    ).configure_view(
        strokeOpacity=0
    )

    st.altair_chart(c, use_container_width=True)


