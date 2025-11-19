import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta, date
import plotly.graph_objects as go
from io import BytesIO
import locale

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

# Funkcja walidująca datę wprowadzoną przez użytkownika
def parse_validate_date(value, label: str = "Data", min_date: date | None = None, max_date: date | None = None) -> date:
    """Spróbuj sparsować i zwalidować wejściową datę.

    - akceptuje obiekt `date` / `datetime`, albo string (próbuje `pd.to_datetime` z dayfirst=True)
    - w razie błędu pokaże komunikat w sidebar i zatrzyma aplikację
    - sprawdza granice `min_date` i `max_date` jeżeli podane
    """
    import re
    import unicodedata

    def _normalize(s: str) -> str:
        # usuń diakrytyczne znaki, zamień na małe litery
        nf = unicodedata.normalize('NFKD', s)
        return ''.join(ch for ch in nf if not unicodedata.combining(ch)).lower()

    # mapa polskich nazw miesięcy (nominative i genitive, krótkie formy) -> English month
    month_map = {
        'styczen': 'January', 'stycznia': 'January', 'sty': 'January',
        'luty': 'February', 'lutego': 'February', 'lut': 'February',
        'marzec': 'March', 'marca': 'March', 'mar': 'March',
        'kwiecien': 'April', 'kwietnia': 'April', 'kwi': 'April',
        'maj': 'May', 'maja': 'May',
        'czerwiec': 'June', 'czerwca': 'June', 'cze': 'June',
        'lipiec': 'July', 'lipca': 'July', 'lip': 'July',
        'sierpien': 'August', 'sierpnia': 'August', 'sie': 'August',
        'wrzesien': 'September', 'wrzesnia': 'September', 'wrz': 'September',
        'pazdziernik': 'October', 'pazdziernika': 'October', 'paz': 'October', 'pazdz': 'October',
        'listopad': 'November', 'listopada': 'November', 'lis': 'November',
        'grudzien': 'December', 'grudnia': 'December', 'gru': 'December',
    }

    try:
        # jeśli to już obiekt datetime/date
        if isinstance(value, (datetime, date)):
            parsed = pd.to_datetime(value).date()
        else:
            s = str(value).strip()
            # normalize input to remove diacritics for matching
            s_norm = _normalize(s)

            # replace any polish month word with English month name
            pattern = r"\b(" + "|".join(re.escape(k) for k in month_map.keys()) + r")\b"
            def _repl(m):
                return month_map.get(m.group(1), m.group(1))

            s_repl = re.sub(pattern, _repl, s_norm, flags=re.IGNORECASE)

            # pandas can parse the transformed string with dayfirst=True
            parsed = pd.to_datetime(s_repl, dayfirst=True, errors='raise').date()
    except Exception as e:
        st.sidebar.error(f"Błędna data dla '{label}': {value}. Podaj poprawną datę. ({e})")
        st.stop()

    if min_date is not None and parsed < min_date:
        st.sidebar.error(f"{label} nie może być wcześniej niż {min_date.isoformat()}")
        st.stop()
    if max_date is not None and parsed > max_date:
        st.sidebar.error(f"{label} nie może być późniejsza niż {max_date.isoformat()}")
        st.stop()

    return parsed

# Walidacja daty wprowadzonej przez użytkownika (dodatkowo sprawdzamy zakres danych API)
min_api_date = datetime(2013, 1, 2).date()
max_allowed = datetime.now().date()

start_date = parse_validate_date(start_date, label="Data początkowa", min_date=min_api_date, max_date=max_allowed)
end_date = parse_validate_date(end_date, label="Data końcowa", min_date=min_api_date, max_date=max_allowed)

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
    



    # Ustaw polskie locale (dodaj na początku pliku, po importach)
    try:
        locale.setlocale(locale.LC_TIME, 'pl_PL.UTF-8')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, 'Polish_Poland.1250')  # Dla Windows
        except locale.Error:
            pass  # Jeśli locale nie jest dostępne, zostaw angielski


        # Wykres interaktywny
    st.subheader("📊 Wykres kursu ceny złota")

    # Polskie nazwy miesięcy
    polish_months = {
        'Jan': 'Sty', 'Feb': 'Lut', 'Mar': 'Mar', 'Apr': 'Kwi',
        'May': 'Maj', 'Jun': 'Cze', 'Jul': 'Lip', 'Aug': 'Sie',
        'Sep': 'Wrz', 'Oct': 'Paź', 'Nov': 'Lis', 'Dec': 'Gru'
    }

    # Sformatuj daty po polsku dla osi X
    df['data_display'] = df['data'].dt.strftime('%d %b %Y')
    for eng, pl in polish_months.items():
        df['data_display'] = df['data_display'].str.replace(eng, pl)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['data'],
        y=df['cena'],
        mode='lines+markers',
        name='Cena złota',
        line=dict(color='gold', width=2),
        marker=dict(size=6),
        customdata=df['data_display'],
        hovertemplate='<b>Data:</b> %{customdata}<br><b>Cena:</b> %{y:.2f} PLN<extra></extra>'
    ))

    # Wybierz co którą datę pokazać (np. co 3 dni dla czytelności)
    step = max(1, len(df) // 10)
    tickvals = df['data'].iloc[::step]
    ticktext = df['data_display'].iloc[::step]

    fig.update_layout(
        title="Kurs ceny złota (1 gram)",
        xaxis_title="Data",
        yaxis_title="Cena (PLN)",
        hovermode='closest',
        height=500,
        template="plotly_white",
        xaxis=dict(
            tickmode='array',
            tickvals=tickvals,
            ticktext=ticktext,
            tickangle=-45
        )
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
