"""
gis_service.py - Service to generate Folium maps from clustering results using geopandas.
Integrates village GeoJSON boundaries with aggregated risk analysis and filtering.
"""

import json
import logging
import folium
import geopandas as gpd
import pandas as pd
from app.models.session_data import session_data
from app.core.config import BASE_DIR

logger = logging.getLogger("lansia.service.gis")

# Path to GeoJSON file with village boundaries
GEOJSON_PATH = BASE_DIR / "batas_desa_maesan.geojson"


# ══════════════════════════════════════════════════════════════════════════════
# Helper Functions
# ══════════════════════════════════════════════════════════════════════════════

def get_geojson_centroid(geometry: dict) -> tuple:
    """Calculate the average latitude and longitude (centroid) of a GeoJSON geometry."""
    coords = []

    def extract_coords(lst):
        if not lst:
            return
        if isinstance(lst[0], (int, float)):
            coords.append((lst[1], lst[0]))  # GeoJSON is [lon, lat] → (lat, lon)
        else:
            for item in lst:
                extract_coords(item)

    if not geometry:
        return None

    g_type = geometry.get("type")
    if g_type in ("Polygon", "MultiPolygon"):
        extract_coords(geometry.get("coordinates", []))
    elif g_type == "Point":
        c = geometry.get("coordinates", [0, 0])
        return (c[1], c[0])

    if coords:
        lats = [c[0] for c in coords]
        lons = [c[1] for c in coords]
        return sum(lats) / len(lats), sum(lons) / len(lons)
    return None


def get_village_color(pct: float, risk_filter: str) -> str:
    """Get fill color for a village polygon based on its percentage and the active filter."""
    risk_filter = str(risk_filter).lower().strip()
    if risk_filter == "sehat":
        # Green gradient
        if pct <= 20: return "#ecfdf5"
        if pct <= 40: return "#d1fae5"
        if pct <= 60: return "#6ee7b7"
        if pct <= 80: return "#34d399"
        return "#059669"
    elif risk_filter == "sedang":
        # Orange gradient
        if pct <= 20: return "#fff7ed"
        if pct <= 40: return "#ffedd5"
        if pct <= 60: return "#fdba74"
        if pct <= 80: return "#fb923c"
        return "#ea580c"
    elif risk_filter == "tinggi":
        # Red gradient
        if pct <= 10: return "#fef2f2"
        if pct <= 25: return "#fee2e2"
        if pct <= 45: return "#fca5a5"
        if pct <= 65: return "#f87171"
        return "#dc2626"
    else:
        # 'all' filter: color based on percentage of risk (sedang + tinggi)
        if pct <= 15: return "#10b981"
        if pct <= 35: return "#84cc16"
        if pct <= 55: return "#eab308"
        if pct <= 75: return "#f97316"
        return "#ef4444"


def load_maesan_gdf() -> gpd.GeoDataFrame:
    """Load the GeoJSON village boundaries file using geopandas and ensure EPSG:4326."""
    if not GEOJSON_PATH.exists():
        logger.warning(f"File GeoJSON tidak ditemukan: {GEOJSON_PATH}")
        return None
    try:
        gdf_maesan = gpd.read_file(GEOJSON_PATH)
        # Ensure CRS is EPSG:4326
        if gdf_maesan.crs is None or gdf_maesan.crs.to_string() != "EPSG:4326":
            logger.info("Mengonversi sistem koordinat GeoJSON ke EPSG:4326")
            gdf_maesan = gdf_maesan.to_crs("EPSG:4326")
        return gdf_maesan
    except Exception as e:
        logger.error(f"Error loading GeoJSON with geopandas: {e}")
        return None


def _normalize_desa_name(name: str) -> str:
    """Normalize desa name for matching between GeoJSON and dataset."""
    if not name:
        return ""
    # Capitalize, strip spaces, and remove special characters/excessive spacing
    normalized = str(name).strip().upper()
    normalized = " ".join(normalized.split())
    return normalized


# ══════════════════════════════════════════════════════════════════════════════
# Main Map Generation
# ══════════════════════════════════════════════════════════════════════════════

