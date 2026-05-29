import os, glob, pandas as pd
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GENERATED_DIR = os.path.join(BASE_DIR, "generated_data")
DATA_DIR = os.path.join(BASE_DIR, "data")

def ensure_dirs():
    os.makedirs(GENERATED_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)

def load_scan_df():
    ensure_dirs()
    p = os.path.join(GENERATED_DIR, "nifty500_live_latest.csv")
    if os.path.exists(p):
        try: return pd.read_csv(p), p
        except: pass
    files = glob.glob(os.path.join(GENERATED_DIR, "nifty500_live_*.csv"))
    if files:
        latest = max(files, key=os.path.getmtime)
        return pd.read_csv(latest), latest
    return pd.DataFrame(), None

def load_user_file(filename, cols):
    ensure_dirs()
    path = os.path.join(DATA_DIR, filename)
    if os.path.exists(path):
        try: return pd.read_csv(path)
        except: pass
    df = pd.DataFrame(columns=cols)
    df.to_csv(path, index=False)
    return df

def save_user_file(filename, df):
    ensure_dirs()
    path = os.path.join(DATA_DIR, filename)
    df.to_csv(path, index=False)
    return path
