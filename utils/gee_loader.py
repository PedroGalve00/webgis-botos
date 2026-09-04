import ee
import pandas as pd
import streamlit as st
import time as time_module
from datetime import datetime

def init_gee(secrets=None):
    try:
        if secrets and "GEE_SERVICE_ACCOUNT" in secrets:
            creds = ee.ServiceAccountCredentials(
                secrets["GEE_SERVICE_ACCOUNT"],
                key_data=secrets["GEE_PRIVATE_KEY"]
            )
            ee.Initialize(creds)
        else:
            ee.Initialize(project="pedrogalve")
    except Exception as e:
        st.error(f"Erro GEE: {e}")
        st.stop()

def get_latest_date():
    col = ee.ImageCollection("MODIS/061/MOD11A2").sort("system:time_start", False)
    latest = col.first()
    date = ee.Date(latest.get("system:time_start"))
    info = date.getInfo()
    ts = info["value"] / 1000
    dt = datetime.utcfromtimestamp(ts)
    return dt.year, dt.month

def modis_temperature(image):
    lst = image.select("LST_Day_1km").multiply(0.02).subtract(273.15).rename("surface_temperature")
    return image.addBands(lst)

def corrections_landsat(image):
    optical = image.select("SR_B.*").multiply(0.0000275).add(-0.2)
    thermal = image.select("ST_B.*").multiply(0.00341802).add(149.0)
    image = image.addBands(optical, None, True).addBands(thermal, None, True)
    qa = image.select("QA_PIXEL")
    cloud = qa.bitwiseAnd(1 << 3).Or(qa.bitwiseAnd(1 << 4))
    image = image.updateMask(cloud.Not())
    lst = image.select("ST_B10").subtract(273.15).rename("surface_temperature")
    return image.addBands(lst)

def get_tile_url(image, vis_params):
    map_id = image.getMapId(vis_params)
    return map_id["tile_fetcher"].url_format

def get_feature(name, asset_id, name_field="name"):
    """Busca feature por nome — tenta variantes com xa0 e espaco normal."""
    fc = ee.FeatureCollection(asset_id)
    # 1. Busca direta
    result = fc.filter(ee.Filter.eq(name_field, name))
    if result.size().getInfo() > 0:
        return result
    # 2. Troca espaco normal por xa0
    name_xa0 = name.replace(" ", "\xa0")
    result = fc.filter(ee.Filter.eq(name_field, name_xa0))
    if result.size().getInfo() > 0:
        return result
    # 3. Remove xa0
    name_clean = name.replace("\xa0", " ").strip()
    result = fc.filter(ee.Filter.eq(name_field, name_clean))
    if result.size().getInfo() > 0:
        return result
    # 4. Busca por similaridade
    all_names = fc.aggregate_array(name_field).getInfo()
    name_norm = name.replace("\xa0", " ").strip().lower()
    for n in all_names:
        if n and name_norm in str(n).replace("\xa0", " ").lower():
            return fc.filter(ee.Filter.eq(name_field, n))
    return result

def get_tocantins_names(asset_id):
    """
    Carrega nomes do asset Tocantins-Araguaia.
    Retorna lista de nomes para display (sem xa0)
    e um dict mapeando display -> nome real no asset.
    """
    try:
        fc = ee.FeatureCollection(asset_id)
        names = fc.aggregate_array("Name").getInfo()
        result = []
        for n in names:
            if n:
                result.append(str(n))
        return sorted(result)
    except Exception as e:
        return []

def get_tocantins_display_names(asset_id):
    """Retorna dict: nome_display -> nome_real (com xa0 se necessario)."""
    try:
        fc = ee.FeatureCollection(asset_id)
        names = fc.aggregate_array("Name").getInfo()
        mapping = {}
        for n in names:
            if n:
                display = str(n).replace("\xa0", " ").strip()
                mapping[display] = str(n)
        return mapping
    except:
        return {}

def _safe_geometry(feat_collection):
    """
    Extrai geometria valida de uma FeatureCollection.
    Trata GeometryCollection extraindo o Polygon interno.
    """
    try:
        info = feat_collection.first().getInfo()
        raw  = info.get("geometry", {})
        gtype = raw.get("type", "")

        if gtype == "GeometryCollection":
            geoms = raw.get("geometries", [])
            # Prioridade: Polygon > MultiPolygon > LineString > qualquer outro
            for priority in ("Polygon", "MultiPolygon", "LineString",
                             "MultiLineString", "Point"):
                for g in geoms:
                    if g.get("type") == priority and g.get("coordinates"):
                        geom_ee = ee.Geometry(g)
                        return geom_ee, geom_ee.bounds()
            # Fallback: usa geometria do GEE
            geom = feat_collection.geometry()
            return geom, geom.bounds()

        elif gtype in ("Polygon","MultiPolygon","LineString",
                       "MultiLineString","Point"):
            geom_ee = ee.Geometry(raw)
            return geom_ee, geom_ee.bounds()

        else:
            geom = feat_collection.geometry()
            return geom, geom.bounds()

    except Exception as e:
        geom = feat_collection.geometry()
        return geom, geom.bounds()

