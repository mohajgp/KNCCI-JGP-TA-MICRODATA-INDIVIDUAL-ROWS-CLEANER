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
st.sidebar.header("🔎 Filters")

# Date filters
st.sidebar.subheader("📅 Date Range")
min_date = df['Timestamp'].min()
max_date = df['Timestamp'].max()

start_date = st.sidebar.date_input("Start Date", min_date.date() if pd.notnull(min_date) else datetime.now().date())
end_date = st.sidebar.date_input("End Date", max_date.date() if pd.notnull(max_date) else datetime.now().date())

# Filter by date
df = df[(df['Timestamp'].dt.date >= start_date) & (df['Timestamp'].dt.date <= end_date)]

# County filter
st.sidebar.subheader("📍 County Filter")
all_counties = ['All'] + sorted(df['Business Location'].dropna().unique().tolist())
selected_county = st.sidebar.selectbox("Select County", all_counties)

if selected_county != 'All':
    df = df[df['Business Location'] == selected_county]

# === 4. Identify Duplicates for Audit ===
initial_count = len(df)

# Find records with same ID but different phone numbers
id_col = 'WHAT IS YOUR NATIONAL ID?'
phone_col = 'Business phone number'

# Same ID, different phone numbers
id_groups = df.groupby(id_col)[phone_col].nunique()
ids_with_multiple_phones = id_groups[id_groups > 1].index.tolist()
same_id_diff_phone = df[df[id_col].isin(ids_with_multiple_phones)].sort_values(by=id_col)

# Same phone, different IDs
phone_groups = df.groupby(phone_col)[id_col].nunique()
phones_with_multiple_ids = phone_groups[phone_groups > 1].index.tolist()
same_phone_diff_id = df[df[phone_col].isin(phones_with_multiple_ids)].sort_values(by=phone_col)

# Exact duplicates (both ID and phone match)
exact_duplicates = df[df.duplicated(subset=[id_col, phone_col], keep=False)].sort_values(by=[id_col, phone_col])

# === 5. Clean Duplicates (Sequential) ===
# Step 1: Remove where both National ID AND phone number match
df_clean = df.drop_duplicates(subset=[id_col, phone_col], keep='first')
after_both = len(df_clean)

# Step 2: Remove remaining National ID duplicates
df_clean = df_clean.drop_duplicates(subset=[id_col], keep='first')
after_id = len(df_clean)

# Step 3: Remove remaining phone number duplicates
df_clean = df_clean.drop_duplicates(subset=[phone_col], keep='first')
cleaned_count = len(df_clean)

# Calculate removals at each stage
duplicates_both = initial_count - after_both
duplicates_id = after_both - after_id
duplicates_phone = after_id - cleaned_count
duplicates_removed = initial_count - cleaned_count

# === 6. Enrich Columns ===
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

# === 7. General Summaries ===
total_participants = cleaned_count
total_youth = len(df_clean[df_clean['Age Group'] == 'Youth (18–35)'])
total_adults = len(df_clean[df_clean['Age Group'] == 'Adult (36+)'])
female_count = len(df_clean[df_clean['Gender of owner'].str.lower().str.contains('female', na=False)])
pwd_count = len(df_clean[df_clean['PWD Status'] == 'Yes'])

youth_pct = (total_youth / total_participants) * 100 if total_participants else 0
female_pct = (female_count / total_participants) * 100 if total_participants else 0
pwd_pct = (pwd_count / total_participants) * 100 if total_participants else 0

# === 8. Display General Summary ===
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

