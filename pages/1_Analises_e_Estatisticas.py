import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import ee
from config import (GRUPOS, ASSETS, ANO_BASE, LOGO_WWF, CORES)
from utils.gee_loader import (
    init_gee, get_latest_date, get_tocantins_names,
    get_tocantins_display_names, get_monthly_temperature,
    get_temp_stats, get_focos_count_periodo, get_feature
)
from utils.charts import colorir_temp, colorir_dif, colorir_focos

st.set_page_config(
    page_title="Analises e Estatisticas — Lagos Amazonicos",
    page_icon=LOGO_WWF if LOGO_WWF else "📊",
    layout="wide"
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
  .hdr {
    background: linear-gradient(135deg, #1565c0 0%, #0d47a1 60%, #283593 100%);
    padding: 14px 22px; border-radius: 10px; margin-bottom: 18px;
    display: flex; align-items: center; justify-content: space-between;
    box-shadow: 0 2px 8px rgba(21,101,192,0.18);
  }
  .hdr-title { color:#fff; font-size:1.22rem; font-weight:800; }
  .hdr-sub   { color:#bbdefb; font-size:0.80rem; margin-top:3px; }
  .sec-title {
    font-size:0.95rem; font-weight:700; color:#1565c0;
    border-bottom:2px solid #1565c0;
    padding-bottom:4px; margin-bottom:14px;
  }
  .kpi {
    background:#ffffff; border-radius:10px; padding:16px;
    border-left:4px solid #1565c0;
    box-shadow:0 1px 4px rgba(0,0,0,0.07); text-align:center;
  }
  .kpi-val { font-size:2rem; font-weight:800; color:#1565c0; }
  .kpi-red  { color:#e53935 !important; }
  .kpi-grn  { color:#2e7d32 !important; }
  .kpi-lbl  { font-size:0.78rem; color:#546e7a; margin-top:4px; }
  div[data-testid="stButton"] > button {
    background:#1565c0; color:white; border:none;
    border-radius:7px; font-weight:600; padding:7px 18px; }
  div[data-testid="stButton"] > button:hover { background:#0d47a1; }
  div[data-testid="stTabs"] button { color:#546e7a !important; }
  div[data-testid="stTabs"] button[aria-selected="true"] {
    color:#1565c0 !important; border-bottom:2px solid #1565c0 !important;
    font-weight:700 !important; }
</style>
""", unsafe_allow_html=True)

# ── GEE ───────────────────────────────────────────────────────
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
def obter_display_map():
    return get_tocantins_display_names(ASSETS["tocantins"])

current_year, current_month = obter_data()
MESES = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]

tocantins_names   = obter_tocantins()
tocantins_disp    = obter_display_map()
toc_display_names = sorted([n.replace("\xa0"," ").strip()
                             for n in tocantins_names if n])
GRUPOS["Tocantins-Araguaia"] = toc_display_names

# ── HEADER ────────────────────────────────────────────────────
logo_html = f'<img src="{LOGO_WWF}" style="height:50px;margin-right:16px">' if LOGO_WWF else ""
st.markdown(f"""
<div class="hdr">
  {logo_html}
  <div style="flex:1">
    <div class="hdr-title">Analises e Estatisticas — Lagos Amazonicos</div>
    <div class="hdr-sub">Painel analitico completo — WWF Brasil</div>
  </div>
  <div style="background:rgba(255,255,255,0.12);color:#fff;border-radius:8px;
              padding:8px 14px;font-size:0.82rem;text-align:right">
    Referencia MODIS<br>
    <b>{MESES[current_month-1]}/{current_year}</b>
  </div>
</div>
""", unsafe_allow_html=True)

# ── SIDEBAR ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Filtros")
    grupo_sel = st.selectbox("Grupo", list(GRUPOS.keys()))
    lagos_grupo = GRUPOS[grupo_sel]
    is_toc = grupo_sel == "Tocantins-Araguaia"
    nf     = "Name" if is_toc else "name"
    asset  = ASSETS["tocantins"] if is_toc else ASSETS["lagos"]

    lago_disp = st.selectbox("Lago / Area",
        lagos_grupo if lagos_grupo else ["Carregando..."])
    lago_sel = tocantins_disp.get(lago_disp, lago_disp) if is_toc else lago_disp

    mes_sel = st.selectbox("Mes de referencia", MESES,
                            index=current_month - 1)
    mes_num = MESES.index(mes_sel) + 1

    anos_disp = list(range(2023, current_year + 1))
    ano_sel   = st.selectbox("Ano de referencia", list(reversed(anos_disp)),
                              index=0)
    st.divider()
    if st.button("Atualizar"):
        st.cache_data.clear()
        st.rerun()
    st.markdown("""
    <div style="font-size:0.75rem;color:#78909c;line-height:1.7;margin-top:8px">
      © WWF Brasil · Pedro Galve & Juliano Schirmbeck
    </div>""", unsafe_allow_html=True)

# ── CARREGA DADOS ─────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_serie(lago, nf, asset, cy, cm):
    return get_monthly_temperature(lago, asset, ANO_BASE, cy, cm, nf)

@st.cache_data(ttl=3600)
def load_stats(lago, nf, asset, sy, sm):
    return get_temp_stats(lago, asset, sy, sm, nf)

@st.cache_data(ttl=3600)
def load_focos(lago, sy, sm, dyn):
    geom_src = None
    if dyn:
        try:
            feat = get_feature(lago, ASSETS["tocantins"], "Name")
            geom_src = feat.geometry()
        except:
            pass
    f5  = get_focos_count_periodo(lago, ASSETS["buffers"], 5000,
                                   sy, sm, dynamic=dyn, geom_src=geom_src)
    f10 = get_focos_count_periodo(lago, ASSETS["buffers"], 10000,
                                   sy, sm, dynamic=dyn, geom_src=geom_src)
    return f5, f10

with st.spinner("Carregando dados..."):
    df_serie    = load_serie(lago_sel, nf, asset, current_year, current_month)
    t_a, t_p, t_h = load_stats(lago_sel, nf, asset, ano_sel, mes_num)
    f5, f10     = load_focos(lago_sel, ano_sel, mes_num, is_toc)

MESES_LABEL = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]

# ── KPIs ──────────────────────────────────────────────────────
st.markdown(f'<div class="sec-title">Resumo — {lago_disp} · {mes_sel}/{ano_sel}</div>',
            unsafe_allow_html=True)

k1,k2,k3,k4,k5 = st.columns(5)
kpis = [
    (k1, f"{t_a:.1f} °C" if t_a else "s/d",
     f"Temperatura atual", "kpi-val"),
    (k2, (f"+{round(t_a-t_p,1)}" if t_a and t_p and t_a-t_p>0
          else f"{round(t_a-t_p,1)}" if t_a and t_p else "s/d") + (" °C" if t_a and t_p else ""),
     f"Desvio vs {ano_sel-1}",
     "kpi-red" if t_a and t_p and t_a-t_p>1 else "kpi-grn"),
    (k3, (f"+{round(t_a-t_h,1)}" if t_a and t_h and t_a-t_h>0
          else f"{round(t_a-t_h,1)}" if t_a and t_h else "s/d") + (" °C" if t_a and t_h else ""),
     "Desvio vs media historica",
     "kpi-red" if t_a and t_h and t_a-t_h>1 else "kpi-grn"),
    (k4, str(f5), "Focos calor (5 km)",
     "kpi-red" if f5 and f5>20 else "kpi-val"),
    (k5, str(f10), "Focos calor (10 km)",
     "kpi-red" if f10 and f10>20 else "kpi-val"),
]
for col, val, lbl, cls in kpis:
    with col:
        st.markdown(f'''<div class="kpi">
          <div class="kpi-val {cls}">{val}</div>
          <div class="kpi-lbl">{lbl}</div>
        </div>''', unsafe_allow_html=True)

st.markdown("")

# ── ABAS DE ANALISE ───────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Serie Temporal",
    "Analise Mensal",
    "Anomalia & Risco",
    "Comparativo de Anos",
    "Perfil do Lago"
])

# ── ABA 1: SERIE TEMPORAL COMPLETA ────────────────────────────
with tab1:
    st.markdown('<div class="sec-title">Serie temporal de temperatura</div>',
                unsafe_allow_html=True)
    if not df_serie.empty:
        anos = sorted(df_serie["ano"].unique())
        cores_linha = {
            anos[0]: "#78909c",
            anos[-2] if len(anos)>1 else anos[0]: "#e65100",
            anos[-1]: "#1565c0",
        }
        fig = go.Figure()
        for ano in anos:
            sub = df_serie[df_serie["ano"]==ano].dropna(subset=["temperatura"])
            cor = cores_linha.get(ano, "#90a4ae")
            fig.add_trace(go.Scatter(
                x=sub["mes"], y=sub["temperatura"],
                mode="lines+markers", name=str(ano),
                line=dict(color=cor,
                          width=3 if ano==anos[-1] else 1.5,
                          dash="solid" if ano>=anos[-1]-1 else "dot"),
                marker=dict(size=6 if ano==anos[-1] else 4),
                hovertemplate=f"<b>{ano}</b><br>Mes: %{{x}}<br>Temp: %{{y:.2f}} °C<extra></extra>"
            ))
        # Linha de media historica
        media_hist = df_serie[df_serie["ano"]<anos[-1]].groupby("mes")["temperatura"].mean()
        fig.add_trace(go.Scatter(
            x=media_hist.index, y=media_hist.values,
            mode="lines", name="Media historica",
            line=dict(color="#b0bec5", width=1.5, dash="dash"),
            hovertemplate="Media historica<br>Mes: %{x}<br>%{y:.2f} °C<extra></extra>"
        ))
        fig.add_vline(x=mes_num, line_dash="dot", line_color="#fb8c00",
                      line_width=1.5)
        fig.update_layout(
            xaxis=dict(tickmode="array", tickvals=list(range(1,13)),
                       ticktext=MESES_LABEL, title="Mes",
                       showgrid=True, gridcolor="#eceff1"),
            yaxis=dict(title="Temperatura (°C)",
                       showgrid=True, gridcolor="#eceff1"),
            plot_bgcolor="white", paper_bgcolor="white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            height=380, margin=dict(l=60,r=20,t=40,b=60)
        )
        st.plotly_chart(fig, use_container_width=True)

# ── ABA 2: ANALISE MENSAL ─────────────────────────────────────
with tab2:
    st.markdown('<div class="sec-title">Distribuicao mensal — Boxplot historico</div>',
                unsafe_allow_html=True)
    if not df_serie.empty:
        fig_box = go.Figure()
        for mes in range(1, 13):
            vals = df_serie[df_serie["mes"]==mes]["temperatura"].dropna()
            fig_box.add_trace(go.Box(
                y=vals, name=MESES_LABEL[mes-1],
                marker_color="#1565c0", boxmean=True, showlegend=False,
                hovertemplate=f"<b>{MESES_LABEL[mes-1]}</b><br>%{{y:.2f}} °C<extra></extra>"
            ))
        fig_box.update_layout(
            yaxis=dict(title="Temperatura (°C)",
                       showgrid=True, gridcolor="#eceff1"),
            plot_bgcolor="white", paper_bgcolor="white",
            height=350, margin=dict(l=60,r=20,t=30,b=40),
            title="Variabilidade de temperatura por mes (todos os anos)"
        )
        st.plotly_chart(fig_box, use_container_width=True)

    st.markdown('<div class="sec-title">Temperatura media por mes</div>',
                unsafe_allow_html=True)
    if not df_serie.empty:
        media_mes = df_serie.groupby("mes")["temperatura"].agg(
            ["mean","min","max","std"]).reset_index()
        media_mes.columns = ["Mes","Media","Minima","Maxima","Desvio Padrao"]
        media_mes["Mes"] = media_mes["Mes"].apply(lambda x: MESES_LABEL[x-1])
        media_mes = media_mes.round(2)
        st.dataframe(media_mes, use_container_width=True, hide_index=True)

# ── ABA 3: ANOMALIA & RISCO ───────────────────────────────────
with tab3:
    st.markdown('<div class="sec-title">Anomalia termica — desvio da media historica</div>',
                unsafe_allow_html=True)
    if not df_serie.empty:
        anos_disp2 = sorted(df_serie["ano"].unique())
        ano_anom = st.selectbox("Ano para anomalia", list(reversed(anos_disp2)))
        df_hist = df_serie[df_serie["ano"]<ano_anom].groupby("mes")["temperatura"].mean()
        df_cur  = df_serie[df_serie["ano"]==ano_anom].dropna(subset=["temperatura"])
        merged  = df_cur.merge(df_hist.reset_index(), on="mes",
                               suffixes=("_cur","_hist"))
        if not merged.empty:
            merged["anomalia"] = merged["temperatura_cur"] - merged["temperatura"]
            colors = ["#e53935" if v>0 else "#1565c0" for v in merged["anomalia"]]
            fig_an = go.Figure()
            fig_an.add_trace(go.Bar(
                x=merged["mes"], y=merged["anomalia"],
                marker_color=colors,
                hovertemplate="Mes: %{x}<br>Anomalia: %{y:.2f} °C<extra></extra>",
                name="Anomalia"
            ))
            fig_an.add_hline(y=1, line_dash="dot", line_color="#fb8c00",
                             annotation_text="Limite atencao (+1°C)")
            fig_an.add_hline(y=2, line_dash="dot", line_color="#e53935",
                             annotation_text="Limite alerta (+2°C)")
            fig_an.add_hline(y=0, line_color="#546e7a", line_width=1)
            fig_an.update_layout(
                xaxis=dict(tickmode="array", tickvals=list(range(1,13)),
                           ticktext=MESES_LABEL, title="Mes"),
                yaxis=dict(title="Anomalia (°C)",
                           showgrid=True, gridcolor="#eceff1"),
                plot_bgcolor="white", paper_bgcolor="white",
                height=350, margin=dict(l=60,r=20,t=30,b=60),
                title=f"Anomalia termica {ano_anom} vs media historica"
            )
            st.plotly_chart(fig_an, use_container_width=True)

            # Meses criticos
            criticos = merged[merged["anomalia"]>1].sort_values("anomalia", ascending=False)
            if not criticos.empty:
                st.markdown('<div class="sec-title">Meses criticos (anomalia > 1°C)</div>',
                            unsafe_allow_html=True)
                criticos["Mes"] = criticos["mes"].apply(lambda x: MESES_LABEL[x-1])
                criticos["Anomalia (°C)"] = criticos["anomalia"].round(2)
                criticos["Temperatura (°C)"] = criticos["temperatura_cur"].round(2)
                criticos["Media historica (°C)"] = criticos["temperatura"].round(2)
                st.dataframe(
                    criticos[["Mes","Temperatura (°C)","Media historica (°C)","Anomalia (°C)"]],
                    use_container_width=True, hide_index=True)

# ── ABA 4: COMPARATIVO DE ANOS ────────────────────────────────
with tab4:
    st.markdown('<div class="sec-title">Comparativo de temperatura entre anos</div>',
                unsafe_allow_html=True)
    if not df_serie.empty:
        anos_comp = sorted(df_serie["ano"].unique())
        # Heatmap: ano x mes
        pivot = df_serie.pivot_table(
            index="ano", columns="mes", values="temperatura", aggfunc="mean")
        pivot.columns = [MESES_LABEL[c-1] for c in pivot.columns]

        fig_heat = px.imshow(
            pivot,
            color_continuous_scale="RdYlBu_r",
            labels=dict(color="Temp (°C)"),
            title="Heatmap de temperatura — ano x mes",
            aspect="auto"
        )
        fig_heat.update_layout(
            height=280,
            margin=dict(l=60,r=20,t=50,b=40),
            plot_bgcolor="white", paper_bgcolor="white"
        )
        st.plotly_chart(fig_heat, use_container_width=True)

        # Media anual
        media_anual = df_serie.groupby("ano")["temperatura"].mean().reset_index()
        media_anual.columns = ["Ano","Temperatura media (°C)"]
        media_anual["Temperatura media (°C)"] = media_anual["Temperatura media (°C)"].round(2)

        fig_anual = go.Figure()
        fig_anual.add_trace(go.Bar(
            x=media_anual["Ano"].astype(str),
            y=media_anual["Temperatura media (°C)"],
            marker_color="#1565c0",
            hovertemplate="Ano: %{x}<br>Media: %{y:.2f} °C<extra></extra>"
        ))
        media_geral = media_anual["Temperatura media (°C)"].mean()
        fig_anual.add_hline(y=media_geral, line_dash="dash",
                            line_color="#e53935",
                            annotation_text=f"Media geral: {media_geral:.2f}°C")
        fig_anual.update_layout(
            title="Temperatura media anual",
            xaxis=dict(title="Ano"),
            yaxis=dict(title="Temperatura media (°C)",
                       showgrid=True, gridcolor="#eceff1"),
            plot_bgcolor="white", paper_bgcolor="white",
            height=300, margin=dict(l=60,r=20,t=50,b=40)
        )
        st.plotly_chart(fig_anual, use_container_width=True)

# ── ABA 5: PERFIL DO LAGO ─────────────────────────────────────
with tab5:
    st.markdown('<div class="sec-title">Perfil estatistico do lago</div>',
                unsafe_allow_html=True)
    if not df_serie.empty:
        col_a, col_b = st.columns(2)
        with col_a:
            # Estatisticas gerais
            stats = df_serie["temperatura"].describe().round(2)
            st.markdown("**Estatisticas gerais de temperatura**")
            df_stats = pd.DataFrame({
                "Metrica": ["Registros","Media","Desvio padrao",
                            "Minima","1o quartil","Mediana",
                            "3o quartil","Maxima"],
                "Valor": [
                    int(stats["count"]),
                    f"{stats['mean']:.2f} °C",
                    f"{stats['std']:.2f} °C",
                    f"{stats['min']:.2f} °C",
                    f"{stats['25%']:.2f} °C",
                    f"{stats['50%']:.2f} °C",
                    f"{stats['75%']:.2f} °C",
                    f"{stats['max']:.2f} °C",
                ]
            })
            st.dataframe(df_stats, use_container_width=True, hide_index=True)

        with col_b:
            # Distribuicao de temperaturas
            fig_hist = px.histogram(
                df_serie.dropna(subset=["temperatura"]),
                x="temperatura", nbins=20,
                title="Distribuicao de temperaturas",
                labels={"temperatura":"Temperatura (°C)", "count":"Frequencia"},
                color_discrete_sequence=["#1565c0"]
            )
            fig_hist.update_layout(
                plot_bgcolor="white", paper_bgcolor="white",
                height=300, margin=dict(l=40,r=20,t=50,b=40),
                showlegend=False
            )
            fig_hist.add_vline(x=df_serie["temperatura"].mean(),
                               line_dash="dash", line_color="#e53935",
                               annotation_text="Media")
            st.plotly_chart(fig_hist, use_container_width=True)

        # Mes mais quente e mais frio historicamente
        st.markdown("**Meses historicamente mais quentes e mais frios**")
        media_mes2 = df_serie.groupby("mes")["temperatura"].mean().reset_index()
        media_mes2 = media_mes2.sort_values("temperatura", ascending=False)
        media_mes2["Mes"] = media_mes2["mes"].apply(lambda x: MESES_LABEL[x-1])
        media_mes2["Temp media (°C)"] = media_mes2["temperatura"].round(2)

        fig_rank = go.Figure()
        fig_rank.add_trace(go.Bar(
            x=media_mes2["Mes"],
            y=media_mes2["Temp media (°C)"],
            marker_color=["#e53935" if i<3 else "#1565c0" if i>=9 else "#fb8c00"
                          for i in range(12)],
            hovertemplate="%{x}<br>%{y:.2f} °C<extra></extra>"
        ))
        fig_rank.update_layout(
            title="Ranking de temperatura media por mes",
            xaxis=dict(title="Mes"),
            yaxis=dict(title="Temperatura media (°C)",
                       showgrid=True, gridcolor="#eceff1"),
            plot_bgcolor="white", paper_bgcolor="white",
            height=300, margin=dict(l=60,r=20,t=50,b=40)
        )
        st.plotly_chart(fig_rank, use_container_width=True)

# ── RODAPE ────────────────────────────────────────────────────
st.divider()
st.markdown(f"""
<div style="text-align:center;color:#90a4ae;font-size:0.78rem;padding:6px">
  Dados: Google Earth Engine · MODIS Terra · VIIRS/SNPP<br>
  WWF Brasil · Pedro Galve & Juliano Schirmbeck · {current_year}
</div>""", unsafe_allow_html=True)
