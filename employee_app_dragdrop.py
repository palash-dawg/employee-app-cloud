import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime
from PIL import Image
import io

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

# --- Helper Function: Compress Image under 50KB ---
def compress_image(uploaded_file, max_kb=50):
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
        
    quality = 90
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG', quality=quality)
    
    while len(img_byte_arr.getvalue()) > (max_kb * 1024) and quality > 10:
        quality -= 10
        if quality <= 50:
            width, height = img.size
            img = img.resize((int(width * 0.8), int(height * 0.8)), Image.Resampling.LANCZOS)
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=quality)
        
    return img_byte_arr.getvalue()

# --- 2. Add / Edit Employee Form ---
with st.form("employee_form", clear_on_submit=True):
    st.subheader("Add / Edit Employee Profile")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**Personal Details**")
        name = st.text_input("Full Name")
        # --- HERE IS THE FATHER'S NAME ---
        father_name = st.text_input("Father's Name")
        aadhar_no = st.text_input("Aadhar Number (12 Digits)", max_chars=12) 
        mobile_no = st.text_input("Mobile Number (10 Digits)", max_chars=10)
        dob = st.date_input(
            "Date of Birth", 
            min_value=datetime.date(1930, 1, 1),
            max_value=datetime.date.today(),
            value=datetime.date(1990, 1, 1) 
        )
        
    with col2:
        st.markdown("**Bank & Address**")
        bank_name = st.text_input("Bank Name (e.g., SBI, HDFC)")
        account_no = st.text_input("Bank Account Number") 
        ifsc_code = st.text_input("IFSC Code (11 Chars)", max_chars=11)
        address = st.text_input("Full Address")
        
    with col3:
        st.markdown("**Documents**")
        photo = st.file_uploader("Upload Aadhar Photo (<50KB)", type=['jpg','jpeg','png'])
    
    submitted = st.form_submit_button("Save Employee", type="primary")

    if submitted:
        if not name or not aadhar_no or not mobile_no:
            st.error("⚠️ Name, Aadhar, and Mobile Number are required!")
        elif not (aadhar_no.isdigit() and len(aadhar_no) == 12):
            st.error("⚠️ Invalid Aadhar! Must be exactly 12 numbers.")
        elif not (mobile_no.isdigit() and len(mobile_no) == 10):
            st.error("⚠️ Invalid Mobile! Must be exactly 10 numbers.")
        elif ifsc_code and len(ifsc_code) != 11:
            st.error("⚠️ Invalid IFSC! Must be exactly 11 characters.")
        else:
            photo_url = ""
            
            # Compress and Save Image
            if photo is not None:
                compressed_bytes = compress_image(photo, max_kb=50)
                clean_filename = photo.name.replace(" ", "_").split('.')[0] + ".jpg"
                file_name = f"{aadhar_no}_{clean_filename}"
                
                supabase.storage.from_("employee-photos").upload(
                    file_name, 
                    compressed_bytes, 
                    {"content-type": "image/jpeg", "upsert": "true"}
                )
                photo_url = supabase.storage.from_("employee-photos").get_public_url(file_name)

            # Save Data
            emp_data = {
                "name": name,
                "father_name": father_name,  # Added Father's Name here
                "aadhar_no": aadhar_no,
                "mobile_no": mobile_no,
                "dob": str(dob),
                "address": address,
                "bank_name": bank_name,
                "account_no": account_no,
                "ifsc_code": ifsc_code.upper() if ifsc_code else "", 
            }
            if photo_url:
                emp_data["photo_url"] = photo_url

            supabase.table("employees").upsert(emp_data).execute()
            st.success(f"✅ Employee {name} saved successfully!")
            st.rerun()

# --- 3. Display, Export & Delete Employees ---
st.subheader("Employee Database")

df = fetch_data()

if not df.empty:
    # Father's Name automatically gets exported to Excel!
    excel_df = df.drop(columns=['photo_url'], errors='ignore')
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        excel_df.to_excel(writer, index=False, sheet_name='Employees')
    excel_data = output.getvalue()
    
    st.download_button(
        label="📥 Download Database as Excel",
        data=excel_data,
        file_name="Employee_Report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary"
    )
    st.divider()

    search_query = st.text_input("🔍 Search by Name, Mobile, or Aadhar")
    if search_query:
        filtered_df = df[
            df['name'].str.contains(search_query, case=False, na=False) |
            df['aadhar_no'].astype(str).str.contains(search_query, na=False) |
            df['mobile_no'].astype(str).str.contains(search_query, na=False) |
            # Enable searching by Father's name too
            df['father_name'].astype(str).str.contains(search_query, case=False, na=False) 
        ]
    else:
        filtered_df = df

    header_cols = st.columns([1.5, 1.5, 2, 2, 1, 1])
    header_cols[0].markdown("**Employee Info**")
    header_cols[1].markdown("**IDs & Contact**")
    header_cols[2].markdown("**Address & DOB**")
    header_cols[3].markdown("**Bank Details**")
    header_cols[4].markdown("**Photo**")
    header_cols[5].markdown("**Action**")
    st.divider()

    for idx, row in filtered_df.iterrows():
        cols = st.columns([1.5, 1.5, 2, 2, 1, 1])
        
        with cols[0]: 
            st.markdown(f"**{row.get('name', '')}**")
            # --- Display Father's Name under Employee Name ---
            if pd.notna(row.get('father_name')) and row.get('father_name') != "":
                st.caption(f"C/O: {row.get('father_name', '')}")
            
        with cols[1]: 
            st.caption(f"Aadhar: {row.get('aadhar_no', '')}")
            st.caption(f"Mob: {row.get('mobile_no', '')}")
            
        with cols[2]: 
            st.caption(f"DOB: {row.get('dob', '')}")
            st.caption(f"{row.get('address', '')}")
            
        with cols[3]: 
            st.caption(f"Bank: {row.get('bank_name', '')}")
            st.caption(f"A/C: {row.get('account_no', '')}")
            st.caption(f"IFSC: {row.get('ifsc_code', '')}")
            
        with cols[4]:
            if pd.notna(row.get('photo_url')) and row.get('photo_url') != "":
                st.image(row['photo_url'], width=70)
            else:
                st.text("No Photo")
        
        with cols[5]:
            if st.button("🗑️ Delete", key=f"del_{row['aadhar_no']}"):
                if pd.notna(row.get('photo_url')) and row.get('photo_url') != "":
                    filename = row['photo_url'].split('/')[-1]
                    supabase.storage.from_("employee-photos").remove([filename])
                
                supabase.table("employees").delete().eq("aadhar_no", row['aadhar_no']).execute()
                st.success(f"Deleted {row['name']}")
                st.rerun()
else:
    st.info("No employees found in the database. Add one above!")
