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
        aadhar_no = st.text_input("Aadhar Number (12 Digits)", max_chars=12) 
        address = st.text_input("Address")
        dob = st.date_input(
            "Date of Birth", 
            min_value=datetime.date(1930, 1, 1),
            max_value=datetime.date.today(),
            value=datetime.date(1990, 1, 1) 
        )
    with col2:
        photo = st.file_uploader("Upload Aadhar Photo", type=['jpg','jpeg','png'])
    
    submitted = st.form_submit_button("Save Employee")

    if submitted:
        if not name or not aadhar_no:
            st.error("⚠️ Name and Aadhar No are required to save.")
        elif not (aadhar_no.isdigit() and len(aadhar_no) == 12):
            st.error("⚠️ Invalid Aadhar! Please enter exactly 12 numbers (no letters).")
        else:
            photo_url = ""
            
            # Save Image
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

            # Save Data
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
            # Refresh to show new data immediately
            st.rerun()

# --- 3. Display & Delete Employees ---
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
    
    # Header Row for clarity
    header_cols = st.columns([1, 1, 2, 1, 1, 1])
    header_cols[0].markdown("**Name**")
    header_cols[1].markdown("**Aadhar**")
    header_cols[2].markdown("**Address**")
    header_cols[3].markdown("**DOB**")
    header_cols[4].markdown("**Photo**")
    header_cols[5].markdown("**Action**")
    st.divider()

    for idx, row in filtered_df.iterrows():
        # Added a 6th column specifically for the delete button
        cols = st.columns([1, 1, 2, 1, 1, 1])
        
        with cols[0]: st.text(row['name'])
        with cols[1]: st.text(row['aadhar_no'])
        with cols[2]: st.text(row['address'])
        with cols[3]: st.text(row['dob'])
        with cols[4]:
            if pd.notna(row.get('photo_url')) and row.get('photo_url') != "":
                st.image(row['photo_url'], width=80)
            else:
                st.text("No Photo")
        
        # --- NEW: Delete Button ---
        with cols[5]:
            # The button needs a unique key, so we use the Aadhar number
            if st.button("🗑️ Delete", key=f"del_{row['aadhar_no']}", type="primary"):
                
                # 1. Delete photo from storage (if it exists)
                if pd.notna(row.get('photo_url')) and row.get('photo_url') != "":
                    # Extract just the filename from the end of the URL
                    filename = row['photo_url'].split('/')[-1]
                    supabase.storage.from_("employee-photos").remove([filename])
                
                # 2. Delete row from database
                supabase.table("employees").delete().eq("aadhar_no", row['aadhar_no']).execute()
                
                # 3. Refresh the app to remove the row from the screen
                st.success(f"Deleted {row['name']}")
                st.rerun()
else:
    st.info("No employees found in the database. Add one above!")
