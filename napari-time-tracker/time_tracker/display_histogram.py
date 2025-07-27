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
    """
    Starts a Dash web application in a separate thread to visualize annotation times.

    The app reads a JSON file containing time data for annotated objects in
    different Napari layers ("points", "shapes", "labels") and displays histograms
    for each or all layers combined.

    Parameters:
    path (str): Path to the folder containing 'time_tracker_data.json'.
    """

    def run_dash():
        """
        Runs the Dash server with layout, data processing, and callbacks defined.
        """

        def extract_points_values(points_data):
            """
            Extracts numeric values from the points layer data.

            Parameters:
            points_data (dict): Nested dictionary of point layer timing values.

            Returns:
            list[float]: List of annotation times.
            """
            values = []
            for layer_name, layer_content in points_data.items():
                for obj_id, val in layer_content.items():
                    if val is not None:
                        values.append(float(val))
            return values

        def extract_third_values(layer_data):
            """
            Extracts the third value (index 2) from shape or label layer data,
            which represents the measured time.

            Parameters:
            layer_data (dict): Nested dictionary of shape or label layer data.

            Returns:
            list[float]: List of annotation times.
            """
            values = []
            for layer_name, layer_content in layer_data.items():
                for obj_id, vals in layer_content.items():
                    if isinstance(vals, list) and len(vals) >= 3:
                        values.append(float(vals[2]))
            return values

        # Load time tracking data from JSON
        json_filepath = os.path.join(path, "time_tracker_data.json")
        with open(json_filepath, "r") as f:
            data = json.load(f)

        per_layer_data = data.get("per_layer_data", {})

        # Extract values for different layer types
        points_values = extract_points_values(per_layer_data.get("points", {}))
        shapes_values = extract_third_values(per_layer_data.get("shapes", {}))
        labels_values = extract_third_values(per_layer_data.get("labels", {}))
        all_values = points_values + shapes_values + labels_values

        # Create Dash app instance
        app = dash.Dash(__name__)

        # Dropdown menu options
        dropdown_options = [
            {"label": "All", "value": "All"},
            {"label": "Points", "value": "Points"},
            {"label": "Shapes", "value": "Shapes"},
            {"label": "Labels", "value": "Labels"}
        ]

        # App layout: Title, dropdown, and histogram
        app.layout = html.Div([
            html.H1("Histogram of Annotation Time"),

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
            """
            Updates the histogram plot based on the selected layer.

            Parameters:
            selected (str): Selected layer name from dropdown.

            Returns:
            plotly.graph_objs._figure.Figure: Updated histogram figure.
            """
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
                xaxis_title='Object Annotation Time (seconds)'
            )
            return fig

        # Start Dash app server
        app.run(debug=True, use_reloader=False)  # Default port is 8050

    # Run the Dash app in a separate thread and open it in the browser
    threading.Thread(target=run_dash, daemon=True).start()
    webbrowser.open("http://127.0.0.1:8050")
