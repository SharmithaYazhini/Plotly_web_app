from dash import Dash, html, dcc, Input, Output
import plotly.express as px
import pandas as pd
url="https://docs.google.com/spreadsheets/d/e/2PACX-1vQNOXPTcP-C5DE9PnclYdLMO31le21XLbZSsrW0gB1jcxX9KxsmpjVt5IwSSPNtqrr0fUXiZDP1imAb/pub?gid=1101721916&single=true&output=csv"
data=pd.read_csv(url)
data.head()
app = Dash("Gloal Terrorism Data: Jan to June 2021")
time_series_data = data[['iyear', 'imonth', 'iday', 'region_txt', 'nkill']].dropna(subset=['iyear', 'imonth', 'iday', 'nkill'])
time_series_data['date'] = time_series_data.apply(
    lambda row: pd.Timestamp(year=int(row['iyear']), month=int(row['imonth']), day=int(row['iday'])),
    axis=1
)
time_series_data = time_series_data.groupby(['date', 'region_txt'])['nkill'].sum().reset_index()
time_series_data['nkill_smooth'] = time_series_data.groupby('region_txt')['nkill'].transform(lambda x: x.rolling(7, 1).mean())

def update_fig1(selected_category, selected_month):
    filtered_df = data[data["region_txt"] == selected_category]
    filtered_df['highlight'] = filtered_df['imonth'].apply(
        lambda x: 'Selected Month' if x == selected_month else 'Other Months'
    )

    fig = px.histogram(
        filtered_df,
        x='imonth',
        y='nkill',
        color='highlight',
        nbins=12,
        title=f"Incidents Per Month in {selected_category}",
        labels={'imonth': 'Month', 'nkill': 'Number of Fatalities'},
        color_discrete_map={'Selected Month': 'red', 'Other Months': 'blue'},
    )
    return fig

def update_fig2(selected_category, selected_month):
    filtered_df = data[(data["region_txt"] == selected_category) & (data['imonth'] == selected_month)]
    fig = px.bar(
        filtered_df,
        x='iday',
        y='nkill',
        title=f"Incidents Per Day in {selected_category}, Month: {selected_month}",
        labels={'iday': 'Day of the Month'},
    )
    return fig

def update_fig3(selected_category, selected_month):
    country_weapon_data = data[['country_txt', 'weaptype1_txt', 'nkill', "region_txt", 'imonth']].dropna()
    country_weapon_data = country_weapon_data.groupby(['country_txt', 'weaptype1_txt', "region_txt", 'imonth'])['nkill'].sum().reset_index()
    filtered_df = country_weapon_data[
        (country_weapon_data["region_txt"] == selected_category) &
        (country_weapon_data['imonth'] == selected_month)
    ]
    fig = px.bar(
        filtered_df,
        x='country_txt',
        y='nkill',
        color='weaptype1_txt',
        title=f"Country vs Number of People Killed in {selected_category}, Month: {selected_month}",
        labels={'nkill': 'Number of People Killed', 'country_txt': 'Country', 'weaptype1_txt': 'Weapon Type'},
    )
    return fig

def update_fig4(selected_region):
    filtered_df = time_series_data[time_series_data['region_txt'] == selected_region]
    fig = px.line(
        filtered_df,
        x='date',
        y='nkill_smooth',
        title=f"Time Series of Fatalities in {selected_region} (7-day Avg)",
        labels={'nkill_smooth': 'Number of People Killed (7-day Avg)', 'date': 'Date'},
        hover_data={'date': "|%B %d, %Y", 'nkill_smooth': ':.2f'}
    )
    return fig

def update_network(selected_region, selected_month):
    # Filter data based on inputs
    filtered_data = data[(data['region_txt'] == selected_region) & (data['imonth'] == selected_month)]
    node_data = filtered_data[['country_txt', 'targtype1_txt']].dropna()
    node_edges = node_data.groupby(['country_txt', 'targtype1_txt']).size().reset_index(name='occurrence')

    # Create network graph
    G = nx.Graph()
    for _, row in node_edges.iterrows():
        G.add_edge(row['country_txt'], row['targtype1_txt'], weight=row['occurrence'])

    # Add positions to nodes
    pos = nx.spring_layout(G)
    for node in G.nodes():
        G.nodes[node]['pos'] = pos[node]

    # Create edge traces
    edge_x = []
    edge_y = []
    for edge in G.edges(data=True):
        x0, y0 = G.nodes[edge[0]]['pos']
        x1, y1 = G.nodes[edge[1]]['pos']
        edge_x.append(x0)
        edge_x.append(x1)
        edge_x.append(None)
        edge_y.append(y0)
        edge_y.append(y1)
        edge_y.append(None)

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines'
    )

    # Create node traces
    node_x = []
    node_y = []
    node_text = []
    for node in G.nodes():
        x, y = G.nodes[node]['pos']
        node_x.append(x)
        node_y.append(y)
        node_text.append(node)

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        text=node_text,
        marker=dict(
            showscale=True,
            colorscale='YlGnBu',
            size=10,
            colorbar=dict(
                thickness=15,
                title='Node Connections',
                xanchor='left',
                titleside='right'
            )
        )
    )

    # Combine traces into a figure
    fig = go.Figure(data=[edge_trace, node_trace],
                    layout=go.Layout(
                        title=f"Country and Target Type Network in {selected_region}, Month: {selected_month}",
                        showlegend=False,
                        hovermode='closest'
                    ))
    return fig


