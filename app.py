import streamlit as st
import ee
import folium
from streamlit_folium import st_folium
from config import (GRUPOS, LAGO_INICIAL, GRUPO_INICIAL, TEMAS,
                    ASSETS, CORES, ANO_BASE, LOGO_WWF)
from utils.gee_loader import (
    init_gee, get_latest_date, get_tocantins_names, get_tocantins_display_names,
    get_sentinel_tile, get_modis_tile, get_landsat_tile, get_focos_tiles,
    get_monthly_temperature, get_temp_stats,
    get_focos_count_periodo, get_monthly_focos,
    get_ranking_temperatura, get_ranking_focos_periodo, get_feature
)
from utils.charts import (
    grafico_temperatura, grafico_anomalia, grafico_boxplot,
    grafico_focos, grafico_acumulado,
    colorir_temp, colorir_dif, colorir_focos
)

st.set_page_config(
    page_title="Monitoramento Lagos Amazonicos",
    page_icon=LOGO_WWF if LOGO_WWF else "🐬",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: #f7f9fc; }
  [data-testid="stSidebar"] { background: #ffffff; border-right: 1px solid #e0e6ed; }
  [data-testid="stSidebar"] * { color: #1a237e !important; }
  [data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: #f0f4ff !important; border: 1px solid #90a4ae !important;
    border-radius: 6px !important; }
  [data-testid="stSidebar"] [data-baseweb="select"] * { color: #1a237e !important; }
  [data-testid="stSidebar"] [role="listbox"] { background: #ffffff !important; }
  [data-testid="stSidebar"] [role="option"] { color: #1a237e !important; }
  [data-testid="stSidebar"] [role="option"]:hover { background: #e8eaf6 !important; }
  [data-testid="stSidebar"] .stCheckbox span { color: #1a237e !important; }
  [data-testid="stSidebar"] hr { border-color: #e0e6ed !important; }
  .hdr {
    background: linear-gradient(135deg, #1565c0 0%, #0d47a1 60%, #283593 100%);
    padding: 14px 22px; border-radius: 10px; margin-bottom: 18px;
    display: flex; align-items: center; justify-content: space-between;
    box-shadow: 0 2px 8px rgba(21,101,192,0.18);
  }
  .hdr-title { color:#fff; font-size:1.22rem; font-weight:800; letter-spacing:.3px; }
  .hdr-sub   { color:#bbdefb; font-size:0.80rem; margin-top:3px; }
  .hdr-date  { background:rgba(255,255,255,0.12); color:#fff; border-radius:8px;
               padding:8px 14px; font-size:0.82rem; text-align:right; min-width:120px; }
  .mcard {
    background:#ffffff; border-radius:10px; padding:14px 16px;
    border-left:4px solid #1565c0;
    box-shadow:0 1px 4px rgba(0,0,0,0.07); margin-bottom:8px;
  }
  .mcard-val  { font-size:1.7rem; font-weight:800; color:#1565c0; }
  .mcard-red  { color:#e53935 !important; }
  .mcard-blue { color:#1565c0 !important; }
  .mcard-lbl  { font-size:0.76rem; color:#546e7a; margin-top:3px; }
  .sec-title {
    font-size:0.92rem; font-weight:700; color:#1565c0;
    border-bottom:2px solid #1565c0;
    padding-bottom:4px; margin-bottom:12px; letter-spacing:.3px;
  }
  .alerta     { background:#fff8e1; border-left:4px solid #fb8c00;
                border-radius:6px; padding:10px 14px; color:#e65100;
                font-size:0.9rem; margin-top:6px; }
  .alerta-red { background:#ffebee; border-left:4px solid #e53935;
                border-radius:6px; padding:10px 14px; color:#b71c1c;
                font-size:0.9rem; margin-top:6px; }
  .map-leg { background:#f7f9fc; border:1px solid #e0e6ed; border-radius:8px;
              padding:10px 14px; margin-top:8px; font-size:0.82rem; color:#37474f; }
  .leg-row { display:flex; align-items:center; gap:8px; margin:4px 0; }
  .leg-dot { width:12px; height:12px; border-radius:50%; flex-shrink:0; }
  div[data-testid="stTabs"] button { color:#546e7a !important; font-size:0.9rem; }
  div[data-testid="stTabs"] button[aria-selected="true"] {
    color:#1565c0 !important; border-bottom:2px solid #1565c0 !important;
    font-weight:700 !important; }
  div[data-testid="stButton"] > button {
    background:#1565c0; color:white; border:none;
    border-radius:7px; font-weight:600; padding:7px 18px; }
  div[data-testid="stButton"] > button:hover { background:#0d47a1; }
</style>
""", unsafe_allow_html=True)

# ── GEE INIT ─────────────────────────────────────────────────
@st.cache_resource
def iniciar_gee():
    try:
        init_gee(dict(st.secrets) if "GEE_SERVICE_ACCOUNT" in st.secrets else None)
    except:
        init_gee()

iniciar_gee()

@st.cache_data(ttl=86400)
def obter_data():
    return get_latest_date()

@st.cache_data(ttl=86400)
def obter_tocantins():
    return get_tocantins_names(ASSETS["tocantins"])

@st.cache_data(ttl=86400)
def obter_tocantins_display():
    """Retorna dict display_name -> nome_real para Tocantins."""
    return get_tocantins_display_names(ASSETS["tocantins"])

# ── VARIAVEIS GLOBAIS ─────────────────────────────────────────
current_year, current_month = obter_data()
MESES = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
tocantins_names = obter_tocantins()
tocantins_display_map = obter_tocantins_display()
# Usa nomes com display limpo (sem xa0) para o selectbox
tocantins_display_names = sorted([
    n.replace("\xa0", " ").strip() for n in tocantins_names if n
])
GRUPOS["Tocantins-Araguaia"] = tocantins_display_names

# ── HEADER ───────────────────────────────────────────────────
st.markdown(
    f'''<div class="hdr">
      <img src="{LOGO_WWF}" style="height:54px;margin-right:16px">
      <div style="flex:1">
        <div class="hdr-title">Monitoramento de Lagos Amazonicos</div>
        <div class="hdr-sub">Sistema de alerta precoce para mortalidade de botos — WWF Brasil</div>
      </div>
      <div class="hdr-date">
        Ultimo dado MODIS<br>
        <b style="font-size:1rem">{MESES[current_month-1]}/{current_year}</b>
      </div>
    </div>''',
    unsafe_allow_html=True)

# ── SIDEBAR ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Controles")
    grupo_sel = st.selectbox("Grupo de areas", list(GRUPOS.keys()),
                              index=list(GRUPOS.keys()).index(GRUPO_INICIAL))
    lagos_do_grupo = GRUPOS[grupo_sel]
    is_tocantins   = (grupo_sel == "Tocantins-Araguaia")
    name_field     = "Name" if is_tocantins else "name"
    asset_lagos    = ASSETS["tocantins"] if is_tocantins else ASSETS["lagos"]

    idx_inicial = 0
    if not is_tocantins and LAGO_INICIAL in lagos_do_grupo:
        idx_inicial = lagos_do_grupo.index(LAGO_INICIAL)
    lago_sel_display = st.selectbox(
        "Area monitorada" if is_tocantins else "Lago monitorado",
        lagos_do_grupo if lagos_do_grupo else ["Carregando..."],
        index=idx_inicial)
    # Para Tocantins: converte display -> nome real no asset (com xa0)
    if is_tocantins:
        lago_sel = tocantins_display_map.get(lago_sel_display, lago_sel_display)
    else:
        lago_sel = lago_sel_display
    tema_sel = st.selectbox("Tema de analise", TEMAS)
    st.divider()

    datas = []
    for y in range(2023, current_year + 1):
        lim = current_month if y == current_year else 12
        for m in range(1, lim + 1):
            datas.append(f"{y}-{m:02d}")
    data_sel  = st.selectbox("Periodo das imagens", list(reversed(datas)))
    year_sel  = int(data_sel[:4])
    month_sel = int(data_sel[5:])
    start_str = f"{year_sel}-{month_sel:02d}-01"
    nm = month_sel % 12 + 1
    ny = year_sel + 1 if month_sel == 12 else year_sel
    end_str = f"{ny}-{nm:02d}-01"

    st.divider()
    st.markdown("### Camadas do mapa")
    if tema_sel == "Temperatura":
        cam_s2      = st.checkbox("Sentinel-2 (RGB)",    value=True)
        cam_modis   = st.checkbox("MODIS Temperatura",   value=True)
        cam_landsat = st.checkbox("Landsat Temperatura", value=False)
        cam_contorno= st.checkbox("Contorno da area",    value=True)
    else:
        cam_s2       = st.checkbox("Sentinel-2 (RGB)",   value=True)
        cam_f07      = st.checkbox("Focos 0-14 dias",    value=True)
        cam_f714     = st.checkbox("Focos 14-30 dias",   value=True)
        cam_contorno = st.checkbox("Contorno da area",   value=True)

    st.divider()
    if st.button("Atualizar dados"):
        st.cache_data.clear()
        st.rerun()
    st.markdown("""
    <div style="font-size:0.75rem;color:#78909c;line-height:1.7;margin-top:8px">
      <b style="color:#37474f">Fontes de dados</b><br>
      MODIS Terra (LST)<br>Sentinel-2 SR<br>Landsat 8/9 C2<br>VIIRS/SNPP (focos)<br><br>
      <b style="color:#37474f">Desenvolvido por</b><br>
      Pedro Galve<br>Juliano Schirmbeck<br><br>
      © WWF Brasil
    </div>""", unsafe_allow_html=True)

# ── Geometria Tocantins ───────────────────────────────────────
geom_tocantins = None
if is_tocantins and lago_sel and lago_sel != "Carregando...":
    try:
        feat_toc = get_feature(lago_sel, asset_lagos, name_field)
        geom_tocantins = feat_toc.geometry()
    except:
        geom_tocantins = None

# ── LAYOUT PRINCIPAL ──────────────────────────────────────────
col_mapa, col_graf = st.columns([55, 45])

with col_mapa:
    st.markdown(
        f'''<div class="sec-title">Mapa — {lago_sel} · {tema_sel} · {MESES[month_sel-1]}/{year_sel}</div>''',
        unsafe_allow_html=True)

    @st.cache_data(ttl=3600)
    def carregar_urls_temp(lago, start, end, nf, asset):
        s_url, centroid = get_sentinel_tile(lago, asset, start, end, nf)
        m_url = get_modis_tile(lago, asset, start, end, nf)
        l_url = get_landsat_tile(lago, asset, start, end, nf)
        return list(reversed(centroid)), {"s":s_url,"m":m_url,"l":l_url}

    def carregar_urls_focos(lago, start, end, nf, asset, yr, mo):
        s_url, centroid = get_sentinel_tile(lago, asset, start, end, nf)
        u1, u2 = get_focos_tiles(yr, mo)
        return list(reversed(centroid)), {"s":s_url,"f1":u1,"f2":u2}

    with st.spinner("Carregando imagens do GEE..."):
        try:
            if tema_sel == "Temperatura":
                coords, urls = carregar_urls_temp(
                    lago_sel, start_str, end_str, name_field, asset_lagos)
            else:
                coords, urls = carregar_urls_focos(
                    lago_sel, start_str, end_str, name_field, asset_lagos,
                    year_sel, month_sel)
        except Exception as e:
            st.error(f"Erro ao carregar imagens: {e}")
            coords, urls = [-3.5, -62.0], {}

    m = folium.Map(location=coords, zoom_start=10, tiles="CartoDB positron")

    if tema_sel == "Temperatura":
        if cam_s2 and "s" in urls:
            folium.TileLayer(tiles=urls["s"], attr="GEE",
                name="Sentinel-2", overlay=True, opacity=0.9).add_to(m)
        if cam_modis and "m" in urls:
            folium.TileLayer(tiles=urls["m"], attr="GEE",
                name="MODIS Temperatura", overlay=True, opacity=0.8).add_to(m)
        if cam_landsat and "l" in urls:
            folium.TileLayer(tiles=urls["l"], attr="GEE",
                name="Landsat Temperatura", overlay=True, opacity=0.8).add_to(m)
    else:
        if cam_s2 and "s" in urls:
            folium.TileLayer(tiles=urls["s"], attr="GEE",
                name="Sentinel-2", overlay=True, opacity=0.9).add_to(m)
        if cam_f07 and "f1" in urls:
            folium.TileLayer(tiles=urls["f1"], attr="GEE",
                name="Focos 0-14 dias", overlay=True, opacity=1.0).add_to(m)
        if cam_f714 and "f2" in urls:
            folium.TileLayer(tiles=urls["f2"], attr="GEE",
                name="Focos 14-30 dias", overlay=True, opacity=1.0).add_to(m)

    if cam_contorno:
        try:
            fc_ee = ee.FeatureCollection(asset_lagos)
            gj = fc_ee.filter(ee.Filter.eq(name_field, lago_sel)).getInfo()
            features_validas = [
                f for f in gj.get("features", [])
                if f.get("geometry") and f["geometry"].get("coordinates")
                and f["geometry"]["coordinates"]
            ]
            if features_validas:
                gj_valido = {"type":"FeatureCollection","features":features_validas}
                lago_geom = features_validas[0]["geometry"]
                world_ring = [[-180,-90],[180,-90],[180,90],[-180,90],[-180,-90]]
                mask = None
                geom_tipo = lago_geom.get("type","")
                try:
                    if geom_tipo == "Polygon":
                        ring = lago_geom["coordinates"][0]
                        if ring and len(ring) > 2:
                            mask = {"type":"Feature","geometry":{
                                "type":"Polygon",
                                "coordinates":[world_ring, ring]}}
                    elif geom_tipo == "MultiPolygon":
                        aneis = [p[0] for p in lago_geom["coordinates"]
                                 if p and p[0] and len(p[0]) > 2]
                        if aneis:
                            maior = max(aneis, key=len)
                            mask = {"type":"Feature","geometry":{
                                "type":"Polygon",
                                "coordinates":[world_ring, maior]}}
                except:
                    mask = None
                if mask:
                    folium.GeoJson(mask, style_function=lambda x: {
                        "color":"transparent","weight":0,
                        "fillColor":"#000000","fillOpacity":0.35}).add_to(m)
                def estilo_contorno(feature):
                    tipo = feature.get("geometry",{}).get("type","")
                    if tipo in ("LineString","MultiLineString"):
                        return {"color":"#FF1493","weight":3,"opacity":0.9}
                    elif tipo == "Point":
                        return {"color":"#FF1493","weight":2}
                    else:
                        return {"color":"#FF1493","weight":2.5,
                                "dashArray":"5 4","fillOpacity":0.0}
                folium.GeoJson(gj_valido, name="Contorno",
                    style_function=estilo_contorno).add_to(m)
        except Exception as e:
            st.caption(f"Contorno indisponivel: {e}")

    folium.LayerControl(collapsed=False).add_to(m)
    st_folium(m, height=460, use_container_width=True)

    if tema_sel == "Temperatura":
        st.markdown("""
        <div class="map-leg"><b>Legenda</b>
          <div class="leg-row">
            <div class="leg-dot" style="background:#FF1493;border:1.5px dashed #555"></div>
            Contorno da area (tracejado rosa)
          </div>
          <div class="leg-row">
            <div style="background:linear-gradient(90deg,blue,green,yellow,orange,red);
                 width:80px;height:10px;border-radius:3px;flex-shrink:0"></div>
            Temperatura: 15C (frio) a 35C (quente)
          </div>
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="map-leg"><b>Legenda</b>
          <div class="leg-row">
            <div class="leg-dot" style="background:#FF1493;border:1.5px dashed #555"></div>
            Contorno da area
          </div>
          <div class="leg-row">
            <div class="leg-dot" style="background:#ff0000"></div>
            Focos — primeiros 14 dias do mes
          </div>
          <div class="leg-row">
            <div class="leg-dot" style="background:#ffaa00"></div>
            Focos — ultimos 16 dias do mes
          </div>
        </div>""", unsafe_allow_html=True)

with col_graf:
    if tema_sel == "Temperatura":
        st.markdown('<div class="sec-title">Analise de temperatura</div>',
                    unsafe_allow_html=True)

        @st.cache_data(ttl=3600)
        def load_temp(lago, nf, asset, cy, cm):
            return get_monthly_temperature(lago, asset, ANO_BASE, cy, cm, nf)

        @st.cache_data(ttl=3600)
        def load_stats(lago, nf, asset, sy, sm):
            return get_temp_stats(lago, asset, sy, sm, nf)

        with st.spinner("Calculando temperatura..."):
            df_t = load_temp(lago_sel, name_field, asset_lagos,
                             current_year, current_month)
            t_a, t_p, t_h = load_stats(lago_sel, name_field, asset_lagos,
                                        year_sel, month_sel)

        c1, c2, c3 = st.columns(3)
        with c1:
            v = f"{t_a:.1f} C" if t_a else "s/d"
            st.markdown(f'''<div class="mcard">
              <div class="mcard-val">{v}</div>
              <div class="mcard-lbl">Temp. atual ({MESES[month_sel-1]}/{year_sel})</div>
            </div>''', unsafe_allow_html=True)
        with c2:
            if t_a and t_p:
                d = round(t_a-t_p,2)
                cls = "mcard-red" if d>1 else "mcard-blue"
                v2 = f"+{d} C" if d>0 else f"{d} C"
            else:
                cls, v2 = "mcard-blue", "s/d"
            st.markdown(f'''<div class="mcard">
              <div class="mcard-val {cls}">{v2}</div>
              <div class="mcard-lbl">Desvio vs {year_sel-1}</div>
            </div>''', unsafe_allow_html=True)
        with c3:
            if t_a and t_h:
                d2 = round(t_a-t_h,2)
                cls2 = "mcard-red" if d2>1 else "mcard-blue"
                v3 = f"+{d2} C" if d2>0 else f"{d2} C"
            else:
                cls2, v3 = "mcard-blue", "s/d"
            st.markdown(f'''<div class="mcard">
              <div class="mcard-val {cls2}">{v3}</div>
              <div class="mcard-lbl">Desvio vs media historica</div>
            </div>''', unsafe_allow_html=True)

        if t_a and t_h:
            d_al = round(t_a-t_h,2)
            if d_al > 2:
                st.markdown(
                    f'<div class="alerta-red">ALERTA: temperatura {d_al} C acima da media historica em <b>{lago_sel}</b>.</div>',
                    unsafe_allow_html=True)
            elif d_al > 1:
                st.markdown(
                    f'<div class="alerta">Atencao: temperatura levemente acima da media historica.</div>',
                    unsafe_allow_html=True)

        tab1, tab2, tab3 = st.tabs(["Serie temporal","Anomalia","Distribuicao"])
        with tab1:
            if not df_t.empty:
                st.plotly_chart(
                    grafico_temperatura(df_t, lago_sel, current_year, month_sel),
                    use_container_width=True)
        with tab2:
            fig_an = grafico_anomalia(df_t, lago_sel, current_year)
            if fig_an:
                st.plotly_chart(fig_an, use_container_width=True)
            else:
                st.info("Dados insuficientes para anomalia.")
        with tab3:
            if not df_t.empty:
                st.plotly_chart(grafico_boxplot(df_t, lago_sel),
                                use_container_width=True)

    else:
        st.markdown('<div class="sec-title">Focos de calor</div>',
                    unsafe_allow_html=True)

        with st.spinner("Contando focos..."):
            fc5  = get_focos_count_periodo(
                lago_sel, ASSETS["buffers"], 5000, year_sel, month_sel,
                name_field=name_field, dynamic=is_tocantins,
                geom_src=geom_tocantins)
            fc10 = get_focos_count_periodo(
                lago_sel, ASSETS["buffers"], 10000, year_sel, month_sel,
                name_field=name_field, dynamic=is_tocantins,
                geom_src=geom_tocantins)

        st.markdown(
            f"<p style='color:#546e7a;font-size:0.82rem'>Focos em <b>{MESES[month_sel-1]}/{year_sel}</b></p>",
            unsafe_allow_html=True)
        cf1, cf2 = st.columns(2)
        for col_fc, lbl, val in [
            (cf1,"Focos no mes (5 km)",fc5),
            (cf2,"Focos no mes (10 km)",fc10)]:
            cor = "mcard-red" if val and val>20 else "mcard-blue"
            with col_fc:
                st.markdown(f'''<div class="mcard">
                  <div class="mcard-val {cor}">{val}</div>
                  <div class="mcard-lbl">{lbl}</div>
                </div>''', unsafe_allow_html=True)

        @st.cache_data(ttl=3600)
        def load_focos_mensal(lago, cy, cm, dyn):
            geom_src = None
            if dyn:
                try:
                    feat_f = get_feature(lago, ASSETS["tocantins"], "Name")
                    geom_src = feat_f.geometry()
                except:
                    geom_src = None
            df5  = get_monthly_focos(lago, ASSETS["buffers"], 5000,
                                     ANO_BASE, cy, cm,
                                     dynamic=dyn, geom_src=geom_src)
            df10 = get_monthly_focos(lago, ASSETS["buffers"], 10000,
                                     ANO_BASE, cy, cm,
                                     dynamic=dyn, geom_src=geom_src)
            return df5, df10

        with st.spinner("Calculando serie de focos..."):
            df5, df10 = load_focos_mensal(
                lago_sel, current_year, current_month, is_tocantins)

        tab_f1, tab_f2 = st.tabs(["Focos mensais","Acumulado no ano"])
        with tab_f1:
            if df5 is not None and not df5.empty and df5["focos"].notna().any():
                st.plotly_chart(grafico_focos(df5, lago_sel, 5, current_year),
                                use_container_width=True)
            else:
                st.info("Sem dados de focos (5 km) para o periodo.")
            if df10 is not None and not df10.empty and df10["focos"].notna().any():
                st.plotly_chart(grafico_focos(df10, lago_sel, 10, current_year),
                                use_container_width=True)
            else:
                st.info("Sem dados de focos (10 km) para o periodo.")
        with tab_f2:
            if (df5 is not None and not df5.empty and df5["focos"].notna().any() and
                df10 is not None and not df10.empty and df10["focos"].notna().any()):
                st.plotly_chart(
                    grafico_acumulado(df5, df10, lago_sel, current_year),
                    use_container_width=True)
            else:
                st.info("Dados insuficientes para grafico acumulado.")

# ── RANKING ───────────────────────────────────────────────────
st.divider()
st.markdown('<div class="sec-title">Ranking — Comparativo entre areas</div>',
            unsafe_allow_html=True)

lagos_rank = GRUPOS[grupo_sel]
dyn_names  = GRUPOS["Tocantins-Araguaia"] if is_tocantins else []

if tema_sel == "Temperatura":
    st.markdown(f"""
    <p style="color:#546e7a;font-size:0.85rem;margin-bottom:10px">
    Temperatura de <b>{MESES[month_sel-1]}/{year_sel}</b>
    vs {year_sel-1} e media historica.<br>
    <span style="background:#e53935;color:white;padding:2px 8px;border-radius:3px">vermelho = mais quente</span>
    &nbsp;
    <span style="background:#1565c0;color:white;padding:2px 8px;border-radius:3px">azul = mais frio</span>
    </p>""", unsafe_allow_html=True)
    if st.button(f"Carregar ranking de temperatura — {MESES[month_sel-1]}/{year_sel}"):
        with st.spinner("Calculando ranking..."):
            df_rank = get_ranking_temperatura(
                lagos_rank, asset_lagos, year_sel, month_sel, name_field)
        col_dif = f"Dif {year_sel-1}"
        for col in ["Temp atual (C)","Media historica",col_dif,"Dif media"]:
            if col in df_rank.columns:
                df_rank[col] = df_rank[col].round(2)
        styled = (df_rank.style
            .map(colorir_temp, subset=["Temp atual (C)","Media historica"])
            .map(colorir_dif,  subset=[col_dif,"Dif media"])
            .highlight_null(color="#f5f5f5")
            .format("{:.2f}", subset=["Temp atual (C)","Media historica",
                                      col_dif,"Dif media"], na_rep="s/d"))
        st.dataframe(styled, use_container_width=True, hide_index=True)
        csv = df_rank.to_csv(index=False).encode("utf-8")
        st.download_button(
            f"Baixar CSV — {MESES[month_sel-1]}/{year_sel}",
            csv, f"ranking_temp_{year_sel}_{month_sel:02d}.csv",
            mime="text/csv")
else:
    st.markdown(f"""
    <p style="color:#546e7a;font-size:0.85rem;margin-bottom:10px">
    Focos VIIRS em <b>{MESES[month_sel-1]}/{year_sel}</b> — buffers 5 km e 10 km.<br>
    <span style="background:#e53935;color:white;padding:2px 8px;border-radius:3px">vermelho = mais focos</span>
    </p>""", unsafe_allow_html=True)
    if st.button(f"Carregar ranking de focos — {MESES[month_sel-1]}/{year_sel}"):
        with st.spinner("Contando focos..."):
            df_rank_f = get_ranking_focos_periodo(
                lagos_rank, ASSETS["buffers"], year_sel, month_sel,
                dynamic_names=dyn_names,
                tocantins_asset=ASSETS["tocantins"])
        styled_f = (df_rank_f.style
            .map(colorir_focos, subset=["Focos 5km","Focos 10km"])
            .highlight_null(color="#f5f5f5")
            .format("{:,.0f}", subset=["Focos 5km","Focos 10km"], na_rep="s/d"))
        st.dataframe(styled_f, use_container_width=True, hide_index=True)
        csv_f = df_rank_f.to_csv(index=False).encode("utf-8")
        st.download_button(
            f"Baixar CSV — {MESES[month_sel-1]}/{year_sel}",
            csv_f, f"ranking_focos_{year_sel}_{month_sel:02d}.csv",
            mime="text/csv")

# ── RODAPE ────────────────────────────────────────────────────
st.divider()
st.markdown(f"""
<div style="text-align:center;color:#90a4ae;font-size:0.78rem;padding:6px">
  Dados: Google Earth Engine · MODIS Terra · Sentinel-2 · Landsat 8/9 · VIIRS/SNPP<br>
  WWF Brasil · Pedro Galve & Juliano Schirmbeck · {current_year}
</div>""", unsafe_allow_html=True)
