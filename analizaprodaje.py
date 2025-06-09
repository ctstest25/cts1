import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go # Import za provjeru tipa grafikona
import re
from datetime import datetime, date # Dodat import za date
from io import BytesIO
import base64
import numpy as np # Import numpy za pd.api.types

st.set_page_config(page_title="Analiza Prodaje po poslovnicama i subagentima", layout="wide")
st.title("📊 Analiza Excel podataka iz TourVisio alata za prodaju")

# CSV Download funkcija je uklonjena prema zahtjevu korisnika

# =======================
# Funkcija za generisanje Excel fajla
# =======================
def generate_excel_download(df_main_data, user_comment=None, charts_data_to_export=None, filename="analiza.xlsx", tip_fajla_za_export=""):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_to_excel = df_main_data.copy()
        
        cols_to_drop = ['Agency_normalized', 'Datum_obj', 'Payment_normalized', 'Package_lower']
        for col in cols_to_drop:
            if col in df_to_excel.columns:
                df_to_excel = df_to_excel.drop(columns=[col], errors='ignore')

        if "ProcenatPopunjenosti" in df_to_excel.columns and tip_fajla_za_export == "Izvještaj Aviokompanije":
            df_to_excel["ProcenatPopunjenosti"] = pd.to_numeric(df_to_excel["ProcenatPopunjenosti"], errors='coerce').fillna(0) / 100.0

        if tip_fajla_za_export == "Izvještaj Aviokompanije" and not df_to_excel.empty:
            if all(col in df_to_excel.columns for col in ["Zakup", "Prodato", "Slobodno"]):
                temp_df_for_sum = df_main_data.copy() 
                if 'Datum_obj' in temp_df_for_sum.columns:
                    temp_df_for_sum_calc = temp_df_for_sum.drop(columns=['Datum_obj'], errors='ignore')
                else:
                    temp_df_for_sum_calc = temp_df_for_sum
                
                total_zakup = temp_df_for_sum_calc["Zakup"].sum()
                total_prodato = temp_df_for_sum_calc["Prodato"].sum()
                total_slobodno = temp_df_for_sum_calc["Slobodno"].sum()
                total_procenat_val_for_excel = (total_prodato / total_zakup) if total_zakup > 0 else 0 
                
                total_row_data = {col: "" for col in df_to_excel.columns} 
                first_text_col_index = 0
                for i, dtype in enumerate(df_to_excel.dtypes): 
                    if not pd.api.types.is_numeric_dtype(dtype):
                        first_text_col_index = i
                        break
                total_row_data[df_to_excel.columns[first_text_col_index]] = "UKUPNO"
                total_row_data["Zakup"] = total_zakup
                total_row_data["Prodato"] = total_prodato
                total_row_data["Slobodno"] = total_slobodno
                if "ProcenatPopunjenosti" in df_to_excel.columns:
                    total_row_data["ProcenatPopunjenosti"] = total_procenat_val_for_excel 
                
                total_row_df = pd.DataFrame([total_row_data])
                df_to_excel = pd.concat([df_to_excel, total_row_df], ignore_index=True)
        
        profit_paid_label = ""
        profit_paid_value = None
        if tip_fajla_za_export == "Analiza Sunexpress leta Main Filter" and not df_main_data.empty: 
            if "Profit" in df_main_data.columns and "Payment" in df_main_data.columns:
                df_temp_profit = df_main_data.copy() 
                df_temp_profit["Profit"] = pd.to_numeric(df_temp_profit["Profit"], errors="coerce").fillna(0)
                
                paid_profit_sum = df_temp_profit[df_temp_profit["Payment"].astype(str).str.lower() == "paid"]["Profit"].sum()
                profit_paid_label = "Ukupan profit za Paid rezervacije:"
                profit_paid_value = paid_profit_sum

        df_to_excel.to_excel(writer, index=False, sheet_name='DetaljniPodaci')
        workbook = writer.book
        worksheet_detailed_data = writer.sheets['DetaljniPodaci']
        
        num_format = workbook.add_format({'num_format': '#,##0.00'})
        int_format = workbook.add_format({'num_format': '#,##0'})
        percent_format_excel = workbook.add_format({'num_format': '0.00%'}) 
        bold_format = workbook.add_format({'bold': True})

        if not df_to_excel.empty:
            for col_num, value in enumerate(df_to_excel.columns.values):
                column_len = max(len(str(value)), 12) 
                current_format_to_apply = None
                
                if value == "ProcenatPopunjenosti" and tip_fajla_za_export == "Izvještaj Aviokompanije":
                    red_fill_format = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006', 'num_format': '0.00%'})
                    yellow_fill_format = workbook.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C6500', 'num_format': '0.00%'})
                    default_percent_format = workbook.add_format({'num_format': '0.00%'})

                    data_rows_count = len(df_to_excel)
                    end_row_for_conditional_formatting = data_rows_count - 1 
                    
                    is_last_row_total = False
                    if data_rows_count > 0:
                        first_col_name_check = df_to_excel.columns[0] if len(df_to_excel.columns) > 0 else None
                        if first_col_name_check and isinstance(df_to_excel.iloc[-1][first_col_name_check], str) and df_to_excel.iloc[-1][first_col_name_check] == "UKUPNO":
                            is_last_row_total = True
                            end_row_for_conditional_formatting = data_rows_count - 2 

                    if end_row_for_conditional_formatting >= 1: 
                        worksheet_detailed_data.conditional_format(1, col_num, end_row_for_conditional_formatting , col_num, 
                                                     {'type': 'cell', 'criteria': '<', 'value': 0.20, 'format': red_fill_format})
                        worksheet_detailed_data.conditional_format(1, col_num, end_row_for_conditional_formatting, col_num,
                                                     {'type': 'cell', 'criteria': 'between', 'minimum': 0.20, 'maximum': 0.3999, 'format': yellow_fill_format})
                        worksheet_detailed_data.conditional_format(1, col_num, end_row_for_conditional_formatting, col_num,
                                                     {'type': 'cell', 'criteria': '>=', 'value': 0.40, 'format': default_percent_format})
                    
                    worksheet_detailed_data.set_column(col_num, col_num, column_len, percent_format_excel)
                    continue 

                elif "Amount" in value or "Price" in value or "Cijena" in value or "Iznos" in value or "Profit" in value : 
                    current_format_to_apply = num_format
                    column_len = max(column_len, 15)
                elif "PAX" in value or "Adult" in value or "Child" in value or "Infant" in value or "Broj" in value or "Zakup" in value or "Prodato" in value or "Slobodno" in value:
                     current_format_to_apply = int_format
                     column_len = max(column_len,10)
                else:
                     column_len = max(column_len,18)
                worksheet_detailed_data.set_column(col_num, col_num, column_len, current_format_to_apply)
            
            if profit_paid_label and profit_paid_value is not None:
                last_data_row_index = len(df_to_excel) 
                profit_col_index = -1
                try:
                    profit_col_index = df_to_excel.columns.get_loc("Profit") 
                except KeyError:
                    if "Profit" in df_main_data.columns: 
                         profit_col_index_original = df_main_data.columns.get_loc("Profit")
                         if df_main_data.columns[profit_col_index_original] in df_to_excel.columns:
                             profit_col_index = df_to_excel.columns.get_loc(df_main_data.columns[profit_col_index_original])

                if profit_col_index != -1 and profit_col_index < len(df_to_excel.columns): 
                    label_col_index = profit_col_index -1 if profit_col_index > 0 else 0
                    worksheet_detailed_data.write(last_data_row_index, label_col_index, profit_paid_label, bold_format)
                    worksheet_detailed_data.write(last_data_row_index, profit_col_index, profit_paid_value, num_format)
                elif profit_col_index !=-1 : 
                    last_col_idx = len(df_to_excel.columns)
                    worksheet_detailed_data.write(last_data_row_index, last_col_idx, profit_paid_label, bold_format)
                    worksheet_detailed_data.write(last_data_row_index, last_col_idx + 1, profit_paid_value, num_format)

        if user_comment:
            worksheet_comment = workbook.add_worksheet('Komentar')
            worksheet_comment.set_column('A:A', 100) 
            wrap_format = workbook.add_format({'text_wrap': True, 'valign': 'top'})
            worksheet_comment.write('A1', user_comment, wrap_format)

        if charts_data_to_export and isinstance(charts_data_to_export, dict):
            for chart_name, chart_info in charts_data_to_export.items():
                fig = chart_info.get("figure")
                source_df_chart_original = chart_info.get("data") 

                if fig is not None and isinstance(fig, go.Figure) and hasattr(fig, 'to_image'):
                    try:
                        img_bytes = fig.to_image(format="png", width=1000, height=700, scale=1.5) 
                        if img_bytes and isinstance(img_bytes, bytes) and len(img_bytes) > 0:
                            img_data = BytesIO(img_bytes)
                            img_data.seek(0)
                            
                            clean_chart_name = re.sub(r'[\\/*?:\[\]]', '', chart_name)
                            clean_chart_name = clean_chart_name[:31] 

                            worksheet_chart = workbook.add_worksheet(clean_chart_name)
                            f_name_chart = clean_chart_name.replace(" ", "_") + ".png" 
                            worksheet_chart.insert_image('A1', f_name_chart, {'image_data': img_data})

                            if source_df_chart_original is not None and not source_df_chart_original.empty:
                                start_row_for_df = 38 
                                
                                df_chart_data_to_write = source_df_chart_original.copy()
                                if 'Datum_obj' in df_chart_data_to_write.columns:
                                    df_chart_data_to_write = df_chart_data_to_write.drop(columns=['Datum_obj'])
                                
                                if "ProcenatPopunjenosti" in df_chart_data_to_write.columns and tip_fajla_za_export == "Izvještaj Aviokompanije":
                                    df_chart_data_to_write["ProcenatPopunjenosti"] = pd.to_numeric(df_chart_data_to_write["ProcenatPopunjenosti"], errors='coerce').fillna(0) / 100.0

                                if not df_chart_data_to_write.empty:
                                    numeric_cols_chart = df_chart_data_to_write.select_dtypes(include='number').columns 
                                    if not numeric_cols_chart.empty:
                                        total_row_chart_data = {col: "" for col in df_chart_data_to_write.columns}
                                        first_text_col_chart_idx = 0
                                        for i_ch, dtype_ch in enumerate(df_chart_data_to_write.dtypes):
                                            if not pd.api.types.is_numeric_dtype(dtype_ch):
                                                first_text_col_chart_idx = i_ch
                                                break
                                        total_row_chart_data[df_chart_data_to_write.columns[first_text_col_chart_idx]] = "UKUPNO"
                                        
                                        for num_col_ch in numeric_cols_chart:
                                            df_for_sum_chart = df_chart_data_to_write 
                                            
                                            total_row_chart_data[num_col_ch] = df_for_sum_chart[num_col_ch].sum()
                                            if num_col_ch == "ProcenatPopunjenosti" and "Prodato" in df_for_sum_chart.columns and "Zakup" in df_for_sum_chart.columns and tip_fajla_za_export == "Izvještaj Aviokompanije":
                                                temp_source_df_for_total_percent = source_df_chart_original.copy() 
                                                total_prod_ch = temp_source_df_for_total_percent["Prodato"].sum()
                                                total_zak_ch = temp_source_df_for_total_percent["Zakup"].sum()
                                                total_row_chart_data[num_col_ch] = (total_prod_ch / total_zak_ch) if total_zak_ch > 0 else 0 
                                        
                                        total_row_chart_df = pd.DataFrame([total_row_chart_data])
                                        df_chart_data_to_write = pd.concat([df_chart_data_to_write, total_row_chart_df], ignore_index=True)


                                for col_num_chart, value_chart in enumerate(df_chart_data_to_write.columns.values):
                                    worksheet_chart.write(start_row_for_df, col_num_chart, value_chart)
                                
                                for row_num_chart, row_data_chart in enumerate(df_chart_data_to_write.values):
                                    is_total_row = False
                                    if len(row_data_chart) > 0 and isinstance(row_data_chart[0], str) and row_data_chart[0] == "UKUPNO":
                                        is_total_row = True
                                    row_format_to_apply = bold_format if is_total_row else None
                                    for col_num_chart, cell_data_chart in enumerate(row_data_chart):
                                        worksheet_chart.write(start_row_for_df + 1 + row_num_chart, col_num_chart, cell_data_chart, row_format_to_apply)
                                
                                for col_num_chart, value_chart in enumerate(df_chart_data_to_write.columns.values):
                                    column_len_chart_df = max(len(str(value_chart)), 10)
                                    current_format_chart = None
                                    if "Amount" in value_chart or "Price" in value_chart or "Cijena" in value_chart or "Iznos" in value_chart or "UkupanIznos" in value_chart :
                                        current_format_chart = num_format
                                        column_len_chart_df = max(column_len_chart_df, 15)
                                    elif "ProcenatPopunjenosti" in value_chart: 
                                        current_format_chart = percent_format_excel
                                        column_len_chart_df = max(column_len_chart_df, 12)
                                    elif "PAX" in value_chart or "Adult" in value_chart or "Child" in value_chart or "Infant" in value_chart or "Broj" in value_chart or "Zakup" in value_chart or "Prodato" in value_chart or "Slobodno" in value_chart or "Putnika" in value_chart: 
                                        current_format_chart = int_format
                                        column_len_chart_df = max(column_len_chart_df, 12)
                                    else:
                                        column_len_chart_df = max(column_len_chart_df, 18)
                                    worksheet_chart.set_column(col_num_chart, col_num_chart, column_len_chart_df, current_format_chart)
                    except Exception as e:
                        st.warning(f"Greška pri dodavanju grafikona '{chart_name}' ili njegovih podataka u Excel: {e}")
    
    processed_data = output.getvalue()
    b64 = base64.b64encode(processed_data).decode()
    return f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}" style="display: inline-block; padding: 0.5em 1em; background-color: #4CAF50; color: white; text-align: center; text-decoration: none; border-radius: 4px; font-weight: bold;">📥 Preuzmi Excel fajl (.xlsx)</a>'

