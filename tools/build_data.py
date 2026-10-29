"""Builds the two data files the map page loads.

    python3 tools/build_data.py <apaar-demo-data/json> <geo folder>

<geo folder> holds DataMeet's states.geojson and dists11.geojson
(https://github.com/datameet/maps). Writes data/branches.js and data/geo.js.

Branch names, districts, coordinates, addresses and IFSC codes are DEMO values
(see tools/branch_locations.csv). The figures are the APAAR export's, by branch code;
the export's own town names are replaced by Gujarat towns for the demo.
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "data")
STATE = "Gujarat"
HEAD_OFFICE = "00001"
# The demo bank is shown in Gujarat; the export's own name and towns are replaced
BANK_NAME = "Gujarat Pragati State Cooperative Bank Ltd."
SHORT_NAME = "GPSCB"
IFSC_PREFIX = "GPSC0"
# DataMeet's 2011 spelling -> the one people use
DISTRICT_NAMES = {"Ahmadabad": "Ahmedabad"}


def load(folder, name):
    with open(os.path.join(folder, name)) as f:
        return json.load(f)


# ---------- branches ----------

def build_branches(src):
    bank = load(src, "bank.json")
    bank.update({"bank_name": BANK_NAME, "short_name": SHORT_NAME})
    # The page is public: keep internal APAAR details (demo URL, tenant) out of the published data
    for k in ("source", "tenant_slug", "extracted_on"):
        bank.pop(k, None)
    branches = load(src, "branches.json")
    dep = {r["branch_code"]: r for r in load(src, "deposits_by_branch.json")}
    loan = {r["branch_code"]: r for r in load(src, "loans_by_branch.json")}
    lock = {r["branch_code"]: r for r in load(src, "lockers_by_branch.json")}
    with open(os.path.join(HERE, "branch_locations.csv")) as f:
        loc = {r["branch_code"]: r for r in csv.DictReader(f)}

    def pick(row, keys):
        return {k: row.get(k) for k in keys} if row else None

    out, unmapped = [], []
    for b in branches:
        code = b["branch_code"]
        rec = {
            "code": code,
            "dep": pick(dep.get(code), ["accounts", "customers", "deposits_cr", "current_balance_cr", "avg_rate_pct",
                                        "fd_count", "rd_count", "sb_count", "ca_count", "top_product", "top_product_amount_cr"]),
            "loan": pick(loan.get(code), ["accounts", "customers", "outstanding_cr", "npa_outstanding_cr", "npa_pct",
                                          "avg_rate_pct", "avg_ticket_lakh", "top_product"]),
            "lock": pick(lock.get(code), ["lockers", "dormant", "dormant_pct", "with_nominee", "with_nominee_pct",
                                          "fee_collected_lakh", "avg_vintage_years"]),
        }
        if code not in loc:  # 00555, 99933: tiny unnamed codes, kept only so totals match APAAR
            unmapped.append(rec)
            continue
        l = loc[code]
        is_ho = code == HEAD_OFFICE
        rec.update({
            "name": l["name"],
            "district": l["district"],
            "isHO": is_ho,
            "lat": float(l["lat"]),
            "lng": float(l["lng"]),
            "ifsc": IFSC_PREFIX + code.zfill(6),
            "address": l["locality"] + ", " + STATE,
        })
        out.append(rec)

    data = {"bank": bank, "asOn": bank["data_as_on"], "branches": out, "unmapped": unmapped}
    write_js("branches.js", "APAAR_DATA", data)
    return {b["district"] for b in out}


# ---------- boundaries ----------

def perp(p, a, b):
    (x, y), (x1, y1), (x2, y2) = p, a, b
    dx, dy = x2 - x1, y2 - y1
    if dx == dy == 0:
        return ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5
    return abs(dy * x - dx * y + x2 * y1 - y2 * x1) / (dx * dx + dy * dy) ** 0.5


def simplify(pts, tol):
    """Douglas-Peucker, iterative so long rings don't hit the recursion limit."""
    if len(pts) < 5:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop()
        best, idx = 0.0, None
        for k in range(i + 1, j):
            d = perp(pts[k], pts[i], pts[j])
            if d > best:
                best, idx = d, k
        if idx is not None and best > tol:
            keep[idx] = True
            stack += [(i, idx), (idx, j)]
    return [[round(x, 4), round(y, 4)] for (x, y), k in zip(pts, keep) if k]


def simplify_geom(g, tol, min_ring):
    polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
    res = []
    for poly in polys:
        rings = [simplify(r, tol) for r in poly]
        if len(rings[0]) >= min_ring:
            res.append([r for r in rings if len(r) >= 4])
    return {"type": "MultiPolygon", "coordinates": res}


def bbox(g):
    xs = [p[0] for poly in g["coordinates"] for r in poly for p in r]
    ys = [p[1] for poly in g["coordinates"] for r in poly for p in r]
    return [round(min(xs), 3), round(min(ys), 3), round(max(xs), 3), round(max(ys), 3)]


def label_point(g):
    """Centre of the largest ring's bounding box: good enough for a label."""
    ring = max((poly[0] for poly in g["coordinates"]), key=len)
    xs, ys = [p[0] for p in ring], [p[1] for p in ring]
    return [round((min(xs) + max(xs)) / 2, 4), round((min(ys) + max(ys)) / 2, 4)]


def build_geo(geo, branch_districts):
    states = load(geo, "states.geojson")
    dists = load(geo, "dists11.geojson")
    st = []
    for f in states["features"]:
        g = simplify_geom(f["geometry"], 0.03, 6)
        if g["coordinates"]:
            st.append({"type": "Feature", "properties": {"name": f["properties"]["ST_NM"]}, "geometry": g})
    mp_state = next(f for f in st if f["properties"]["name"] == STATE)

    ds, labels = [], []
    for f in dists["features"]:
        if f["properties"]["ST_NM"] != STATE:
            continue
        g = simplify_geom(f["geometry"], 0.006, 4)
        name = DISTRICT_NAMES.get(f["properties"]["DISTRICT"], f["properties"]["DISTRICT"])
        ds.append({"type": "Feature", "properties": {"name": name, "bbox": bbox(g)}, "geometry": g})
        labels.append({"type": "Feature", "properties": {"name": name},
                       "geometry": {"type": "Point", "coordinates": label_point(g)}})
    missing = branch_districts - {f["properties"]["name"] for f in ds}
    if missing:
        sys.exit("Districts with branches but no boundary: %s" % sorted(missing))

    write_js("geo.js", "APAAR_GEO", {
        "state": STATE,
        "stateBbox": bbox(mp_state["geometry"]),
        "states": {"type": "FeatureCollection", "features": st},
        "districts": {"type": "FeatureCollection", "features": ds},
        "labels": {"type": "FeatureCollection", "features": labels},
    })


def write_js(name, var, obj):
    path = os.path.join(OUT, name)
    with open(path, "w") as f:
        f.write("/* Generated by tools/build_data.py. Do not edit by hand. */\n")
        f.write("window.%s = %s;\n" % (var, json.dumps(obj, separators=(",", ":"), ensure_ascii=False)))
    print("%s  %.0f KB" % (path, os.path.getsize(path) / 1024))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    os.makedirs(OUT, exist_ok=True)
    build_geo(sys.argv[2], build_branches(sys.argv[1]))
