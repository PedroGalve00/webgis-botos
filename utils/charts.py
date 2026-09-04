import plotly.graph_objects as go
import pandas as pd

MESES = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]

def cor_por_ano(ano, ref_year):
    if ano == ref_year:       return "#1565c0"
    elif ano == ref_year - 1: return "#e65100"
    else:                     return "#78909c"

def _layout(titulo, subtitulo, ylab, height=300):
    return dict(
        title=dict(text=f"<b>{titulo}</b>",
                   font=dict(size=13, color="#1a237e"), x=0),
        annotations=[dict(text=subtitulo, xref="paper", yref="paper",
                          x=0, y=1.01, xanchor="left", yanchor="bottom",
                          font=dict(size=10, color="#546e7a"), showarrow=False)],
        xaxis=dict(title="<b>Mes</b>", tickmode="array",
                   tickvals=list(range(1,13)), ticktext=MESES,
                   tickfont=dict(size=10, color="#37474f"),
                   showgrid=True, gridcolor="#eceff1", linecolor="#90a4ae"),
        yaxis=dict(title=f"<b>{ylab}</b>",
                   tickfont=dict(size=10, color="#37474f"),
                   showgrid=True, gridcolor="#eceff1", linecolor="#90a4ae"),
        plot_bgcolor="white", paper_bgcolor="white",
        legend=dict(title=dict(text="<b>Ano</b>",
                               font=dict(size=10, color="#37474f")),
                    orientation="h", yanchor="top", y=-0.22,
                    xanchor="left", x=0,
                    font=dict(size=10, color="#37474f"),
                    bgcolor="white", bordercolor="#eceff1", borderwidth=1),
        margin=dict(l=60, r=20, t=55, b=80),
        height=height,
        hoverlabel=dict(bgcolor="white", font_size=11, font_color="#1a1a1a")
    )

def grafico_temperatura(df, lago, ref_year, sel_month):
    anos = sorted(df["ano"].unique())
    fig = go.Figure()
    for ano in anos:
        sub = df[df["ano"]==ano].dropna(subset=["temperatura"])
        cor = cor_por_ano(ano, ref_year)
        fig.add_trace(go.Scatter(
            x=sub["mes"], y=sub["temperatura"],
            mode="lines+markers", name=str(ano),
            line=dict(color=cor,
                      width=3 if ano==ref_year else 1.5,
                      dash="solid" if ano>=ref_year-1 else "dot"),
            marker=dict(size=6 if ano==ref_year else 4),
            hovertemplate=f"<b>{ano}</b><br>Mes: %{{x}}<br>Temp: %{{y:.2f}} C<extra></extra>"
        ))
    fig.add_vline(x=sel_month, line_dash="dot",
                  line_color="#fb8c00", line_width=1.5,
                  annotation_text=MESES[sel_month-1],
                  annotation_font_color="#fb8c00",
                  annotation_font_size=10)
    fig.update_layout(**_layout(
        f"Temperatura Superficial — {lago}",
        "Fonte: MODIS Terra (MOD11A2) · Media mensal · graus C",
        "Temperatura (C)", height=290))
    return fig

def grafico_anomalia(df, lago, ref_year):
    df_hist = df[df["ano"]<ref_year].groupby("mes")["temperatura"].mean().reset_index()
    df_cur  = df[df["ano"]==ref_year].dropna(subset=["temperatura"])
    merged  = df_cur.merge(df_hist, on="mes", suffixes=("_cur","_hist"))
    if merged.empty: return None
    merged["anomalia"] = merged["temperatura_cur"] - merged["temperatura_hist"]
    colors = ["#e53935" if v>0 else "#1565c0" for v in merged["anomalia"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=merged["mes"], y=merged["anomalia"],
                         marker_color=colors, name="Anomalia",
                         hovertemplate="Mes: %{x}<br>Anomalia: %{y:.2f} C<extra></extra>"))
    fig.add_hline(y=0, line_color="#546e7a", line_width=1)
    fig.update_layout(**_layout(
        f"Anomalia Termica {ref_year} — {lago}",
        f"Diferenca entre {ref_year} e media historica · graus C",
        "Anomalia (C)", height=260))
    return fig

