import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import scipy.stats as stats

# 1. CONFIGURACIÓN INICIAL DE LA PÁGINA
st.set_page_config(
    page_title="Dashboard de Calidad y Tiempos - Toyota",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. CARGA Y LIMPIEZA DE DATOS
@st.cache_data
def load_data():
    # URL directa para descargar el CSV desde Google Sheets
    url_sheet = "https://docs.google.com/spreadsheets/d/1grY2OAJkokZ9EZ74VvBKE5CDIVBlv05W-pCCTFIfup4/export?format=csv"
    
    # Leemos directamente desde la web
    df = pd.read_csv(url_sheet)
    
    # Aislar y estandarizar columnas específicas solicitadas (E, F, G)
    df['Modelo_Estandarizado'] = df.iloc[:, 4].fillna('Sin Datos').astype(str).str.upper()
    df['WO_Modelo'] = df.iloc[:, 5].fillna('Sin Datos').astype(str).str.upper()
    df['Tipo_Trabajo'] = df.iloc[:, 6].fillna('Sin Datos').astype(str).str.upper()
    
    # Columna I (índice 8): Duración Ideal 
    # La limpiamos y convertimos a número
    if len(df.columns) > 8:
        df['Duracion_Ideal'] = pd.to_numeric(df.iloc[:, 8].astype(str).str.replace(',', '.'), errors='coerce')
    else:
        df['Duracion_Ideal'] = pd.NA

    # Crear columna Registro utilizando estrictamente la Columna V (índice 21)
    try:
        df['Registro'] = df.iloc[:, 21].fillna('Sin Registro').astype(str)
    except IndexError:
        df['Registro'] = 'Sin Registro'
    
    # Convertimos la 'Duración real (minutos)' a numérico, reemplazando comas por puntos
    if 'Duración real (minutos)' in df.columns:
        df['Duración real (minutos)'] = pd.to_numeric(df['Duración real (minutos)'].astype(str).str.replace(',', '.'), errors='coerce')
    
    # Columna K (índice 10): FechaEM - Base para el filtro de fechas
    df['FechaEM_Col_K'] = pd.to_datetime(df.iloc[:, 10], format='%d/%m/%Y', errors='coerce')
    
    # Crear columna de Mes-Año basada en la Columna K para el gráfico histórico
    df['Mes_Anio'] = df['FechaEM_Col_K'].dt.to_period('M').astype(str)
    
    return df

# 3. INTERFAZ DE USUARIO (UI)
def main():
    st.title("🚗 Panel de Tiempos Operativos y Calidad (Six Sigma)")
    st.markdown("---")
    
    try:
        with st.spinner('Cargando datos desde Google Sheets...'):
            df = load_data()
        
        # --- BARRA LATERAL (Filtros) ---
        st.sidebar.header("Filtros Globales")
        
        # 1. Territorio (Sucursal)
        territorios = df['Territorio de servicio: Nombre ↑'].dropna().unique().tolist()
        territorio_sel = st.sidebar.multiselect("Sucursal (Territorio):", territorios, default=territorios)
        
        # 2. Tipo de Trabajo (Columna G)
        tipos_trabajo = df['Tipo_Trabajo'].dropna().unique().tolist()
        trabajo_sel = st.sidebar.multiselect("Tipo de Trabajo:", tipos_trabajo, default=tipos_trabajo)
        
        # 3. Modelo (Columna E)
        modelos = df['Modelo_Estandarizado'].dropna().unique().tolist()
        modelo_sel = st.sidebar.multiselect("Modelo de Vehículo:", modelos, default=modelos)
        
        # 4. Orden Kilometro
        orden_km = sorted(df['Orden Kilometro'].dropna().unique().tolist())
        orden_km_sel = st.sidebar.multiselect("Orden Kilómetro:", orden_km, default=orden_km)

        # 5. Registro (Basado en Columna V)
        registros = df['Registro'].dropna().unique().tolist()
        registro_sel = st.sidebar.multiselect("Registro (Columna V):", registros, default=registros)
        
        # 6. Rango de Fechas (Basado estrictamente en Columna K)
        df_fechas_validas = df.dropna(subset=['FechaEM_Col_K'])
        if not df_fechas_validas.empty:
            min_date = df_fechas_validas['FechaEM_Col_K'].min().date()
            max_date = df_fechas_validas['FechaEM_Col_K'].max().date()
            
            if min_date == max_date:
                fecha_inicio, fecha_fin = st.sidebar.date_input("Rango FechaEM (Columna K):", value=(min_date, max_date), min_value=min_date, max_value=max_date)
            else:
                rango_fechas = st.sidebar.date_input("Rango FechaEM (Columna K):", value=(min_date, max_date), min_value=min_date, max_value=max_date)
                if len(rango_fechas) == 2:
                    fecha_inicio, fecha_fin = rango_fechas
                else:
                    fecha_inicio = fecha_fin = rango_fechas[0]
        else:
            st.warning("No hay fechas válidas en la Columna K.")
            return

        # --- APLICAR FILTROS GLOBALES ---
        df_filtrado = df[
            (df['Territorio de servicio: Nombre ↑'].isin(territorio_sel)) &
            (df['Tipo_Trabajo'].isin(trabajo_sel)) &
            (df['Modelo_Estandarizado'].isin(modelo_sel)) &
            (df['Orden Kilometro'].isin(orden_km_sel)) &
            (df['Registro'].isin(registro_sel)) &
            (df['FechaEM_Col_K'].dt.date >= fecha_inicio) &
            (df['FechaEM_Col_K'].dt.date <= fecha_fin)
        ].copy()

        if df_filtrado.empty:
            st.warning("⚠️ No hay datos que coincidan con los filtros seleccionados.")
            return

        # ==========================================
        # CREACIÓN DE PESTAÑAS (TABS)
        # ==========================================
        tab1, tab2 = st.tabs(["📊 Panel Operativo (General)", "📈 Análisis Six Sigma (Variación)"])

        # ------------------------------------------
        # PESTAÑA 1: PANEL OPERATIVO (Código anterior)
        # ------------------------------------------
        with tab1:
            st.subheader("Indicadores Generales")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Vehículos Filtrados", len(df_filtrado))
            with col2:
                promedio_general = df_filtrado['Duración real (minutos)'].mean()
                st.metric("Promedio Duración (min)", f"{promedio_general:.1f}" if pd.notna(promedio_general) else "0.0")
            with col3:
                max_duracion = df_filtrado['Duración real (minutos)'].max()
                st.metric("Pico Máx. Duración (min)", f"{max_duracion:.1f}" if pd.notna(max_duracion) else "0.0")

            st.markdown("---")
            
            st.subheader("Duración Real por Vehículo")
            fig_barras = px.bar(
                df_filtrado, x='Patente', y='Duración real (minutos)', color='Modelo_Estandarizado',
                hover_data=['Id Pre Orden', 'Orden Kilometro', 'Tipo_Trabajo', 'Registro'],
                title="Detalle de Duración Real"
            )
            st.plotly_chart(fig_barras, use_container_width=True)

            colA, colB = st.columns(2)
            with colA:
                st.subheader("Promedio de Duración por Modelo")
                promedio_modelo = df_filtrado.groupby('Modelo_Estandarizado')['Duración real (minutos)'].mean().reset_index()
                fig_prom_mod = px.bar(promedio_modelo, x='Modelo_Estandarizado', y='Duración real (minutos)', text_auto='.1f', color='Modelo_Estandarizado')
                st.plotly_chart(fig_prom_mod, use_container_width=True)

            with colB:
                st.subheader("Promedio de Duración por Mes")
                promedio_mes = df_filtrado.groupby('Mes_Anio')['Duración real (minutos)'].mean().reset_index().sort_values('Mes_Anio')
                promedio_mes = promedio_mes[promedio_mes['Mes_Anio'] != 'NaT'] 
                fig_prom_mes = px.bar(promedio_mes, x='Mes_Anio', y='Duración real (minutos)', text_auto='.1f', color_discrete_sequence=['#4B8BBE'])
                fig_prom_mes.update_xaxes(type='category')
                st.plotly_chart(fig_prom_mes, use_container_width=True)

            st.markdown("---")
            
            st.subheader("⚠️ Tiempos con Registro Incorrecto (Mudas Operativas)")
            df_incorrectos = df_filtrado[(df_filtrado['Duración real (minutos)'] <= 0) | (df_filtrado['Duración real (minutos)'].isna())].copy()
            
            if not df_incorrectos.empty:
                df_incorrectos = df_incorrectos.rename(columns={'Territorio de servicio: Nombre ↑': 'Sucursal'})
                resumen_incorrectos = df_incorrectos.groupby(['Registro', 'Sucursal', 'Modelo_Estandarizado', 'Tipo_Trabajo']).size().reset_index(name='Cantidad de Casos')
                resumen_incorrectos = resumen_incorrectos.sort_values(by='Cantidad de Casos', ascending=False)
                st.dataframe(resumen_incorrectos, use_container_width=True)
                
                with st.expander("🔎 Ver detalle completo de las órdenes afectadas"):
                    columnas_detalle = ['Patente', 'Id Pre Orden', 'Sucursal', 'Modelo_Estandarizado', 'Tipo_Trabajo', 'Duración real (minutos)', 'Registro', 'FechaEM']
                    st.dataframe(df_incorrectos[[col for col in columnas_detalle if col in df_incorrectos.columns]], use_container_width=True)
            else:
                st.success("¡Excelente! No se encontraron tiempos con registro incorrecto.")

        # ------------------------------------------
        # PESTAÑA 2: ANÁLISIS SIX SIGMA
        # ------------------------------------------
        with tab2:
            st.header("📈 Análisis de Variación del Proceso (Campana de Gauss)")
            st.markdown("Analizá la dispersión de los tiempos reales frente al tiempo ideal establecido en la **Columna I**.")
            
            # Filtro específico para esta pestaña: Seleccionar el Tiempo Ideal a analizar
            duraciones_ideales = sorted(df_filtrado['Duracion_Ideal'].dropna().unique().tolist())
            
            if not duraciones_ideales:
                st.warning("No se detectaron tiempos ideales (Columna I) para los filtros actuales.")
            else:
                duracion_seleccionada = st.selectbox(
                    "🎯 Seleccioná la Duración Ideal (Target) que deseas analizar:", 
                    options=duraciones_ideales,
                    help="Ejemplo: Si elegís '30', el gráfico analizará cómo variaron los trabajos que debían durar 30 minutos."
                )
                
                # Filtramos el dataframe para analizar solo los trabajos que tienen ese tiempo ideal
                df_sigma = df_filtrado[df_filtrado['Duracion_Ideal'] == duracion_seleccionada].copy()
                datos_reales = df_sigma['Duración real (minutos)'].dropna()
                
                if len(datos_reales) > 1: # Necesitamos al menos 2 datos para hacer estadística
                    # Calcular Media y Desviación Estándar (Sigma)
                    media_real = datos_reales.mean()
                    desviacion_estandar = datos_reales.std()
                    
                    # KPIs Six Sigma
                    s_col1, s_col2, s_col3, s_col4 = st.columns(4)
                    s_col1.metric("Cantidad de Casos Analizados", len(datos_reales))
                    s_col2.metric("Tiempo Ideal (Target)", f"{duracion_seleccionada} min")
                    s_col3.metric("Media Real Alcanzada (μ)", f"{media_real:.1f} min", delta=f"{(media_real - duracion_seleccionada):.1f} min", delta_color="inverse")
                    s_col4.metric("Variación / Desv. Estándar (σ)", f"{desviacion_estandar:.1f} min")
                    
                    # Generar la Campana de Gauss con Plotly
                    fig_sigma = go.Figure()
                    
                    # 1. Histograma (Distribución de los datos reales)
                    fig_sigma.add_trace(go.Histogram(
                        x=datos_reales, 
                        histnorm='probability density', 
                        name='Distribución Real', 
                        marker_color='#4B8BBE', 
                        opacity=0.75
                    ))
                    
                    # 2. Curva de Distribución Normal Teórica (Campana)
                    xmin, xmax = datos_reales.min(), datos_reales.max()
                    # Si todos los valores son iguales, agregamos un margen para poder graficar
                    if xmin == xmax:
                        xmin, xmax = xmin - 5, xmax + 5
                        
                    x_curve = np.linspace(xmin, xmax, 200)
                    y_curve = stats.norm.pdf(x_curve, media_real, desviacion_estandar)
                    
                    fig_sigma.add_trace(go.Scatter(
                        x=x_curve, y=y_curve, 
                        mode='lines', 
                        name='Campana de Gauss', 
                        line=dict(color='red', width=3)
                    ))
                    
                    # 3. Línea del Tiempo Ideal (Target)
                    fig_sigma.add_vline(x=duracion_seleccionada, line_dash="dash", line_color="green", annotation_text="Tiempo Ideal", annotation_position="top left")
                    
                    # 4. Línea de la Media Real
                    fig_sigma.add_vline(x=media_real, line_dash="solid", line_color="orange", annotation_text="Media Real", annotation_position="top right")
                    
                    fig_sigma.update_layout(
                        title=f"Distribución de Tiempos: Trabajos con Target de {duracion_seleccionada} min",
                        xaxis_title="Duración Real Registrada (minutos)",
                        yaxis_title="Densidad de Probabilidad (Frecuencia)",
                        barmode='overlay'
                    )
                    
                    st.plotly_chart(fig_sigma, use_container_width=True)
                    
                    # Detalle de variación por abajo
                    st.subheader(f"🔍 Detalle de Variación (Trabajos de {duracion_seleccionada} min)")
                    df_sigma['Variación (min)'] = df_sigma['Duración real (minutos)'] - df_sigma['Duracion_Ideal']
                    
                    columnas_variacion = ['Patente', 'Modelo_Estandarizado', 'Tipo_Trabajo', 'Registro', 'Duracion_Ideal', 'Duración real (minutos)', 'Variación (min)']
                    
                    # Formato de color para la tabla (Rojo si tardó más, verde si tardó menos o igual)
                    def color_variacion(val):
                        color = 'red' if val > 0 else 'green'
                        return f'color: {color}'
                    
                    st.dataframe(df_sigma[columnas_variacion].style.applymap(color_variacion, subset=['Variación (min)']), use_container_width=True)
                    
                else:
                    st.info("No hay suficientes datos válidos para generar una Campana de Gauss para esta duración (se requieren al menos 2 casos).")

    except Exception as e:
        st.error(f"Ocurrió un error al procesar los datos: {e}. Verificá los permisos del Google Sheet o las columnas.")

if __name__ == "__main__":
    main()
