import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Nassau Candy Route Efficiency", page_icon="🍬", layout="wide")

# ── Custom styling ──────────────────────────────────────────
st.markdown("""
<style>
    h1 { color: #7B2D8E; font-weight: 700; }
    .metric-box {
        background: linear-gradient(135deg, #7B2D8E 0%, #B83280 100%);
        padding: 20px; border-radius: 12px; color: white; text-align: center;
    }
    .metric-box h2 { color: white; margin: 0; font-size: 32px; }
    .metric-box p { color: #F0D9E8; margin: 4px 0 0; font-size: 13px; }
</style>
""", unsafe_allow_html=True)

# ── Load data ────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv('cleaned_shipment_data.csv')
    df['Order Date'] = pd.to_datetime(df['Order Date'])
    df['Ship Date'] = pd.to_datetime(df['Ship Date'])
    route_master = pd.read_csv('route_master.csv')
    return df, route_master

df, route_master = load_data()

factory_coords = pd.DataFrame({
    'Factory': ["Lot's O' Nuts", "Wicked Choccy's", "Sugar Shack", "Secret Factory", "The Other Factory"],
    'Latitude': [32.881893, 32.076176, 48.11914, 41.446333, 35.1175],
    'Longitude': [-111.768036, -81.088371, -96.18115, -90.565487, -89.971107]
})

st.title("🍬 Nassau Candy Distributor — Shipping Route Efficiency")
st.caption("Factory-to-customer logistics intelligence dashboard")

# ── Sidebar filters ──────────────────────────────────────────
st.sidebar.header("Filters")

min_date = df['Order Date'].min()
max_date = df['Order Date'].max()
date_range = st.sidebar.date_input("Order Date Range", [min_date, max_date])

regions = st.sidebar.multiselect("Region", options=sorted(df['Region'].unique()), default=sorted(df['Region'].unique()))
ship_modes = st.sidebar.multiselect("Ship Mode", options=sorted(df['Ship Mode'].unique()), default=sorted(df['Ship Mode'].unique()))
lead_time_threshold = st.sidebar.slider("Lead Time Threshold (days)", 0, int(df['Lead Time (days)'].max()), 7)

# ── Apply filters ────────────────────────────────────────────
mask = (
    (df['Order Date'] >= pd.to_datetime(date_range[0])) &
    (df['Order Date'] <= pd.to_datetime(date_range[1])) &
    (df['Region'].isin(regions)) &
    (df['Ship Mode'].isin(ship_modes))
)
filtered = df[mask]

# ── Top KPI row ──────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f'<div class="metric-box"><p>TOTAL SHIPMENTS</p><h2>{len(filtered):,}</h2></div>', unsafe_allow_html=True)
with col2:
    avg_lead = filtered['Lead Time (days)'].mean()
    st.markdown(f'<div class="metric-box"><p>AVG LEAD TIME</p><h2>{avg_lead:.1f} days</h2></div>', unsafe_allow_html=True)
with col3:
    delayed_pct = (filtered['Lead Time (days)'] > lead_time_threshold).mean() * 100
    st.markdown(f'<div class="metric-box"><p>DELAYED SHIPMENTS</p><h2>{delayed_pct:.1f}%</h2></div>', unsafe_allow_html=True)
with col4:
    st.markdown(f'<div class="metric-box"><p>ACTIVE ROUTES</p><h2>{filtered["Route_State"].nunique()}</h2></div>', unsafe_allow_html=True)

st.divider()

# ── Module 1: Route Efficiency Overview ──────────────────────
st.subheader("📊 Route Efficiency Overview")
tab1, tab2 = st.tabs(["Top 10 Most Efficient", "Bottom 10 Least Efficient"])
with tab1:
    top10 = route_master.sort_values('Efficiency_Score', ascending=False).head(10)
    st.dataframe(top10[['Route_State', 'Avg_Lead_Time', 'Total_Shipments', 'Efficiency_Score']], use_container_width=True)
with tab2:
    bottom10 = route_master.sort_values('Efficiency_Score', ascending=True).head(10)
    st.dataframe(bottom10[['Route_State', 'Avg_Lead_Time', 'Total_Shipments', 'Efficiency_Score']], use_container_width=True)

st.divider()

# ── Module 2: Geographic Shipping Map ────────────────────────
st.subheader("🗺️ Geographic Shipping Map")
state_geo = filtered.groupby('State/Province').agg(
    Avg_Lead_Time=('Lead Time (days)', 'mean'),
    Total_Shipments=('Order ID', 'count'),
    Lat=('Cust_Lat', 'first'),
    Lon=('Cust_Lon', 'first')
).reset_index()

fig_map = px.scatter_geo(
    state_geo, lat='Lat', lon='Lon', size='Total_Shipments', color='Avg_Lead_Time',
    color_continuous_scale='RdYlGn_r', hover_name='State/Province',
    hover_data=['Avg_Lead_Time', 'Total_Shipments'], scope='usa'
)
fig_map.add_trace(go.Scattergeo(
    lat=factory_coords['Latitude'], lon=factory_coords['Longitude'],
    text=factory_coords['Factory'], mode='markers+text',
    marker=dict(size=14, color='black', symbol='star'), textposition='top center', name='Factories'
))
st.plotly_chart(fig_map, use_container_width=True)

st.divider()

# ── Module 3: Ship Mode Comparison ───────────────────────────
st.subheader("🚚 Ship Mode Comparison")
shipmode_compare = filtered.groupby('Ship Mode').agg(
    Avg_Lead_Time=('Lead Time (days)', 'mean'),
    Total_Shipments=('Order ID', 'count')
).reset_index()
fig_ship = px.bar(shipmode_compare, x='Ship Mode', y='Avg_Lead_Time', color='Ship Mode',
                   text_auto='.1f', title='Average Lead Time by Ship Mode')
st.plotly_chart(fig_ship, use_container_width=True)

st.divider()

# ── Module 4: Route Drill-Down ───────────────────────────────
st.subheader("🔍 Route Drill-Down")
selected_state = st.selectbox("Select a State to Drill Down", sorted(filtered['State/Province'].unique()))
state_detail = filtered[filtered['State/Province'] == selected_state]
st.write(f"**{len(state_detail)} shipments** to {selected_state}")
st.dataframe(
    state_detail[['Order ID', 'Order Date', 'Ship Date', 'Lead Time (days)', 'Ship Mode', 'Factory']].sort_values('Order Date'),
    use_container_width=True
)
