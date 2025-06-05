import pandas as pd
import streamlit as st
import plotly.express as px

# ── 1) CONFIGURACIÓN BÁSICA ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard de Pronóstico Mensual (Filtros en Cascada)",
    layout="wide",
)
st.title("📊 Pronóstico Mensual")

# ── 2) CARGAR DATOS ────────────────────────────────────────────────────────────
@st.cache_data
def cargar_datos(ruta_archivo: str) -> pd.DataFrame:
    """
    Lee un CSV o Excel con columnas:
    PAIS | CLIENTE | PRODUCTO | FECHA | TOTAL VENDIDO
    Devuelve un DataFrame con FECHA en datetime.
    """
    # Si tu archivo es Excel, descomenta la siguiente línea y comenta la de CSV:
    # df = pd.read_excel(ruta_archivo, parse_dates=['FECHA'])
    df = pd.read_excel(ruta_archivo, parse_dates=['FECHA'])
    return df

# Ajusta la ruta al archivo real (puede ser .csv o .xlsx según tu caso)
RUTA_ARCHIVO = "BD_STREAMLIT.xlsx"
df = cargar_datos(RUTA_ARCHIVO)

if df.empty:
    st.error("❌ El DataFrame está vacío. Revisa la ruta o el contenido del archivo.")
    st.stop()

# ── 3) PREPROCESAMIENTO: EXTRAER MES Y AÑO ─────────────────────────────────────
df['Mes'] = df['FECHA'].dt.month
df['Año'] = df['FECHA'].dt.year

# ── 4) FILTROS EN CASCADA ───────────────────────────────────────────────────────
st.markdown("*Filtra tus datos (si no seleccionas nada, se muestra ventas totales):*")

col1, col2, col3 = st.columns(3)

# 4.1) Primero: FILTRO PAÍS (lista completa de países, SIN DEPENDER DE NADA)
with col1:
    todos_paises = sorted(df['PAIS'].dropna().unique())
    sel_paises = st.multiselect(
        label="País(es)",
        options=todos_paises,
        default=[],
        help="Si no seleccionas nada, se usarán todos los países."
    )

# 4.2) Con base en la selección de País, defino qué Clientes mostrar
# Si no hay selección de País, usamos TODO el df para mirar clientes
if sel_paises:
    df_filtrado_pais = df[df['PAIS'].isin(sel_paises)]
else:
    df_filtrado_pais = df

with col2:
    clientes_disponibles = sorted(df_filtrado_pais['CLIENTE'].dropna().unique())
    sel_clientes = st.multiselect(
        label="Cliente(s)",
        options=clientes_disponibles,
        default=[],
        help="Si no seleccionas nada, se usarán todos los clientes posibles dentro del/los país(es) seleccionado(s)."
    )

# 4.3) Con base en País + Cliente, defino qué Productos mostrar
# Si no hay selección de Cliente, uso df_filtrado_pais para ver todos los productos
if sel_clientes:
    df_filtrado_cliente = df_filtrado_pais[df_filtrado_pais['CLIENTE'].isin(sel_clientes)]
else:
    df_filtrado_cliente = df_filtrado_pais

with col3:
    productos_disponibles = sorted(df_filtrado_cliente['PRODUCTO'].dropna().unique())
    sel_productos = st.multiselect(
        label="Producto(s)",
        options=productos_disponibles,
        default=[],
        help="Si no seleccionas nada, se usarán todos los productos posibles dentro del/los cliente(s) (y país(es)) ya seleccionados."
    )

# ── 5) APLICAR FILTROS DEFINITIVOS ──────────────────────────────────────────────
# Partiendo de df, voy aplicando los filtros en cascada:
df_filtrado = df.copy()

# Filtrar por País (si se seleccionó al menos uno)
if sel_paises:
    df_filtrado = df_filtrado[df_filtrado['PAIS'].isin(sel_paises)]

# Filtrar por Cliente (si se seleccionó al menos uno)
if sel_clientes:
    df_filtrado = df_filtrado[df_filtrado['CLIENTE'].isin(sel_clientes)]

# Filtrar por Producto (si se seleccionó al menos uno)
if sel_productos:
    df_filtrado = df_filtrado[df_filtrado['PRODUCTO'].isin(sel_productos)]

if df_filtrado.empty:
    st.warning("⚠ No hay datos que coincidan con los filtros seleccionados. Ajusta los filtros para ver resultados.")
    st.stop()

# ── 6) AGREGAR VENTAS MENSUALES POR MES-AÑO ────────────────────────────────────
ventas_mensuales_agrupadas = (
    df_filtrado
    .groupby(['Año', 'Mes'], as_index=False)['TOTAL VENDIDO']
    .sum()
    .rename(columns={'TOTAL VENDIDO': 'Ventas Mensuales'})
)

# ── 7) CREAR Fecha_Mes (primer día de cada mes) CORRECTAMENTE ────────────────────
ventas_mensuales_agrupadas['Fecha_Mes'] = pd.to_datetime({
    'year':  ventas_mensuales_agrupadas['Año'],
    'month': ventas_mensuales_agrupadas['Mes'],
    'day':   1
})

# ── 8) CALCULAR PROMEDIO HISTÓRICO POR MES (IGNORAR AÑO) ────────────────────────
promedios_por_mes = (
    ventas_mensuales_agrupadas
    .groupby('Mes')['Ventas Mensuales']
    .mean()
    .reindex(range(1, 13))   # nos aseguramos de tener índice 1..12
    .fillna(0)
)

# ── 9) CONSTRUIR PRONÓSTICO PARA EL PRÓXIMO AÑO ────────────────────────────────
ultimo_ano = ventas_mensuales_agrupadas['Año'].max()
proximo_ano = ultimo_ano + 1

