"""
Dashboard de Refacciones GCC - Streamlit App
Ejecutar con: streamlit run dashboard_tec.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Dashboard Refacciones GCC",
    page_icon="gcc_logo.png",
    layout="wide",
)

st.markdown("""
<style>
    .metric-card {
        background: #f0f4ff;
        border-radius: 10px;
        padding: 16px 20px;
        border-left: 4px solid #4361ee;
        margin-bottom: 8px;
    }
    .metric-title { font-size: 13px; color: #555; margin: 0; }
    .metric-value { font-size: 26px; font-weight: 700; color: #1a1a2e; margin: 4px 0 0; }
    h1 { color: #1a1a2e; }
</style>
""", unsafe_allow_html=True)


# ── Carga de datos ─────────────────────────────────────────────────────────────
@st.cache_data
def load_refacciones(path):
    df_eq  = pd.read_excel(path, sheet_name="Equipos")
    df_ot  = pd.read_excel(path, sheet_name="Ordenes de trabajo")
    df_ref = pd.read_excel(path, sheet_name="Refacciones")

    df_ref["Order"]    = df_ref["Order"].astype(str)
    df_ot["Order"]     = df_ot["Order"].astype(str)
    df_eq["EQUIPO"]    = df_eq["EQUIPO"].astype(str)
    df_ot["Equipment"] = df_ot["Equipment"].astype(str)

    merged = df_ref.merge(
        df_ot[["Order", "Equipment", "Description.1", "Order Type"]],
        on="Order", how="left"
    ).merge(
        df_eq.rename(columns={"EQUIPO": "Equipment"}),
        on="Equipment", how="left"
    )
    merged["Year"]  = pd.to_datetime(merged["Posting Date"], errors="coerce").dt.year.astype("Int64")
    merged["Month"] = pd.to_datetime(merged["Posting Date"], errors="coerce").dt.to_period("M").astype(str)
    merged.rename(columns={"Description": "Refaccion", "Amount in LC": "Costo"}, inplace=True)
    return merged, df_eq, df_ot


@st.cache_data
def load_inventarios(path):
    raw = pd.read_excel(path, sheet_name="INVENTARIOS MIN-MAX", header=None)

    totales = raw.iloc[85:88, 23:27].copy()
    totales.columns = ["Refaccion", "Costo_Total", "Cantidad_Total", "Precio_Ponderado"]
    totales = totales.dropna(subset=["Refaccion"])
    totales = totales[totales["Refaccion"].astype(str).str.len() > 3].copy()
    for c in ["Costo_Total", "Cantidad_Total", "Precio_Ponderado"]:
        totales[c] = pd.to_numeric(totales[c], errors="coerce")

    # Inventarios mínimos/máximos por producto y flota
    productos_inv = [
        {
            "Producto": "Aceite Mobil DTE 26 19Lt",
            "Flota China": {"inv_min_avg": raw.iloc[88, 17], "inv_min_max": raw.iloc[88, 18],
                            "inv_max_avg": raw.iloc[88, 19], "inv_max_max": raw.iloc[88, 20]},
            "Flota A/E":   {"inv_min_avg": raw.iloc[89, 17], "inv_min_max": None,
                            "inv_max_avg": raw.iloc[89, 19], "inv_max_max": None},
        },
        {
            "Producto": "Aceite Hidráulico Nuno 68 19Lt",
            "Flota China": {"inv_min_avg": raw.iloc[93, 17], "inv_min_max": raw.iloc[93, 18],
                            "inv_max_avg": raw.iloc[93, 19], "inv_max_max": raw.iloc[93, 20]},
            "Flota A/E":   {"inv_min_avg": raw.iloc[94, 17], "inv_min_max": None,
                            "inv_max_avg": raw.iloc[94, 19], "inv_max_max": None},
        },
        {
            "Producto": "Oil Delvac 1300 15W40",
            "Flota China": {"inv_min_avg": raw.iloc[98, 17], "inv_min_max": raw.iloc[98, 18],
                            "inv_max_avg": raw.iloc[98, 19], "inv_max_max": raw.iloc[98, 20]},
            "Flota A/E":   {"inv_min_avg": raw.iloc[99, 17], "inv_min_max": None,
                            "inv_max_avg": raw.iloc[99, 19], "inv_max_max": None},
        },
    ]

    # Consumo mensual
    meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
             "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

    def extract_monthly(start_row, col):
        return [pd.to_numeric(raw.iloc[r, col], errors="coerce") for r in range(start_row, start_row + 12)]

    consumo = pd.DataFrame({"Mes": meses})
    consumo["Aceite Mobil DTE"]       = extract_monthly(87, 1)
    consumo["Aceite Hidráulico Nuno"] = extract_monthly(100, 1)
    consumo["Oil Delvac"]             = extract_monthly(113, 1)

    return totales, productos_inv, consumo


FILE_REFAC = "info_TEC_limpio.xlsx"
FILE_INV   = "min&max_GCC.xlsx"

try:
    df, df_eq, df_ot = load_refacciones(FILE_REFAC)
except FileNotFoundError:
    up = st.file_uploader("Sube info_TEC_limpio.xlsx", type="xlsx", key="refac")
    if up is None:
        st.info("Sube el archivo de refacciones para continuar.")
        st.stop()
    df, df_eq, df_ot = load_refacciones(up)

try:
    totales_inv, productos_inv, consumo_mensual = load_inventarios(FILE_INV)
except FileNotFoundError:
    up_inv = st.file_uploader("Sube Inventarios_mi_nimos___ma_ximos_GCC.xlsx", type="xlsx", key="inv")
    if up_inv is None:
        st.info("Sube el archivo de inventarios para continuar.")
        st.stop()
    totales_inv, productos_inv, consumo_mensual = load_inventarios(up_inv)


# Barra Filtros
st.sidebar.title("Filtros")
tipos  = ["Todos"] + sorted(df["TIPO"].dropna().unique().tolist())
marcas = ["Todas"] + sorted(df["MARCA"].dropna().unique().tolist())
years  = ["Todos"] + sorted(df["Year"].dropna().unique().tolist(), reverse=True)

sel_tipo  = st.sidebar.selectbox("Tipo de equipo", tipos)
sel_marca = st.sidebar.selectbox("Marca", marcas)
sel_year  = st.sidebar.selectbox("Año", years)
top_n     = st.sidebar.slider("Top N refacciones críticas", 5, 30, 15)
sel_flota = st.sidebar.radio("Flota (inventarios)", ["Flota China", "Flota A/E", "Ambas"])

filt = df.copy()
if sel_tipo  != "Todos": filt = filt[filt["TIPO"]  == sel_tipo]
if sel_marca != "Todas": filt = filt[filt["MARCA"] == sel_marca]
if sel_year  != "Todos": filt = filt[filt["Year"]  == sel_year]


def metric_card(title, value):
    return (f'<div class="metric-card"><p class="metric-title">{title}</p>'
            f'<p class="metric-value">{value}</p></div>')


# KPIs
st.title("Dashboard Refacciones GCC")
st.caption(f"Filtros: Tipo = **{sel_tipo}** | Marca = **{sel_marca}** | Año = **{sel_year}**")
st.divider()

k1, k2, k3, k4 = st.columns(4)
k1.markdown(metric_card("Costo Total",              f"${filt['Costo'].sum():,.0f}"),    unsafe_allow_html=True)
k2.markdown(metric_card("Órdenes de trabajo",       f"{filt['Order'].nunique():,}"),     unsafe_allow_html=True)
k3.markdown(metric_card("Equipos únicos",           f"{filt['Equipment'].nunique():,}"), unsafe_allow_html=True)
k4.markdown(metric_card("Costo promedio/refacción", f"${filt['Costo'].mean():,.0f}"),    unsafe_allow_html=True)

st.divider()


# Minimos y maximos
st.subheader("Inventarios Mínimos y Máximos de Lubricantes")
st.caption("Niveles calculados con base en consumo 2023-2026 y lead times por tipo de flota.")

t1, t2, t3 = st.columns(3)
for col, (_, row) in zip([t1, t2, t3], totales_inv.iterrows()):
    col.markdown(f"""
    <div style="background:#f8fafc; border-radius:10px; padding:14px 18px;
                border-left:4px solid #6366f1; margin-bottom:12px;">
        <p style="font-size:12px; color:#555; margin:0"> {row['Refaccion']}</p>
        <p style="font-size:22px; font-weight:700; margin:4px 0 0; color:#1a1a2e">
            {int(row['Cantidad_Total']):,} unid.</p>
        <p style="font-size:13px; color:#666; margin:2px 0 0">
            Costo total: <b>${row['Costo_Total']:,.0f}</b> &nbsp;|&nbsp;
            Precio pond.: <b>${row['Precio_Ponderado']:.2f}</b>/unid.
        </p>
    </div>""", unsafe_allow_html=True)

st.markdown("##### Niveles de inventario por producto y flota")
flotas_mostrar = (["Flota China"] if sel_flota == "Flota China"
                  else ["Flota A/E"] if sel_flota == "Flota A/E"
                  else ["Flota China", "Flota A/E"])

rows_table = []
for prod in productos_inv:
    for flota in flotas_mostrar:
        d = prod[flota]
        rows_table.append({
            "Producto":            prod["Producto"],
            "Flota":               flota,
            "Inv. Mín. (AVG LT)":  round(float(d["inv_min_avg"]), 1) if d["inv_min_avg"] else "—",
            "Inv. Mín. (MAX LT)":  round(float(d["inv_min_max"]), 1) if d["inv_min_max"] else "—",
            "Inv. Máx. (AVG LT)":  round(float(d["inv_max_avg"]), 1) if d["inv_max_avg"] else "—",
            "Inv. Máx. (MAX LT)":  round(float(d["inv_max_max"]), 1) if d["inv_max_max"] else "—",
        })

df_minmax = pd.DataFrame(rows_table)

def color_rows(row):
    color = "#000000" if "China" in str(row["Flota"]) else "#000000"
    return [f"background-color: white"] * len(row)

st.dataframe(df_minmax.style.apply(color_rows, axis=1),
             hide_index=True, use_container_width=True)

# Gráfico barras min/max
st.markdown("##### Comparación visual Mínimo vs Máximo (AVG Lead Time)")
chart_data = []
for prod in productos_inv:
    for flota in flotas_mostrar:
        d = prod[flota]
        label = prod["Producto"][:22] + f" – {flota}"
        chart_data.append({"Producto": label, "Tipo": "Inventario Mínimo",
                            "Valor": float(d["inv_min_avg"] or 0)})
        chart_data.append({"Producto": label, "Tipo": "Inventario Máximo",
                            "Valor": float(d["inv_max_avg"] or 0)})

fig_minmax = px.bar(
    pd.DataFrame(chart_data), x="Producto", y="Valor", color="Tipo",
    barmode="group", text_auto=".0f",
    color_discrete_map={"Inventario Mínimo": "#f59e0b", "Inventario Máximo": "#22c55e"},
    labels={"Valor": "Unidades", "Producto": ""},
    title="Inventario Mínimo y Máximo por lubricante y flota (unidades)",
)
fig_minmax.update_layout(height=370, xaxis_tickangle=-15, legend_title="")
st.plotly_chart(fig_minmax, use_container_width=True)

# Consumo mensual
st.markdown("##### Consumo mensual promedio por lubricante (2023-2026)")
lubricantes = ["Aceite Mobil DTE", "Aceite Hidráulico Nuno", "Oil Delvac"]
fig_consumo = px.line(
    consumo_mensual.melt(id_vars="Mes", value_vars=lubricantes,
                         var_name="Lubricante", value_name="Unidades"),
    x="Mes", y="Unidades", color="Lubricante", markers=True,
    title="Consumo mensual por lubricante",
    color_discrete_sequence=px.colors.qualitative.Set2,
)
fig_consumo.update_layout(height=340, xaxis_tickangle=-30, legend_title="")
st.plotly_chart(fig_consumo, use_container_width=True)

st.divider()


# Refacciones Críticas
st.subheader(f"Top {top_n} Refacciones Críticas (por costo total)")

critical = (
    filt.groupby("Refaccion")["Costo"]
    .agg(Costo_Total="sum", Frecuencia="count")
    .sort_values("Costo_Total", ascending=False)
    .head(top_n).reset_index()
)
critical["% del Total"]     = (critical["Costo_Total"] / critical["Costo_Total"].sum() * 100).round(1)
critical["Costo_Total_fmt"] = critical["Costo_Total"].map("${:,.0f}".format)

col_chart, col_table = st.columns([3, 2])
with col_chart:
    fig_bar = px.bar(
        critical.sort_values("Costo_Total"),
        x="Costo_Total", y="Refaccion", orientation="h",
        color="Costo_Total", color_continuous_scale="Reds",
        text="Costo_Total_fmt",
        labels={"Costo_Total": "Costo Total (MXN)", "Refaccion": ""},
        title="Costo acumulado por refacción",
    )
    fig_bar.update_traces(textposition="outside")
    fig_bar.update_layout(coloraxis_showscale=False, height=480,
                          margin=dict(l=20, r=20, t=40, b=20),
                          yaxis=dict(tickfont=dict(size=11)))
    st.plotly_chart(fig_bar, use_container_width=True)

with col_table:
    st.markdown("#### Detalle")
    disp = critical[["Refaccion", "Costo_Total_fmt", "Frecuencia", "% del Total"]].copy()
    disp.columns = ["Refacción", "Costo Total", "Frecuencia", "% Total"]
    st.dataframe(disp, hide_index=True, use_container_width=True, height=460)

st.divider()


# Distribución Tipo / Marca
st.subheader("Distribución de Costos por Tipo y Marca")

col_tipo, col_marca = st.columns(2)
with col_tipo:
    by_tipo = filt.groupby("TIPO")["Costo"].sum().reset_index()
    fig_pie = px.pie(by_tipo, values="Costo", names="TIPO", hole=0.4,
                     title="Costo total por Tipo de Equipo",
                     color_discrete_sequence=px.colors.qualitative.Set2)
    fig_pie.update_traces(textinfo="label+percent", textposition="outside")
    st.plotly_chart(fig_pie, use_container_width=True)

with col_marca:
    by_marca = filt.groupby("MARCA")["Costo"].sum().sort_values(ascending=False).reset_index()
    fig_marca = px.bar(by_marca, x="MARCA", y="Costo", color="MARCA",
                       color_discrete_sequence=px.colors.qualitative.Bold,
                       title="Costo total por Marca",
                       labels={"Costo": "Costo (MXN)", "MARCA": "Marca"})
    fig_marca.update_layout(showlegend=False)
    st.plotly_chart(fig_marca, use_container_width=True)

st.divider()


# Evolución Mensual
st.subheader("Evolución Mensual del Gasto en Refacciones")

monthly = (
    filt[filt["Month"] != "NaT"]
    .groupby("Month")["Costo"].sum()
    .reset_index().sort_values("Month")
)
fig_line = px.area(monthly, x="Month", y="Costo",
                   title="Gasto mensual (MXN)",
                   labels={"Month": "Mes", "Costo": "Costo (MXN)"},
                   color_discrete_sequence=["#4361ee"])
fig_line.update_layout(height=320, xaxis_tickangle=-45)
st.plotly_chart(fig_line, use_container_width=True)

st.divider()


# Scatter Criticidad
st.subheader("Análisis de Criticidad: Frecuencia vs Costo Unitario")
st.caption("Las refacciones en la esquina superior derecha son las más críticas.")

scatter_df = (
    filt.groupby("Refaccion")["Costo"]
    .agg(Costo_Total="sum", Frecuencia="count", Costo_Promedio="mean")
    .reset_index()
)
scatter_df["Criticidad"] = (
    (scatter_df["Costo_Total"] - scatter_df["Costo_Total"].min()) /
    (scatter_df["Costo_Total"].max() - scatter_df["Costo_Total"].min())
)
fig_scatter = px.scatter(
    scatter_df.head(100),
    x="Frecuencia", y="Costo_Promedio", size="Costo_Total", color="Criticidad",
    color_continuous_scale="RdYlGn_r", hover_name="Refaccion",
    hover_data={"Costo_Total": ":,.0f", "Frecuencia": True, "Costo_Promedio": ":,.0f"},
    labels={"Frecuencia": "Frecuencia de uso",
            "Costo_Promedio": "Costo Promedio por Uso (MXN)",
            "Costo_Total": "Costo Total (MXN)"},
    title="Top 100 refacciones – tamaño = costo total",
)
fig_scatter.update_layout(height=450, coloraxis_showscale=False)
st.plotly_chart(fig_scatter, use_container_width=True)

st.divider()


# Tabla completa
with st.expander("Ver tabla completa de datos filtrados"):
    show_cols = ["Order", "Refaccion", "Costo", "Equipment", "MARCA", "MODELO", "TIPO", "Year", "Vendor"]
    st.dataframe(filt[show_cols].sort_values("Costo", ascending=False),
                 use_container_width=True, height=400)
    st.caption(f"Total de registros: {len(filt):,}")

st.markdown("---")
st.caption("Dashboard desarrollado con Streamlit + Plotly · TEC")