def get_sentinel_tile(name, asset_id, start, end, name_field="name"):
    feat = get_feature(name, asset_id, name_field)
    _, bounds = _safe_geometry(feat)
    def mask_clouds(img):
        prob = img.select("MSK_CLDPRB").eq(0)
        scl = img.select("SCL")
        mask = prob.And(scl.neq(3)).And(scl.neq(10))
        return img.updateMask(mask)
    col = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
           .filterDate(start, end)
           .filterBounds(bounds)
           .map(mask_clouds)
           .median())
    vis = {"bands": ["B11", "B8", "B4"], "min": 155, "max": 4920, "gamma": 1}
    geom_safe, _ = _safe_geometry(feat)
    centroid = geom_safe.centroid().getInfo()["coordinates"]
    return get_tile_url(col, vis), centroid

def get_modis_tile(name, asset_id, start, end, name_field="name"):
    feat = get_feature(name, asset_id, name_field)
    _, bounds = _safe_geometry(feat)
    col = (ee.ImageCollection("MODIS/061/MOD11A2")
           .filterDate(start, end)
           .filterBounds(bounds)
           .map(modis_temperature)
           .select("surface_temperature")
           .median())
    vis = {"min": "15", "max": "35", "palette": "blue,green,yellow,orange,red"}
    return get_tile_url(col, vis)

def get_landsat_tile(name, asset_id, start, end, name_field="name"):
    feat = get_feature(name, asset_id, name_field)
    _, bounds = _safe_geometry(feat)
    col = (ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
           .merge(ee.ImageCollection("LANDSAT/LC08/C02/T1_L2"))
           .filterDate(start, end)
           .filterBounds(bounds)
           .map(corrections_landsat)
           .select("surface_temperature")
           .median())
    vis = {"min": "15", "max": "35", "palette": "blue,green,yellow,orange,red"}
    return get_tile_url(col, vis)

def get_focos_tiles(year, month):
    focos = ee.ImageCollection("NASA/LANCE/SNPP_VIIRS/C2")
    start1 = ee.Date.fromYMD(year, month, 1)
    mid    = start1.advance(15, "day")
    end1   = start1.advance(1, "month")
    img1 = focos.filterDate(start1, mid).select("confidence").max().gte(1).selfMask()
    img2 = focos.filterDate(mid, end1).select("confidence").max().gte(1).selfMask()
    url1 = get_tile_url(img1, {"palette": "ff0000"})
    url2 = get_tile_url(img2, {"palette": "ffaa00"})
    return url1, url2

def get_monthly_temperature(name, asset_id, ano_base, ref_year, ref_month, name_field="name"):
    """Busca temp mensal para anos: ano_base, ref_year-1, ref_year."""
    feat = get_feature(name, asset_id, name_field)
    geom = feat.geometry()
    anos = sorted(set([ano_base, ref_year - 1, ref_year]))
    if ref_year - 1 == ano_base:
        anos = [ano_base, ref_year]
    records = []
    for year in anos:
        lim = ref_month if year == ref_year else 12
        for month in range(1, lim + 1):
            start = f"{year}-{month:02d}-01"
            nm = month % 12 + 1
            ny = year + 1 if month == 12 else year
            end = f"{ny}-{nm:02d}-01"
            try:
                col = (ee.ImageCollection("MODIS/061/MOD11A2")
                       .filterDate(start, end)
                       .filterBounds(geom)
                       .map(modis_temperature)
                       .select("surface_temperature")
                       .mean())
                val = col.reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=geom, scale=1000, maxPixels=1e13
                ).get("surface_temperature").getInfo()
                records.append({"ano": year, "mes": month,
                                 "temperatura": round(val, 2) if val else None})
            except:
                records.append({"ano": year, "mes": month, "temperatura": None})
    return pd.DataFrame(records)

