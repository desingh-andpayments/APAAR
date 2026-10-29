# APAAR · Branch network map (design prototype)

An interactive 3D map for head-office users of **Gujarat Pragati State Cooperative Bank (GPSCB, demo bank)**. It opens on India, then flies to Gujarat, where the bank's branches are. Districts rise as 3D blocks: taller means more branches, darker means more business (or higher NPA for the Credit head). Click a district to zoom in. Click a branch and the camera glides down to street level, where each branch is a standing 3D bank icon whose roof colour shows the role's metric, and a card on the right shows the branch's identity (IFSC, code, address), while the left column switches to that branch's deposits, loans and lockers. The panel button (or the D key) hides the whole dashboard to show just the map.

This is a **design prototype** for the dev team: one HTML page plus data files. The look follows *APAAR · Compliance* (same tokens, fonts and light/dark themes). The layout follows the Chandigarh Transport Undertaking dashboard: full-screen map, cards on the left, controls on the right.

## Run it

```bash
node tools/serve.mjs        # → http://localhost:5288
```

Any static server works. Needs internet for the map tiles and the MapLibre library.

## What's in it

| Path | What it is |
| --- | --- |
| `index.html` | The whole prototype: styles, map and interactions |
| `data/branches.js` | Branches with deposits, loans and lockers, built from the APAAR demo export (as on 31 May 2026) |
| `data/geo.js` | India state outlines and Gujarat district outlines, simplified |
| `tools/build_data.py` | Rebuilds both data files: `python3 tools/build_data.py <apaar-demo-data/json> <folder with states.geojson + dists11.geojson>` |
| `assets/bank.svg` | The bank icon. Its roof colours (`#F6D13A`, `#F08700`, `#F3AE00`) are swapped at runtime for the branch's colour step |
| `tools/branch_locations.csv` | **Demo** coordinates and addresses for each branch (town centres) |

## Roles (switch with the top-right menu)

| Role | Sees | Map colour |
| --- | --- | --- |
| MD & Chairman | All branches: deposits, loans, lockers. Can edit branch details | Total business |
| Credit head | All branches: loans and NPA only | Gross NPA % |
| Deposits & Treasury head | All branches: deposits only | Deposit balance |
| Branch manager (Gandhinagar, 00004) | Only their branch; others greyed out with no data | Own branch only |

**For the dev team:** the prototype hides data on screen, which is not security. In APAAR the server must send each user only the data their role allows. A branch user's browser must never receive other branches' figures. Edits should go through maker-checker, with an audit log.

## How the map works (for learning)

- **MapLibre GL JS 5.6** (BSD-3) draws the map. It handles the smooth zoom from the whole country down to street level.
- **Camera:** every view is a center, zoom, pitch (tilt) and bearing (rotation). `flyTo` animates between two views. The intro shows India for a moment, then flies to the state and waits for that move to end before showing the cards.
- **Fast start:** the page starts on MapLibre's `style.load` (the style file, ~0.1 s), not `load` (every tile, 5–10 s on a first visit). India is drawn from our local boundary file, so it appears at once while basemap tiles stream in under a thin progress line.
- **Layers** are drawn from GeoJSON: district fills, 3D district blocks (`fill-extrusion`, height = √branches × 10 km, fading out as you zoom in), district labels on pills, branch dots, standing bank icons from zoom 10 (a `symbol` layer, viewport-aligned so they always face the viewer), and a thin state edge in a darker shade of the state's fill.
- **Colour:** soft pastel, chosen with design. Branch districts use 3 lavender levels (light `#D6DAF5 #B9BFEE #959DE2`, dark `#3A4070 #4E5694 #6971BE`); NPA uses APAAR's soft status colours (`#9AD3A8 #EBC26E #E8968F`); Gujarat is soft lime in the India view and a white surface after, edged in a darker shade of its own fill; everything outside Gujarat is neutral grey. Fills are deliberately below WCAG 1.4.11's 3:1, so values are always also on a pill (text 4.5:1+) and branch dots stay strong (4.5:1+). Bank roofs use a deeper shade of the same level. City labels: capitals and OpenMapTiles rank 1–4 only (`CITY_RANK` in `index.html`).
- **Basemap (production note):** the free OpenFreeMap server sends 250–650 KB per tile at India zoom. For APAAR, self-host a Protomaps PMTiles file on the bank's own server/CDN.
- **Basemap:** OpenFreeMap "positron" vector tiles (free, no key), recoloured from the APAAR tokens and decluttered: no buildings, villages, towns, highway numbers, rail or minor roads; major roads appear only from zoom 10. OSM borders are hidden; India is drawn from DataMeet's boundaries instead.

## Data notes

- All figures are demo data from the APAAR export. They are shown as-is, including oddities such as negative balances and a 183% rate at the head office.
- **Relocated for the demo:** the export's bank ("Rajasthan Pragati…", branches in Madhya Pradesh towns) is shown as Gujarat Pragati State Cooperative Bank. Each branch code keeps its own figures; its town, district, address and coordinates are real Gujarat places from `tools/branch_locations.csv`. Localities are made up.
- **Placeholders**, not in the export: IFSC (`GPSC0` + code), addresses, coordinates, manager and phone.
- `00001` is shown as the **Head Office** in Ahmedabad. `00555` and `99933` have no name; they are left off the map but counted in state totals, so totals match APAAR.
- District boundaries are DataMeet's 2011 census set (26 Gujarat districts; Gujarat has 33 today). Before production, use Survey of India boundaries and the current district list.

## Credits

MapLibre GL JS (BSD-3) · OpenFreeMap / OpenMapTiles / © OpenStreetMap contributors (ODbL) · Natural Earth relief (public domain) · DataMeet boundaries (CC BY) · Outfit and Inter fonts (OFL)
