import pandas as pd
import streamlit as st
from io import BytesIO
from datetime import datetime

# === Streamlit Config ===
st.set_page_config(page_title="KNCCI TA Microdata Dashboard", layout="wide")
st.title("📊 Jiinue Growth Program - Microdata Summary Dashboard")

# === 1. Google Sheet link ===
sheet_url = "https://docs.google.com/spreadsheets/d/1LDPRGnR5jlzIMP6RJ9gAcB5m91OO_Wf_1_4liYtVPYM/edit?usp=sharing"
csv_url = sheet_url.replace("/edit?usp=sharing", "/export?format=csv")

# === 2. Load Data ===
df = pd.read_csv(csv_url)
df.columns = df.columns.str.strip()

# Ensure date column exists and is parsed
if 'Timestamp' in df.columns:
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
elif 'Training date' in df.columns:
    df['Timestamp'] = pd.to_datetime(df['Training date'], errors='coerce')
else:
    df['Timestamp'] = pd.NaT

# === 3. Sidebar Filters ===
st.sidebar.header("📅 Date Filters")
min_date = df['Timestamp'].min()
max_date = df['Timestamp'].max()

start_date = st.sidebar.date_input("Start Date", min_date.date() if pd.notnull(min_date) else datetime.now().date())
end_date = st.sidebar.date_input("End Date", max_date.date() if pd.notnull(max_date) else datetime.now().date())

# Filter by date
df = df[(df['Timestamp'].dt.date >= start_date) & (df['Timestamp'].dt.date <= end_date)]

# === 4. Clean Duplicates (Sequential) ===
initial_count = len(df)

# Step 1: Remove where both National ID AND phone number match
df_clean = df.drop_duplicates(subset=['WHAT IS YOUR NATIONAL ID?', 'Business phone number'], keep='first')
after_both = len(df_clean)

# Step 2: Remove remaining National ID duplicates
df_clean = df_clean.drop_duplicates(subset=['WHAT IS YOUR NATIONAL ID?'], keep='first')
after_id = len(df_clean)

# Step 3: Remove remaining phone number duplicates
df_clean = df_clean.drop_duplicates(subset=['Business phone number'], keep='first')
cleaned_count = len(df_clean)

# Calculate removals at each stage
duplicates_both = initial_count - after_both
duplicates_id = after_both - after_id
duplicates_phone = after_id - cleaned_count
duplicates_removed = initial_count - cleaned_count

# === 5. Enrich Columns ===
df_clean['Age of owner (full years)'] = pd.to_numeric(df_clean['Age of owner (full years)'], errors='coerce')

df_clean['Age Group'] = df_clean['Age of owner (full years)'].apply(
    lambda x: 'Youth (18–35)' if 18 <= x <= 35 else ('Adult (36+)' if pd.notnull(x) and x > 35 else 'Unknown')
)

pwd_col = 'DO YOU IDENTIFY AS A PERSON WITH A DISABILITY? (THIS QUESTION IS OPTIONAL AND YOUR RESPONSE WILL NOT AFFECT YOUR ELIGIBILITY FOR THE PROGRAM.)'
if pwd_col in df_clean.columns:
    df_clean[pwd_col] = df_clean[pwd_col].astype(str).str.strip().str.lower()
    df_clean['PWD Status'] = df_clean[pwd_col].apply(
        lambda x: 'Yes' if 'yes' in x else ('No' if 'no' in x else 'Unspecified')
    )
else:
    df_clean['PWD Status'] = 'Unspecified'

# === 6. General Summaries ===
total_participants = cleaned_count
total_youth = len(df_clean[df_clean['Age Group'] == 'Youth (18–35)'])
total_adults = len(df_clean[df_clean['Age Group'] == 'Adult (36+)'])
female_count = len(df_clean[df_clean['Gender of owner'].str.lower().str.contains('female', na=False)])
pwd_count = len(df_clean[df_clean['PWD Status'] == 'Yes'])

