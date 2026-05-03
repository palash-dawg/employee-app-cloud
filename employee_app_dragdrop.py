import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

st.set_page_config(page_title="Employee Management - Cloud", layout="wide")
st.title("Employee Management App (Cloud Database & Photos)")

# --- 1. Securely Connect to Supabase ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# --- Helper Function: Fetch Data ---
def fetch_data():
    response = supabase.table("employees").select("*").execute()
    return pd.DataFrame(response.data)

# --- 2. Add / Edit Employee Form ---
with st.form("employee_form", clear_on_submit=True):
    st.subheader("Add / Edit Employee")
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Name")
        # Restrict typing to 12 characters
        aadhar_no = st.text_input("Aadhar Number (12 Digits)", max_chars=12) 
        address = st.text_input("Address")
        
        # FIX: Unlock the calendar from 1930 up to today
        dob = st.date_input(
            "Date of Birth", 
            min_value=datetime.date(1930, 1, 1),
            max_value=datetime.date.today(),
            value=datetime.date(1990, 1, 1) # Sets a nice default starting year
        )
    with col2:
        photo = st.file_uploader("Upload Aadhar Photo", type=['jpg','jpeg','png'])
    
    submitted = st.form_submit_button("Save Employee")

    if submitted:
        # FIX: Strict Validation Rules
        if not name or not aadhar_no:
            st.error("⚠️ Name and Aadhar No are required to save.")
        elif not (aadhar_no.isdigit() and len(aadhar_no) == 12):
            st.error("⚠️ Invalid Aadhar! Please enter exactly 12 numbers (no letters).")
        else:
            photo_url = ""
            
            # Save Image to Supabase Storage Bucket
            if photo is not None:
                clean_filename = photo.name.replace(" ", "_")
                file_name = f"{aadhar_no}_{clean_filename}"
                file_bytes = photo.getvalue()
                
                supabase.storage.from_("employee-photos").upload(
                    file_name, 
                    file_bytes, 
                    {"content-type": photo.type, "upsert": "true"}
                )
                photo_url = supabase.storage.from_("employee-photos").get_public_url(file_name)

            # Save Text Data to Supabase Database
            emp_data = {
                "name": name,
                "aadhar_no": aadhar_no,
                "address": address,
                "dob": str(dob),
            }
            if photo_url:
                emp_data["photo_url"] = photo_url

            supabase.table("employees").upsert(emp_data).execute()
            st.success(f"✅ Employee {name} saved successfully to the cloud!")

# --- 3. Display Employees ---
st.subheader("Search / Filter Employees")
search_query = st.text_input("Search by Name or Aadhar")

df = fetch_data()

if not df.empty:
    if search_query:
        filtered_df = df[df['name'].str.contains(search_query, case=False, na=False) |
                         df['aadhar_no'].astype(str).str.contains(search_query, na=False)]
    else:
        filtered_df = df

    st.subheader("Employee List")
    for idx, row in filtered_df.iterrows():
        cols = st.columns([1,1,2,2,2])
        with cols[0]: st.text(row['name'])
        with cols[1]: st.text(row['aadhar_no'])
        with cols[2]: st.text(row['address'])
        with cols[3]: st.text(row['dob'])
        with cols[4]:
            if pd.notna(row.get('photo_url')) and row.get('photo_url') != "":
                st.image(row['photo_url'], width=100)
            else:
                st.text("No Photo")
else:
    st.info("No employees found in the database. Add one above!")