# ========================
# Pomoćne funkcije i konstante za Prodaju
# ========================
NASE_POSLOVNICE_RAW = [
    "Poslovnica Stari grad", "Poslovnica Tuzla", "Poslovnica Zenica",
    "Poslovnica Novi Grad", "Centrotours", "Last Minute"
]
NASE_POSLOVNICE_NORM = [x.lower().strip() for x in NASE_POSLOVNICE_RAW]

def je_nasa_poslovnica(ime):
    if not isinstance(ime, str):
        return False
    ime_norm = ime.lower().strip()
    return any(naziv in ime_norm for naziv in NASE_POSLOVNICE_NORM)

# =======================
# Logika za obradu fajlova
# =======================
def process_prodaja_subagenti_poslovnice(df_raw):
    st.info("--- Započinjem obradu 'Prodaja Subagenti i Poslovnice' ---")
    df = df_raw.copy()
    df.dropna(how='all', inplace=True) 
    
    if df.empty:
        st.warning("DataFrame je prazan nakon uklanjanja potpuno praznih redova (iz df_raw).")
        return pd.DataFrame()

    if df.columns.empty:
        st.error("DataFrame nema kolona nakon čitanja sa header=1. Provjerite da li Excel fajl zaista ima zaglavlja u drugom redu.")
        return pd.DataFrame()

    df.columns = df.columns.str.strip().str.replace('\n', ' ', regex=False)
    
    ključne_analiticke_kolone = [
        "Reservation No", "Agency", "Package", "Hotel Name", "Arrival City", 
        "Author", "Agency Amount to Pay", "Adult", "Child", "Infant", "Payment", "Begin Date", "Profit"
    ]

    missing_cols = [col for col in ključne_analiticke_kolone if col not in df.columns]
    if missing_cols:
        st.error(f"Nedostaju očekivane ključne analitičke kolone: {', '.join(missing_cols)}. Provjerite nazive kolona u drugom redu Excel fajla. Stvarno prepoznate kolone su: {', '.join(df.columns.tolist())}")
        return pd.DataFrame()

    df["Agency Amount to Pay"] = pd.to_numeric(df["Agency Amount to Pay"], errors="coerce").fillna(0)
    if "Profit" in df.columns: 
        df["Profit"] = pd.to_numeric(df["Profit"], errors="coerce").fillna(0)

    df["Agency"] = df["Agency"].fillna("Nepoznata agencija").astype(str)
    df["Agency_normalized"] = df["Agency"].str.strip().str.lower() 
    df["Author"] = df["Author"].fillna("Nepoznat autor").astype(str)
    df["Arrival City"] = df["Arrival City"].fillna("Nepoznat grad").astype(str)
    df["Hotel Name"] = df["Hotel Name"].fillna("Nepoznat hotel").astype(str)
    df["Package"] = df["Package"].fillna("Nepoznat paket").astype(str)
    df["Reservation No"] = df["Reservation No"].fillna("N/A").astype(str) 
    
    for col_pax in ["Adult", "Child", "Infant"]:
        df[col_pax] = pd.to_numeric(df[col_pax], errors='coerce').fillna(0).astype(int)
    
    df["PAX"] = df["Adult"] + df["Child"] + df["Infant"] 
    df["PAX_za_sjediste"] = df["Adult"] + df["Child"] 
    
    df["Payment"] = df["Payment"].fillna("Nepoznato").astype(str)
    df["Payment_normalized"] = df["Payment"].str.strip().str.lower() 

    df["Tip Agencije"] = df["Agency_normalized"].apply(lambda x: "Naša poslovnica" if je_nasa_poslovnica(x) else "Subagent")
    
    if 'Begin Date' in df.columns:
        try:
            df['Datum_obj'] = pd.to_datetime(df['Begin Date'], errors='coerce')
        except Exception:
            df['Datum_obj'] = pd.to_datetime(df['Begin Date'], infer_datetime_format=True, errors='coerce')
    else:
        df['Datum_obj'] = pd.NaT 

    if df.empty:
        st.warning("DataFrame je postao prazan nakon obrade i konverzija unutar 'process_prodaja_subagenti_poslovnice'.")
        return pd.DataFrame()
        
    st.success(f"Uspešno obrađeno {len(df)} redova za 'Prodaja Subagenti i Poslovnice'.")
    return df

