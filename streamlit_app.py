import streamlit as st
import pandas as pd
import plotly.express as px

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
    # URL directa para descargar el CSV desde Google Sheets automáticamente
    url_sheet = "https://docs.google.com/spreadsheets/d/1grY2OAJkokZ9EZ74VvBKE5CDIVBlv05W-pCCTFIfup4/export?format=csv"
    
    # Leemos directamente desde la web
    df = pd.read_csv(url_sheet)
    
    # Aislar y estandarizar columnas E, F y G para sectores a auditar
    df['Modelo_Estandarizado'] = df.iloc[:, 4].fillna('Sin Datos').astype(str).str.upper()
    df['WO_Modelo'] = df.iloc[:, 5].fillna('Sin Datos').astype(str).str.upper()
    df['Tipo_Trabajo'] = df.iloc[:, 6].fillna('Sin Datos').astype(str).str.upper()
    
    # Estandarizar columnas de Fecha y extraer Mes/Año para análisis
    columnas_fecha = ['FechaEM', 'Inicio real', 'Finalización real', 'Recepción Vehículo', 'Entrega Vehículo']
    for col in columnas_fecha:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format='%d/%m/%Y %H:%M', errors='coerce')
            
    # Crear columna de Mes-Año basada en FechaEM para el histórico (Formato YYYY-MM)
    df['Mes_Anio'] = df['FechaEM'].dt.to_period('M').astype(str)
    
    return df

