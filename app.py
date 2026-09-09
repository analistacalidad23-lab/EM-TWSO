import streamlit as st
import pandas as pd

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
    # Para arrancar, asumimos que descargás la hoja como 'datos_servicios.csv'
    # Si preferís conectarlo directo a Google Sheets mediante gspread, avisame y sumamos la API.
    df = pd.read_csv("datos_servicios.csv")
    
    # Aislar y estandarizar columnas E, F y G solicitadas para auditoría
    # E: Modelo | F: Work Order: Vehículo: Modelo | G: Tipo de trabajo.
    df['Modelo_Estandarizado'] = df.iloc[:, 4].fillna('Sin Datos').astype(str).str.upper()
    df['WO_Modelo'] = df.iloc[:, 5].fillna('Sin Datos').astype(str).str.upper()
    df['Tipo_Trabajo'] = df.iloc[:, 6].fillna('Sin Datos').astype(str).str.upper()
    
    # Estandarizar columnas de Tiempos para cálculos de Mudas y flujos
    columnas_fecha = ['FechaEM', 'Inicio real', 'Finalización real', 'Recepción Vehículo', 'Entrega Vehículo']
    for col in columnas_fecha:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format='%d/%m/%Y %H:%M', errors='coerce')
            
    # Calcular el tiempo real de estadía del vehículo en taller (Entrega - Recepción)
    if 'Entrega Vehículo' in df.columns and 'Recepción Vehículo' in df.columns:
        df['Estadia_Total_Minutos'] = (df['Entrega Vehículo'] - df['Recepción Vehículo']).dt.total_seconds() / 60
        
    return df

# 3. INTERFAZ DE USUARIO (UI)
def main():
    st.title("🚗 Panel de Control Operativo - Taller")
    st.markdown("---")
    
    try:
        df = load_data()
        
        # BARRA LATERAL (Filtros)
        st.sidebar.header("Filtros de Gestión")
        
        # Filtro por Modelo (Columna E)
        modelos_unicos = df['Modelo_Estandarizado'].unique().tolist()
        modelo_seleccionado = st.sidebar.multiselect("Filtrar por Modelo de Vehículo:", modelos_unicos, default=modelos_unicos)
        
        # Aplicar filtros
        df_filtrado = df[df['Modelo_Estandarizado'].isin(modelo_seleccionado)]
        
        # KPIs PRINCIPALES
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Vehículos Procesados", len(df_filtrado))
        with col2:
            promedio_duracion = df_filtrado['Duración real (minutos)'].mean()
            st.metric("Promedio Duración Real (min)", f"{promedio_duracion:.1f}" if pd.notna(promedio_duracion) else "0")
        with col3:
            # Aquí podemos añadir tu lógica específica para las Mudas luego
            st.metric("Objetivo de Calidad 2026", "En Progreso") 
        with col4:
            st.metric("Tipo de Trabajo Principal", df_filtrado['Tipo_Trabajo'].mode()[0] if not df_filtrado.empty else "N/A")
            
        st.markdown("### 📋 Vista de Datos Estructurados (Columnas E, F, G y Tiempos)")
        # Mostramos las columnas aisladas junto con las de seguimiento de tiempo
        columnas_mostrar = ['Modelo_Estandarizado', 'WO_Modelo', 'Tipo_Trabajo', 'Duración real (minutos)', 'Inicio real', 'Finalización real']
        st.dataframe(df_filtrado[columnas_mostrar], use_container_width=True)

    except FileNotFoundError:
        st.warning("⚠️ No se encontró el archivo 'datos_servicios.csv'. Por favor, asegurate de tenerlo en la misma carpeta que el script app.py.")

if __name__ == "__main__":
    main()
