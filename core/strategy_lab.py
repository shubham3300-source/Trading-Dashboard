import pandas as pd

def ensure_scores(df: pd.DataFrame):
    out = df.copy()
    def num(col):
        return pd.to_numeric(out[col], errors="coerce") if col in out.columns else pd.Series([None]*len(out))

    out["technical_score"] = (
        (num("final_score").fillna(0) * 0.50) +
        (num("relative_strength_pct").clip(-10, 10).fillna(0) * 3) +
        (num("volume_ratio").clip(0, 3).fillna(0) * 10)
    ).round(2)

    pe = num("pe_ratio")
    pb = num("pb_ratio")
    roe = num("roe_pct")
    debt = num("debt_equity")

    value_score = pd.Series(0.0, index=out.index)
    value_score += pe.apply(lambda x: 30 if pd.notna(x) and x < 15 else (20 if pd.notna(x) and x < 25 else (10 if pd.notna(x) and x < 40 else 0)))
    value_score += pb.apply(lambda x: 20 if pd.notna(x) and x < 3 else (10 if pd.notna(x) and x < 6 else 0))
    value_score += roe.apply(lambda x: 30 if pd.notna(x) and x > 18 else (20 if pd.notna(x) and x > 12 else (10 if pd.notna(x) and x > 8 else 0)))
    value_score += debt.apply(lambda x: 20 if pd.notna(x) and x < 0.6 else (10 if pd.notna(x) and x < 1.2 else 0))
    out["value_score"] = value_score.round(2)

    out["combined_score"] = (out["technical_score"].fillna(0) * 0.6 + out["value_score"].fillna(0) * 0.4).round(2)
    return out
