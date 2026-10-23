# Largest terrain: component_obs_044

Completed projected footprint: 77.20 m². Bounds: 11.40 × 11.60 m (not a full rectangle).

Use `closed/terrain_closed_m.obj` or `closed/terrain_closed_m.stl`, at metre scale 1. The export is a single closed solid with no open edges, nonmanifold vertices, or inconsistent winding. Both formats were read back and checked. Side walls and a flat base 0.25 m below the lowest top point are artificial.

31.0% of interior grid cells have observed-point support; the rest are interpolated. Maximum distance from an inferred grid cell to support: 2.42 m. The labels and distance array in `terrain_grids.npz` preserve that distinction.

This is a local terrain patch, not a global lunar map. Grid spacing is 5 cm, not a statement of accuracy. Per-frame gravity, acquisition motion, unseen obstacles, and absolute accuracy remain uncertain. Geometry is prepared for import; flight readiness and simulator collision behavior have not been demonstrated.
