# -*- coding: utf-8 -*-
"""生成 3D 地球陆地散点数据：下载世界 GeoJSON，网格采样陆地点，输出 JS 数组"""
import base64
import json
import math
import os
import urllib.request

with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "deploy.local.json"), encoding="utf-8") as f:
    PAT = json.load(f)["github_pat"]
URL = "https://api.github.com/repos/johan/world.geo.json/contents/countries.geo.json"

req = urllib.request.Request(URL)
req.add_header("Authorization", "Bearer " + PAT)
req.add_header("Accept", "application/vnd.github.raw")
gj = json.loads(urllib.request.urlopen(req).read())
print("features:", len(gj["features"]))


def polygons_of(feature):
    g = feature["geometry"]
    if g["type"] == "Polygon":
        return [g["coordinates"]]
    if g["type"] == "MultiPolygon":
        return g["coordinates"]
    return []


def point_in_ring(x, y, ring):
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            inside = not inside
        j = i
    return inside


def point_in_poly(x, y, poly):
    if not point_in_ring(x, y, poly[0]):
        return False
    for hole in poly[1:]:
        if point_in_ring(x, y, hole):
            return False
    return True


polys = []
for f in gj["features"]:
    for p in polygons_of(f):
        xs = [pt[0] for pt in p[0]]
        ys = [pt[1] for pt in p[0]]
        polys.append((min(xs), min(ys), max(xs), max(ys), p))
print("polygons:", len(polys))

STEP = 1.1
points = []
lat = -85.0
while lat <= 85.0:
    lon_step = STEP / max(math.cos(math.radians(lat)), 0.08)
    lon = -180.0
    while lon <= 180.0:
        for x0, y0, x1, y1, p in polys:
            if x0 <= lon <= x1 and y0 <= lat <= y1 and point_in_poly(lon, lat, p):
                points.append([round(lon, 1), round(lat, 1)])
                break
        lon += lon_step
    lat += STEP

print("land points:", len(points))
# 抽稀：约 2400 点足够呈现大陆轮廓且体积小
points = points[::4]
print("thinned:", len(points))
with open(r"C:/Users/Lenovo/Desktop/wuliu-logistics/frontend_template/src/globeData.js", "w", encoding="utf-8") as f:
    f.write("// 世界陆地散点（由 countries.geojson 网格采样生成）\n")
    f.write("export default " + json.dumps(points, separators=(",", ",")).replace("],[", "],[") + "\n")
print("done")
