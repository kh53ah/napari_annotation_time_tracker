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
    def run_dash():

        def extract_points_values(points_data):
            values = []
            for layer_name, layer_content in points_data.items():
                for obj_id, val in layer_content.items():
                    if val is not None:
                        values.append(float(val))
            return values

        def extract_third_values(layer_data):
            values = []
            for layer_name, layer_content in layer_data.items():
                for obj_id, vals in layer_content.items():
                    if isinstance(vals, list) and len(vals) >= 3:
                        values.append(float(vals[2]))
            return values

        json_filepath = os.path.join(path, "time_tracker_data.json")
        with open(json_filepath, "r") as f:
            data = json.load(f)

        per_layer_data = data.get("per_layer_data", {})

        points_values = extract_points_values(per_layer_data.get("points", {}))
        shapes_values = extract_third_values(per_layer_data.get("shapes", {}))
        labels_values = extract_third_values(per_layer_data.get("labels", {}))
        all_values = points_values + shapes_values + labels_values

        app = dash.Dash(__name__)

        # Formatieren der Name der CSV Dateien, die im Dropdown angezeigt werden sollen und speichern in einer Liste
        dropdown_options = [{"label": "All", "value": "All"}, {"label": "Points", "value": "Points"}, {"label": "Shapes", "value": "Shapes"},
                            {"label": "Labels", "value": "Labels"}]

        app.layout = html.Div([
            html.H1("Histogram of time"),

            dcc.Dropdown(
                id='Layer-dropdown',
                options=dropdown_options,
                value='All'
            ),

            dcc.Graph(id='Histogram-graph')
        ])

        @app.callback(
            Output('Histogram-graph', 'figure'),
            Input('Layer-dropdown', 'value')
        )
        def update_graph(selected):
            if selected == "Points":
                values = points_values
            elif selected == "Shapes":
                values = shapes_values
            elif selected == "Labels":
                values = labels_values
            elif selected == "All":
                values = all_values
            else:
                values = []
            print(f"Selected layer: {selected}, Values: {values}")

            df = pd.DataFrame({"time": values})
            fig = px.histogram(df, x='time', nbins=20,
                               title=f"{selected.capitalize()} Annotation Time")
            fig.update_layout(
                xaxis_title='object annotation time'
            )
            return fig

        app.run(debug=True, use_reloader=False)  # Default-Port ist 8050

    threading.Thread(target=run_dash, daemon=True).start()
    webbrowser.open("http://127.0.0.1:8050")

