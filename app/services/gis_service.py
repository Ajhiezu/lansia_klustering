"""
gis_service.py - Service to generate Folium maps from clustering results.
Integrates village GeoJSON boundaries with aggregated risk analysis and filtering.
"""

import json
import logging
import folium
from app.models.session_data import session_data
from app.core.config import BASE_DIR

logger = logging.getLogger("lansia.service.gis")

# Path to GeoJSON file with village boundaries
GEOJSON_PATH = BASE_DIR / "tempeh_desa.geojson"


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


def load_geojson() -> dict:
    """Load the GeoJSON village boundaries file."""
    if not GEOJSON_PATH.exists():
        logger.warning(f"File GeoJSON tidak ditemukan: {GEOJSON_PATH}")
        return None
    try:
        with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading GeoJSON: {e}")
        return None


def _normalize_desa_name(name: str) -> str:
    """Normalize desa name for matching between GeoJSON and dataset."""
    if not name:
        return ""
    return str(name).strip().upper()


# ══════════════════════════════════════════════════════════════════════════════
# Main Map Generation
# ══════════════════════════════════════════════════════════════════════════════

def generate_map(risk_filter: str = "all") -> str:
    """
    Generate an interactive Folium map based on clustering results.
    Uses GeoJSON village boundaries (choropleth polygons) only — no individual markers.

    Args:
        risk_filter: Filter risk level ('all', 'sehat', 'sedang', 'tinggi')
    Returns:
        HTML string of the map
    """
    from app.core.utils import calculate_individual_risk

    if not session_data.has_data():
        logger.warning("No session data available for GIS mapping.")
        return ""

    df = session_data.df_result.copy()
    geojson_data = load_geojson()

    # Pre-calculate individual risk scores and levels
    risk_info_list = [calculate_individual_risk(row) for _, row in df.iterrows()]
    df["risk_score"] = [r["score"] for r in risk_info_list]
    df["risk_level"] = [r["level"] for r in risk_info_list]
    df["risk_color"] = [r["color"] for r in risk_info_list]

    # Save details to session_data
    session_data.df_result["risk_score"] = df["risk_score"]
    session_data.df_result["risk_level"] = df["risk_level"]
    session_data.df_result["risk_color"] = df["risk_color"]

    # Calculate aggregations per Desa
    desa_stats = {}
    for desa_name in df["desa"].unique():
        dn_upper = _normalize_desa_name(desa_name)
        df_desa = df[df["desa"].str.upper().str.strip() == dn_upper]
        sehat = int((df_desa["risk_level"] == "Sehat").sum())
        sedang = int((df_desa["risk_level"] == "Sedang").sum())
        tinggi = int((df_desa["risk_level"] == "Tinggi").sum())
        total = len(df_desa)
        pct_sehat = round(sehat / total * 100, 1) if total > 0 else 0
        pct_sedang = round(sedang / total * 100, 1) if total > 0 else 0
        pct_tinggi = round(tinggi / total * 100, 1) if total > 0 else 0
        pct_risiko = round((sedang + tinggi) / total * 100, 1) if total > 0 else 0
        desa_stats[dn_upper] = {
            "sehat": sehat,
            "sedang": sedang,
            "tinggi": tinggi,
            "total": total,
            "pct_sehat": pct_sehat,
            "pct_sedang": pct_sedang,
            "pct_tinggi": pct_tinggi,
            "pct_risiko": pct_risiko,
        }

    risk_filter = str(risk_filter).lower().strip()

    # Default center (Tempeh, Lumajang)
    center_lat, center_lon = -8.21, 113.19
    m = folium.Map(
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
    ).add_to(m)

    # Feature group for village boundaries
    boundary_layer = folium.FeatureGroup(name="Batas Wilayah Desa", show=True).add_to(m)

    # ── DRAW VILLAGE BOUNDARY POLYGONS (GeoJSON) ──
    if geojson_data:
        for feature in geojson_data.get("features", []):
            props = feature.get("properties", {})
            desa_geojson_name = _normalize_desa_name(props.get("DESA", ""))
            alt_name = _normalize_desa_name(props.get("DESKEL u_7", ""))

            # Try to match stats by primary name or alt name
            stats = desa_stats.get(desa_geojson_name) or desa_stats.get(alt_name)
            if not stats:
                stats = {"sehat": 0, "sedang": 0, "tinggi": 0, "total": 0,
                         "pct_sehat": 0, "pct_sedang": 0, "pct_tinggi": 0, "pct_risiko": 0}

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

    m.get_root().html.add_child(folium.Element(legend_html))

    # Add Layer Control
    folium.LayerControl(position="topright").add_to(m)

    # Save to session
    map_html = m._repr_html_()
    session_data.gis_map_html = map_html
    return map_html
