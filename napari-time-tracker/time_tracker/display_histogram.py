import datetime

import dash
from dash import dcc, html, Input, Output
import plotly.express as px
import pandas as pd
import os
from PyQt5.QtWidgets import QApplication, QFileDialog
import sys

app = QApplication(sys.argv)
file_path, _ = QFileDialog.getOpenFileName(None, "Select file")
print("Ausgewählte Datei:", file_path)

# Dash-App initialisieren
app = dash.Dash(__name__)

# Formatieren der Name der CSV Dateien, die im Dropdown angezeigt werden sollen und speichern in einer Liste
dropdown_options = ['All Layers', 'Points', 'Shapes', 'Labels']

app.layout = html.Div([
    html.H1("Histogram of time"),

    dcc.Dropdown(
        id='Layer-dropdown',
        options=dropdown_options
    ),

    dcc.Graph(id='Histogram-graph')
])


@app.callback(
    Output('Histogram-graph', 'figure'),
    Input('Layer-dropdown', 'value')
)
def update_graph(selected_file):
    fig = px.line(df, x='delta', y='frequency', title=f'Histogram')
    fig.update_layout(
        xaxis_title='Objecttime',
        yaxis_title='Frequency of Occurrences',
        xaxis_tickformat='%H:%M'
    )
    return fig


if __name__ == '__main__':
    app.run(debug=True, host="127.0.0.1")  # Default-Port ist 8050