# 3. INTERFAZ DE USUARIO (UI)
def main():
    st.title("🚗 Panel de Tiempos Operativos y Mudas")
    st.markdown("---")
    
    try:
        with st.spinner('Cargando datos desde Google Sheets...'):
            df = load_data()
        
        # --- BARRA LATERAL (Filtros) ---
        st.sidebar.header("Filtros Globales")
        
        # 1. Territorio
        territorios = df['Territorio de servicio: Nombre ↑'].dropna().unique().tolist()
        territorio_sel = st.sidebar.multiselect("Territorio de Servicio:", territorios, default=territorios)
        
        # 2. Tipo de Trabajo (Columna G)
        tipos_trabajo = df['Tipo_Trabajo'].dropna().unique().tolist()
        trabajo_sel = st.sidebar.multiselect("Tipo de Trabajo:", tipos_trabajo, default=tipos_trabajo)
        
        # 3. Modelo (Columna E)
        modelos = df['Modelo_Estandarizado'].dropna().unique().tolist()
        modelo_sel = st.sidebar.multiselect("Modelo de Vehículo:", modelos, default=modelos)
        
        # 4. Orden Kilometro
        orden_km = sorted(df['Orden Kilometro'].dropna().unique().tolist())
        orden_km_sel = st.sidebar.multiselect("Orden Kilómetro:", orden_km, default=orden_km)
        
        # 5. FechaEM (Rango)
        # Limpiamos los nulos temporalmente solo para poder armar el selector de fechas
        df_fechas_validas = df.dropna(subset=['FechaEM'])
        if not df_fechas_validas.empty:
            min_date = df_fechas_validas['FechaEM'].min().date()
            max_date = df_fechas_validas['FechaEM'].max().date()
            
            # Control por si min_date y max_date son el mismo día
            if min_date == max_date:
                fecha_inicio, fecha_fin = st.sidebar.date_input(
                    "Rango FechaEM:", 
                    value=(min_date, max_date), 
                    min_value=min_date, 
                    max_value=max_date
                )
            else:
                rango_fechas = st.sidebar.date_input(
                    "Rango FechaEM:",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )
                # Manejar cuando el usuario está eligiendo la fecha y todavía no seleccionó la segunda
                if len(rango_fechas) == 2:
                    fecha_inicio, fecha_fin = rango_fechas
                else:
                    fecha_inicio = fecha_fin = rango_fechas[0]
        else:
            st.warning("No hay fechas válidas en la columna FechaEM.")
            return

        # --- APLICAR FILTROS ---
        df_filtrado = df[
            (df['Territorio de servicio: Nombre ↑'].isin(territorio_sel)) &
            (df['Tipo_Trabajo'].isin(trabajo_sel)) &
            (df['Modelo_Estandarizado'].isin(modelo_sel)) &
            (df['Orden Kilometro'].isin(orden_km_sel)) &
            (df['FechaEM'].dt.date >= fecha_inicio) &
            (df['FechaEM'].dt.date <= fecha_fin)
        ]

        if df_filtrado.empty:
            st.warning("⚠️ No hay datos que coincidan con los filtros seleccionados.")
            return

        # --- KPIs PRINCIPALES ---
        st.subheader("Indicadores Generales")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Vehículos Filtrados", len(df_filtrado))
        with col2:
            promedio_general = df_filtrado['Duración real (minutos)'].mean()
            st.metric("Promedio Duración (min)", f"{promedio_general:.1f}")
        with col3:
            max_duracion = df_filtrado['Duración real (minutos)'].max()
            st.metric("Pico Máx. Duración (min)", f"{max_duracion:.1f}")

        st.markdown("---")

        # --- GRÁFICOS ---
        
        # 1. Gráfico de Barras: Duración real por cada orden
        st.subheader("Duración Real por Vehículo")
        fig_barras = px.bar(
            df_filtrado, 
            x='Patente', 
            y='Duración real (minutos)', 
            color='Modelo_Estandarizado',
            hover_data=['Id Pre Orden', 'Orden Kilometro', 'Tipo_Trabajo', 'FechaEM'],
            title="Detalle de Duración Real (Muestra las barras por cada vehículo ingresado)"
        )
        st.plotly_chart(fig_barras, use_container_width=True)

        # Dividimos la pantalla en dos columnas para los promedios
        colA, colB = st.columns(2)
        
        with colA:
            # 2. Promedio por Modelo
            st.subheader("Promedio de Duración por Modelo")
            promedio_modelo = df_filtrado.groupby('Modelo_Estandarizado')['Duración real (minutos)'].mean().reset_index()
            fig_prom_mod = px.bar(
                promedio_modelo, 
                x='Modelo_Estandarizado', 
                y='Duración real (minutos)',
                text_auto='.1f',
                color='Modelo_Estandarizado',
                labels={'Modelo_Estandarizado': 'Modelo', 'Duración real (minutos)': 'Promedio (min)'}
            )
            st.plotly_chart(fig_prom_mod, use_container_width=True)

        with colB:
            # 3. Promedio por Mes
            st.subheader("Promedio de Duración por Mes")
            promedio_mes = df_filtrado.groupby('Mes_Anio')['Duración real (minutos)'].mean().reset_index().sort_values('Mes_Anio')
            # Filtramos los 'NaT' por si alguna fecha quedó vacía
            promedio_mes = promedio_mes[promedio_mes['Mes_Anio'] != 'NaT'] 
            fig_prom_mes = px.bar(
                promedio_mes, 
                x='Mes_Anio', 
                y='Duración real (minutos)',
                text_auto='.1f',
                labels={'Mes_Anio': 'Mes y Año', 'Duración real (minutos)': 'Promedio (min)'},
                color_discrete_sequence=['#4B8BBE']
            )
            fig_prom_mes.update_xaxes(type='category')
            st.plotly_chart(fig_prom_mes, use_container_width=True)

        st.markdown("---")
        
        # 4. Histórico por Modelo (Tendencia en el tiempo)
        st.subheader("Histórico de Duración por Modelo (Tendencia Mensual)")
        historico = df_filtrado.groupby(['Mes_Anio', 'Modelo_Estandarizado'])['Duración real (minutos)'].mean().reset_index().sort_values('Mes_Anio')
        historico = historico[historico['Mes_Anio'] != 'NaT']
        fig_historico = px.line(
            historico, 
            x='Mes_Anio', 
            y='Duración real (minutos)', 
            color='Modelo_Estandarizado',
            markers=True,
            labels={'Mes_Anio': 'Mes y Año', 'Duración real (minutos)': 'Promedio de Duración (min)'}
        )
        fig_historico.update_xaxes(type='category')
        st.plotly_chart(fig_historico, use_container_width=True)

    except Exception as e:
        st.error(f"Ocurrió un error al procesar los datos: {e}. Verificá los permisos del Google Sheet o las columnas.")

if __name__ == "__main__":
    main()
