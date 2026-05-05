import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re
from io import BytesIO

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Whirlpool Production Plan Dashboard",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.metric-card {
    background: #f0f4ff;
    border-radius: 10px;
    padding: 16px 20px;
    border-left: 4px solid #1d4ed8;
    margin-bottom: 8px;
}
.metric-label { font-size: 12px; color: #6b7280; font-weight: 600; text-transform: uppercase; }
.metric-value { font-size: 28px; font-weight: 700; color: #1e293b; }
.metric-sub   { font-size: 12px; color: #6b7280; margin-top: 2px; }
.section-header {
    font-size: 18px; font-weight: 700; color: #1e293b;
    border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; margin: 24px 0 12px 0;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# PARSING
# ─────────────────────────────────────────────
def parse_release_date(raw):
    if pd.isna(raw):
        return "—"
    s = str(raw).strip()
    if hasattr(raw, 'strftime'):
        return raw.strftime("%d %b '%y")
    match = re.search(r'(\d{1,2})[a-z]{0,2}[\s\-]([A-Za-z]+)', s)
    if match:
        return f"{match.group(1)} {match.group(2)}"
    return s[:15]

@st.cache_data(show_spinner=False)
def parse_excel(file_bytes, filename):
    if isinstance(file_bytes, bytes):
        file_bytes = BytesIO(file_bytes)
    df_raw = pd.read_excel(file_bytes, sheet_name=0, header=None)

    date_row  = df_raw.iloc[17]
    total_row = df_raw.iloc[18]

    # --- Auto-detect version columns: row 17 cells containing "Released"
    version_cols = sorted(
        [c for c in range(len(date_row))
         if pd.notna(date_row.iloc[c]) and 'released' in str(date_row.iloc[c]).lower()],
        reverse=True   # highest index = oldest, lowest index = most recent
    )

    # --- Weekly cols: row 17 cells labelled Wk1–Wk4
    wk_map = {}
    for c in range(len(date_row)):
        val = str(date_row.iloc[c]).strip()
        if val in ['Wk1', 'Wk2', 'Wk3', 'Wk4']:
            wk_map[val] = c

    # --- Latest version = lowest-index col with non-zero total (handles unreleased months)
    latest_col = min(version_cols)   # fallback: most recent = lowest col index
    for c in sorted(version_cols):
        if (pd.to_numeric(total_row.iloc[c], errors='coerce') or 0) > 0:
            latest_col = c
            break

    first_col = max(version_cols)    # oldest = highest col index

    # --- Version labels ordered oldest → newest
    version_labels = [parse_release_date(date_row.iloc[c]) for c in sorted(version_cols, reverse=True)]

    # --- Parse SKU rows
    raw = df_raw.iloc[19:].copy().reset_index(drop=True)
    raw.columns = range(raw.shape[1])

    data = pd.DataFrame()
    data['MAT']         = raw[0].astype(str).str.strip()
    data['Color']       = raw[1].astype(str).str.strip()
    data['Star']        = raw[2].astype(str).str.strip()
    data['Segment']     = raw[3].astype(str).str.strip()
    data['Description'] = raw[4].astype(str).str.strip()
    data['v1_final']    = pd.to_numeric(raw[latest_col], errors='coerce').fillna(0).astype(int)
    data['v5_first']    = pd.to_numeric(raw[first_col],  errors='coerce').fillna(0).astype(int)

    # Intermediate versions for plan evolution chart
    mid_cols = sorted([c for c in version_cols if c != latest_col and c != first_col])
    data['_version_cols'] = str(version_cols)   # store for evolution chart
    # Store all version totals as metadata on the df (via attrs)
    all_version_cols = sorted(version_cols, reverse=True)  # old → new

    data['Wk1'] = pd.to_numeric(raw[wk_map['Wk1']], errors='coerce').fillna(0).astype(int) if 'Wk1' in wk_map else 0
    data['Wk2'] = pd.to_numeric(raw[wk_map['Wk2']], errors='coerce').fillna(0).astype(int) if 'Wk2' in wk_map else 0
    data['Wk3'] = pd.to_numeric(raw[wk_map['Wk3']], errors='coerce').fillna(0).astype(int) if 'Wk3' in wk_map else 0
    data['Wk4'] = pd.to_numeric(raw[wk_map['Wk4']], errors='coerce').fillna(0).astype(int) if 'Wk4' in wk_map else 0

    # Store per-version columns for the evolution chart
    for i, c in enumerate(all_version_cols):
        data[f'ver_{i}'] = pd.to_numeric(raw[c], errors='coerce').fillna(0).astype(int)

    data = data[~data['MAT'].isin(['nan', 'NaN', '', 'None'])]

    data['Is_Active'] = data['v1_final'] > 0
    data['Is_TBC']    = data['MAT'].str.upper().str.startswith('TBC')
    data['drift_abs'] = data['v1_final'] - data['v5_first']
    data['drift_pct'] = np.where(
        data['v5_first'] > 0,
        (data['drift_abs'] / data['v5_first'] * 100).round(1),
        np.nan
    )

    def sku_status(row):
        f, l = row['v5_first'], row['v1_final']
        if f == 0 and l > 0:  return 'New'
        if f > 0 and l == 0:  return 'Dropped'
        if f == l:             return 'Unchanged'
        return 'Increased' if l > f else 'Decreased'

    data['Status'] = data.apply(sku_status, axis=1)
    return data, version_labels

# ─────────────────────────────────────────────
# CHART HELPERS
# ─────────────────────────────────────────────
BLUE   = '#1d4ed8'
GREEN  = '#16a34a'
RED    = '#dc2626'
AMBER  = '#d97706'
PURPLE = '#7c3aed'
GRAY   = '#6b7280'

COLOR_MAP = {'Wine':'#8B1A1A','Blue':'#1d4ed8','Grey':'#9ca3af','Black':'#1f2937','Purple':'#7c3aed'}
STATUS_COLOR = {'New':GREEN,'Increased':'#86efac','Unchanged':'#94a3b8','Decreased':'#fca5a5','Dropped':RED}

def fmt(n): return f"{int(n):,}"

def plan_evolution_chart(df, version_labels):
    # Use dynamically stored ver_N columns (ver_0 = oldest, ver_N = newest)
    ver_cols = sorted([c for c in df.columns if str(c).startswith('ver_')],
                      key=lambda x: int(x.split('_')[1]))
    totals = [df[c].sum() for c in ver_cols]
    # Trim version_labels to match available columns
    labels = version_labels[-len(totals):]
    fig = go.Figure(go.Scatter(
        x=labels, y=totals, mode='lines+markers+text',
        text=[fmt(t) for t in totals], textposition='top center',
        line=dict(color=BLUE, width=3), marker=dict(size=10, color=BLUE),
        fill='tozeroy', fillcolor='rgba(29,78,216,0.07)',
    ))
    fig.update_layout(title='Plan Evolution — Total Units Across All Versions',
        xaxis_title='Version (chronological →)', yaxis_title='Total Units',
        yaxis_tickformat=',', height=340, margin=dict(t=45,b=30,l=60,r=20),
        plot_bgcolor='white', paper_bgcolor='white',
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#f1f5f9'))
    return fig

def segment_drift_chart(df):
    seg = df.groupby('Segment').agg(first=('v5_first','sum'), final=('v1_final','sum')).reset_index()
    seg = seg[(seg['first'] > 0) | (seg['final'] > 0)]
    seg['drift_pct'] = np.where(seg['first'] > 0, ((seg['final']-seg['first'])/seg['first']*100).round(1), np.nan)
    seg = seg.dropna(subset=['drift_pct']).sort_values('drift_pct')
    colors = [GREEN if x >= 0 else RED for x in seg['drift_pct']]
    fig = go.Figure(go.Bar(
        x=seg['drift_pct'], y=seg['Segment'], orientation='h', marker_color=colors,
        text=[f"{x:+.1f}%" for x in seg['drift_pct']], textposition='outside',
    ))
    fig.add_vline(x=0, line_color='#374151', line_width=1.5)
    fig.update_layout(title='Segment Drift — 1st Tentative → Final (%)',
        xaxis_title='% Change', height=max(300, len(seg)*38),
        margin=dict(t=45,b=30,l=140,r=80),
        plot_bgcolor='white', paper_bgcolor='white',
        xaxis=dict(showgrid=True, gridcolor='#f1f5f9'), yaxis=dict(showgrid=False))
    return fig

def color_mix_donut(df):
    active = df[df['Is_Active']]
    ca = active.groupby('Color')['v1_final'].sum().reset_index()
    ca = ca[ca['v1_final'] > 0].sort_values('v1_final', ascending=False)
    total = ca['v1_final'].sum()
    fig = go.Figure(go.Pie(
        labels=ca['Color'], values=ca['v1_final'], hole=0.55,
        marker_colors=[COLOR_MAP.get(c,'#94a3b8') for c in ca['Color']],
        textinfo='label+percent', textfont_size=12,
    ))
    fig.update_layout(title='Color Mix — Final Plan',
        annotations=[dict(text=f"<b>{fmt(total)}</b><br>units", x=0.5, y=0.5, font_size=14, showarrow=False)],
        height=360, margin=dict(t=45,b=10,l=20,r=20), paper_bgcolor='white',
        legend=dict(orientation='v', x=1.02, y=0.5))
    return fig

def star_rating_chart(df):
    active = df[df['Is_Active']]
    sa = active.groupby('Star')['v1_final'].sum().reset_index()
    sa = sa[sa['v1_final'] > 0].sort_values('Star')
    fig = go.Figure(go.Bar(
        x=sa['Star'], y=sa['v1_final'], marker_color=PURPLE,
        text=[fmt(v) for v in sa['v1_final']], textposition='outside',
    ))
    fig.update_layout(title='Star Rating Mix — Final Plan',
        xaxis_title='Star Rating', yaxis_title='Units', yaxis_tickformat=',',
        height=300, margin=dict(t=45,b=30,l=60,r=20),
        plot_bgcolor='white', paper_bgcolor='white',
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#f1f5f9'))
    return fig

def weekly_loading_chart(df):
    active = df[df['Is_Active']]
    weeks  = ['Wk1','Wk2','Wk3','Wk4']
    totals = [active[w].sum() for w in weeks]
    avg    = np.mean(totals)
    colors = [AMBER if t < avg * 0.9 else BLUE for t in totals]
    fig = go.Figure(go.Bar(
        x=weeks, y=totals, marker_color=colors,
        text=[fmt(t) for t in totals], textposition='outside',
    ))
    fig.add_hline(y=avg, line_dash='dot', line_color=GRAY,
                  annotation_text=f"Avg: {fmt(avg)}", annotation_position='right')
    fig.update_layout(title='Weekly Loading — Final Plan (amber = below avg)',
        yaxis_title='Units', yaxis_tickformat=',',
        height=300, margin=dict(t=45,b=30,l=60,r=80),
        plot_bgcolor='white', paper_bgcolor='white',
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#f1f5f9'))
    return fig

def sku_status_chart(df):
    order  = ['New','Increased','Unchanged','Decreased','Dropped']
    counts = df['Status'].value_counts().reindex(order, fill_value=0)
    fig = go.Figure(go.Bar(
        x=counts.index, y=counts.values,
        marker_color=[STATUS_COLOR[s] for s in order],
        text=counts.values, textposition='outside',
    ))
    fig.update_layout(title='SKU Status — 1st Tentative → Final',
        yaxis_title='# SKUs', height=300, margin=dict(t=45,b=30,l=50,r=20),
        plot_bgcolor='white', paper_bgcolor='white',
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#f1f5f9'))
    return fig

def segment_breakdown_chart(df):
    seg = df.groupby('Segment').agg(first=('v5_first','sum'), final=('v1_final','sum')).reset_index()
    seg = seg[(seg['first'] > 0) | (seg['final'] > 0)].sort_values('final', ascending=False)
    fig = go.Figure()
    fig.add_trace(go.Bar(name='1st Tentative', x=seg['Segment'], y=seg['first'], marker_color='#93c5fd'))
    fig.add_trace(go.Bar(name='Final Plan',    x=seg['Segment'], y=seg['final'], marker_color=BLUE))
    fig.update_layout(barmode='group', title='Segment Volume: 1st Tentative vs Final',
        yaxis_title='Units', yaxis_tickformat=',',
        height=340, margin=dict(t=45,b=60,l=60,r=20),
        plot_bgcolor='white', paper_bgcolor='white',
        xaxis=dict(tickangle=-35, showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='#f1f5f9'),
        legend=dict(orientation='h', x=0, y=1.12))
    return fig

def multi_month_chart(all_data):
    rows = []
    for month, (df, _) in all_data.items():
        first = df['v5_first'].sum()
        final = df['v1_final'].sum()
        drift = ((final-first)/first*100) if first > 0 else 0
        rows.append({'Month': month, 'First': first, 'Final': final, 'Drift': drift})
    mdf = pd.DataFrame(rows)
    fig = make_subplots(rows=1, cols=2,
        subplot_titles=('Total Volume by Month','Planning Accuracy (Drift %)'))
    fig.add_trace(go.Bar(x=mdf['Month'], y=mdf['First'], name='1st Tentative', marker_color='#93c5fd'), row=1, col=1)
    fig.add_trace(go.Bar(x=mdf['Month'], y=mdf['Final'], name='Final', marker_color=BLUE), row=1, col=1)
    fig.add_trace(go.Bar(x=mdf['Month'], y=mdf['Drift'],
        marker_color=[GREEN if d >= 0 else RED for d in mdf['Drift']],
        text=[f"{d:+.1f}%" for d in mdf['Drift']], textposition='outside'), row=1, col=2)
    fig.add_hline(y=0, line_color='#374151', line_width=1, row=1, col=2)
    fig.update_layout(height=340, barmode='group', paper_bgcolor='white',
        showlegend=True, margin=dict(t=50,b=30))
    fig.update_yaxes(tickformat=',', row=1, col=1, showgrid=True, gridcolor='#f1f5f9')
    fig.update_yaxes(ticksuffix='%', row=1, col=2, showgrid=True, gridcolor='#f1f5f9')
    return fig

# ─────────────────────────────────────────────
# SIDEBAR — built once, fully
# ─────────────────────────────────────────────
with st.sidebar:
    st.image("whirlpool_logo.png", width=170)
    st.markdown("### Production Plan Dashboard")
    st.divider()

    uploaded_files = st.file_uploader(
        "Upload Plan File(s) (.xlsx)",
        type=['xlsx','xls'],
        accept_multiple_files=True,
    )

    # Parse files here so filters can be populated in the same sidebar block
    all_data = {}
    if uploaded_files:
        for f in uploaded_files:
            try:
                df_parsed, ver_labels = parse_excel(f.read(), f.name)
                all_data[f.name] = (df_parsed, ver_labels)
            except Exception as e:
                st.error(f"❌ {f.name}: {e}")

    st.divider()
    st.markdown("**Filters**")

    if all_data:
        all_dfs      = pd.concat([v[0] for v in all_data.values()], ignore_index=True)
        seg_options  = sorted(all_dfs['Segment'].dropna().unique().tolist())
        col_options  = sorted(all_dfs['Color'].dropna().unique().tolist())
        star_options = sorted(all_dfs['Star'].dropna().unique().tolist())
    else:
        seg_options = col_options = star_options = []

    filter_segments = st.multiselect("Segment",     options=seg_options)
    filter_colors   = st.multiselect("Color",       options=col_options)
    filter_stars    = st.multiselect("Star Rating", options=star_options)
    show_tbc        = st.checkbox("Include TBC SKUs", value=False)

    st.divider()
    st.caption("Built with Streamlit + Plotly · Whirlpool India")

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
st.markdown("## ❄️ Whirlpool Production Planning Dashboard")

if not uploaded_files or not all_data:
    st.info("👈 Upload one or more monthly plan `.xlsx` files using the sidebar to get started.")
    st.markdown("""
**Expected file format:**
- Standard Whirlpool production plan Excel (raw file, not the cleaned output)
- Rows 1–18: segment-level summary block · Row 17: release dates · Row 19: headers
- Rows 20+: SKU data — MAT | Color | Star | Segment | Description | v1_final → v5_first | Wk1–Wk4
    """)
    st.stop()

# Month selector
if len(all_data) == 1:
    selected_month = list(all_data.keys())[0]
else:
    selected_month = st.selectbox("📅 Select month to view:", list(all_data.keys()))

df, version_labels = all_data[selected_month]

# Apply filters
df_f = df.copy()
if filter_segments: df_f = df_f[df_f['Segment'].isin(filter_segments)]
if filter_colors:   df_f = df_f[df_f['Color'].isin(filter_colors)]
if filter_stars:    df_f = df_f[df_f['Star'].isin(filter_stars)]
if not show_tbc:    df_f = df_f[~df_f['Is_TBC']]

# ─────────────────────────────────────────────
# KPI STRIP
# ─────────────────────────────────────────────
active_df   = df_f[df_f['Is_Active']]
total_final = df_f['v1_final'].sum()
total_first = df_f['v5_first'].sum()
drift_total = total_final - total_first
drift_pct   = (drift_total / total_first * 100) if total_first else 0
n_active    = active_df['MAT'].nunique()
n_new       = (df_f['Status'] == 'New').sum()
n_dropped   = (df_f['Status'] == 'Dropped').sum()

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Final Plan Volume</div>
        <div class='metric-value'>{fmt(total_final)}</div>
        <div class='metric-sub'>units · latest version</div></div>""", unsafe_allow_html=True)
with c2:
    col = GREEN if drift_pct >= 0 else RED
    sign = '+' if drift_pct >= 0 else ''
    st.markdown(f"""<div class='metric-card' style='border-left-color:{col}'>
        <div class='metric-label'>Drift vs 1st Tentative</div>
        <div class='metric-value' style='color:{col}'>{sign}{drift_pct:.1f}%</div>
        <div class='metric-sub'>{sign}{fmt(drift_total)} units</div></div>""", unsafe_allow_html=True)
with c3:
    st.markdown(f"""<div class='metric-card'>
        <div class='metric-label'>Active SKUs</div>
        <div class='metric-value'>{n_active}</div>
        <div class='metric-sub'>in final plan</div></div>""", unsafe_allow_html=True)
with c4:
    st.markdown(f"""<div class='metric-card' style='border-left-color:{GREEN}'>
        <div class='metric-label'>New SKUs</div>
        <div class='metric-value'>{n_new}</div>
        <div class='metric-sub'>added vs 1st tentative</div></div>""", unsafe_allow_html=True)
with c5:
    st.markdown(f"""<div class='metric-card' style='border-left-color:{RED}'>
        <div class='metric-label'>Dropped SKUs</div>
        <div class='metric-value'>{n_dropped}</div>
        <div class='metric-sub'>removed vs 1st tentative</div></div>""", unsafe_allow_html=True)

st.caption(f"Version dates: {' → '.join(version_labels)}")

# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Plan Evolution", "📦 Segments", "🎨 Mix Analysis", "🔍 SKU Drill-Down", "📊 Multi-Month"
])

with tab1:
    st.markdown("<div class='section-header'>Plan Evolution</div>", unsafe_allow_html=True)
    st.plotly_chart(plan_evolution_chart(df_f, version_labels), use_container_width=True)
    ver_cols = sorted([c for c in df_f.columns if str(c).startswith('ver_')],
                      key=lambda x: int(x.split('_')[1]))
    totals   = [df_f[c].sum() for c in ver_cols]
    labels   = version_labels[-len(totals):]
    chgs     = ['—'] + [f"{((totals[i]-totals[i-1])/totals[i-1]*100):+.1f}%" if totals[i-1] else '—'
                        for i in range(1, len(totals))]
    st.dataframe(pd.DataFrame({'Version': labels, 'Total Units': [fmt(t) for t in totals],
        'Change vs Prev': chgs}), use_container_width=True, hide_index=True)

with tab2:
    st.markdown("<div class='section-header'>Segment Analysis</div>", unsafe_allow_html=True)
    ca, cb = st.columns(2)
    with ca: st.plotly_chart(segment_breakdown_chart(df_f), use_container_width=True)
    with cb: st.plotly_chart(segment_drift_chart(df_f), use_container_width=True)
    seg_tbl = df_f.groupby('Segment').agg(
        First_Tentative=('v5_first','sum'), Final=('v1_final','sum'), Active_SKUs=('Is_Active','sum')
    ).reset_index()
    seg_tbl['Drift']   = seg_tbl['Final'] - seg_tbl['First_Tentative']
    seg_tbl['Drift %'] = np.where(seg_tbl['First_Tentative'] > 0,
        (seg_tbl['Drift']/seg_tbl['First_Tentative']*100).round(1), np.nan)
    st.dataframe(seg_tbl.sort_values('Final', ascending=False).style.format({
        'First_Tentative':'{:,.0f}','Final':'{:,.0f}','Drift':'{:+,.0f}','Drift %':'{:+.1f}%'
    }).background_gradient(subset=['Drift %'], cmap='RdYlGn', vmin=-50, vmax=50),
    use_container_width=True, hide_index=True)

with tab3:
    st.markdown("<div class='section-header'>Mix Analysis — Final Plan</div>", unsafe_allow_html=True)
    ca, cb = st.columns(2)
    with ca: st.plotly_chart(color_mix_donut(df_f), use_container_width=True)
    with cb: st.plotly_chart(star_rating_chart(df_f), use_container_width=True)
    st.plotly_chart(weekly_loading_chart(df_f), use_container_width=True)
    st.plotly_chart(sku_status_chart(df_f), use_container_width=True)

with tab4:
    st.markdown("<div class='section-header'>SKU-Level Data</div>", unsafe_allow_html=True)
    view_mode = st.radio("Show:", ["Active SKUs only","All SKUs","Dropped SKUs","New SKUs"], horizontal=True)
    drill = {'Active SKUs only': df_f[df_f['Is_Active']], 'All SKUs': df_f,
             'Dropped SKUs': df_f[df_f['Status']=='Dropped'],
             'New SKUs': df_f[df_f['Status']=='New']}[view_mode]
    show_cols = [c for c in ['MAT','Description','Segment','Color','Star',
        'v5_first','v4','v3','v2','v1_final','drift_abs','drift_pct','Status','Wk1','Wk2','Wk3','Wk4']
        if c in drill.columns]
    st.caption(f"{len(drill):,} SKUs")
    st.dataframe(drill[show_cols].rename(columns={
        'v5_first':'1st Tent.','v4':'N-3','v3':'N-2','v2':'N-1','v1_final':'Final',
        'drift_abs':'Δ Units','drift_pct':'Δ %'}).style.format({
        '1st Tent.':'{:,.0f}','N-3':'{:,.0f}','N-2':'{:,.0f}','N-1':'{:,.0f}','Final':'{:,.0f}',
        'Δ Units':'{:+,.0f}','Δ %':'{:+.1f}%','Wk1':'{:,.0f}','Wk2':'{:,.0f}',
        'Wk3':'{:,.0f}','Wk4':'{:,.0f}'}, na_rep='—'),
    use_container_width=True, hide_index=True, height=480)
    st.download_button("⬇️ Download CSV", drill[show_cols].to_csv(index=False).encode(),
        file_name=f"sku_{selected_month}.csv", mime='text/csv')

with tab5:
    st.markdown("<div class='section-header'>Multi-Month Planning Accuracy</div>", unsafe_allow_html=True)
    if len(all_data) < 2:
        st.info("Upload 2 or more monthly files to see cross-month trends.")
    else:
        st.plotly_chart(multi_month_chart(all_data), use_container_width=True)
        rows = []
        for month, (mdf, _) in all_data.items():
            first = mdf['v5_first'].sum(); final = mdf['v1_final'].sum()
            rows.append({'Month':month,'Final':final,'1st Tent.':first,
                'Active SKUs':mdf['Is_Active'].sum(),
                'New':(mdf['Status']=='New').sum(),'Dropped':(mdf['Status']=='Dropped').sum(),
                'Drift %':round((final-first)/first*100,1) if first else 0})
        st.dataframe(pd.DataFrame(rows).style.format(
            {'Final':'{:,.0f}','1st Tent.':'{:,.0f}','Drift %':'{:+.1f}%'}
        ).background_gradient(subset=['Drift %'], cmap='RdYlGn', vmin=-30, vmax=30),
        use_container_width=True, hide_index=True)
