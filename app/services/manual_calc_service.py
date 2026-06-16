"""
manual_calc_service.py - Step-by-step manual calculation service.
Extracts a small sample of data and performs exact step-by-step formulas
for K-Means, Silhouette Score, Davies-Bouldin, and Calinski-Harabasz.
"""

import logging
import numpy as np
import pandas as pd
from app.models.session_data import session_data

logger = logging.getLogger("lansia.service.manual_calc")


def get_manual_calculation_steps() -> dict:
    """
    Generate step-by-step manual calculation data for K-Means and validation metrics.
    Uses a small subset of features and data rows for readability.
    """
    if not session_data.has_data():
        return None

    # 1. Prepare sample data
    # Select 5 representative rows and 3 key features for explanation
    df_clean = session_data.df_clean.copy()
    df_scaled = session_data.df_scaled.copy()
    
    # Selected features for manual calculation demo
    demo_features = ["umur", "imt", "gula_darah"]
    demo_features = [f for f in demo_features if f in df_scaled.columns]
    if len(demo_features) < 3:
        demo_features = list(df_scaled.columns[:3])

    # Select 5 rows
    sample_size = min(5, len(df_scaled))
    sample_df = df_clean.head(sample_size)
    sample_scaled = df_scaled[demo_features].head(sample_size)
    
    # Values as list of dicts for presentation
    data_points = []
    for idx, (original_idx, row) in enumerate(sample_scaled.iterrows()):
        orig_row = sample_df.iloc[idx]
        pt = {
            "id": idx + 1,
            "nama": orig_row.get("nama", f"Lansia {idx+1}"),
            "original_vals": {f: round(float(orig_row[f]), 2) for f in demo_features},
            "scaled_vals": {f: round(float(row[f]), 4) for f in demo_features},
        }
        data_points.append(pt)

    # 2. Step-by-Step K-Means
    # We will run 1 iteration of K-Means manually on these 5 points with K=3
    X_demo = sample_scaled.values
    k_demo = min(3, sample_size)
    
    # Initial Centroids (let's pick points 1, 2, 3 as initial centroids)
    init_centroids = X_demo[:k_demo].copy()
    
    kmeans_steps = []
    
    # Iteration 1
    distances = []
    assignments = []
    
    for idx, pt in enumerate(X_demo):
        pt_dist = []
        for c_idx in range(k_demo):
            dist = np.sqrt(np.sum((pt - init_centroids[c_idx]) ** 2))
            pt_dist.append(round(float(dist), 4))
        nearest = int(np.argmin(pt_dist))
        distances.append(pt_dist)
        assignments.append(nearest)
        
    # Calculate new centroids
    new_centroids = []
    new_centroid_calculations = []
    for c_idx in range(k_demo):
        assigned_pts = [X_demo[i] for i in range(sample_size) if assignments[i] == c_idx]
        if assigned_pts:
            mean_val = np.mean(assigned_pts, axis=0)
            new_centroids.append(mean_val)
            # detail string
            pt_indices = [f"P{i+1}" for i in range(sample_size) if assignments[i] == c_idx]
            calc_str = f"({ ' + '.join(pt_indices) }) / {len(assigned_pts)}"
            new_centroid_calculations.append({
                "cluster": c_idx,
                "pts": pt_indices,
                "calc_str": calc_str,
                "vals": [round(float(v), 4) for v in mean_val]
            })
        else:
            new_centroids.append(init_centroids[c_idx])
            new_centroid_calculations.append({
                "cluster": c_idx,
                "pts": [],
                "calc_str": "No points assigned (keep initial)",
                "vals": [round(float(v), 4) for v in init_centroids[c_idx]]
            })

    # Prepare K-Means presentation dict
    kmeans_step_1 = {
        "initial_centroids": [
            {"cluster": i, "vals": [round(float(v), 4) for v in init_centroids[i]]}
            for i in range(k_demo)
        ],
        "points": [
            {
                "id": i + 1,
                "name": data_points[i]["nama"],
                "vals": [round(float(v), 4) for v in X_demo[i]],
                "dists": distances[i],
                "assigned_cluster": assignments[i]
            }
            for i in range(sample_size)
        ],
        "updated_centroids": new_centroid_calculations
    }

    # 3. Silhouette Score step-by-step
    # We will compute silhouette score for the demo points based on the above assignments
    silhouette_steps = []
    total_sil = 0.0
    
    for i in range(sample_size):
        c_i = assignments[i]
        pt_i = X_demo[i]
        
        # a(i) - average distance to other points in the same cluster
        same_cluster_pts = [X_demo[j] for j in range(sample_size) if assignments[j] == c_i and j != i]
        if same_cluster_pts:
            a_i = np.mean([np.sqrt(np.sum((pt_i - pt_j) ** 2)) for pt_j in same_cluster_pts])
            a_i_str = f"Rata-rata jarak P{i+1} ke " + ", ".join([f"P{j+1}" for j in range(sample_size) if assignments[j] == c_i and j != i])
        else:
            a_i = 0.0
            a_i_str = "Hanya 1 anggota dalam cluster"
            
        # b(i) - average distance to points in other clusters, then find the minimum
        b_i_candidates = {}
        for c_other in range(k_demo):
            if c_other == c_i:
                continue
            other_pts = [X_demo[j] for j in range(sample_size) if assignments[j] == c_other]
            if other_pts:
                avg_dist = np.mean([np.sqrt(np.sum((pt_i - pt_j) ** 2)) for pt_j in other_pts])
                b_i_candidates[c_other] = avg_dist
                
        if b_i_candidates:
            b_i = min(b_i_candidates.values())
            min_other_c = min(b_i_candidates, key=b_i_candidates.get)
            b_i_str = f"Rata-rata jarak P{i+1} ke Cluster {min_other_c}"
        else:
            b_i = 0.0
            b_i_str = "Tidak ada cluster lain"
            
        # s(i)
        denom = max(a_i, b_i)
        s_i = (b_i - a_i) / denom if denom > 0 else 0.0
        total_sil += s_i
        
        silhouette_steps.append({
            "id": i + 1,
            "nama": data_points[i]["nama"],
            "cluster": c_i,
            "a_i": round(float(a_i), 4),
            "a_i_desc": a_i_str,
            "b_i": round(float(b_i), 4),
            "b_i_desc": b_i_str,
            "s_i": round(float(s_i), 4),
            "calc_str": f"({round(float(b_i), 4)} - {round(float(a_i), 4)}) / max({round(float(a_i), 4)}, {round(float(b_i), 4)}) = {round(float(s_i), 4)}"
        })
        
    avg_sil_demo = total_sil / sample_size

    # 4. Davies-Bouldin Index step-by-step
    # S_i - dispersion of cluster i
    dispersions = []
    dispersion_calculations = []
    
    for c_idx in range(k_demo):
        c_val = new_centroids[c_idx]
        assigned_indices = [j for j in range(sample_size) if assignments[j] == c_idx]
        if assigned_indices:
            pts = [X_demo[j] for j in assigned_indices]
            dists = [np.sqrt(np.sum((pt - c_val) ** 2)) for pt in pts]
            s_i = np.mean(dists)
            disp_str = f"Mean distance of {', '.join([f'P{j+1}' for j in assigned_indices])} to Centroid {c_idx}"
            dispersions.append(s_i)
            dispersion_calculations.append({
                "cluster": c_idx,
                "s_i": round(float(s_i), 4),
                "pts": [f"P{j+1}" for j in assigned_indices],
                "dists": [round(float(d), 4) for d in dists],
                "calc_str": disp_str
            })
        else:
            dispersions.append(0.0)
            dispersion_calculations.append({
                "cluster": c_idx,
                "s_i": 0.0,
                "pts": [],
                "dists": [],
                "calc_str": "No points in cluster"
            })
            
    # Centroid distances and Similarity Ratios
    dbi_ratios = []
    max_ratios = []
    for i in range(k_demo):
        ratios_i = {}
        for j in range(k_demo):
            if i == j:
                continue
            # distance between centroids
            m_ij = np.sqrt(np.sum((new_centroids[i] - new_centroids[j]) ** 2))
            r_ij = (dispersions[i] + dispersions[j]) / m_ij if m_ij > 0 else 0.0
            ratios_i[j] = {
                "m_ij": round(float(m_ij), 4),
                "r_ij": round(float(r_ij), 4),
                "formula": f"({round(dispersions[i], 4)} + {round(dispersions[j], 4)}) / {round(float(m_ij), 4)}"
            }
        max_r_val = max([item["r_ij"] for item in ratios_i.values()]) if ratios_i else 0.0
        max_ratios.append(max_r_val)
        dbi_ratios.append({
            "cluster": i,
            "ratios": ratios_i,
            "max_ratio": max_r_val
        })
        
    dbi_demo = np.mean(max_ratios) if max_ratios else 0.0

    # 5. Calinski-Harabasz Score step-by-step
    # Overall mean of demo dataset (global centroid)
    global_centroid = np.mean(X_demo, axis=0)
    
    # SS_W: Within-cluster sum of squares
    ss_w = 0.0
    ss_w_details = []
    for c_idx in range(k_demo):
        c_val = new_centroids[c_idx]
        assigned_indices = [j for j in range(sample_size) if assignments[j] == c_idx]
        cluster_sum = 0.0
        for j in assigned_indices:
            dist_sq = np.sum((X_demo[j] - c_val) ** 2)
            cluster_sum += dist_sq
        ss_w += cluster_sum
        ss_w_details.append({
            "cluster": c_idx,
            "pts": [f"P{j+1}" for j in assigned_indices],
            "sum_sq": round(float(cluster_sum), 4)
        })
        
    # SS_B: Between-cluster sum of squares
    ss_b = 0.0
    ss_b_details = []
    for c_idx in range(k_demo):
        c_val = new_centroids[c_idx]
        assigned_count = len([j for j in range(sample_size) if assignments[j] == c_idx])
        dist_sq = np.sum((c_val - global_centroid) ** 2)
        weighted_dist = assigned_count * dist_sq
        ss_b += weighted_dist
        ss_b_details.append({
            "cluster": c_idx,
            "count": assigned_count,
            "dist_sq": round(float(dist_sq), 4),
            "weighted_val": round(float(weighted_dist), 4),
            "calc_str": f"{assigned_count} * {round(float(dist_sq), 4)}"
        })
        
    # CH index
    k_num = k_demo
    n_num = sample_size
    
    ch_numerator = ss_b / (k_num - 1) if k_num > 1 else 0.0
    ch_denominator = ss_w / (n_num - k_num) if (n_num - k_num) > 0 else 1.0
    ch_demo = ch_numerator / ch_denominator if ch_denominator > 0 else 0.0

    ch_calc = {
        "global_centroid": [round(float(v), 4) for v in global_centroid],
        "ss_w_details": ss_w_details,
        "ss_w": round(float(ss_w), 4),
        "ss_b_details": ss_b_details,
        "ss_b": round(float(ss_b), 4),
        "numerator": round(float(ch_numerator), 4),
        "denominator": round(float(ch_denominator), 4),
        "ch_score": round(float(ch_demo), 4),
        "formula": f"({round(float(ss_b), 4)} / ({k_num}-1)) / ({round(float(ss_w), 4)} / ({n_num}-{k_num})) = {round(float(ch_demo), 4)}"
    }

    return {
        "features": demo_features,
        "data_points": data_points,
        "kmeans": kmeans_step_1,
        "silhouette": {
            "steps": silhouette_steps,
            "avg_score": round(float(avg_sil_demo), 4)
        },
        "davies_bouldin": {
            "dispersions": dispersion_calculations,
            "ratios": dbi_ratios,
            "dbi_score": round(float(dbi_demo), 4)
        },
        "calinski_harabasz": ch_calc
    }