youth_pct = (total_youth / total_participants) * 100 if total_participants else 0
female_pct = (female_count / total_participants) * 100 if total_participants else 0
pwd_pct = (pwd_count / total_participants) * 100 if total_participants else 0

# === 7. Display General Summary ===
st.markdown("## 🧾 General Summary")
col1, col2, col3 = st.columns(3)
col1.metric("Total Records (Raw)", initial_count)
col2.metric("Cleaned Participants", cleaned_count)
col3.metric("Total Duplicates Removed", duplicates_removed)

st.markdown("### 🔍 Duplicate Removal Breakdown")
col4, col5, col6 = st.columns(3)
col4.metric("ID + Phone duplicates", duplicates_both)
col5.metric("National ID only duplicates", duplicates_id)
col6.metric("Phone only duplicates", duplicates_phone)

st.markdown("### 👥 Participant Demographics")
col7, col8, col9, col10 = st.columns(4)
col7.metric("Youth (18–35)", f"{total_youth} ({youth_pct:.1f}%)")
col8.metric("Adult (36+)", total_adults)
col9.metric("Female Participants", f"{female_count} ({female_pct:.1f}%)")
col10.metric("PWD Participants", f"{pwd_count} ({pwd_pct:.1f}%)")

st.caption(f"⏱️ Data Filter: {start_date} to {end_date} | Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# === 8. Summaries by County ===
county_summary = df_clean['Business Location'].value_counts().reset_index()
county_summary.columns = ['County', 'Count']

gender_summary = df_clean.groupby(['Business Location', 'Gender of owner']).size().reset_index(name='Count')
age_summary = df_clean.groupby(['Business Location', 'Age Group']).size().reset_index(name='Count')
pwd_summary = df_clean.groupby(['Business Location', 'PWD Status']).size().reset_index(name='Count')

# === Helper: Convert to Excel Bytes ===
def df_to_excel_bytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# === 9. Downloadable Summaries ===
st.markdown("## 📍 County-Level Summary")
st.dataframe(county_summary)
st.download_button("⬇️ Download County Summary (.xlsx)", df_to_excel_bytes(county_summary), "County_Summary.xlsx")

st.markdown("### 👩‍💼 Gender Distribution per County")
st.dataframe(gender_summary)
st.download_button("⬇️ Download Gender Summary (.xlsx)", df_to_excel_bytes(gender_summary), "Gender_Summary.xlsx")

st.markdown("### 🧑‍💻 Age Group Distribution (Youth vs Adult)")
st.dataframe(age_summary)
st.download_button("⬇️ Download Age Summary (.xlsx)", df_to_excel_bytes(age_summary), "Age_Summary.xlsx")

st.markdown("### ♿ Persons with Disabilities (PWD) Summary")
st.dataframe(pwd_summary)
st.download_button("⬇️ Download PWD Summary (.xlsx)", df_to_excel_bytes(pwd_summary), "PWD_Summary.xlsx")

# === 10. Charts ===
st.markdown("## 📊 Visual Insights")
st.bar_chart(data=county_summary.set_index('County'))
st.bar_chart(data=df_clean['Gender of owner'].value_counts())
st.bar_chart(data=df_clean['Age Group'].value_counts())
st.bar_chart(data=df_clean['PWD Status'].value_counts())

# === 11. Combined Excel Download ===
def all_to_excel(dfs: dict):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for name, data in dfs.items():
            data.to_excel(writer, sheet_name=name, index=False)
    return output.getvalue()

excel_all = all_to_excel({
    "Cleaned_Data": df_clean,
    "County_Summary": county_summary,
    "Gender_Summary": gender_summary,
    "Age_Group_Summary": age_summary,
    "PWD_Summary": pwd_summary
})

st.markdown("### 💾 Combined Download")
st.download_button(
    label="⬇️ Download All Summaries in One Excel File",
    data=excel_all,
    file_name="TA_Cleaned_Data_Report_All.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
