import datetime

import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd
import os
import json
import threading
import webbrowser


def start_dash_app(path):
    print(f"Starte Dash-App mit path={path}")

    def run_dash():
        json_filepath = os.path.join(path, "time_tracker_data.json")
        with open(json_filepath, "r") as f:
            data = json.load(f)

        # Zugriff auf per_layer_data (die TimeMaps)
        per_layer_data = data.get("per_layer_data", {})

        app = dash.Dash(__name__)

        # Formatieren der Name der CSV Dateien, die im Dropdown angezeigt werden sollen und speichern in einer Liste
        dropdown_options = [{"label": "Points", "value": "Points"}, {"label": "Shapes", "value": "Shapes"},
                            {"label": "Labels", "value": "Labels"}]

        app.layout = html.Div([
            html.H1("Histogram of time"),

            dcc.Dropdown(
                id='Layer-dropdown',
                options=dropdown_options,
                value='Points'
            ),

            dcc.Graph(id='Histogram-graph')
        ])

        @app.callback(
            Output('Histogram-graph', 'figure'),
            Input('Layer-dropdown', 'value')
        )
        def update_graph(selected_layer):
            layer_data = per_layer_data.get(selected_layer, {})
            all_times = []

            for layer_name, obj_times in layer_data.items():
                for obj_id, time_value in obj_times.items():
                    if isinstance(time_value, list):  # shapes or labels
                        time_in_seconds = time_value[2] - time_value[0]
                    else:
                        time_in_seconds = time_value
                    all_times.append(round(time_in_seconds))

            if not all_times:
                return px.histogram(title="No data available")

            df = pd.DataFrame({"AnnotationTime_sec": all_times})
            fig = px.histogram(df, x='delta', y='frequency', nbins=20, title=f"{selected_layer.capitalize()} Annotation Time")
            fig.update_layout(
                xaxis_title='Object_time',
                yaxis_title='Frequency of Occurrences'
            )
            return fig

        app.run(debug=True, use_reloader=False)  # Default-Port ist 8050

    threading.Thread(target=run_dash, daemon=True).start()
    webbrowser.open("http://127.0.0.1:8050")

