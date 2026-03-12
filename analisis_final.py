"""
Dashboard de Refacciones GCC - Streamlit App
Ejecutar con: streamlit run analisis_final.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Dashboard Refacciones GCC",
    page_icon="⚙️",
    layout="wide",
)

st.markdown("""
<style>
    .metric-card {
        background: rgba(67, 97, 238, 0.12);
        border-radius: 10px;
        padding: 16px 20px;
        border-left: 4px solid #4361ee;
        margin-bottom: 8px;
    }
    .metric-title {
        font-size: 13px;
        color: inherit;
        opacity: 0.7;
        margin: 0;
    }
    .metric-value {
        font-size: 26px;
        font-weight: 700;
        color: inherit;
        margin: 4px 0 0;
    }
    .upload-box {
        background: rgba(67, 97, 238, 0.07);
        border-radius: 12px;
        padding: 24px 28px;
        border: 1.5px dashed #4361ee55;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)


# ── Funciones de carga ─────────────────────────────────────────────────────────
@st.cache_data
def load_refacciones(file):
    df_eq  = pd.read_excel(file, sheet_name="Equipos")
    df_ot  = pd.read_excel(file, sheet_name="Ordenes de trabajo")
    df_ref = pd.read_excel(file, sheet_name="Refacciones")

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
    merged.rename(columns={
        "Description":  "Refaccion",
        "Amount in LC": "Costo",
        "Quantity":     "Cantidad"
    }, inplace=True)
    return merged, df_eq, df_ot


@st.cache_data
def load_inventarios(file):
    raw = pd.read_excel(file, sheet_name="INVENTARIOS MIN-MAX", header=None)

    totales = raw.iloc[85:88, 23:27].copy()
    totales.columns = ["Refaccion", "Costo_Total", "Cantidad_Total", "Precio_Ponderado"]
    totales = totales.dropna(subset=["Refaccion"])
    totales = totales[totales["Refaccion"].astype(str).str.len() > 3].copy()
    for c in ["Costo_Total", "Cantidad_Total", "Precio_Ponderado"]:
        totales[c] = pd.to_numeric(totales[c], errors="coerce")

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

    meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
             "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

    def extract_monthly(start_row, col):
        return [pd.to_numeric(raw.iloc[r, col], errors="coerce") for r in range(start_row, start_row + 12)]

    consumo = pd.DataFrame({"Mes": meses})
    consumo["Aceite Mobil DTE"]       = extract_monthly(87, 1)
    consumo["Aceite Hidráulico Nuno"] = extract_monthly(100, 1)
    consumo["Oil Delvac"]             = extract_monthly(113, 1)

    return totales, productos_inv, consumo


# ── Pantalla de carga de archivos ──────────────────────────────────────────────
def show_upload_screen():
    st.title("⚙️ Dashboard Refacciones GCC")
    st.markdown("### Carga de archivos de datos")
    st.info("Por seguridad, los archivos **no se almacenan** en el servidor. Debes subirlos cada vez que accedas.", icon="🔒")
    st.markdown("")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="upload-box">', unsafe_allow_html=True)
        st.markdown("**📋 Archivo de Refacciones**")
        st.caption("Debe contener las hojas: *Equipos*, *Ordenes de trabajo*, *Refacciones*")
        up_refac = st.file_uploader(
            "Sube `info_TEC_limpio.xlsx`",
            type=["xlsx"],
            key="refac",
            label_visibility="collapsed"
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="upload-box">', unsafe_allow_html=True)
        st.markdown("**📦 Archivo de Inventarios Min/Max**")
        st.caption("Debe contener la hoja: *INVENTARIOS MIN-MAX*")
        up_inv = st.file_uploader(
            "Sube `min&max_GCC.xlsx`",
            type=["xlsx"],
            key="inv",
            label_visibility="collapsed"
        )
        st.markdown('</div>', unsafe_allow_html=True)

    return up_refac, up_inv


# ── Flujo principal ────────────────────────────────────────────────────────────

# Verificar si los archivos ya están en session_state (para no perderlos al interactuar)
if "df" not in st.session_state:
    st.session_state.df            = None
    st.session_state.df_eq         = None
    st.session_state.df_ot         = None
    st.session_state.totales_inv   = None
    st.session_state.productos_inv = None
    st.session_state.consumo       = None

# Mostrar pantalla de carga SOLO si falta algún archivo
if st.session_state.df is None or st.session_state.productos_inv is None:
    up_refac, up_inv = show_upload_screen()

    if up_refac is not None:
        try:
            df, df_eq, df_ot = load_refacciones(up_refac)
            st.session_state.df    = df
            st.session_state.df_eq = df_eq
            st.session_state.df_ot = df_ot
        except Exception as e:
            st.error(f"Error al leer el archivo de refacciones: {e}")

    if up_inv is not None:
        try:
            totales_inv, productos_inv, consumo_mensual = load_inventarios(up_inv)
            st.session_state.totales_inv   = totales_inv
            st.session_state.productos_inv = productos_inv
            st.session_state.consumo       = consumo_mensual
        except Exception as e:
            st.error(f"Error al leer el archivo de inventarios: {e}")

    # Mostrar progreso si solo falta uno
    archivos_ok = []
    if st.session_state.df is not None:
        archivos_ok.append("✅ Refacciones cargado")
    if st.session_state.productos_inv is not None:
        archivos_ok.append("✅ Inventarios cargado")
    if archivos_ok:
        st.success("  |  ".join(archivos_ok))

    # Si aún falta alguno, no continuar
    if st.session_state.df is None or st.session_state.productos_inv is None:
        st.stop()

    # Ambos listos — rerun para limpiar la pantalla de upload
    st.rerun()

# Recuperar datos del session_state
df              = st.session_state.df
df_eq           = st.session_state.df_eq
df_ot           = st.session_state.df_ot
totales_inv     = st.session_state.totales_inv
productos_inv   = st.session_state.productos_inv
consumo_mensual = st.session_state.consumo

st.success("✅ Ambos archivos cargados correctamente. Puedes usar los filtros del panel lateral.", icon="✅")
st.divider()


# ── Filtros ────────────────────────────────────────────────────────────────────
st.sidebar.title("Filtros")
tipos  = ["Todos"] + sorted(df["TIPO"].dropna().unique().tolist())
marcas = ["Todas"] + sorted(df["MARCA"].dropna().unique().tolist())
years  = ["Todos"] + sorted(df["Year"].dropna().unique().tolist(), reverse=True)

sel_tipo  = st.sidebar.selectbox("Tipo de equipo", tipos)
sel_marca = st.sidebar.selectbox("Marca", marcas)
sel_year  = st.sidebar.selectbox("Año", years)
top_n     = st.sidebar.slider("Top N refacciones críticas", 5, 30, 15)
sel_flota = st.sidebar.radio("Flota (inventarios)", ["Flota China", "Flota A/E", "Ambas"], index=2)

# Botón para limpiar caché y subir nuevos archivos
st.sidebar.divider()
if st.sidebar.button("🔄 Cargar nuevos archivos", use_container_width=True):
    for key in ["df", "df_eq", "df_ot", "totales_inv", "productos_inv", "consumo"]:
        st.session_state[key] = None
    st.cache_data.clear()
    st.rerun()

filt = df.copy()
if sel_tipo  != "Todos": filt = filt[filt["TIPO"]  == sel_tipo]
if sel_marca != "Todas": filt = filt[filt["MARCA"] == sel_marca]
if sel_year  != "Todos": filt = filt[filt["Year"]  == sel_year]


def metric_card(title, value):
    return (f'<div class="metric-card"><p class="metric-title">{title}</p>'
            f'<p class="metric-value">{value}</p></div>')


# ── KPIs ───────────────────────────────────────────────────────────────────────
st.title("Dashboard Refacciones GCC")
st.caption(f"Filtros: Tipo = **{sel_tipo}** | Marca = **{sel_marca}** | Año = **{sel_year}**")
st.divider()

k1, k2, k3, k4 = st.columns(4)
k1.markdown(metric_card("Costo Total",              f"${filt['Costo'].sum():,.0f}"),    unsafe_allow_html=True)
k2.markdown(metric_card("Órdenes de trabajo",       f"{filt['Order'].nunique():,}"),     unsafe_allow_html=True)
k3.markdown(metric_card("Equipos únicos",           f"{filt['Equipment'].nunique():,}"), unsafe_allow_html=True)
k4.markdown(metric_card("Costo promedio/refacción", f"${filt['Costo'].mean():,.0f}"),    unsafe_allow_html=True)

st.divider()


# ── Flota ──────────────────────────────────────────────────────────────────────
st.subheader("Datos básicos de la flota")
tabla_flota = (df_eq.groupby(["MARCA"])["EQUIPO"].count().reset_index()
               .rename(columns={"EQUIPO": "Cantidad de Equipos"}))
st.dataframe(tabla_flota, use_container_width=True, hide_index=True)


# ── Inventarios Min/Max ────────────────────────────────────────────────────────
st.markdown("##### Niveles de inventario por producto y flota")
flotas_mostrar = (["Flota China"] if sel_flota == "Flota China"
                  else ["Flota A/E"] if sel_flota == "Flota A/E"
                  else ["Flota China", "Flota A/E"])

rows_table = []
for prod in productos_inv:
    for flota in flotas_mostrar:
        d = prod[flota]
        rows_table.append({
            "Producto":           prod["Producto"],
            "Flota":              flota,
            "Inv. Mín. (AVG LT)": round(float(d["inv_min_avg"]), 1) if d["inv_min_avg"] else "—",
            "Inv. Mín. (MAX LT)": round(float(d["inv_min_max"]), 1) if d["inv_min_max"] else "—",
            "Inv. Máx. (AVG LT)": round(float(d["inv_max_avg"]), 1) if d["inv_max_avg"] else "—",
            "Inv. Máx. (MAX LT)": round(float(d["inv_max_max"]), 1) if d["inv_max_max"] else "—",
        })

st.dataframe(pd.DataFrame(rows_table), hide_index=True, use_container_width=True)

st.markdown("##### Comparación visual Mínimo vs Máximo (AVG Lead Time)")
chart_data = []
for prod in productos_inv:
    for flota in flotas_mostrar:
        d = prod[flota]
        label = prod["Producto"][:22] + f" – {flota}"
        chart_data.append({"Producto": label, "Tipo": "Inventario Mínimo", "Valor": float(d["inv_min_avg"] or 0)})
        chart_data.append({"Producto": label, "Tipo": "Inventario Máximo", "Valor": float(d["inv_max_avg"] or 0)})

fig_minmax = px.bar(
    pd.DataFrame(chart_data), x="Producto", y="Valor", color="Tipo",
    barmode="group", text_auto=".0f",
    color_discrete_map={"Inventario Mínimo": "#f59e0b", "Inventario Máximo": "#22c55e"},
    labels={"Valor": "Unidades", "Producto": ""},
    title="Inventario Mínimo y Máximo por lubricante (Litros) y origen de flota",
)
fig_minmax.update_layout(height=370, xaxis_tickangle=-15, legend_title="",
                         paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
st.plotly_chart(fig_minmax, use_container_width=True)

st.markdown("##### Consumo mensual promedio por lubricante (2023-2026)")
lubricantes = ["Aceite Mobil DTE", "Aceite Hidráulico Nuno", "Oil Delvac"]
fig_consumo = px.line(
    consumo_mensual.melt(id_vars="Mes", value_vars=lubricantes,
                         var_name="Lubricante", value_name="Unidades"),
    x="Mes", y="Unidades", color="Lubricante", markers=True,
    title="Consumo mensual por lubricante",
    color_discrete_sequence=px.colors.qualitative.Set2,
)
fig_consumo.update_layout(height=340, xaxis_tickangle=-30, legend_title="",
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
st.plotly_chart(fig_consumo, use_container_width=True)

st.divider()


# ── Refacciones Críticas ───────────────────────────────────────────────────────
st.subheader(f"Top {top_n} Refacciones Críticas (por cantidad total consumida)")

resumen = filt.groupby("Refaccion").agg(
    Cantidad_Total    =("Cantidad",   "sum"),
    Frecuencia        =("Order",      "count"),
    Costo_Total       =("Costo",      "sum"),
    Costo_Promedio    =("Costo",      "mean"),
    Equipos_Afectados =("Equipment",  "nunique"),
).reset_index()
resumen["Cantidad_Total"] = pd.to_numeric(resumen["Cantidad_Total"], errors="coerce").fillna(0)
resumen["Costo_Total"]    = pd.to_numeric(resumen["Costo_Total"],    errors="coerce").fillna(0)
resumen["Costo_Promedio"] = pd.to_numeric(resumen["Costo_Promedio"], errors="coerce").fillna(0)
resumen = resumen.sort_values("Cantidad_Total", ascending=False).reset_index(drop=True)

_qty_max = resumen["Cantidad_Total"].max()
_qty_min = resumen["Cantidad_Total"].min()
resumen["Qty_norm"] = (resumen["Cantidad_Total"] - _qty_min) / (_qty_max - _qty_min)

def nivel_criticidad(score):
    if score >= 0.7:   return "🔴 CRÍTICA"
    elif score >= 0.4: return "🟡 MEDIA"
    else:              return "🟢 BAJA"

resumen["Nivel"] = resumen["Qty_norm"].apply(nivel_criticidad)
critical = resumen.head(top_n).copy()
critical["Costo_Total_fmt"]    = critical["Costo_Total"].map("${:,.0f}".format)
critical["Cantidad_Total_fmt"] = critical["Cantidad_Total"].map("{:,.0f}".format)
critical_chart = critical.sort_values("Cantidad_Total", ascending=True)

col_chart, col_table = st.columns([3, 2])
with col_chart:
    fig_bar = px.bar(
        critical_chart, x="Cantidad_Total", y="Refaccion", orientation="h",
        color="Cantidad_Total", color_continuous_scale="Reds",
        text="Cantidad_Total_fmt",
        labels={"Cantidad_Total": "Cantidad Total Consumida", "Refaccion": ""},
        title="Cantidad total consumida por refacción",
    )
    fig_bar.update_traces(textposition="outside")
    fig_bar.update_layout(coloraxis_showscale=False, height=480,
                          margin=dict(l=20, r=20, t=40, b=20),
                          yaxis=dict(tickfont=dict(size=11)),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_bar, use_container_width=True)

with col_table:
    st.markdown("#### Detalle")
    disp = critical[["Refaccion","Nivel","Cantidad_Total_fmt","Frecuencia","Costo_Total_fmt","Costo_Promedio","Equipos_Afectados"]].copy()
    disp["Costo_Promedio"] = disp["Costo_Promedio"].map("${:,.2f}".format)
    disp.columns = ["Refacción","Nivel","Cantidad Total","Frecuencia","Costo Total","Costo Prom.","Equipos"]
    st.dataframe(disp, hide_index=True, use_container_width=True, height=460)

st.divider()


# ── Distribución Tipo / Marca ──────────────────────────────────────────────────
st.subheader("Distribución de Costos por Tipo y Marca")

col_tipo, col_marca = st.columns(2)
with col_tipo:
    by_tipo = filt.groupby("TIPO")["Costo"].sum().reset_index()
    fig_pie = px.pie(by_tipo, values="Costo", names="TIPO", hole=0.4,
                     title="Costo total por Tipo de Equipo",
                     color_discrete_sequence=px.colors.qualitative.Set2)
    fig_pie.update_traces(textinfo="label+percent", textposition="outside")
    fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_pie, use_container_width=True)

with col_marca:
    by_marca = filt.groupby("MARCA")["Costo"].sum().sort_values(ascending=False).reset_index()
    fig_marca = px.bar(by_marca, x="MARCA", y="Costo", color="MARCA",
                       color_discrete_sequence=px.colors.qualitative.Bold,
                       title="Costo total por Marca",
                       labels={"Costo": "Costo (MXN)", "MARCA": "Marca"})
    fig_marca.update_layout(showlegend=False,
                            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_marca, use_container_width=True)

st.divider()


# ── Evolución Mensual ──────────────────────────────────────────────────────────
st.subheader("Evolución Mensual del Gasto en Refacciones")

monthly = (filt[filt["Month"] != "NaT"]
           .groupby("Month")["Costo"].sum()
           .reset_index().sort_values("Month"))
fig_line = px.area(monthly, x="Month", y="Costo",
                   title="Gasto mensual (MXN)",
                   labels={"Month": "Mes", "Costo": "Costo (MXN)"},
                   color_discrete_sequence=["#4361ee"])
fig_line.update_layout(height=320, xaxis_tickangle=-45,
                       paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
st.plotly_chart(fig_line, use_container_width=True)

st.divider()


# ── Scatter Criticidad ─────────────────────────────────────────────────────────
st.subheader("Análisis de Criticidad: Cantidad Consumida vs Costo Promedio")
st.caption("Las refacciones en la esquina superior derecha son las más críticas.")

fig_scatter = px.scatter(
    resumen.head(100),
    x="Cantidad_Total", y="Costo_Promedio", size="Equipos_Afectados", color="Qty_norm",
    color_continuous_scale="RdYlGn_r", hover_name="Refaccion",
    hover_data={"Cantidad_Total": ":,.0f", "Costo_Total": ":,.0f",
                "Frecuencia": True, "Equipos_Afectados": True},
    labels={"Cantidad_Total": "Cantidad Total Consumida",
            "Costo_Promedio": "Costo Promedio por Uso (MXN)",
            "Qty_norm": "Criticidad"},
    title="Top 100 refacciones – tamaño = equipos afectados",
)
fig_scatter.update_layout(height=450, coloraxis_showscale=False,
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
st.plotly_chart(fig_scatter, use_container_width=True)

st.divider()


# ── Tabla completa ─────────────────────────────────────────────────────────────
with st.expander("Ver tabla completa de datos filtrados"):
    show_cols = ["Order","Refaccion","Costo","Equipment","MARCA","MODELO","TIPO","Year","Vendor"]
    st.dataframe(filt[show_cols].sort_values("Costo", ascending=False),
                 use_container_width=True, height=400)
    st.caption(f"Total de registros: {len(filt):,}")

st.markdown("---")
st.caption("Dashboard desarrollado con Streamlit + Plotly · GCC")