def update_treemap(selected_region, selected_month):
    filtered_data1 = data[(data['region_txt'] == selected_region) & (data['imonth'] == selected_month)]
    filtered_data1['total_casualty'] = filtered_data1['nkill'] + filtered_data1.get('nwound', 0)
    treemap_data = filtered_data1[['country_txt', 'attacktype1_txt', 'total_casualty']].dropna()
    treemap_data = treemap_data.groupby(['country_txt', 'attacktype1_txt'])['total_casualty'].sum().reset_index()

    # Create treemap
    fig = px.treemap(
        treemap_data,
        path=['country_txt', 'attacktype1_txt'],
        values='total_casualty',
        title=f"Total Casualties by Country and Attack Type in {selected_region}, Month: {selected_month}",
        labels={'total_casualty': 'Total Casualties'}
    )
    return fig

def create_annotated_heatmap():
    # Create a copy of the data to avoid modifying the original DataFrame
    processed_data = data.copy()

    # Ensure 'total_casualties' column exists
    processed_data['total_casualties'] = processed_data['nkill'] + processed_data.get('nwound', 0)

    # Safely calculate severity index
    processed_data['severity_index'] = processed_data['total_casualties'] * (
        1 + np.log(processed_data['attacktype1_txt'].str.len() + 1)
    )

    # Normalize severity index
    processed_data['severity_normalized'] = (
        processed_data['severity_index'] - processed_data['severity_index'].min()
    ) / (processed_data['severity_index'].max() - processed_data['severity_index'].min())

    pivot_data = processed_data.pivot_table(
        values='severity_normalized',
        index='region_txt',
        columns='attacktype1_txt',
        aggfunc='mean'
    ).fillna(0)

    fig = go.Figure(data=go.Heatmap(
        z=pivot_data.values,
        x=pivot_data.columns,
        y=pivot_data.index,
        colorscale='YlOrRd',
        hoverongaps = False,
        text=pivot_data.values.round(2),
        texttemplate='%{text:.2f}',
        textfont={"size":8},
        hoverinfo='text',
        hovertext=[
            [f'Region: {y}<br>Attack Type: {x}<br>Severity: {z:.2f}'
             for x, z in zip(pivot_data.columns, row)]
            for y, row in zip(pivot_data.index, pivot_data.values)
        ]
    ))

    fig.update_layout(
        title='Attack Severity Heatmap: Regions vs Attack Types',
        xaxis_title='Attack Types',
        yaxis_title='Regions',
        annotations=[
            dict(
                x=0.5,
                y=-0.15,
                xref='paper',
                yref='paper',
                text='Higher values indicate more severe attacks',
                showarrow=False,
                font=dict(size=10)
            )
        ]
    )

    return fig

def create_parallel_coordinates():
    parallel_data = data[[
        'nkill', 'nwound', 'iyear'
    ]].dropna()
    parallel_data['total_casualty'] = parallel_data['nkill'] + parallel_data.get('nwound', 0)

    fig = px.parallel_coordinates(
        parallel_data,
        color='severity_normalized',
        title='Multi-Dimensional Attack Characteristics',
        color_continuous_scale=px.colors.sequential.Viridis
    )

    fig.update_layout(
        coloraxis_colorbar=dict(
            title='Attack Severity'
        )
    )

    return fig

# Updated layout to include the third graph
app.layout = html.Div([
    html.H1("Interactive Visualizations: Incidents Analysis"),

    # Dropdown for region selection
    dcc.Dropdown(
        id='category-dropdown',
        options=[{'label': cat, 'value': cat} for cat in data["region_txt"].unique()],
        value=data["region_txt"].unique()[0],
        placeholder="Select a region"
    ),

    # Dropdown for month selection
    dcc.Dropdown(
        id='month-dropdown',
        options=[{'label': f"Month {month}", 'value': month} for month in range(1, 13)],
        value=1,  # Default to January
        placeholder="Select a month"
    ),

    # Graphs
    dcc.Graph(id='graph7'),
    dcc.Graph(id='graph1'),  # Incidents by month
    dcc.Graph(id='graph2'),  # Incidents by day
    dcc.Graph(id='graph3'),   # Country vs Weapon Type
    dcc.Graph(id='graph4'),
    dcc.Graph(id='graph5'),
    dcc.Graph(id='graph6'),

])

# Updated callback to include the third graph
@app.callback(
    [Output('graph1', 'figure'),
     Output('graph2', 'figure'),
     Output('graph3', 'figure'),
     Output('graph4','figure'),
     Output('graph5','figure'),
     Output('graph6','figure'),
     Output('graph7','figure')
     ],
    [Input('category-dropdown', 'value'),
     Input('month-dropdown', 'value')]
)
def update_graphs(selected_category, selected_month):
    fig1 = update_fig1(selected_category, selected_month)
    fig2 = update_fig2(selected_category, selected_month)
    fig3 = update_fig3(selected_category, selected_month)
    fig4 = update_fig4(selected_category)
    fig5 = update_network(selected_category, selected_month)
    fig6 = update_treemap(selected_category, selected_month)
    fig7 = create_annotated_heatmap()
    return fig1, fig2, fig3, fig4, fig5 , fig6, fig7

# Run the app (you can copy this code to your local environment if not executable here)
if __name__ == '__main__':
    app.run_server(debug=False, use_reloader=False)
