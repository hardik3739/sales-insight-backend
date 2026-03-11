"""
Parses CSV/XLSX bytes and returns a structured metrics dict.
Never sends raw rows to the LLM — only aggregated metrics.
This prevents prompt-injection via malicious cell content.
"""
import io
import pandas as pd
from fastapi import HTTPException


def process_file(raw: bytes, filename: str) -> dict:
    """
    Parse the uploaded file and compute key sales metrics.

    Returns a dict safe to embed in a structured LLM prompt.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    try:
        if ext == "csv":
            df = pd.read_csv(io.BytesIO(raw))
        else:  # xlsx
            df = pd.read_excel(io.BytesIO(raw), engine="openpyxl")
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Could not parse file: {exc}",
        )

    if df.empty:
        raise HTTPException(
            status_code=422, detail="Uploaded file is empty or unreadable."
        )

    # --- Normalize column names ---
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    metrics: dict = {
        "row_count": int(len(df)),
        "columns": list(df.columns),
    }

    # Revenue
    rev_col = next((c for c in df.columns if "revenue" in c), None)
    if rev_col:
        metrics["total_revenue"] = round(float(df[rev_col].sum()), 2)
        metrics["avg_revenue_per_row"] = round(float(df[rev_col].mean()), 2)

    # Units
    units_col = next((c for c in df.columns if "unit" in c and "price" not in c), None)
    if units_col:
        metrics["total_units_sold"] = int(df[units_col].sum())

    # Region breakdown
    region_col = next(
        (c for c in df.columns if c in ("region", "territory", "area")), None
    )
    if region_col and rev_col:
        region_revenue = (
            df.groupby(region_col)[rev_col].sum().sort_values(ascending=False)
        )
        metrics["top_region"] = str(region_revenue.index[0])
        metrics["top_region_revenue"] = round(float(region_revenue.iloc[0]), 2)
        metrics["region_breakdown"] = {
            str(k): round(float(v), 2) for k, v in region_revenue.items()
        }

    # Category breakdown
    cat_col = next(
        (
            c
            for c in df.columns
            if any(x in c for x in ("category", "product", "segment"))
        ),
        None,
    )
    if cat_col and rev_col:
        cat_revenue = (
            df.groupby(cat_col)[rev_col].sum().sort_values(ascending=False)
        )
        metrics["top_category"] = str(cat_revenue.index[0])
        metrics["category_breakdown"] = {
            str(k): round(float(v), 2) for k, v in cat_revenue.items()
        }

    # Status / order health
    status_col = next(
        (c for c in df.columns if "status" in c), None
    )
    if status_col:
        status_counts = df[status_col].value_counts().to_dict()
        metrics["status_breakdown"] = {str(k): int(v) for k, v in status_counts.items()}
        cancelled = sum(
            v
            for k, v in status_counts.items()
            if "cancel" in str(k).lower()
        )
        metrics["cancelled_orders"] = int(cancelled)

    # Date range
    date_col = next((c for c in df.columns if "date" in c), None)
    if date_col:
        try:
            dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
            if not dates.empty:
                metrics["date_range"] = {
                    "start": dates.min().strftime("%Y-%m-%d"),
                    "end": dates.max().strftime("%Y-%m-%d"),
                }
        except Exception:
            pass

    return metrics