def get_temp_stats(name, asset_id, sel_year, sel_month, name_field="name"):
    """Temperatura do mes selecionado, ano anterior e media historica."""
    feat = get_feature(name, asset_id, name_field)
    geom = feat.geometry()
    def get_temp(year, month):
        start = f"{year}-{month:02d}-01"
        nm = month % 12 + 1
        ny = year + 1 if month == 12 else year
        end = f"{ny}-{nm:02d}-01"
        try:
            col = (ee.ImageCollection("MODIS/061/MOD11A2")
                   .filterDate(start, end).filterBounds(geom)
                   .map(modis_temperature).select("surface_temperature").mean())
            val = col.reduceRegion(
                reducer=ee.Reducer.mean(), geometry=geom,
                scale=1000, maxPixels=1e13
            ).get("surface_temperature").getInfo()
            return round(val, 2) if val else None
        except:
            return None
    t_atual = get_temp(sel_year, sel_month)
    t_prev  = get_temp(sel_year - 1, sel_month)
    hist = [get_temp(y, sel_month) for y in range(sel_year - 3, sel_year)]
    hist = [v for v in hist if v]
    t_hist = round(sum(hist) / len(hist), 2) if hist else None
    return t_atual, t_prev, t_hist

def get_focos_count_periodo(name, buffer_asset, dist_m, year, month,
                             name_field="name", dynamic=False, geom_src=None):
    """Conta focos num mes/ano. Se dynamic=True usa buffer calculado."""
    try:
        if dynamic and geom_src is not None:
            geom = geom_src.buffer(dist_m)
        else:
            buffers = ee.FeatureCollection(buffer_asset)
            geom = (buffers.filter(ee.Filter.eq("name", name))
                           .filter(ee.Filter.eq("dist_m", dist_m))
                           .geometry())
        start_ee = ee.Date.fromYMD(year, month, 1)
        end_ee   = start_ee.advance(1, "month")
        focos = ee.ImageCollection("NASA/LANCE/SNPP_VIIRS/C2").filterDate(start_ee, end_ee)
        if focos.size().getInfo() == 0:
            return 0
        def count_img(img):
            conf = img.select("confidence").gte(1).selfMask()
            n = conf.reduceRegion(
                reducer=ee.Reducer.count(),
                geometry=geom, scale=375, maxPixels=1e13, tileScale=2
            ).get("confidence")
            return img.set("count", ee.Algorithms.If(n, n, 0))
        total = focos.map(count_img).aggregate_sum("count").getInfo()
        return int(total) if total else 0
    except:
        return 0

def get_monthly_focos(name, buffer_asset, dist_m, ano_base, ref_year, ref_month,
                       name_field="name", dynamic=False, geom_src=None):
    """Focos mensais para anos: ano_base, ref_year-1, ref_year."""
    anos = sorted(set([ano_base, ref_year - 1, ref_year]))
    if ref_year - 1 == ano_base:
        anos = [ano_base, ref_year]
    records = []
    for year in anos:
        lim = ref_month if year == ref_year else 12
        for month in range(1, lim + 1):
            val = get_focos_count_periodo(
                name, buffer_asset, dist_m, year, month,
                name_field=name_field, dynamic=dynamic, geom_src=geom_src)
            records.append({"ano": year, "mes": month, "focos": val})
    return pd.DataFrame(records)

def get_ranking_temperatura(lagos, asset_id, sel_year, sel_month, name_field="name"):
    rows = []
    for name in lagos:
        try:
            t_a, t_p, t_h = get_temp_stats(name, asset_id, sel_year, sel_month, name_field)
            rows.append({
                "Lago": name,
                "Temp atual (C)":  round(t_a, 2) if t_a else None,
                "Media historica": round(t_h, 2) if t_h else None,
                f"Dif {sel_year-1}": round(t_a - t_p, 2) if t_a and t_p else None,
                "Dif media":       round(t_a - t_h, 2) if t_a and t_h else None,
            })
        except:
            rows.append({"Lago": name, "Temp atual (C)": None,
                         "Media historica": None,
                         f"Dif {sel_year-1}": None, "Dif media": None})
    return pd.DataFrame(rows)

def get_ranking_focos_periodo(lagos, buffer_asset, year, month,
                               dynamic_names=None, tocantins_asset=None):
    rows = []
    dynamic_names = dynamic_names or []
    for name in lagos:
        try:
            is_dynamic = name in dynamic_names
            geom_src = None
            if is_dynamic and tocantins_asset:
                feat = get_feature(name, tocantins_asset, "Name")
                geom_src = feat.geometry()
            f5  = get_focos_count_periodo(name, buffer_asset, 5000,  year, month,
                                           dynamic=is_dynamic, geom_src=geom_src)
            f10 = get_focos_count_periodo(name, buffer_asset, 10000, year, month,
                                           dynamic=is_dynamic, geom_src=geom_src)
            rows.append({"Lago": name, "Focos 5km": f5, "Focos 10km": f10})
        except:
            rows.append({"Lago": name, "Focos 5km": None, "Focos 10km": None})
    return pd.DataFrame(rows)