def generate_map(risk_filter: str = "all") -> str:
    """
    Generate an interactive Folium map based on clustering results.
    Uses GeoJSON village boundaries (choropleth polygons) only.

    Args:
        risk_filter: Filter risk level ('all', 'sehat', 'sedang', 'tinggi')
    Returns:
        HTML string of the map
    """
    from app.core.clustering import _rank_clusters_by_risk

    if not session_data.has_data():
        logger.warning("No session data available for GIS mapping.")
        return ""

    df = session_data.df_result.copy()
    
    # Load Geopandas GeoDataFrame
    gdf_maesan = load_maesan_gdf()
    if gdf_maesan is None:
        return ""

    # ── Use actual K-Means cluster results with relative risk ranking ──
    key_feats = ["umur", "imt", "sistolik", "diastolik", "kolesterol", "gds_1"]
    key_feats = [f for f in key_feats if f in df.columns]

    cluster_means = df.groupby("cluster")[key_feats].mean()
    rank_labels, _ = _rank_clusters_by_risk(cluster_means)

    # Convert internal labels to display labels
    label_map = {
        "RELATIF SEHAT": "Sehat",
        "RISIKO SEDANG": "Sedang",
        "RISIKO TINGGI": "Tinggi",
    }
    cluster_risk_map = {cl: label_map.get(lbl, "Sedang") for cl, lbl in rank_labels.items()}

    df["risk_level"] = df["cluster"].map(cluster_risk_map)

    # Save to session_data
    session_data.df_result["risk_level"] = df["risk_level"]

    # Calculate aggregations per Desa
    df["desa_norm"] = df["desa"].apply(_normalize_desa_name)
    df_grouped = df.groupby("desa_norm").agg(
        sehat=("risk_level", lambda x: int((x == "Sehat").sum())),
        sedang=("risk_level", lambda x: int((x == "Sedang").sum())),
        tinggi=("risk_level", lambda x: int((x == "Tinggi").sum())),
        total=("risk_level", "count")
    ).reset_index()

    # Normalize GeoJSON desa columns
    gdf_maesan["DESA_NORM"] = gdf_maesan["DESA"].apply(_normalize_desa_name)
    gdf_maesan["ALT_NORM"] = gdf_maesan["DESKEL u_7"].apply(_normalize_desa_name)

    # Perform Join (merge)
    # Primary merge on DESA_NORM
    gdf_merged = gdf_maesan.merge(df_grouped, left_on="DESA_NORM", right_on="desa_norm", how="left")
    
    # Secondary merge fallback on ALT_NORM for unmatched rows
    unmatched_mask = gdf_merged["total"].isna()
    if unmatched_mask.any():
        df_grouped_alt = df_grouped.rename(columns={"desa_norm": "alt_norm"})
        gdf_alt_merged = gdf_maesan.merge(df_grouped_alt, left_on="ALT_NORM", right_on="alt_norm", how="left")
        for col in ["sehat", "sedang", "tinggi", "total"]:
            gdf_merged.loc[unmatched_mask, col] = gdf_alt_merged.loc[unmatched_mask, col]

    # Fill NaN values with 0
    for col in ["sehat", "sedang", "tinggi", "total"]:
        gdf_merged[col] = gdf_merged[col].fillna(0).astype(int)

    # Calculate percentages
    gdf_merged["pct_sehat"] = (gdf_merged["sehat"] / gdf_merged["total"] * 100).round(1).fillna(0)
    gdf_merged["pct_sedang"] = (gdf_merged["sedang"] / gdf_merged["total"] * 100).round(1).fillna(0)
    gdf_merged["pct_tinggi"] = (gdf_merged["tinggi"] / gdf_merged["total"] * 100).round(1).fillna(0)
    gdf_merged["pct_risiko"] = ((gdf_merged["sedang"] + gdf_merged["tinggi"]) / gdf_merged["total"] * 100).round(1).fillna(0)

    # ── VALIDATION: PRINT UNMATCHED VILLAGES ──
    # Check GeoJSON villages that don't have cluster data
    unmatched_geojson = gdf_merged[gdf_merged["total"] == 0]
    if not unmatched_geojson.empty:
        logger.info("=== VALIDASI SPASIAL: DESA GEOJSON TANPA DATA KLASTER (UNMATCHED) ===")
        for _, row_g in unmatched_geojson.iterrows():
            logger.info(f" GeoJSON Desa: {row_g['DESA']} ({row_g['DESKEL u_7']}) - Tidak ada data lansia")

    # Check Dataset villages that are missing from GeoJSON boundaries
    all_geojson_names = set(gdf_merged["DESA_NORM"].tolist() + gdf_merged["ALT_NORM"].tolist())
    unmatched_dataset = df_grouped[~df_grouped["desa_norm"].isin(all_geojson_names)]
    if not unmatched_dataset.empty:
        logger.warning("=== VALIDASI SPASIAL: DESA DATASET TANPA BATAS GEOJSON ===")
        for _, row_d in unmatched_dataset.iterrows():
            logger.warning(f" Dataset Desa: {row_d['desa_norm']} - Batas GeoJSON tidak ditemukan!")

    risk_filter = str(risk_filter).lower().strip()

    # Default center (Maesan, Bondowoso)
    center_lat, center_lon = -8.0241, 113.7668
    peta_maesan = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=13,
        tiles="CartoDB positron",
        control_scale=True
    )

    # Add satellite base map option
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
        name="Esri Satellite"
    ).add_to(peta_maesan)

    # Feature group for village boundaries
    boundary_layer = folium.FeatureGroup(name="Batas Wilayah Desa", show=True).add_to(peta_maesan)

    # Convert GDF to geojson dictionary format to draw polygons
    geojson_data = json.loads(gdf_merged.to_json())

    # ── DRAW VILLAGE BOUNDARY POLYGONS (GeoJSON) ──
    if geojson_data:
        for feature in geojson_data.get("features", []):
            props = feature.get("properties", {})
            
            stats = {
                "sehat": int(props.get("sehat", 0)),
                "sedang": int(props.get("sedang", 0)),
                "tinggi": int(props.get("tinggi", 0)),
                "total": int(props.get("total", 0)),
                "pct_sehat": float(props.get("pct_sehat", 0.0)),
                "pct_sedang": float(props.get("pct_sedang", 0.0)),
                "pct_tinggi": float(props.get("pct_tinggi", 0.0)),
                "pct_risiko": float(props.get("pct_risiko", 0.0))
            }

            has_data = stats["total"] > 0

            # Determine fill color based on filter
            if not has_data:
                fill_color = "#e2e8f0"  # Slate gray for no data
                border_color = "#94a3b8"
            else:
                if risk_filter == "sehat":
                    fill_color = get_village_color(stats["pct_sehat"], risk_filter)
                elif risk_filter == "sedang":
                    fill_color = get_village_color(stats["pct_sedang"], risk_filter)
                elif risk_filter == "tinggi":
                    fill_color = get_village_color(stats["pct_tinggi"], risk_filter)
                else:
                    fill_color = get_village_color(stats["pct_risiko"], risk_filter)
                border_color = "#475569"

            display_name = (props.get("DESKEL u_7") or props.get("DESA") or "?").title()

            # Popup HTML with statistics
            popup_html = f"""
            <div style="font-family: 'Inter', sans-serif; font-size: 13px; width: 240px; line-height: 1.6; padding: 4px;">
                <h4 style="margin: 0 0 8px 0; border-bottom: 2px solid {fill_color}; padding-bottom: 4px; color: #1e293b;">
                    Desa {display_name}
                </h4>
                <p style="margin: 0 0 8px 0; font-size: 12px; color: #64748b;">Distribusi Risiko Kesehatan Lansia:</p>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 3px 0; color: #475569;">
                            <span style="background: #10b981; width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 6px;"></span>
                            Relatif Sehat
                        </td>
                        <td style="font-weight: bold; text-align: right; color: #10b981;">{stats['sehat']} ({stats['pct_sehat']}%)</td>
                    </tr>
                    <tr>
                        <td style="padding: 3px 0; color: #475569;">
                            <span style="background: #f59e0b; width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 6px;"></span>
                            Risiko Sedang
                        </td>
                        <td style="font-weight: bold; text-align: right; color: #f59e0b;">{stats['sedang']} ({stats['pct_sedang']}%)</td>
                    </tr>
                    <tr>
                        <td style="padding: 3px 0; color: #475569;">
                            <span style="background: #ef4444; width: 10px; height: 10px; border-radius: 50%; display: inline-block; margin-right: 6px;"></span>
                            Risiko Tinggi
                        </td>
                        <td style="font-weight: bold; text-align: right; color: #ef4444;">{stats['tinggi']} ({stats['pct_tinggi']}%)</td>
                    </tr>
                    <tr style="border-top: 1px solid #e2e8f0;">
                        <td style="padding: 6px 0 0 0; font-weight: bold; color: #1e293b;">Total Lansia</td>
                        <td style="padding: 6px 0 0 0; font-weight: bold; text-align: right; color: #1e293b;">{stats['total']} lansia</td>
                    </tr>
                </table>
            </div>
            """

            # Tooltip (shown on hover)
            tooltip_text = f"<b>{display_name}</b><br>Total: {stats['total']} lansia"
            if has_data:
                tooltip_text += f"<br>Sehat: {stats['sehat']} · Sedang: {stats['sedang']} · Tinggi: {stats['tinggi']}"

            # Create single-feature GeoJSON for this village
            single_feature = {
                "type": "FeatureCollection",
                "features": [feature]
            }

            folium.GeoJson(
                single_feature,
                style_function=lambda x, fc=fill_color, bc=border_color, hd=has_data: {
                    "fillColor": fc,
                    "color": bc,
                    "weight": 2 if hd else 1.5,
                    "fillOpacity": 0.55 if hd else 0.15,
                    "dashArray": "" if hd else "5, 5",
                },
                highlight_function=lambda x: {
                    "weight": 4,
                    "color": "#1e293b",
                    "fillOpacity": 0.75,
                },
                tooltip=folium.Tooltip(tooltip_text, sticky=True,
                                       style="font-family: 'Inter', sans-serif; font-size: 12px; padding: 6px 10px; border-radius: 6px;"),
                popup=folium.Popup(popup_html, max_width=300),
            ).add_to(boundary_layer)


    # ── ADD LEGEND ──
    legend_container_style = """
        position: fixed;
        bottom: 30px; left: 30px; width: 200px; height: auto;
        z-index: 9999; font-size: 11.5px; font-family: 'Inter', sans-serif;
        background-color: rgba(255, 255, 255, 0.96);
        box-shadow: 0 4px 12px -1px rgba(0,0,0,0.12), 0 2px 6px -2px rgba(0,0,0,0.08);
        border-radius: 10px; border: 1px solid #cbd5e1;
        padding: 12px 14px;
    """

    def _legend_item(color, label):
        return f"""
        <div style="display: flex; align-items: center; margin-bottom: 5px;">
            <span style="background: {color}; width: 18px; height: 12px; border-radius: 3px; display: inline-block; margin-right: 8px; border: 1px solid rgba(0,0,0,0.1);"></span>
            <span style="color: #475569; font-weight: 500;">{label}</span>
        </div>
        """

    if risk_filter == "sehat":
        legend_html = f"""
        <div style="{legend_container_style}">
            <h4 style="margin: 0 0 8px 0; font-size: 12px; font-weight: 700; color: #1e293b;">Tingkat Lansia Sehat</h4>
            {_legend_item("#ecfdf5", "≤ 20%")}
            {_legend_item("#d1fae5", "21 – 40%")}
            {_legend_item("#6ee7b7", "41 – 60%")}
            {_legend_item("#34d399", "61 – 80%")}
            {_legend_item("#059669", "> 80%")}
            {_legend_item("#e2e8f0", "Tidak Ada Data")}
        </div>
        """
    elif risk_filter == "sedang":
        legend_html = f"""
        <div style="{legend_container_style}">
            <h4 style="margin: 0 0 8px 0; font-size: 12px; font-weight: 700; color: #1e293b;">Tingkat Risiko Sedang</h4>
            {_legend_item("#fff7ed", "≤ 20%")}
            {_legend_item("#ffedd5", "21 – 40%")}
            {_legend_item("#fdba74", "41 – 60%")}
            {_legend_item("#fb923c", "61 – 80%")}
            {_legend_item("#ea580c", "> 80%")}
            {_legend_item("#e2e8f0", "Tidak Ada Data")}
        </div>
        """
    elif risk_filter == "tinggi":
        legend_html = f"""
        <div style="{legend_container_style}">
            <h4 style="margin: 0 0 8px 0; font-size: 12px; font-weight: 700; color: #1e293b;">Tingkat Risiko Tinggi</h4>
            {_legend_item("#fef2f2", "≤ 10%")}
            {_legend_item("#fee2e2", "11 – 25%")}
            {_legend_item("#fca5a5", "26 – 45%")}
            {_legend_item("#f87171", "46 – 65%")}
            {_legend_item("#dc2626", "> 65%")}
            {_legend_item("#e2e8f0", "Tidak Ada Data")}
        </div>
        """
    else:
        legend_html = f"""
        <div style="{legend_container_style}">
            <h4 style="margin: 0 0 8px 0; font-size: 12px; font-weight: 700; color: #1e293b;">Tingkat Risiko Desa</h4>
            {_legend_item("#10b981", "Rendah (≤ 15%)")}
            {_legend_item("#84cc16", "Cukup (16 – 35%)")}
            {_legend_item("#eab308", "Sedang (36 – 55%)")}
            {_legend_item("#f97316", "Tinggi (56 – 75%)")}
            {_legend_item("#ef4444", "Sangat Tinggi (> 75%)")}
            {_legend_item("#e2e8f0", "Tidak Ada Data")}
        </div>
        """

    peta_maesan.get_root().html.add_child(folium.Element(legend_html))

    # Add Layer Control
    folium.LayerControl(position="topright").add_to(peta_maesan)

    # Save to session
    map_html = peta_maesan._repr_html_()
    session_data.gis_map_html = map_html
    return map_html