def process_sunexpress_main_filter(df_raw):
    st.info("--- Započinjem obradu 'Analiza Sunexpress leta Main Filter' ---")
    df = df_raw.copy()
    df.dropna(how='all', inplace=True)

    if df.empty:
        st.warning("DataFrame je prazan nakon uklanjanja potpuno praznih redova (Sunexpress).")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame() 

    if df.columns.empty:
        st.error("DataFrame nema kolona nakon čitanja sa header=1 (Sunexpress). Provjerite Excel fajl.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df.columns = df.columns.str.strip().str.replace('\n', ' ', regex=False)

    required_cols_sunexpress = ["Begin Date", "Adult", "Child", "Infant", "Arrival City", "Package", "Payment", "Profit"] 
    missing_cols = [col for col in required_cols_sunexpress if col not in df.columns]
    if missing_cols:
        st.error(f"Nedostaju očekivane kolone za Sunexpress analizu: {', '.join(missing_cols)}. Stvarno prepoznate kolone: {', '.join(df.columns.tolist())}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    for col_pax in ["Adult", "Child", "Infant"]:
        df[col_pax] = pd.to_numeric(df[col_pax], errors='coerce').fillna(0).astype(int)
    if "Profit" in df.columns:
        df["Profit"] = pd.to_numeric(df["Profit"], errors="coerce").fillna(0)


    df["PAX_za_sjediste"] = df["Adult"] + df["Child"]
    df["Package"] = df["Package"].fillna("Nepoznat paket").astype(str) 
    df["Payment"] = df["Payment"].fillna("Nepoznato").astype(str) 
    
    try:
        df['Datum_obj'] = pd.to_datetime(df['Begin Date'], errors='coerce')
    except Exception as e:
        st.error(f"Greška pri parsiranju kolone 'Begin Date': {e}. Provjerite format datuma.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    
    df_valid_dates = df.dropna(subset=['Datum_obj']).copy() 
    if df_valid_dates.empty:
        st.warning("Nema validnih datuma u koloni 'Begin Date' nakon parsiranja.")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df_valid_dates.loc[:, 'Datum Leta'] = df_valid_dates['Datum_obj'].dt.strftime('%d.%m.%Y')

    df_aggregated = df_valid_dates.groupby('Datum Leta', as_index=False).agg(
        Ukupno_Putnika_Sjediste=('PAX_za_sjediste', 'sum'),
        Broj_Infanata=('Infant', 'sum')
    ).sort_values(by='Datum Leta')

    df_valid_dates.loc[:, 'Package_lower'] = df_valid_dates['Package'].astype(str).str.lower()
    df_10_nocenja = df_valid_dates[
        df_valid_dates['Package_lower'].str.contains("10 nocenja", case=False, na=False) | \
        df_valid_dates['Package_lower'].str.contains("10 noćenja", case=False, na=False)
    ].copy()

    df_10_nocenja_aggregated = pd.DataFrame()
    if not df_10_nocenja.empty:
        df_10_nocenja_aggregated = df_10_nocenja.groupby('Datum Leta', as_index=False).agg(
            Ukupno_Putnika_Sjediste=('PAX_za_sjediste', 'sum'),
            Broj_Infanata=('Infant', 'sum')
        ).sort_values(by='Datum Leta')
    else:
        st.info("Nisu pronađeni aranžmani '10 noćenja' u učitanom fajlu za Sunexpress.")

    st.success(f"Uspešno obrađeno {len(df_valid_dates)} rezervacija za Sunexpress analizu.")
    return df_valid_dates, df_aggregated, df_10_nocenja_aggregated


def process_izvjestaj_aviokompanije(df_raw):
    st.info("--- Započinjem obradu 'Izvještaj Aviokompanije' ---")
    df = df_raw.copy()
    df.dropna(how='all', inplace=True) 

    if df.empty:
        st.warning("DataFrame (Izvještaj Aviokompanije) je prazan nakon uklanjanja praznih redova.")
        return pd.DataFrame(), pd.DataFrame() 
        
    df = df.fillna("") 
    tekstualni_sadrzaj = df.astype(str).apply(lambda row: ' '.join(row.str.strip()), axis=1).tolist()

    data_blokovi = []
    trenutni_datum_str = None
    current_blok_redovi = []
    
    date_pattern = re.compile(r'Date\s*[:：\s]\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})', re.IGNORECASE)

    for red_str in tekstualni_sadrzaj:
        match_datum = date_pattern.search(red_str)
        if match_datum:
            if trenutni_datum_str and current_blok_redovi: 
                data_blokovi.append((trenutni_datum_str, current_blok_redovi))
            trenutni_datum_str = match_datum.group(1) 
            current_blok_redovi = [] 
        elif trenutni_datum_str: 
            is_header_candidate = False
            header_keywords = ["city", "flight", "dest", "zakup", "prodato", "slobodno", "date", "datum", "grad"] 
            if any(keyword in red_str.lower() for keyword in header_keywords):
                numeric_parts = re.findall(r'\b\d+\b', red_str)
                non_numeric_parts = re.findall(r'[A-Za-z]+', red_str)
                if len(non_numeric_parts) > len(numeric_parts) and len(numeric_parts) < 3:
                    is_header_candidate = True
            
            if not red_str.strip() or red_str.lower().startswith("total") or is_header_candidate: 
                continue
            current_blok_redovi.append(red_str)
    
    if trenutni_datum_str and current_blok_redovi: 
        data_blokovi.append((trenutni_datum_str, current_blok_redovi))

    if not data_blokovi:
        st.warning("Nisu pronađeni blokovi podataka označeni sa 'Date :' u 'Izvještaj Aviokompanije'.")
        return pd.DataFrame(), pd.DataFrame()

    svi_letovi_standard = []
    svi_letovi_10_nocenja = []
    flight_data_pattern = re.compile(r'([A-Za-zČĆŽŠĐčćžšđ\s.]+?)\s+(\d+)\s+(\d+)\s+(?:\d+\s+)?([\d.,]+%?)')

    for datum_str, blok_redova in data_blokovi:
        gradovi_procesirani_za_datum = set() 
        for red_str_u_bloku in blok_redova:
            clean_red_str = re.sub(r'\s+', ' ', red_str_u_bloku).strip()
            match_let = flight_data_pattern.match(clean_red_str)
            if match_let:
                try:
                    grad = match_let.group(1).strip()
                    if grad.isdigit() or len(grad) < 2 or grad.lower() == "total": 
                        continue
                    
                    if len(match_let.groups()) == 4: 
                        zakup = int(match_let.group(2))
                        prodato = int(match_let.group(3))
                    elif len(match_let.groups()) == 5: 
                        zakup = int(match_let.group(2))
                        prodato = int(match_let.group(3))
                    else: 
                        continue
                                        
                    entry = {"Datum": datum_str, "Grad": grad, "Zakup": zakup, "Prodato": prodato}
                    
                    if grad in gradovi_procesirani_za_datum:
                        svi_letovi_10_nocenja.append(entry)
                    else:
                        svi_letovi_standard.append(entry)
                        gradovi_procesirani_za_datum.add(grad)
                except ValueError as e:
                    continue
                except Exception as ex:
                    continue
    
    df_standard_raw = pd.DataFrame(svi_letovi_standard)
    df_10_nocenja_raw = pd.DataFrame(svi_letovi_10_nocenja)

    df_standard_agg = pd.DataFrame(columns=['Datum', 'Grad', 'Zakup', 'Prodato', 'Slobodno', 'ProcenatPopunjenosti', 'Datum_obj'])
    if not df_standard_raw.empty:
        df_standard_agg = df_standard_raw.groupby(['Datum', 'Grad'], as_index=False).agg(Zakup=('Zakup', 'sum'), Prodato=('Prodato', 'sum'))
        df_standard_agg['Slobodno'] = df_standard_agg['Zakup'] - df_standard_agg['Prodato']
        df_standard_agg['ProcenatPopunjenosti'] = df_standard_agg.apply(lambda r: (r['Prodato'] / r['Zakup'] * 100) if r['Zakup'] > 0 else 0, axis=1).round(2).fillna(0)
        try:
            df_standard_agg['Datum_obj'] = pd.to_datetime(df_standard_agg['Datum'], dayfirst=True, errors='coerce')
        except: df_standard_agg['Datum_obj'] = pd.to_datetime(df_standard_agg['Datum'], infer_datetime_format=True, errors='coerce')
        df_standard_agg.dropna(subset=['Datum_obj'], inplace=True)


    df_10_nocenja_agg = pd.DataFrame(columns=['Datum', 'Grad', 'Zakup', 'Prodato', 'Slobodno', 'ProcenatPopunjenosti', 'Datum_obj'])
    if not df_10_nocenja_raw.empty:
        st.info(f"Pronađeno {len(df_10_nocenja_raw)} unosa identifikovanih kao aranžmani od 10 noćenja (prije agregacije).")
        df_10_nocenja_agg = df_10_nocenja_raw.groupby(['Datum', 'Grad'], as_index=False).agg(Zakup=('Zakup', 'sum'), Prodato=('Prodato', 'sum'))
        df_10_nocenja_agg['Slobodno'] = df_10_nocenja_agg['Zakup'] - df_10_nocenja_agg['Prodato']
        df_10_nocenja_agg['ProcenatPopunjenosti'] = df_10_nocenja_agg.apply(lambda r: (r['Prodato'] / r['Zakup'] * 100) if r['Zakup'] > 0 else 0, axis=1).round(2).fillna(0)
        try:
            df_10_nocenja_agg['Datum_obj'] = pd.to_datetime(df_10_nocenja_agg['Datum'], dayfirst=True, errors='coerce')
        except: df_10_nocenja_agg['Datum_obj'] = pd.to_datetime(df_10_nocenja_agg['Datum'], infer_datetime_format=True, errors='coerce')
        df_10_nocenja_agg.dropna(subset=['Datum_obj'], inplace=True)
    
    df_combined_agg = pd.concat([df_standard_agg, df_10_nocenja_agg]).groupby(
        ['Datum', 'Grad'], as_index=False
    ).agg(
        Zakup=('Zakup', 'sum'),
        Prodato=('Prodato', 'sum')
    )
    if not df_combined_agg.empty:
        df_combined_agg['Slobodno'] = df_combined_agg['Zakup'] - df_combined_agg['Prodato']
        df_combined_agg['ProcenatPopunjenosti'] = df_combined_agg.apply(
            lambda row: (row['Prodato'] / row['Zakup'] * 100) if row['Zakup'] > 0 else 0, axis=1
        ).round(2).fillna(0)
        try:
            df_combined_agg['Datum_obj'] = pd.to_datetime(df_combined_agg['Datum'], dayfirst=True, errors='coerce')
        except: df_combined_agg['Datum_obj'] = pd.to_datetime(df_combined_agg['Datum'], infer_datetime_format=True, errors='coerce')
        df_combined_agg.dropna(subset=['Datum_obj'], inplace=True)
    else: 
         df_combined_agg = pd.DataFrame(columns=['Datum', 'Grad', 'Zakup', 'Prodato', 'Slobodno', 'ProcenatPopunjenosti', 'Datum_obj'])


    if df_combined_agg.empty and df_10_nocenja_agg.empty:
        st.warning("Nije pronađen nijedan validan let u dokumentu 'Izvještaj Aviokompanije' nakon parsiranja blokova.")
        return pd.DataFrame(), pd.DataFrame()

    st.success(f"Uspešno obrađeno. Kombinovano: {len(df_combined_agg)} letova. Aranžmani 10 noćenja (odvojeno): {len(df_10_nocenja_agg)} letova.")
    return df_combined_agg, df_10_nocenja_agg


# =======================
# Funkcija za resetovanje stanja aplikacije
# =======================
def reset_app_state():
    st.session_state.df_processed = pd.DataFrame()
    st.session_state.df_processed_aggregated = pd.DataFrame() 
    st.session_state.df_10_nocenja_aggregated = pd.DataFrame() 
    st.session_state.df_avio_10_nocenja = pd.DataFrame() 
    st.session_state.main_fig = None
    st.session_state.selected_date_for_details_str = "Nije odabrano" 
    
    st.session_state.secondary_uploaded_file_data = None
    st.session_state.secondary_file_flight_dates = set()
    st.session_state.target_destination_from_secondary = None

    chart_keys_to_reset = [
        "fig_prodaja_agencija", "fig_prodaja_paketa", "fig_pax_agencija",
        "fig_pax_tip_agencije", "fig_pax_destinacija", 
        "fig_trend_datumi_avio", "fig_avio_10_nocenja_gradovi", "fig_avio_10_nocenja_trend", 
        "fig_sunexpress_trend_putnika", "fig_sunexpress_10_nocenja_trend", 
        "charts_for_excel" 
    ]
    for key in chart_keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]
            
    filter_keys = [
        "filter_tip_agencije_prodaja_unique", 
        "filter_destinacija_prodaja_unique", 
        "filter_autor_prodaja_unique", 
        "filter_payment_status_prodaja_unique",
        "chart_type_grad_avio_unique",
        "filter_destinacija_sunexpress_unique",
        "selected_date_for_details_str_key", 
        "secondary_file_uploader_key",
        "hotel_filter_prodaja_unique" 
    ]
    for key in filter_keys:
        if key in st.session_state:
            del st.session_state[key]

# =======================
# Funkcija za obradu sekundarnog (avio) fajla za upoređivanje
# =======================
def process_secondary_airline_file(uploaded_file_obj):
    target_destination = None
    flight_dates = set()
    # df_secondary_for_info = pd.DataFrame() # Nije više potrebno vraćati cijeli DF

    filename_lower = uploaded_file_obj.name.lower()
    if "egipat" in filename_lower:
        target_destination = "Hurgada"
    elif "tunis" in filename_lower:
        target_destination = "Monastir"
    elif "turska" in filename_lower:
        target_destination = "Antalijska regija-svi hoteli" 
    
    if target_destination:
        st.info(f"Prepoznata ciljna destinacija iz naziva sekundarnog fajla: {target_destination}")
    else:
        st.warning("Nije prepoznata ključna riječ (Egipat, Tunis, Turska) u nazivu sekundarnog fajla za automatsko određivanje destinacije.")

    try:
        try:
            uploaded_file_obj.seek(0) 
            df_secondary_raw = pd.read_excel(uploaded_file_obj, header=1)
            df_secondary_raw.dropna(how='all', inplace=True)
            if not df_secondary_raw.empty and "Begin Date" in df_secondary_raw.columns:
                st.info("Sekundarni fajl se obrađuje kao format sa 'Begin Date' kolonom.")
                df_secondary_processed = df_secondary_raw[['Begin Date']].copy()
                df_secondary_processed['Datum_obj'] = pd.to_datetime(df_secondary_processed['Begin Date'], errors='coerce')
                df_secondary_processed.dropna(subset=['Datum_obj'], inplace=True)
                flight_dates = set(df_secondary_processed['Datum_obj'].dt.date)
                # df_secondary_for_info = df_secondary_processed # Nije više potrebno
            else:
                raise ValueError("Format nije 'Prodaja Subagenti' ili nedostaje 'Begin Date'.")
        
        except Exception as e1:
            st.info(f"Prvi pokušaj obrade sekundarnog fajla (kao Prodaja) nije uspio: {e1}. Pokušavam kao format 'Izvještaj Aviokompanije'.")
            uploaded_file_obj.seek(0) 
            df_secondary_raw_avio = pd.read_excel(uploaded_file_obj, header=None)
            df_secondary_raw_avio.dropna(how='all', inplace=True)
            
            if not df_secondary_raw_avio.empty:
                temp_df_avio = df_secondary_raw_avio.fillna("")
                tekstualni_sadrzaj_avio = temp_df_avio.astype(str).apply(lambda r: ' '.join(r.str.strip()), axis=1).tolist()
                date_pattern_avio = re.compile(r'Date\s*[:：\s]\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})', re.IGNORECASE)
                extracted_dates_str = []
                for red_str_avio in tekstualni_sadrzaj_avio:
                    match_datum_avio = date_pattern_avio.search(red_str_avio)
                    if match_datum_avio:
                        extracted_dates_str.append(match_datum_avio.group(1))
                
                if extracted_dates_str:
                    unique_dates_str = sorted(list(set(extracted_dates_str)))
                    temp_dates_df = pd.DataFrame({'DatumStr': unique_dates_str})
                    try:
                        temp_dates_df['Datum_obj'] = pd.to_datetime(temp_dates_df['DatumStr'], dayfirst=True, errors='coerce')
                    except Exception:
                         temp_dates_df['Datum_obj'] = pd.to_datetime(temp_dates_df['DatumStr'], infer_datetime_format=True, errors='coerce')
                    temp_dates_df.dropna(subset=['Datum_obj'], inplace=True)
                    flight_dates = set(temp_dates_df['Datum_obj'].dt.date)
                    # df_secondary_for_info = temp_dates_df # Nije više potrebno
                else:
                    st.warning("Nije pronađen 'Date :' marker u sekundarnom fajlu (format kao Izvještaj Aviokompanije).")
            else:
                st.warning("Sekundarni fajl je prazan nakon pokušaja čitanja kao 'Izvještaj Aviokompanije'.")

        if flight_dates:
            st.info(f"Pronađeno {len(flight_dates)} jedinstvenih datuma letova iz sekundarnog fajla.")
        else:
            st.warning("Nije bilo moguće ekstrahovati datume letova iz sekundarnog fajla ni jednim od poznatih formata.")
            
    except Exception as e:
        st.error(f"Greška pri obradi sekundarnog fajla: {e}")
        st.exception(e)

    return target_destination, flight_dates # Vraća samo destinaciju i set datuma

# =======================
# Funkcija za stilizovanje procenta popunjenosti
# =======================
def style_procenat_popunjenosti(val):
    if pd.isna(val):
        return ''
    try:
        val_num = float(val) # Vrijednost je 0-100
        if val_num < 20:
            return 'background-color: #FFC7CE; color: #9C0006;' # Crvena
        elif val_num < 40:
            return 'background-color: #FFEB9C; color: #9C6500;' # Žuta
    except ValueError:
        return '' 
    return ''


# =======================
# Glavna UI logika
# =======================
st.sidebar.header("⚙️ Postavke Analize")

tip_fajla = st.sidebar.selectbox("📂 Odaberi tip fajla za analizu", 
                                 ["Prodaja Subagenti i Poslovnice", "Izvještaj Aviokompanije", "Analiza Sunexpress leta Main Filter"], 
                                 key="tip_fajla_select",
                                 on_change=reset_app_state) 

uploaded_file = st.sidebar.file_uploader("📥 Učitaj Glavni Excel fajl", type=["xlsx", "xls"], key="file_uploader_main", on_change=reset_app_state) 

# Inicijalizacija ključeva
if 'main_fig' not in st.session_state: st.session_state.main_fig = None 
if 'charts_for_excel' not in st.session_state: st.session_state.charts_for_excel = {}
if 'df_processed' not in st.session_state: st.session_state.df_processed = pd.DataFrame()
if 'df_processed_aggregated' not in st.session_state: st.session_state.df_processed_aggregated = pd.DataFrame() 
if 'df_10_nocenja_aggregated' not in st.session_state: st.session_state.df_10_nocenja_aggregated = pd.DataFrame()
if 'df_avio_10_nocenja' not in st.session_state: st.session_state.df_avio_10_nocenja = pd.DataFrame() 
if 'user_comment_text' not in st.session_state: st.session_state.user_comment_text = ""
if 'report_title_for_excel' not in st.session_state: st.session_state.report_title_for_excel = "Analitički Izvještaj"
if 'selected_date_for_details_str' not in st.session_state: st.session_state.selected_date_for_details_str = "Nije odabrano" 
if 'secondary_uploaded_file_data' not in st.session_state: st.session_state.secondary_uploaded_file_data = None
if 'secondary_file_flight_dates' not in st.session_state: st.session_state.secondary_file_flight_dates = set()
if 'target_destination_from_secondary' not in st.session_state: st.session_state.target_destination_from_secondary = None


if uploaded_file is not None:
    process_new_file = False
    if tip_fajla == "Analiza Sunexpress leta Main Filter":
        if st.session_state.df_processed.empty and st.session_state.df_processed_aggregated.empty and st.session_state.df_10_nocenja_aggregated.empty:
            process_new_file = True
    elif tip_fajla == "Izvještaj Aviokompanije":
        if st.session_state.df_processed.empty and st.session_state.df_avio_10_nocenja.empty:
            process_new_file = True
    elif st.session_state.df_processed.empty: 
        process_new_file = True

    if process_new_file: 
        try:
            excel_file = pd.ExcelFile(uploaded_file)
            st.sidebar.success(f"Glavni fajl '{uploaded_file.name}' uspješno učitan.")
            
            sheet_name_to_process = excel_file.sheet_names[0]
            if len(excel_file.sheet_names) > 1:
                sheet_name_to_process = st.sidebar.selectbox("Odaberi sheet za obradu (Glavni fajl)", 
                                                             excel_file.sheet_names, 
                                                             key=f"sheet_select_{uploaded_file.name}") 
            else:
                st.sidebar.write(f"Obrada sheeta (Glavni fajl): {sheet_name_to_process}")

            header_row = 1 if tip_fajla in ["Prodaja Subagenti i Poslovnice", "Analiza Sunexpress leta Main Filter"] else None
            df_raw_initial = excel_file.parse(sheet_name_to_process, header=header_row)
            df_raw_initial.dropna(how='all', inplace=True) 

            if df_raw_initial.empty:
                st.error(f"Učitani sheet '{sheet_name_to_process}' je prazan nakon uklanjanja praznih redova.")
                st.session_state.df_processed = pd.DataFrame() 
                st.session_state.df_processed_aggregated = pd.DataFrame()
                st.session_state.df_10_nocenja_aggregated = pd.DataFrame()
                st.session_state.df_avio_10_nocenja = pd.DataFrame()
            else:
                if tip_fajla == "Prodaja Subagenti i Poslovnice":
                    st.session_state.df_processed = process_prodaja_subagenti_poslovnice(df_raw_initial)
                    st.session_state.report_title_for_excel = "Izvještaj o Prodaji Agencija"
                elif tip_fajla == "Izvještaj Aviokompanije":
                    df_combined, df_10_noc = process_izvjestaj_aviokompanije(df_raw_initial)
                    st.session_state.df_processed = df_combined 
                    st.session_state.df_avio_10_nocenja = df_10_noc 
                    st.session_state.report_title_for_excel = "Izvještaj Aviokompanije o Letovima"
                elif tip_fajla == "Analiza Sunexpress leta Main Filter":
                    df_original_sunexpress, df_aggregated_sunexpress, df_10_nocenja_agg_sunexpress = process_sunexpress_main_filter(df_raw_initial)
                    st.session_state.df_processed = df_original_sunexpress 
                    st.session_state.df_processed_aggregated = df_aggregated_sunexpress 
                    st.session_state.df_10_nocenja_aggregated = df_10_nocenja_agg_sunexpress
                    st.session_state.report_title_for_excel = "Analiza Sunexpress Leta"
            
            data_loaded_successfully = False
            if tip_fajla == "Analiza Sunexpress leta Main Filter":
                if not st.session_state.df_processed_aggregated.empty or not st.session_state.df_10_nocenja_aggregated.empty:
                    data_loaded_successfully = True
            elif tip_fajla == "Izvještaj Aviokompanije":
                if not st.session_state.df_processed.empty or not st.session_state.df_avio_10_nocenja.empty:
                     data_loaded_successfully = True
            elif not st.session_state.df_processed.empty:
                data_loaded_successfully = True

            if data_loaded_successfully:
                len_to_show = 0
                if tip_fajla == "Analiza Sunexpress leta Main Filter":
                    len_to_show = len(st.session_state.df_processed_aggregated) if not st.session_state.df_processed_aggregated.empty else len(st.session_state.df_10_nocenja_aggregated)
                elif tip_fajla == "Izvještaj Aviokompanije":
                    len_to_show = len(st.session_state.df_processed) 
                else:
                    len_to_show = len(st.session_state.df_processed)
                st.success(f"Ukupno {len_to_show} redova/grupa podataka iz glavnog fajla je spremno za analizu.")
            else:
                st.info("Obrada glavnog fajla nije rezultirala podacima za prikaz.")
        except Exception as e:
            st.error(f"Globalna greška pri čitanju ili obradi glavnog Excel fajla: {e}")
            st.exception(e) 
            st.session_state.df_processed = pd.DataFrame() 
            st.session_state.df_processed_aggregated = pd.DataFrame()
            st.session_state.df_10_nocenja_aggregated = pd.DataFrame()
            st.session_state.df_avio_10_nocenja = pd.DataFrame()

# --- Glavni prikaz i desni "sidebar" za kalendar/detalje ---
col_main_content, col_right_panel = st.columns([3, 1])

with col_main_content:
    main_ui_placeholder = st.container() 
    selected_date_details_placeholder = st.container() 

with col_right_panel:
    calendar_placeholder = st.container()
    secondary_file_uploader_placeholder = st.container() 

# Određivanje koji DataFrame koristiti za analizu i prikaz
df_analiza = pd.DataFrame()
df_analiza_detaljno_sunexpress = pd.DataFrame() 
df_avio_10_noc_za_prikaz = pd.DataFrame()

if tip_fajla == "Analiza Sunexpress leta Main Filter":
    if 'df_processed_aggregated' in st.session_state and not st.session_state.df_processed_aggregated.empty:
        df_analiza = st.session_state.df_processed_aggregated.copy()
    if 'df_processed' in st.session_state: 
        df_analiza_detaljno_sunexpress = st.session_state.df_processed.copy() 
elif tip_fajla == "Izvještaj Aviokompanije":
    if 'df_processed' in st.session_state and not st.session_state.df_processed.empty:
        df_analiza = st.session_state.df_processed.copy()
    if 'df_avio_10_nocenja' in st.session_state:
        df_avio_10_noc_za_prikaz = st.session_state.df_avio_10_nocenja.copy()
elif 'df_processed' in st.session_state and not st.session_state.df_processed.empty:
    df_analiza = st.session_state.df_processed.copy()


data_available_for_display = False
if tip_fajla == "Analiza Sunexpress leta Main Filter":
    if not df_analiza.empty or not df_analiza_detaljno_sunexpress.empty:
        data_available_for_display = True
elif tip_fajla == "Izvještaj Aviokompanije":
    if not df_analiza.empty or not df_avio_10_noc_za_prikaz.empty:
        data_available_for_display = True
elif not df_analiza.empty: 
    data_available_for_display = True


if data_available_for_display:
    sidebar_filters_placeholder = st.sidebar.container() 

    st.session_state.main_fig = None 
    st.session_state.charts_for_excel = {} 

    available_dates_for_calendar = []
    df_for_calendar_details = pd.DataFrame()

    if tip_fajla == "Izvještaj Aviokompanije" and 'Datum_obj' in df_analiza.columns:
        available_dates_for_calendar = sorted(df_analiza['Datum_obj'].dt.date.unique())
        df_for_calendar_details = df_analiza 
    elif tip_fajla == "Analiza Sunexpress leta Main Filter" and 'Datum_obj' in df_analiza_detaljno_sunexpress.columns:
        available_dates_for_calendar = sorted(df_analiza_detaljno_sunexpress['Datum_obj'].dt.date.unique())
        df_for_calendar_details = df_analiza_detaljno_sunexpress
    elif tip_fajla == "Prodaja Subagenti i Poslovnice" and 'Datum_obj' in df_analiza.columns: 
        available_dates_for_calendar = sorted(df_analiza[df_analiza['Datum_obj'].notna()]['Datum_obj'].dt.date.unique()) 
        df_for_calendar_details = df_analiza


    with calendar_placeholder:
        if available_dates_for_calendar:
            st.subheader("🗓️ Odaberi Datum za Detalje")
            date_options_str = ["Nije odabrano"] + [d.strftime("%d.%m.%Y.") for d in available_dates_for_calendar]
            current_selected_date_str = st.session_state.get("selected_date_for_details_str", "Nije odabrano")
            selected_date_str = st.selectbox("Dostupni datumi:", options=date_options_str, 
                                             index=date_options_str.index(current_selected_date_str) if current_selected_date_str in date_options_str else 0,
                                             key="selected_date_for_details_str_key")
            st.session_state.selected_date_for_details_str = selected_date_str 

            if selected_date_str != "Nije odabrano":
                try:
                    selected_date_obj = datetime.strptime(selected_date_str.rstrip('.'), "%d.%m.%Y").date()
                    with selected_date_details_placeholder:
                        st.subheader(f"🔎 Detalji za Datum: {selected_date_str}")
                        if not df_for_calendar_details.empty and 'Datum_obj' in df_for_calendar_details.columns:
                            details_for_date_df_with_dateobj = df_for_calendar_details[df_for_calendar_details['Datum_obj'].dt.date == selected_date_obj].copy()
                            
                            cols_to_drop_details = ['Datum_obj', 'Agency_normalized', 'Payment_normalized', 'Package_lower']
                            final_details_df = details_for_date_df_with_dateobj.copy()
                            for col_drop in cols_to_drop_details:
                                if col_drop in final_details_df.columns:
                                    final_details_df.drop(columns=[col_drop], inplace=True)

                            if not final_details_df.empty:
                                st.dataframe(final_details_df, use_container_width=True)
                                # CSV Download za detalje odabranog datuma
                                # csv_details_date = convert_df_to_csv(final_details_df) # CSV uklonjen
                                # st.download_button(label=f"📥 CSV Detalji ({selected_date_str})",data=csv_details_date,file_name=f"detalji_datum_{selected_date_str.replace('.','-')}.csv",mime="text/csv",key=f"csv_detalji_datum_{selected_date_str}")
                            else:
                                st.info("Nema detaljnih podataka za odabrani datum.")
                        else:
                            st.info("Nema podataka za prikaz detalja.")
                except ValueError:
                    st.error("Greška pri parsiranju odabranog datuma.")
            else: 
                 selected_date_details_placeholder.empty() 


    with main_ui_placeholder: 
        if tip_fajla == "Prodaja Subagenti i Poslovnice":
            st.header("📊 Analiza Prodaje Agencija")
            df_analiza_filtered = df_analiza.copy() 
            
            with sidebar_filters_placeholder:
                st.subheader("Filteri za Prodaju Agencija")
                tipovi_agencija_opts = ["Sve"] + df_analiza_filtered["Tip Agencije"].unique().tolist() if "Tip Agencije" in df_analiza_filtered.columns else ["Sve"]
                odabrani_tip_agencije = st.selectbox("Tip agencije:", tipovi_agencija_opts, key="filter_tip_agencije_prodaja_unique")
                
                destinacije_opts = ["Sve"]
                if "Arrival City" in df_analiza_filtered.columns:
                    destinacije_opts += sorted(df_analiza_filtered["Arrival City"].unique().tolist())
                odabrana_destinacija = st.selectbox("Destinacija (Arrival City):", destinacije_opts, key="filter_destinacija_prodaja_unique")
                
                autori_opts = ["Sve"]
                if "Author" in df_analiza_filtered.columns:
                    autori_opts += sorted(df_analiza_filtered["Author"].unique().tolist())
                odabrani_autor = st.selectbox("Autor rezervacije:", autori_opts, key="filter_autor_prodaja_unique")

                payment_opts = ["Sve"]
                if "Payment_normalized" in df_analiza_filtered.columns:
                    payment_opts += sorted(df_analiza_filtered["Payment_normalized"].unique().tolist())
                odabrani_payment_status = st.selectbox("Status Plaćanja:", payment_opts, key="filter_payment_status_prodaja_unique")

                hotel_opts = ["Svi Hoteli"]
                if "Hotel Name" in df_analiza_filtered.columns: 
                    hotel_opts += sorted(df_analiza_filtered["Hotel Name"].unique().tolist())
                odabrani_hotel = st.selectbox("Odaberi Hotel za Analizu:", hotel_opts, key="hotel_filter_prodaja_unique")


            with secondary_file_uploader_placeholder:
                st.subheader("✈️ Uporedi sa Podacima o Letovima")
                secondary_file = st.file_uploader("Učitaj Excel fajl aviokompanije za upoređivanje", type=["xlsx", "xls"], key="secondary_file_uploader_key")

                if secondary_file is not None:
                    if st.session_state.get('secondary_uploaded_file_data') is None or \
                       st.session_state.secondary_uploaded_file_data.name != secondary_file.name or \
                       st.session_state.secondary_uploaded_file_data.size != secondary_file.size: 
                        
                        st.session_state.secondary_uploaded_file_data = secondary_file
                        target_dest, flight_dates_set = process_secondary_airline_file(secondary_file) 
                        st.session_state.target_destination_from_secondary = target_dest
                        st.session_state.secondary_file_flight_dates = flight_dates_set
                        if target_dest:
                            st.success(f"Datumi letova učitani. Ciljna destinacija: {target_dest}")
                        elif not flight_dates_set:
                             st.warning("Nije bilo moguće ekstrahovati datume letova iz sekundarnog fajla.")
                        else:
                            st.info("Datumi letova učitani, ali destinacija nije automatski prepoznata iz naziva fajla.")
                elif st.session_state.get('secondary_uploaded_file_data') is not None:
                    if st.session_state.target_destination_from_secondary:
                        st.caption(f"Aktivno poređenje sa: {st.session_state.secondary_uploaded_file_data.name} (Dest: {st.session_state.target_destination_from_secondary})")
                    else:
                         st.caption(f"Aktivno poređenje sa: {st.session_state.secondary_uploaded_file_data.name} (Destinacija nije prepoznata)")


            if odabrani_tip_agencije != "Sve" and "Tip Agencije" in df_analiza_filtered.columns:
                df_analiza_filtered = df_analiza_filtered[df_analiza_filtered["Tip Agencije"] == odabrani_tip_agencije]
            if odabrana_destinacija != "Sve" and "Arrival City" in df_analiza_filtered.columns:
                df_analiza_filtered = df_analiza_filtered[df_analiza_filtered["Arrival City"] == odabrana_destinacija]
            if odabrani_autor != "Sve" and "Author" in df_analiza_filtered.columns:
                 df_analiza_filtered = df_analiza_filtered[df_analiza_filtered["Author"] == odabrani_autor]
            if odabrani_payment_status != "Sve" and "Payment_normalized" in df_analiza_filtered.columns:
                df_analiza_filtered = df_analiza_filtered[df_analiza_filtered["Payment_normalized"] == odabrani_payment_status]
            
            if odabrani_hotel != "Svi Hoteli" and "Hotel Name" in df_analiza_filtered.columns:
                df_analiza_filtered = df_analiza_filtered[df_analiza_filtered["Hotel Name"] == odabrani_hotel]


            if st.session_state.get('secondary_uploaded_file_data') and st.session_state.get('secondary_file_flight_dates'):
                st.info("Primjenjuje se filter na osnovu učitanog fajla aviokompanije.")
                target_dest_secondary = st.session_state.target_destination_from_secondary
                flight_dates_secondary = st.session_state.secondary_file_flight_dates

                if target_dest_secondary and "Arrival City" in df_analiza_filtered.columns:
                    df_analiza_filtered = df_analiza_filtered[df_analiza_filtered["Arrival City"].str.contains(target_dest_secondary, case=False, na=False)]
                    if df_analiza_filtered.empty:
                        st.warning(f"Nema prodaje za destinaciju '{target_dest_secondary}' u glavnom fajlu nakon primjene standardnih filtera.")
                
                if not df_analiza_filtered.empty and 'Datum_obj' in df_analiza_filtered.columns and flight_dates_secondary:
                    df_analiza_filtered = df_analiza_filtered[df_analiza_filtered['Datum_obj'].notna() & df_analiza_filtered['Datum_obj'].dt.date.isin(flight_dates_secondary)]

                    if df_analiza_filtered.empty:
                        st.warning(f"Nema prodaje koja se poklapa sa datumima letova iz fajla '{st.session_state.secondary_uploaded_file_data.name}' nakon primjene ostalih filtera.")


            if df_analiza_filtered.empty:
                st.warning("Nema podataka nakon primjene filtera.")
            else:
                st.subheader("📊 Sumarni Pregled Plaćanja")
                if "Payment_normalized" in df_analiza_filtered.columns:
                    payment_counts = df_analiza_filtered["Payment_normalized"].value_counts()
                    st.write(f"Broj Paid Aranžmana: {payment_counts.get('paid', 0)}")
                    st.write(f"Broj UnPaid Aranžmana: {payment_counts.get('unpaid', 0)}") 
                    st.write(f"Broj Partly Paid Rezervacija: {payment_counts.get('partly paid', 0)}") 
                else:
                    st.warning("Kolona 'Payment' nije dostupna za sumarni pregled plaćanja.")


                st.subheader("💰 Ukupna prodaja po agenciji")
                if "Agency" in df_analiza_filtered.columns and "Agency Amount to Pay" in df_analiza_filtered.columns:
                    suma_po_agenciji_df = df_analiza_filtered.groupby("Agency")["Agency Amount to Pay"].sum().reset_index().sort_values(by="Agency Amount to Pay", ascending=False)
                    total_amount = suma_po_agenciji_df["Agency Amount to Pay"].sum()
                    total_row_df = pd.DataFrame([{"Agency": "UKUPNO", "Agency Amount to Pay": total_amount}])
                    suma_po_agenciji_display = pd.concat([suma_po_agenciji_df, total_row_df], ignore_index=True)
                    st.dataframe(suma_po_agenciji_display.style.format({"Agency Amount to Pay": "{:,.2f}"}), use_container_width=True)
                    # CSV uklonjen
                    
                    fig_agencija = px.bar(suma_po_agenciji_df, x="Agency", y="Agency Amount to Pay", title="Ukupan Iznos Prodaje po Agenciji")
                    fig_agencija.update_traces(texttemplate='%{y:,.2f}', textposition='outside')
                    fig_agencija.update_layout(xaxis_tickangle=-45, margin=dict(b=150))
                    st.plotly_chart(fig_agencija, use_container_width=True)
                    st.session_state.charts_for_excel['Prodaja_Po_Agenciji'] = {"figure": fig_agencija, "data": suma_po_agenciji_df}
                else:
                    st.warning("Nedostaju kolone 'Agency' ili 'Agency Amount to Pay' za prikaz prodaje po agenciji.")

                if odabrani_hotel != "Svi Hoteli":
                    st.subheader(f"🏨 Analiza Prodaje za Hotel: {odabrani_hotel}")
                    if not df_analiza_filtered.empty: 
                        hotel_prodaja_tip_agencije = df_analiza_filtered.groupby("Tip Agencije").agg(
                            BrojProdaja=("Reservation No", "count"),
                            UkupanIznos=("Agency Amount to Pay", "sum")
                        ).reset_index()
                        st.dataframe(hotel_prodaja_tip_agencije.style.format({"UkupanIznos": "{:,.2f}"}), use_container_width=True)
                        # CSV uklonjen

                        fig_hotel_tip = px.bar(hotel_prodaja_tip_agencije, x="Tip Agencije", y="BrojProdaja", color="Tip Agencije",
                                               title=f"Broj Prodaja za {odabrani_hotel} po Tipu Agencije", text_auto=True)
                        st.plotly_chart(fig_hotel_tip, use_container_width=True)
                        st.session_state.charts_for_excel[f'Hotel_{odabrani_hotel.replace(" ","_")}_Tip'] = {"figure": fig_hotel_tip, "data": hotel_prodaja_tip_agencije}

                        hotel_prodaja_agencije = df_analiza_filtered.groupby("Agency").agg(
                             BrojProdaja=("Reservation No", "count"),
                             UkupanIznos=("Agency Amount to Pay", "sum")
                        ).reset_index().sort_values(by="BrojProdaja", ascending=False)
                        st.dataframe(hotel_prodaja_agencije.style.format({"UkupanIznos": "{:,.2f}"}), use_container_width=True)
                        # CSV uklonjen

                        fig_hotel_ag = px.bar(hotel_prodaja_agencije, x="Agency", y="BrojProdaja",
                                               title=f"Broj Prodaja za {odabrani_hotel} po Agenciji", text_auto=True)
                        fig_hotel_ag.update_layout(xaxis_tickangle=-45, margin=dict(b=150))
                        st.plotly_chart(fig_hotel_ag, use_container_width=True)
                        st.session_state.charts_for_excel[f'Hotel_{odabrani_hotel.replace(" ","_")}_Agencije'] = {"figure": fig_hotel_ag, "data": hotel_prodaja_agencije}
                    else:
                        st.info(f"Nema podataka za hotel '{odabrani_hotel}' nakon primjene ostalih filtera.")
                else: 
                    st.subheader("🏨 Najprodavaniji hoteli (ukupno)")
                    if "Hotel Name" in df_analiza_filtered.columns and "Reservation No" in df_analiza_filtered.columns and "Agency Amount to Pay" in df_analiza_filtered.columns:
                        prodaja_hotela_df = df_analiza_filtered.groupby("Hotel Name").agg(
                            BrojProdaja=("Reservation No", "count"),
                            UkupanIznos=("Agency Amount to Pay", "sum")
                        ).reset_index().sort_values(by="BrojProdaja", ascending=False)
                        st.dataframe(prodaja_hotela_df.style.format({"UkupanIznos": "{:,.2f}"}), use_container_width=True)
                        # CSV uklonjen
                    else:
                        st.warning("Nedostaju kolone za prikaz najprodavanijih hotela.")


                st.subheader("📦 Prodaja po paketima (aranžmanima)")
                if "Package" in df_analiza_filtered.columns and "Reservation No" in df_analiza_filtered.columns:
                    prodaja_paketa_df = df_analiza_filtered.groupby("Package").agg(
                        BrojProdaja=("Reservation No", "count"),
                        UkupanIznos=("Agency Amount to Pay", "sum") if "Agency Amount to Pay" in df_analiza_filtered.columns else pd.NamedAgg(column="Package", aggfunc="size")
                    ).reset_index().sort_values(by="BrojProdaja", ascending=False)
                    fig_paketi = px.pie(prodaja_paketa_df, values="BrojProdaja", names="Package", title="Udio Prodaje po Paketima")
                    st.plotly_chart(fig_paketi, use_container_width=True)
                    st.session_state.charts_for_excel['Prodaja_Paketi'] = {"figure": fig_paketi, "data": prodaja_paketa_df}
                else:
                    st.warning("Nedostaju kolone 'Package' ili 'Reservation No' za prikaz prodaje po paketima.")
                
                st.subheader("🧑‍🤝‍🧑 Analiza Broja Putnika (PAX)")
                if "PAX" in df_analiza_filtered.columns:
                    pax_po_agenciji_df = df_analiza_filtered.groupby("Agency")["PAX"].sum().reset_index().sort_values(by="PAX", ascending=False)
                    total_pax_agency = pax_po_agenciji_df["PAX"].sum()
                    total_pax_agency_row = pd.DataFrame([{"Agency": "UKUPNO", "PAX": total_pax_agency}])
                    pax_po_agenciji_display = pd.concat([pax_po_agenciji_df, total_pax_agency_row], ignore_index=True)
                    st.dataframe(pax_po_agenciji_display, use_container_width=True)
                    # CSV uklonjen

                    fig_pax_ag = px.bar(pax_po_agenciji_df, x="Agency", y="PAX", text_auto=True, title="Ukupan PAX po Agenciji")
                    fig_pax_ag.update_layout(xaxis_tickangle=-45, margin=dict(b=150))
                    st.plotly_chart(fig_pax_ag, use_container_width=True)
                    st.session_state.charts_for_excel['PAX_Agencije'] = {"figure": fig_pax_ag, "data": pax_po_agenciji_df}

                    pax_po_tipu_agencije_df = df_analiza_filtered.groupby("Tip Agencije")["PAX"].sum().reset_index()
                    total_pax_type = pax_po_tipu_agencije_df["PAX"].sum()
                    total_pax_type_row = pd.DataFrame([{"Tip Agencije": "UKUPNO", "PAX": total_pax_type}])
                    pax_po_tipu_agencije_display = pd.concat([pax_po_tipu_agencije_df, total_pax_type_row], ignore_index=True)
                    st.dataframe(pax_po_tipu_agencije_display, use_container_width=True)
                    # CSV uklonjen

                    fig_pax_tip = px.bar(pax_po_tipu_agencije_df, x="Tip Agencije", y="PAX", text_auto=True, title="Ukupan PAX po Tipu Agencije")
                    st.plotly_chart(fig_pax_tip, use_container_width=True)
                    st.session_state.charts_for_excel['PAX_Tip_Agencije'] = {"figure": fig_pax_tip, "data": pax_po_tipu_agencije_df}
                    
                    if "Arrival City" in df_analiza_filtered.columns:
                        pax_po_destinaciji_df = df_analiza_filtered.groupby("Arrival City")["PAX"].sum().reset_index().sort_values(by="PAX", ascending=False).head(15) 
                        fig_pax_dest = px.bar(pax_po_destinaciji_df, x="Arrival City", y="PAX", text_auto=True, title="Ukupan PAX po Destinaciji (Top 15)")
                        fig_pax_dest.update_layout(xaxis_tickangle=-45, margin=dict(b=150))
                        st.plotly_chart(fig_pax_dest, use_container_width=True)
                        st.session_state.charts_for_excel['PAX_Destinacije'] = {"figure": fig_pax_dest, "data": pax_po_destinaciji_df}
                else:
                    st.warning("Kolona 'PAX' nije dostupna za analizu broja putnika.")

                st.subheader("📋 Detaljna tabela prodaje (filtrirano)")
                df_display_prodaja = df_analiza_filtered.copy()
                if "Agency Amount to Pay" in df_display_prodaja.columns:
                    df_display_prodaja["Agency Amount to Pay"] = df_display_prodaja["Agency Amount to Pay"].map('{:,.2f}'.format)
                st.dataframe(df_display_prodaja, use_container_width=True)
                # CSV uklonjen


        elif tip_fajla == "Izvještaj Aviokompanije":
            # UI za Izvještaj Aviokompanije 
            st.header("✈️ Analiza Izvještaja Aviokompanije")
            df_avio_combined = df_analiza 
            df_avio_10_noc = df_avio_10_noc_za_prikaz 

            with sidebar_filters_placeholder: 
                st.empty() 

            st.subheader("📈 Ukupan pregled po gradovima (Svi letovi)")
            required_cols_avio = ["Grad", "Zakup", "Prodato", "Slobodno", "ProcenatPopunjenosti"]
            if all(col in df_avio_combined.columns for col in required_cols_avio): 
                agregat_grad_avio_df = df_avio_combined.groupby("Grad")[["Zakup", "Prodato", "Slobodno"]].sum().reset_index()
                agregat_grad_avio_df["ProcenatPopunjenosti"] = (agregat_grad_avio_df["Prodato"] / agregat_grad_avio_df["Zakup"] * 100).round(2).fillna(0)
                
                total_zakup_grad = agregat_grad_avio_df["Zakup"].sum()
                total_prodato_grad = agregat_grad_avio_df["Prodato"].sum()
                total_slobodno_grad = agregat_grad_avio_df["Slobodno"].sum()
                total_procenat_grad = (total_prodato_grad / total_zakup_grad * 100) if total_zakup_grad > 0 else 0
                total_row_grad_df = pd.DataFrame([{"Grad": "UKUPNO", "Zakup": total_zakup_grad, "Prodato": total_prodato_grad, "Slobodno": total_slobodno_grad, "ProcenatPopunjenosti": total_procenat_grad}])
                agregat_grad_avio_display = pd.concat([agregat_grad_avio_df, total_row_grad_df], ignore_index=True)
                
                st.dataframe(agregat_grad_avio_display.style.apply(lambda x: x.map(style_procenat_popunjenosti), subset=['ProcenatPopunjenosti'])
                                                        .format({'ProcenatPopunjenosti': "{:.2f}%"}), 
                             use_container_width=True)
                # CSV uklonjen


                chart_type_options_avio = ["Bar Chart", "Line Chart", "Pie Chart (Prodato)"]
                selected_chart_type_avio = st.selectbox("Odaberite tip grafikona:", chart_type_options_avio, key="chart_type_grad_avio_unique")
                
                current_fig_avio_grad = None
                if selected_chart_type_avio == "Bar Chart":
                    current_fig_avio_grad = px.bar(agregat_grad_avio_df, x="Grad", y=["Prodato", "Slobodno", "Zakup"], title="Popunjenost po Gradovima (Svi Letovi)", labels={"value": "Broj Mjesta", "variable": "Status", "Grad":"Grad"}, barmode='group', text_auto=True)
                elif selected_chart_type_avio == "Line Chart":
                    current_fig_avio_grad = px.line(agregat_grad_avio_df, x="Grad", y=["Prodato", "Slobodno", "Zakup"], title="Trend Popunjenosti po Gradovima (Svi Letovi)", labels={"value": "Broj Mjesta", "variable": "Status", "Grad":"Grad"}, markers=True)
                elif selected_chart_type_avio == "Pie Chart (Prodato)":
                    current_fig_avio_grad = px.pie(agregat_grad_avio_df, names="Grad", values="Prodato", title="Udio Prodatih Mjesta po Gradovima (Svi Letovi)", hole=0.3)
                
                if current_fig_avio_grad:
                    current_fig_avio_grad.update_layout(xaxis_tickangle=-45, margin=dict(b=150))
                    st.plotly_chart(current_fig_avio_grad, use_container_width=True)
                    st.session_state.charts_for_excel['Avio_Svi_Letovi_Gradovi'] = {"figure": current_fig_avio_grad, "data": agregat_grad_avio_df}
                    st.session_state.main_fig = current_fig_avio_grad 
            else:
                st.warning("Nedostaju kolone 'Grad', 'Zakup', 'Prodato' ili 'Slobodno' za generisanje grafikona po gradovima.")

            st.subheader("📆 Pregled po datumima (Svi letovi)")
            if 'Datum_obj' in df_avio_combined.columns and all(col in df_avio_combined.columns for col in required_cols_avio): 
                df_sorted_by_date_avio = df_avio_combined.sort_values(by='Datum_obj')
                summary_by_date_avio_df = df_sorted_by_date_avio.groupby(df_sorted_by_date_avio['Datum_obj'].dt.strftime('%d.%m.%Y'))[["Zakup", "Prodato", "Slobodno"]].sum().reset_index()
                summary_by_date_avio_df.rename(columns={summary_by_date_avio_df.columns[0]: 'Datum'}, inplace=True) 
                summary_by_date_avio_df["ProcenatPopunjenosti"] = (summary_by_date_avio_df["Prodato"] / summary_by_date_avio_df["Zakup"] * 100).round(2).fillna(0)

                total_zakup_date = summary_by_date_avio_df["Zakup"].sum()
                total_prodato_date = summary_by_date_avio_df["Prodato"].sum()
                total_slobodno_date = summary_by_date_avio_df["Slobodno"].sum()
                total_procenat_date = (total_prodato_date / total_zakup_date * 100) if total_zakup_date > 0 else 0
                total_row_date_df = pd.DataFrame([{"Datum": "UKUPNO", "Zakup": total_zakup_date, "Prodato": total_prodato_date, "Slobodno": total_slobodno_date, "ProcenatPopunjenosti": total_procenat_date}])
                summary_by_date_avio_display = pd.concat([summary_by_date_avio_df, total_row_date_df], ignore_index=True)
                
                st.dataframe(summary_by_date_avio_display.style.apply(lambda x: x.map(style_procenat_popunjenosti), subset=['ProcenatPopunjenosti'])
                                                            .format({'ProcenatPopunjenosti': "{:.2f}%"}), 
                             use_container_width=True, hide_index=True)
                # CSV uklonjen
                
                fig_trend_avio = px.bar(summary_by_date_avio_df, x="Datum", y=["Zakup", "Prodato", "Slobodno"], 
                                        title="Popunjenost po Datumima (Svi Letovi)", 
                                        labels={"value": "Broj Mjesta", "variable": "Status", "Datum":"Datum"}, 
                                        barmode='group', text_auto=True) 
                fig_trend_avio.update_layout(xaxis_tickangle=-45, margin=dict(b=150))
                st.plotly_chart(fig_trend_avio, use_container_width=True)
                st.session_state.charts_for_excel['Avio_Svi_Letovi_Datumi'] = {"figure": fig_trend_avio, "data": summary_by_date_avio_df}
            else:
                st.warning("Nedostaju kolone 'Datum_obj', 'Zakup', 'Prodato' ili 'Slobodno' za generisanje pregleda po datumima.")

            st.subheader("📋 Detaljna tabela svih letova (kombinovano i agregirano po datumu i gradu)")
            df_display_detailed_avio = df_avio_combined.copy() 
            if 'Datum_obj' in df_display_detailed_avio.columns:
                df_display_detailed_avio = df_display_detailed_avio.drop(columns="Datum_obj")
            
            df_display_styled = df_display_detailed_avio.copy()
            if "ProcenatPopunjenosti" in df_display_styled.columns:
                 df_display_styled["ProcenatPopunjenosti_Display"] = df_display_styled["ProcenatPopunjenosti"].map('{:.2f}%'.format)
                 st.dataframe(df_display_styled.style.apply(lambda x: x.map(style_procenat_popunjenosti), subset=['ProcenatPopunjenosti']), 
                             column_config={"ProcenatPopunjenosti": None, "ProcenatPopunjenosti_Display": st.column_config.TextColumn("Procenat Popunjenosti")},
                             use_container_width=True, hide_index=True)
                 # CSV uklonjen
            else:
                 st.dataframe(df_display_detailed_avio, use_container_width=True, hide_index=True)
                 # CSV uklonjen


            if not df_avio_10_noc.empty:
                st.subheader("✈️ Analiza Letova - Aranžmani 10 Noćenja (Izvještaj Aviokompanije)")
                
                st.markdown("**Pregled po Gradovima (10 Noćenja)**")
                agregat_grad_10_noc_df = df_avio_10_noc.groupby("Grad")[["Zakup", "Prodato", "Slobodno"]].sum().reset_index()
                agregat_grad_10_noc_df["ProcenatPopunjenosti"] = (agregat_grad_10_noc_df["Prodato"] / agregat_grad_10_noc_df["Zakup"] * 100).round(2).fillna(0)
                
                total_zakup_10n_grad = agregat_grad_10_noc_df["Zakup"].sum()
                total_prodato_10n_grad = agregat_grad_10_noc_df["Prodato"].sum()
                total_slobodno_10n_grad = agregat_grad_10_noc_df["Slobodno"].sum()
                total_procenat_10n_grad = (total_prodato_10n_grad / total_zakup_10n_grad * 100) if total_zakup_10n_grad > 0 else 0
                total_row_10n_grad_df = pd.DataFrame([{"Grad": "UKUPNO", "Zakup": total_zakup_10n_grad, "Prodato": total_prodato_10n_grad, "Slobodno": total_slobodno_10n_grad, "ProcenatPopunjenosti": total_procenat_10n_grad}])
                agregat_grad_10_noc_display = pd.concat([agregat_grad_10_noc_df, total_row_10n_grad_df], ignore_index=True)
                st.dataframe(agregat_grad_10_noc_display.style.apply(lambda x: x.map(style_procenat_popunjenosti), subset=['ProcenatPopunjenosti'])
                                                                .format({'ProcenatPopunjenosti': "{:.2f}%"}), 
                             use_container_width=True)
                # CSV uklonjen

                
                fig_avio_10_noc_grad = px.bar(agregat_grad_10_noc_df, x="Grad", y=["Prodato", "Slobodno", "Zakup"], title="Popunjenost po Gradovima (10 Noćenja)", labels={"value": "Broj Mjesta", "variable": "Kategorija"}, barmode='group', text_auto=True)
                fig_avio_10_noc_grad.update_layout(xaxis_tickangle=-45, margin=dict(b=150))
                st.plotly_chart(fig_avio_10_noc_grad, use_container_width=True)
                st.session_state.charts_for_excel['Avio_10Noc_Gradovi'] = {"figure": fig_avio_10_noc_grad, "data": agregat_grad_10_noc_df}

                st.markdown("**Pregled po Datumima (10 Noćenja)**")
                summary_by_date_10_noc_df = df_avio_10_noc.groupby(df_avio_10_noc['Datum_obj'].dt.strftime('%d.%m.%Y'))[["Zakup", "Prodato", "Slobodno"]].sum().reset_index()
                summary_by_date_10_noc_df.rename(columns={summary_by_date_10_noc_df.columns[0]: 'Datum'}, inplace=True)
                summary_by_date_10_noc_df["ProcenatPopunjenosti"] = (summary_by_date_10_noc_df["Prodato"] / summary_by_date_10_noc_df["Zakup"] * 100).round(2).fillna(0)

                
                total_zakup_10n_date = summary_by_date_10_noc_df["Zakup"].sum()
                total_prodato_10n_date = summary_by_date_10_noc_df["Prodato"].sum()
                total_slobodno_10n_date = summary_by_date_10_noc_df["Slobodno"].sum()
                total_procenat_10n_date = (total_prodato_10n_date / total_zakup_10n_date * 100) if total_zakup_10n_date > 0 else 0
                total_row_10n_date_df = pd.DataFrame([{"Datum": "UKUPNO", "Zakup": total_zakup_10n_date, "Prodato": total_prodato_10n_date, "Slobodno": total_slobodno_10n_date, "ProcenatPopunjenosti": total_procenat_10n_date}])
                summary_by_date_10_noc_display = pd.concat([summary_by_date_10_noc_df, total_row_10n_date_df], ignore_index=True)
                st.dataframe(summary_by_date_10_noc_display.style.apply(lambda x: x.map(style_procenat_popunjenosti), subset=['ProcenatPopunjenosti'])
                                                                .format({'ProcenatPopunjenosti': "{:.2f}%"}), 
                             use_container_width=True, hide_index=True)
                # CSV uklonjen


                fig_trend_10_noc_avio = px.bar(summary_by_date_10_noc_df, x="Datum", y=["Zakup", "Prodato", "Slobodno"], title="Popunjenost po Datumima (10 Noćenja)", labels={"value": "Broj Mjesta", "variable": "Kategorija"}, barmode='group', text_auto=True) 
                fig_trend_10_noc_avio.update_layout(xaxis_tickangle=-45, margin=dict(b=150))
                st.plotly_chart(fig_trend_10_noc_avio, use_container_width=True)
                st.session_state.charts_for_excel['Avio_10Noc_Trend_Datumi'] = {"figure": fig_trend_10_noc_avio, "data": summary_by_date_10_noc_df}
            else:
                st.info("Nema podataka za aranžmane od 10 noćenja u ovom izvještaju aviokompanije.")

        
        elif tip_fajla == "Analiza Sunexpress leta Main Filter":
            st.header("✈️ Analiza Sunexpress Leta (Glavni Filter)")
            df_analiza_sunexpress_agg = df_analiza 
            df_analiza_sunexpress_detaljno = df_analiza_detaljno_sunexpress 
            df_10_nocenja_sunexpress_agg = st.session_state.get('df_10_nocenja_aggregated', pd.DataFrame())
            
            with sidebar_filters_placeholder:
                st.subheader("Filteri za Sunexpress")
                destinacije_sun_opts = ["Sve"]
                if "Arrival City" in df_analiza_sunexpress_detaljno.columns: 
                    destinacije_sun_opts += sorted(df_analiza_sunexpress_detaljno["Arrival City"].unique().tolist())
                odabrana_destinacija_sun = st.selectbox("Destinacija (Arrival City):", destinacije_sun_opts, key="filter_destinacija_sunexpress_unique")

            df_analiza_sunexpress_detaljno_filtered = df_analiza_sunexpress_detaljno.copy()
            df_analiza_sunexpress_agg_filtered = df_analiza_sunexpress_agg.copy()
            df_10_nocenja_sunexpress_filtered = df_10_nocenja_sunexpress_agg.copy()

            if odabrana_destinacija_sun != "Sve":
                if "Arrival City" in df_analiza_sunexpress_detaljno_filtered.columns:
                    df_analiza_sunexpress_detaljno_filtered = df_analiza_sunexpress_detaljno_filtered[df_analiza_sunexpress_detaljno_filtered["Arrival City"] == odabrana_destinacija_sun]
                
                if not df_analiza_sunexpress_detaljno_filtered.empty:
                     df_analiza_sunexpress_agg_filtered = df_analiza_sunexpress_detaljno_filtered.groupby('Datum Leta', as_index=False).agg(
                        Ukupno_Putnika_Sjediste=('PAX_za_sjediste', 'sum'),
                        Broj_Infanata=('Infant', 'sum')
                    ).sort_values(by='Datum Leta')
                else:
                    df_analiza_sunexpress_agg_filtered = pd.DataFrame(columns=df_analiza_sunexpress_agg.columns) 

                if not df_10_nocenja_sunexpress_filtered.empty and "Arrival City" in df_analiza_detaljno_sunexpress.columns: 
                    df_detaljno_10_noc_za_dest = df_analiza_sunexpress_detaljno_filtered[ 
                        df_analiza_sunexpress_detaljno_filtered['Package_lower'].str.contains("10 nocenja|10 noćenja", case=False, na=False)
                    ]
                    if not df_detaljno_10_noc_za_dest.empty:
                        df_10_nocenja_sunexpress_filtered = df_detaljno_10_noc_za_dest.groupby('Datum Leta', as_index=False).agg(
                            Ukupno_Putnika_Sjediste=('PAX_za_sjediste', 'sum'),
                            Broj_Infanata=('Infant', 'sum')
                        ).sort_values(by='Datum Leta')
                    else:
                         df_10_nocenja_sunexpress_filtered = pd.DataFrame(columns=df_10_nocenja_sunexpress_filtered.columns)


            if df_analiza_sunexpress_agg_filtered.empty and odabrana_destinacija_sun != "Sve":
                 st.warning(f"Nema podataka za destinaciju '{odabrana_destinacija_sun}'.")
            
            st.subheader("📅 Pregled po Datumima Leta (Sunexpress - Opšti)")
            if not df_analiza_sunexpress_agg_filtered.empty:
                df_display_sun_agg = df_analiza_sunexpress_agg_filtered.rename(columns={"Ukupno_Putnika_Sjediste": "Putnici (sjedišta)", "Broj_Infanata": "Infanti"})
                total_putnici_sjediste = df_display_sun_agg["Putnici (sjedišta)"].sum()
                total_infanti = df_display_sun_agg["Infanti"].sum()
                total_row_sun_df = pd.DataFrame([{"Datum Leta": "UKUPNO", "Putnici (sjedišta)": total_putnici_sjediste, "Infanti": total_infanti}])
                df_display_sun_agg_total = pd.concat([df_display_sun_agg, total_row_sun_df], ignore_index=True)
                st.dataframe(df_display_sun_agg_total, use_container_width=True, hide_index=True)
                # CSV uklonjen

                fig_sun_trend = px.bar(df_analiza_sunexpress_agg_filtered, x="Datum Leta", y="Ukupno_Putnika_Sjediste", title="Broj Putnika (koji zauzimaju sjedišta) po Datumu Leta", labels={"Ukupno_Putnika_Sjediste": "Broj Putnika (sjedišta)"})
                fig_sun_trend.add_bar(x=df_analiza_sunexpress_agg_filtered["Datum Leta"], y=df_analiza_sunexpress_agg_filtered["Broj_Infanata"], name="Broj Infanata")
                fig_sun_trend.update_layout(xaxis_tickangle=-45, margin=dict(b=150), barmode='stack')
                st.plotly_chart(fig_sun_trend, use_container_width=True)
                st.session_state.charts_for_excel['Sunexpress_Opsti_Trend'] = {"figure": fig_sun_trend, "data": df_analiza_sunexpress_agg_filtered}
                st.session_state.main_fig = fig_sun_trend 
            else:
                st.warning("Nema agregiranih podataka za Sunexpress za prikaz nakon primjene filtera.")

            if not df_10_nocenja_sunexpress_filtered.empty:
                st.subheader("☀️ Analiza Aranžmana '10 Noćenja' (Sunexpress)")
                df_display_10_nocenja_agg = df_10_nocenja_sunexpress_filtered.rename(columns={"Ukupno_Putnika_Sjediste": "Putnici (sjedišta)", "Broj_Infanata": "Infanti"})
                total_putnici_10n = df_display_10_nocenja_agg["Putnici (sjedišta)"].sum()
                total_infanti_10n = df_display_10_nocenja_agg["Infanti"].sum()
                total_row_10n_df = pd.DataFrame([{"Datum Leta": "UKUPNO", "Putnici (sjedišta)": total_putnici_10n, "Infanti": total_infanti_10n}])
                df_display_10_nocenja_agg_total = pd.concat([df_display_10_nocenja_agg, total_row_10n_df], ignore_index=True)
                st.dataframe(df_display_10_nocenja_agg_total, use_container_width=True, hide_index=True)
                # CSV uklonjen

                fig_sun_10_nocenja_trend = px.bar(df_10_nocenja_sunexpress_filtered, x="Datum Leta", y="Ukupno_Putnika_Sjediste", title="Broj Putnika (10 Noćenja) po Datumu Leta", labels={"Ukupno_Putnika_Sjediste": "Broj Putnika (sjedišta)"})
                fig_sun_10_nocenja_trend.add_bar(x=df_10_nocenja_sunexpress_filtered["Datum Leta"], y=df_10_nocenja_sunexpress_filtered["Broj_Infanata"], name="Broj Infanata")
                fig_sun_10_nocenja_trend.update_layout(xaxis_tickangle=-45, margin=dict(b=150), barmode='stack')
                st.plotly_chart(fig_sun_10_nocenja_trend, use_container_width=True)
                st.session_state.charts_for_excel['Sunexpress_10_Nocenja'] = {"figure": fig_sun_10_nocenja_trend, "data": df_10_nocenja_sunexpress_filtered}
            else:
                st.info("Nema aranžmana '10 noćenja' za prikaz nakon primjene filtera za Sunexpress.")


            st.subheader("📋 Detaljna Tabela Rezervacija (Sunexpress - filtrirano)")
            if not df_analiza_sunexpress_detaljno_filtered.empty: 
                df_display_sun_detaljno = df_analiza_sunexpress_detaljno_filtered[['Datum Leta', 'Arrival City', 'Package', 'Adult', 'Child', 'Infant', 'PAX_za_sjediste', 'Payment', 'Profit']].copy() 
                st.dataframe(df_display_sun_detaljno, use_container_width=True, hide_index=True)
                # CSV uklonjen
            else:
                st.warning("Nema detaljnih podataka za Sunexpress za prikaz nakon primjene filtera.")


        # Export sekcija je zajednička za sve tipove
        st.header("📝 Komentar i Export Podataka")
        st.session_state.user_comment_text = st.text_area("Unesite Vaš komentar za izvještaj:", 
                                                          value=st.session_state.user_comment_text, 
                                                          height=150,
                                                          key="user_comment_input_main") 
        
        df_to_pass_to_excel = pd.DataFrame() 
        if tip_fajla == "Prodaja Subagenti i Poslovnice":
            df_to_pass_to_excel = df_analiza_filtered if 'df_analiza_filtered' in locals() and not df_analiza_filtered.empty else df_analiza
        elif tip_fajla == "Analiza Sunexpress leta Main Filter":
            df_to_pass_to_excel = df_analiza_sunexpress_detaljno_filtered if 'df_analiza_sunexpress_detaljno_filtered' in locals() and not df_analiza_sunexpress_detaljno_filtered.empty else df_analiza_detaljno_sunexpress
        else: 
            df_to_pass_to_excel = df_analiza 
        
        excel_link = generate_excel_download(
            df_to_pass_to_excel, 
            user_comment=st.session_state.user_comment_text, 
            charts_data_to_export=st.session_state.charts_for_excel, 
            filename=f"analiza_{tip_fajla.lower().replace(' ', '_')}.xlsx",
            tip_fajla_za_export=tip_fajla 
        )
        st.markdown(excel_link, unsafe_allow_html=True)


elif uploaded_file is None:
    st.info("Molimo učitajte Excel fajl koristeći opcije na lijevoj strani.")
    if 'main_ui_placeholder' in locals() and hasattr(main_ui_placeholder, 'empty'): main_ui_placeholder.empty()
    if 'sidebar_filters_placeholder' in locals() and hasattr(sidebar_filters_placeholder, 'empty'): sidebar_filters_placeholder.empty()


st.sidebar.markdown("---")
st.sidebar.info("ISKLJUČIVO ANALIZA PRODAJE PO POSLOVNICAMA I SUBAGENTIMA")

