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
    df = pd.read_csv("datos_servicios.csv")
    
    # Aislar y estandarizar columnas E, F y G
    df['Modelo_Estandarizado'] = df.iloc[:, 4].fillna('Sin Datos').astype(str).str.upper()
    df['WO_Modelo'] = df.iloc[:, 5].fillna('Sin Datos').astype(str).str.upper()
    df['Tipo_Trabajo'] = df.iloc[:, 6].fillna('Sin Datos').astype(str).str.upper()
    
    # Estandarizar columnas de Fecha y extraer Mes/Año para análisis
    columnas_fecha = ['FechaEM', 'Inicio real', 'Finalización real', 'Recepción Vehículo', 'Entrega Vehículo']
    for col in columnas_fecha:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format='%d/%m/%Y %H:%M', errors='coerce')
            
    # Crear columna de Mes-Año basada en FechaEM para el histórico
    df['Mes_Anio'] = df['FechaEM'].dt.to_period('M').astype(str)
    
    return df

# 3. INTERFAZ DE USUARIO (UI)
def main():
    st.title("🚗 Panel de Tiempos Operativos y Mudas")
    st.markdown("---")
    
    try:
        df = load_data()
        
        # --- BARRA LATERAL (Filtros) ---
        st.sidebar.header("Filtros Globales")
        
        # 1. Territorio
        territorios = df['Territorio de servicio: Nombre ↑'].dropna().unique().tolist()
        territorio_sel = st.sidebar.multiselect("Territorio:", territorios, default=territorios)
        
        # 2. Tipo de Trabajo (Columna G estandarizada)
        tipos_trabajo = df['Tipo_Trabajo'].dropna().unique().tolist()
        trabajo_sel = st.sidebar.multiselect("Tipo de Trabajo:", tipos_trabajo, default=tipos_trabajo)
        
        # 3. Modelo (Columna E estandarizada)
        modelos = df['Modelo_Estandarizado'].dropna().unique().tolist()
        modelo_sel = st.sidebar.multiselect("Modelo:", modelos, default=modelos)
        
        # 4. Orden Kilometro
        orden_km = sorted(df['Orden Kilometro'].dropna().unique().tolist())
        orden_km_sel = st.sidebar.multiselect("Orden Kilometro:", orden_km, default=orden_km)
        
        # 5. FechaEM (Rango)
        min_date = df['FechaEM'].min().date()
        max_date = df['FechaEM'].max().date()
        fecha_inicio, fecha_fin = st.sidebar.date_input(
            "Rango FechaEM:",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )

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

        # --- KPIs ---
        st.subheader("Indicadores Generales")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Vehículos", len(df_filtrado))
        with col2:
            promedio_general = df_filtrado['Duración real (minutos)'].mean()
            st.metric("Promedio Duración (min)", f"{promedio_general:.1f}")
        with col3:
            max_duracion = df_filtrado['Duración real (minutos)'].max()
            st.metric("Pico Máx. Duración (min)", f"{max_duracion:.1f}")

        st.markdown("---")

        # --- GRÁFICOS ---
        
        # 1. Gráfico de Barras: Duración real por cada orden (Patente/VIN como eje X)
        st.subheader("Duración Real por Vehículo")
        fig_barras = px.bar(
            df_filtrado, 
            x='Patente', # Podés cambiarlo a 'Id Pre Orden' si preferís
            y='Duración real (minutos)', 
            color='Modelo_Estandarizado',
            hover_data=['Id Pre Orden', 'Orden Kilometro', 'Tipo_Trabajo', 'FechaEM'],
            title="Detalle de Duración Real (Filtros aplicados)"
        )
        st.plotly_chart(fig_barras, use_container_width=True)

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
                color='Modelo_Estandarizado'
            )
            st.plotly_chart(fig_prom_mod, use_container_width=True)

        with colB:
            # 3. Promedio por Mes
            st.subheader("Promedio de Duración por Mes")
            promedio_mes = df_filtrado.groupby('Mes_Anio')['Duración real (minutos)'].mean().reset_index().sort_values('Mes_Anio')
            fig_prom_mes = px.bar(
                promedio_mes, 
                x='Mes_Anio', 
                y='Duración real (minutos)',
                text_auto='.1f'
            )
            st.plotly_chart(fig_prom_mes, use_container_width=True)

        st.markdown("---")
        
        # 4. Histórico por Modelo (Tendencia en el tiempo)
        st.subheader("Histórico de Duración por Modelo (Tendencia)")
        # Agrupamos por Mes y Modelo para ver la evolución
        historico = df_filtrado.groupby(['Mes_Anio', 'Modelo_Estandarizado'])['Duración real (minutos)'].mean().reset_index().sort_values('Mes_Anio')
        fig_historico = px.line(
            historico, 
            x='Mes_Anio', 
            y='Duración real (minutos)', 
            color='Modelo_Estandarizado',
            markers=True,
            title="Evolución del Promedio de Duración a lo largo de los meses"
        )
        st.plotly_chart(fig_historico, use_container_width=True)

    except FileNotFoundError:
        st.error("⚠️ No se encontró el archivo 'datos_servicios.csv'.")
    except Exception as e:
        st.error(f"Ocurrió un error al procesar los datos: {e}")

if __name__ == "__main__":
    main()
