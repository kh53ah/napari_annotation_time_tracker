import datetime

import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd
import os
from PyQt5.QtWidgets import QApplication, QFileDialog
import sys
import json

app = QApplication(sys.argv)
file_path, _ = QFileDialog.getOpenFileName(None, "Select file")
print("Ausgewählte Datei:", file_path)

with open("time_tracker_data.json", "r") as f:
    data = json.load(f)

# Zugriff auf per_layer_data (die TimeMaps)
per_layer_data = data.get("per_layer_data", {})

points_timemap = per_layer_data.get("Points", {})
shapes_timemap = per_layer_data.get("Shapes", {})
labels_timemap = per_layer_data.get("Labels", {})

# Dash-App initialisieren
app = dash.Dash(__name__)

# Formatieren der Name der CSV Dateien, die im Dropdown angezeigt werden sollen und speichern in einer Liste
dropdown_options = [{"label": "Points", "value": points_timemap}, {"label": "Shapes", "value": shapes_timemap},
                    {"label": "Labels", "value": labels_timemap}]

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
    df = pd.DataFrame.from_dict(selected_layer)
    fig = px.histogram(df, x='delta', y='frequency', title=f'Histogram')
    fig.update_layout(
        xaxis_title='Object_time',
        yaxis_title='Frequency of Occurrences'
    )
    return fig


if __name__ == '__main__':
    app.run(debug=True)  # Default-Port ist 8050
