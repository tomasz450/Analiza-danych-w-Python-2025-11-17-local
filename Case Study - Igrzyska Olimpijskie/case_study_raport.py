import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go
from io import BytesIO

# Konfiguracja strony
st.set_page_config(
    page_title="Kursy ceny złota - NBP",
    page_icon="🏅",
    layout="wide"
)

st.title("📊 Kursy ceny złota z API NBP")
st.markdown("Aplikacja pobiera dane o cenach złota z API Narodowego Banku Polskiego")

# Funkcja do pobierania danych z API NBP
def get_gold_prices(start_date, end_date):
    """
    Pobiera kursy ceny złota z API NBP dla zadanego zakresu dat
    """
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    url = f"https://api.nbp.pl/api/cenyzlota/{start_str}/{end_str}/"
    
    try:
        response = requests.get(url, headers={"Accept": "application/json"})
        
        if response.status_code == 200:
            data = response.json()
            return data
        elif response.status_code == 404:
            st.error("Brak danych dla wybranego zakresu dat")
            return None
        else:
            st.error(f"Błąd API: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Wystąpił błąd: {str(e)}")
        return None

# Funkcja do konwersji DataFrame do Excel
def to_excel(df):
    """
    Konwertuje DataFrame do pliku Excel w pamięci
    """
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Ceny złota')
    output.seek(0)
    return output

# Interfejs użytkownika - wybór dat
st.sidebar.header("⚙️ Parametry")

col1, col2 = st.sidebar.columns(2)

with col1:
    start_date = st.date_input(
        "Data początkowa",
        value=datetime.now() - timedelta(days=30),
        max_value=datetime.now(),
        format="YYYY-MM-DD"
    )

with col2:
    end_date = st.date_input(
        "Data końcowa",
        value=datetime.now(),
        max_value=datetime.now(),
        format="YYYY-MM-DD"
    )

# Walidacja dat
if start_date > end_date:
    st.sidebar.error("Data początkowa nie może być późniejsza niż data końcowa!")
    st.stop()

# Sprawdzenie limitu 93 dni
date_diff = (end_date - start_date).days
if date_diff > 93:
    st.sidebar.warning(f"⚠️ Wybrany zakres: {date_diff} dni. API NBP pozwala na maksymalnie 93 dni.")
    st.stop()

# Przycisk do pobierania danych
if st.sidebar.button("🔄 Pobierz dane", type="primary"):
    with st.spinner("Pobieranie danych z API NBP..."):
        data = get_gold_prices(start_date, end_date)
        
        if data:
            # Tworzenie DataFrame
            df = pd.DataFrame(data)
            df['data'] = pd.to_datetime(df['data'])
            df = df.sort_values('data')
            
            # Zapisanie w session_state
            st.session_state['gold_data'] = df
            st.success(f"✅ Pobrano {len(df)} rekordów")

# Wyświetlanie danych jeśli są dostępne
if 'gold_data' in st.session_state:
    df = st.session_state['gold_data']
    
    # Statystyki
    st.subheader("📈 Statystyki")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Średnia cena", f"{df['cena'].mean():.2f} PLN")
    with col2:
        st.metric("Cena minimalna", f"{df['cena'].min():.2f} PLN")
    with col3:
        st.metric("Cena maksymalna", f"{df['cena'].max():.2f} PLN")
    with col4:
        st.metric("Liczba notowań", len(df))
    
    # Wykres interaktywny
    st.subheader("📊 Wykres kursu ceny złota")
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['data'],
        y=df['cena'],
        mode='lines+markers',
        name='Cena złota',
        line=dict(color='gold', width=2),
        marker=dict(size=6)
    ))
    
    fig.update_layout(
        title="Kurs ceny złota (1 gram)",
        xaxis_title="Data",
        yaxis_title="Cena (PLN)",
        hovermode='x unified',
        height=500,
        template="plotly_white"
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Tabela z danymi
    st.subheader("📋 Dane tabelaryczne")
    st.dataframe(
        df.style.format({"cena": "{:.2f} PLN", "data": lambda x: x.strftime("%Y-%m-%d")}),
        use_container_width=True,
        height=400
    )
    
    # Przycisk do pobierania Excel
    st.subheader("💾 Eksport danych")
    
    excel_file = to_excel(df)
    
    st.download_button(
        label="⬇️ Pobierz dane do Excel (.xlsx)",
        data=excel_file,
        file_name=f"ceny_zlota_{start_date}_{end_date}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

else:
    st.info("👈 Wybierz zakres dat i kliknij 'Pobierz dane' aby rozpocząć")

# Informacje w stopce
st.sidebar.markdown("---")
st.sidebar.markdown("### ℹ️ Informacje")
st.sidebar.markdown("""
- API NBP: https://api.nbp.pl
- Maksymalny zakres: 93 dni
- Dane archiwalne od 2013-01-02
- Cena za 1 gram złota
""")