meses_futuros = pd.date_range(
    start=f"{proximo_ano}-01-01",
    end=f"{proximo_ano}-12-01",
    freq='MS'
)

pronostico_df = pd.DataFrame({
    'Fecha_Mes': meses_futuros,
    'Mes': meses_futuros.month
})
pronostico_df['Pronóstico'] = pronostico_df['Mes'].map(promedios_por_mes)

# ── 10) TABLA: PROMEDIO HISTÓRICO POR MES ──────────────────────────────────────
st.subheader("🗒 Promedio Histórico de Ventas por Mes")

tabla_promedios = promedios_por_mes.reset_index().rename(
    columns={'index': 'Mes', 'Ventas Mensuales': 'Promedio Vendido'}
)
mes_a_texto = {
    1: 'Enero',      2: 'Febrero',   3: 'Marzo',      4: 'Abril',
    5: 'Mayo',       6: 'Junio',     7: 'Julio',      8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre',  11: 'Noviembre', 12: 'Diciembre'
}
tabla_promedios['Mes'] = tabla_promedios['Mes'].map(mes_a_texto)

st.dataframe(
    tabla_promedios.style.format({"Promedio Vendido": "{:,.2f}"}),
    use_container_width=True
)

# ── 11) GRAFICAR: HISTÓRICO + PRONÓSTICO ───────────────────────────────────────
st.subheader("📈 Ventas Mensuales Históricas y Pronóstico para el Año Siguiente")

fig = px.line(
    ventas_mensuales_agrupadas,
    x='Fecha_Mes',
    y='Ventas Mensuales',
    title="Ventas Mensuales Históricas",
    labels={'Ventas Mensuales': 'Total Vendido', 'Fecha_Mes': 'Fecha'}
)

fig.add_scatter(
    x=pronostico_df['Fecha_Mes'],
    y=pronostico_df['Pronóstico'],
    mode='lines+markers',
    name=f"Pronóstico {proximo_ano}"
)

fig.update_layout(
    xaxis_title="Fecha (Mes)",
    yaxis_title="Total Vendido",
    legend_title_text="",
    hovermode="x unified"
)

st.plotly_chart(fig, use_container_width=True)

## TABLAS DETALLADAS (COLAPSABLES) ────────────────────────────────────────
with st.expander("Ver detalle mensual completo"):
    # —— Serie histórica completa (solo Año, Mes, Ventas Mensuales Totales) ——
    st.write("*Serie histórica completa (suma de ventas por mes-año):*")
    detalle_historico = ventas_mensuales_agrupadas[['Año', 'Mes', 'Ventas Mensuales']].copy()
    # Mapeo numérico → texto para el mes
    detalle_historico['Mes'] = detalle_historico['Mes'].map(mes_a_texto)
    # Renombramos la columna de Ventas Mensuales
    detalle_historico = detalle_historico.rename(
        columns={'Ventas Mensuales': 'Ventas Mensuales Totales'}
    )
    # Ordenamos primero por Año y luego por el número de mes (opcional)
    detalle_historico['MesNumero'] = ventas_mensuales_agrupadas['Mes']
    detalle_historico = detalle_historico.sort_values(['Año', 'MesNumero'])
    detalle_historico = detalle_historico.drop(columns=['MesNumero'])
    st.dataframe(
        detalle_historico.style.format({"Ventas Mensuales Totales": "{:,.2f}"}),
        use_container_width=True
    )

    # —— Pronóstico mes a mes para el año proximo_ano (solo Año, Mes, Pronóstico) ——
    st.write(f"*Pronóstico mes a mes para el año {proximo_ano}:*")
    pron_mostrar = pd.DataFrame({
        'Año': proximo_ano,
        'Mes': pronostico_df['Fecha_Mes'].dt.month.map(mes_a_texto),
        f'Pronóstico {proximo_ano}': pronostico_df['Pronóstico']
    })
    # (Opcional) Si quieres ordenar por el número de mes:
    pron_mostrar['MesNumero'] = pronostico_df['Fecha_Mes'].dt.month
    pron_mostrar = pron_mostrar.sort_values('MesNumero').drop(columns=['MesNumero'])

    st.dataframe(
        pron_mostrar.style.format({f'Pronóstico {proximo_ano}': "{:,.2f}"}),
        use_container_width=True
    )

# ── 13) EXPLICACIÓN FINAL ───────────────────────────────────────────────────────
'''st.markdown(
    """
    ---
    *¿Cómo funcionan los filtros en cascada?*  
    1. Primero seleccionas *País(es)*. Si no seleccionas ninguno, se usan todos los países.  
    2. Luego, el desplegable de *Cliente(s)* solo muestra aquellos clientes que pertenecen 
       a los países ya seleccionados (o a todos si no se seleccionó país).  
    3. Finalmente, el desplegable de *Producto(s)* solo muestra los productos que vende 
       el/los cliente(s) seleccionados (dentro del alcance del país ya elegido).  
    4. Con esa combinación (uno, dos o los tres filtros), se filtran las ventas y se calcula:  
       - La serie de *Ventas Mensuales Históricas* (suma por mes-año).  
       - El *Promedio Histórico por Mes* (enero – diciembre) para armar el pronóstico.  
    5. El pronóstico para cada mes de *2026* se calcula como  
       \[
         \frac{\text{Ventas Mensuales de ese mes en 2021} + \dots + \text{Ventas Mensuales de ese mes en 2025}}{5}.
       \]  
       Si el filtro reduce el rango de años (por ejemplo solo hay datos de 2022–2025 en ese subconjunto), 
       entonces el divisor será la cantidad de años realmente presentes.  
    6. El gráfico muestra la curva histórica y la línea de pronóstico para enero 2026 – diciembre 2026.
    """
)
'''