def grafico_boxplot(df, lago):
    fig = go.Figure()
    for mes in range(1,13):
        sub = df[df["mes"]==mes]["temperatura"].dropna()
        fig.add_trace(go.Box(y=sub, name=MESES[mes-1],
                             marker_color="#1565c0", showlegend=False,
                             boxmean=True,
                             hovertemplate=f"<b>{MESES[mes-1]}</b><br>%{{y:.2f}} C<extra></extra>"))
    lay = _layout(f"Distribuicao Historica — {lago}",
                  "Todos os anos disponíveis · MODIS Terra", "Temperatura (C)", 260)
    lay.pop("xaxis", None)
    fig.update_layout(**lay)
    fig.update_xaxes(tickfont=dict(size=10, color="#37474f"))
    return fig

def grafico_focos(df, lago, dist_km, ref_year):
    anos = sorted(df["ano"].unique())
    fig = go.Figure()
    for ano in anos:
        sub = df[df["ano"]==ano].dropna(subset=["focos"])
        cor = cor_por_ano(ano, ref_year)
        fig.add_trace(go.Bar(x=sub["mes"], y=sub["focos"],
                             name=str(ano), marker_color=cor,
                             hovertemplate=f"<b>{ano}</b><br>Mes: %{{x}}<br>Focos: %{{y}}<extra></extra>"))
    lay = _layout(f"Focos de Calor Mensais — {lago}",
                  f"Buffer {dist_km} km · Fonte: VIIRS/SNPP",
                  "Numero de focos", 270)
    lay["barmode"] = "group"
    fig.update_layout(**lay)
    return fig

def grafico_acumulado(df5, df10, lago, ref_year):
    fig = go.Figure()
    for df, dist, cor in [(df5,"5km","#e65100"),(df10,"10km","#b71c1c")]:
        sub = df[df["ano"]==ref_year].dropna(subset=["focos"]).copy()
        sub["acum"] = sub["focos"].cumsum()
        fig.add_trace(go.Scatter(x=sub["mes"], y=sub["acum"],
                                 mode="lines+markers", name=f"Buffer {dist}",
                                 line=dict(color=cor, width=2),
                                 hovertemplate=f"Buffer {dist}<br>Mes: %{{x}}<br>Acum: %{{y}}<extra></extra>"))
    fig.update_layout(**_layout(f"Focos Acumulados {ref_year} — {lago}",
                                "Comparativo buffer 5km vs 10km",
                                "Focos acumulados", 260))
    return fig

def colorir_temp(val):
    if pd.isna(val): return "background-color:#f5f5f5;color:#9e9e9e"
    norm = max(0, min(1, (val-24)/(31-24)))
    r = int(220+35*norm); g = int(220*(1-norm)); b = int(220*(1-norm))
    txt = "#000" if norm<0.6 else "#fff"
    return f"background-color:rgb({r},{g},{b});color:{txt};font-weight:600"

def colorir_dif(val):
    if pd.isna(val): return "background-color:#f5f5f5;color:#9e9e9e"
    norm = max(-1, min(1, val/5))
    if norm<=0:
        i=1+norm; r=int(220*i); g=int(220*i); b=220; txt="#000"
    else:
        r=220; g=int(220*(1-0.4*norm)); b=int(220*(1-norm))
        txt="#000" if norm<0.7 else "#fff"
    return f"background-color:rgb({r},{g},{b});color:{txt};font-weight:600"

def colorir_focos(val):
    if pd.isna(val): return "background-color:#f5f5f5;color:#9e9e9e"
    norm = min(1, val/50)
    r=int(200+55*norm); g=int(200*(1-norm)); b=int(200*(1-norm))
    txt="#000" if norm<0.6 else "#fff"
    return f"background-color:rgb({r},{g},{b});color:{txt};font-weight:600"