filter_text = f"County: {selected_county}" if selected_county != 'All' else "All Counties"
st.caption(f"⏱️ Data Filter: {start_date} to {end_date} | {filter_text} | Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# === 9. Audit Section ===
st.markdown("---")
st.markdown("## 🔎 Audit Reports")
st.markdown("Use these reports to investigate data quality issues and potential fraud.")

# Helper: Convert to Excel Bytes
def df_to_excel_bytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# Audit tabs
audit_tab1, audit_tab2, audit_tab3 = st.tabs([
    f"🆔 Same ID, Different Phone ({len(same_id_diff_phone)})",
    f"📱 Same Phone, Different ID ({len(same_phone_diff_id)})",
    f"📋 Exact Duplicates ({len(exact_duplicates)})"
])

with audit_tab1:
    st.markdown("### 🆔 Same National ID with Different Phone Numbers")
    st.markdown("These records have the same National ID but registered with different phone numbers. Could indicate re-registration or data entry errors.")
    if len(same_id_diff_phone) > 0:
        # Show summary of affected IDs
        st.info(f"**{len(ids_with_multiple_phones)} unique IDs** with multiple phone numbers ({len(same_id_diff_phone)} total records)")
        st.dataframe(same_id_diff_phone[[id_col, phone_col, 'Business Location', 'Gender of owner', 'Timestamp']].reset_index(drop=True))
        st.download_button(
            "⬇️ Download Same ID, Different Phone (.xlsx)",
            df_to_excel_bytes(same_id_diff_phone),
            "Audit_Same_ID_Different_Phone.xlsx"
        )
    else:
        st.success("✅ No records found with same ID and different phone numbers.")

with audit_tab2:
    st.markdown("### 📱 Same Phone Number with Different National IDs")
    st.markdown("These records share a phone number but have different National IDs. Could indicate shared devices, fraud, or data entry errors.")
    if len(same_phone_diff_id) > 0:
        st.info(f"**{len(phones_with_multiple_ids)} phone numbers** used by multiple IDs ({len(same_phone_diff_id)} total records)")
        st.dataframe(same_phone_diff_id[[id_col, phone_col, 'Business Location', 'Gender of owner', 'Timestamp']].reset_index(drop=True))
        st.download_button(
            "⬇️ Download Same Phone, Different ID (.xlsx)",
            df_to_excel_bytes(same_phone_diff_id),
            "Audit_Same_Phone_Different_ID.xlsx"
        )
    else:
        st.success("✅ No records found with same phone and different IDs.")

with audit_tab3:
    st.markdown("### 📋 Exact Duplicates (Same ID + Same Phone)")
    st.markdown("These are exact duplicate registrations - same person registered multiple times.")
    if len(exact_duplicates) > 0:
        st.info(f"**{len(exact_duplicates)} records** are exact duplicates")
        st.dataframe(exact_duplicates[[id_col, phone_col, 'Business Location', 'Gender of owner', 'Timestamp']].reset_index(drop=True))
        st.download_button(
            "⬇️ Download Exact Duplicates (.xlsx)",
            df_to_excel_bytes(exact_duplicates),
            "Audit_Exact_Duplicates.xlsx"
        )
    else:
        st.success("✅ No exact duplicates found.")

# === 10. Summaries by County ===
st.markdown("---")
st.markdown("## 📍 County-Level Summary")

county_summary = df_clean['Business Location'].value_counts().reset_index()
county_summary.columns = ['County', 'Count']

gender_summary = df_clean.groupby(['Business Location', 'Gender of owner']).size().reset_index(name='Count')
age_summary = df_clean.groupby(['Business Location', 'Age Group']).size().reset_index(name='Count')
pwd_summary = df_clean.groupby(['Business Location', 'PWD Status']).size().reset_index(name='Count')

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

# === 11. Charts ===
st.markdown("## 📊 Visual Insights")
st.bar_chart(data=county_summary.set_index('County'))
st.bar_chart(data=df_clean['Gender of owner'].value_counts())
st.bar_chart(data=df_clean['Age Group'].value_counts())
st.bar_chart(data=df_clean['PWD Status'].value_counts())

# === 12. Combined Excel Download ===
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
    "PWD_Summary": pwd_summary,
    "Audit_Same_ID_Diff_Phone": same_id_diff_phone,
    "Audit_Same_Phone_Diff_ID": same_phone_diff_id,
    "Audit_Exact_Duplicates": exact_duplicates
})

st.markdown("### 💾 Combined Download")
st.download_button(
    label="⬇️ Download All Summaries + Audit Reports in One Excel File",
    data=excel_all,
    file_name="TA_Cleaned_Data_Report_All.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
