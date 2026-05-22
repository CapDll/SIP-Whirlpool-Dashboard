"""
extract_data.py  —  reads a Whirlpool production plan Excel and outputs JSON
Usage: python3 extract_data.py <path_to_xlsx> <output_json>
"""
import sys, json, re
import pandas as pd
import numpy as np

def parse_release_date(raw):
    if pd.isna(raw): return "—"
    s = str(raw).strip()
    if hasattr(raw, 'strftime'): return raw.strftime("%d %b '%y")
    match = re.search(r'(\d{1,2})[a-z]{0,2}[\s\-]([A-Za-z]+)', s)
    if match: return f"{match.group(1)} {match.group(2)}"
    return s[:15]

def run(xlsx_path, out_path):
    df_raw    = pd.read_excel(xlsx_path, sheet_name=0, header=None)
    date_row  = df_raw.iloc[17]
    total_row = df_raw.iloc[18]

    # Auto-detect version columns
    version_cols = sorted(
        [c for c in range(len(date_row))
         if pd.notna(date_row.iloc[c]) and 'released' in str(date_row.iloc[c]).lower()],
        reverse=True   # highest = oldest
    )
    wk_map = {}
    for c in range(len(date_row)):
        v = str(date_row.iloc[c]).strip()
        if v in ['Wk1','Wk2','Wk3','Wk4']:
            wk_map[v] = c

    # Latest = first non-zero total col (lowest index)
    latest_col = min(version_cols)
    for c in sorted(version_cols):
        if (pd.to_numeric(total_row.iloc[c], errors='coerce') or 0) > 0:
            latest_col = c
            break
    first_col = max(version_cols)

    # Version labels old→new
    version_labels = [parse_release_date(date_row.iloc[c]) for c in sorted(version_cols, reverse=True)]
    version_totals = [int(pd.to_numeric(total_row.iloc[c], errors='coerce') or 0)
                      for c in sorted(version_cols, reverse=True)]

    # SKU data
    raw = df_raw.iloc[19:].copy().reset_index(drop=True)
    raw.columns = range(raw.shape[1])

    data = pd.DataFrame()
    data['MAT']      = raw[0].astype(str).str.strip()
    data['Color']    = raw[1].astype(str).str.strip()
    data['Star']     = raw[2].astype(str).str.strip()
    data['Segment']  = raw[3].astype(str).str.strip()
    data['Desc']     = raw[4].astype(str).str.strip()
    data['final']    = pd.to_numeric(raw[latest_col], errors='coerce').fillna(0).astype(int)
    data['first']    = pd.to_numeric(raw[first_col],  errors='coerce').fillna(0).astype(int)
    data['Wk1'] = pd.to_numeric(raw[wk_map.get('Wk1',0)], errors='coerce').fillna(0).astype(int) if 'Wk1' in wk_map else 0
    data['Wk2'] = pd.to_numeric(raw[wk_map.get('Wk2',0)], errors='coerce').fillna(0).astype(int) if 'Wk2' in wk_map else 0
    data['Wk3'] = pd.to_numeric(raw[wk_map.get('Wk3',0)], errors='coerce').fillna(0).astype(int) if 'Wk3' in wk_map else 0
    data['Wk4'] = pd.to_numeric(raw[wk_map.get('Wk4',0)], errors='coerce').fillna(0).astype(int) if 'Wk4' in wk_map else 0
    data = data[~data['MAT'].isin(['nan','NaN','','None'])]

    data['active']  = data['final'] > 0
    data['drift']   = data['final'] - data['first']

    def status(row):
        f, l = row['first'], row['final']
        if f == 0 and l > 0: return 'New'
        if f > 0 and l == 0: return 'Dropped'
        if f == l:            return 'Unchanged'
        return 'Increased' if l > f else 'Decreased'
    data['status'] = data.apply(status, axis=1)

    # Segment summary
    seg = data.groupby('Segment').agg(first=('first','sum'), final=('final','sum')).reset_index()
    seg = seg[(seg['first']>0)|(seg['final']>0)].copy()
    seg['drift_pct'] = np.where(seg['first']>0,
        ((seg['final']-seg['first'])/seg['first']*100).round(1), float('nan'))
    seg = seg.dropna(subset=['drift_pct']).sort_values('drift_pct')

    # Color mix
    active = data[data['active']]
    color_mix = active.groupby('Color')['final'].sum().sort_values(ascending=False)

    # Weekly
    wk_totals = [int(active['Wk1'].sum()), int(active['Wk2'].sum()),
                 int(active['Wk3'].sum()), int(active['Wk4'].sum())]

    # SKU status counts
    status_counts = data['status'].value_counts().to_dict()

    total_final = int(data['final'].sum())
    total_first = int(data['first'].sum())
    drift_pct   = round((total_final - total_first) / total_first * 100, 1) if total_first else 0
    n_active    = int(data['active'].sum())

    # Month label from filename
    month = re.sub(r'[_\-]', ' ', xlsx_path.split('/')[-1].replace('.xlsx','').replace('.xls',''))

    result = {
        "month": month,
        "version_labels": version_labels,
        "version_totals": version_totals,
        "total_final": total_final,
        "total_first": total_first,
        "drift_pct": drift_pct,
        "n_active": n_active,
        "n_new":     status_counts.get('New', 0),
        "n_dropped": status_counts.get('Dropped', 0),
        "n_increased": status_counts.get('Increased', 0),
        "n_decreased": status_counts.get('Decreased', 0),
        "n_unchanged": status_counts.get('Unchanged', 0),
        "weekly": wk_totals,
        "segment_drift": [
            {"segment": r['Segment'], "first": int(r['first']),
             "final": int(r['final']), "drift_pct": float(r['drift_pct'])}
            for _, r in seg.iterrows()
        ],
        "color_mix": [
            {"color": k, "qty": int(v)} for k, v in color_mix.items() if v > 0
        ],
    }

    with open(out_path, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"Extracted: {out_path}")

if __name__ == '__main__':
    run(sys.argv[1], sys.argv[2])
