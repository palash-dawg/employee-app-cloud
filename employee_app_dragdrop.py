import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime
from PIL import Image
import io

# Setup the page configuration first
st.set_page_config(page_title="Enterprise HR & Finance Portal", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# 1. SECURITY & LOGIN SYSTEM
# ==========================================
# Initialize login state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# Fetch password securely, default to 'admin123' if not set
MASTER_PASSWORD = st.secrets.get("APP_PASSWORD", "admin123")

# Show login screen if not logged in
if not st.session_state.logged_in:
    st.title("🔒 Enterprise Portal Login")
    st.markdown("Please enter the master password to access HR and Finance records.")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        pwd = st.text_input("Password", type="password")
        if st.button("Login", type="primary"):
            if pwd == MASTER_PASSWORD:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("❌ Incorrect Password!")
    # Stop the app from loading anything else until logged in
    st.stop()

# ==========================================
# 2. SECURE CLOUD CONNECTION & ERROR HANDLING
# ==========================================
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase: Client = init_connection()
except Exception as e:
    st.error("⚠️ Failed to connect to the database. Please check your internet connection or API keys.")
    st.stop()

# --- Helper Functions with Crash Prevention ---
def fetch_hr_data():
    try:
        response = supabase.table("employees").select("*").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error("⚠️ Error fetching employee data. Please ensure the 'employees' table exists in Supabase.")
        return pd.DataFrame()

def fetch_salary_data():
    try:
        response = supabase.table("employee_salary").select("*").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        st.error("⚠️ Error fetching salary data. Please ensure the 'employee_salary' table exists in Supabase.")
        return pd.DataFrame()

def compress_image(uploaded_file, max_kb=50):
    """Compresses uploaded images to save cloud storage space."""
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

# ==========================================
# SIDEBAR NAVIGATION
# ==========================================
st.sidebar.title("🏢 Enterprise Portal")
department = st.sidebar.radio(
    "Select Department:",
    ["📊 Executive Dashboard", "👤 HR Department", "💰 Finance & Attendance"]
)
st.sidebar.divider()

if st.sidebar.button("🚪 Secure Logout"):
    st.session_state.logged_in = False
    st.rerun()

st.sidebar.caption("Secure Cloud Connected ✅")

# Pre-fetch global data to use across the app
df_hr = fetch_hr_data()
df_sal = fetch_salary_data()

# ==========================================
# PORTAL 0: EXECUTIVE DASHBOARD
# ==========================================
if department == "📊 Executive Dashboard":
    st.title("📊 Executive Overview")
    
    if df_hr.empty:
        st.info("No data available yet. Add employees in the HR Department first.")
    else:
        st.subheader("Company Metrics")
        m1, m2, m3 = st.columns(3)
        
        total_emps = len(df_hr)
        m1.metric("Total Active Employees", f"👤 {total_emps}")
        
        if not df_sal.empty:
            total_payroll = df_sal['net_salary'].sum()
            avg_salary = df_sal['net_salary'].mean()
            m2.metric("Total Payroll Dispensed", f"₹ {total_payroll:,.2f}")
            m3.metric("Average Net Salary", f"₹ {avg_salary:,.2f}")
        else:
            m2.metric("Total Payroll Dispensed", "₹ 0")
            m3.metric("Average Net Salary", "₹ 0")

# ==========================================
# PORTAL 1: HR DEPARTMENT
# ==========================================
elif department == "👤 HR Department":
    st.title("HR Portal - Employee Management")
    
    with st.form("employee_form", clear_on_submit=True):
        st.subheader("Add / Edit Employee Profile")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**Personal Details**")
            name = st.text_input("Full Name")
            father_name = st.text_input("Father's Name")
            aadhar_no = st.text_input("Aadhar Number (12 Digits)", max_chars=12) 
            mobile_no = st.text_input("Mobile Number (10 Digits)", max_chars=10)
            date_col1, date_col2 = st.columns(2)
            with date_col1:
                dob = st.date_input("Date of Birth", min_value=datetime.date(1930, 1, 1), max_value=datetime.date.today(), value=datetime.date(1990, 1, 1))
            with date_col2:
                joining_date = st.date_input("Joining Date", value=datetime.date.today())
                
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
            # Data Validation Checks
            if not name or not aadhar_no or not mobile_no:
                st.error("⚠️ Name, Aadhar, and Mobile Number are required!")
            elif len(aadhar_no) != 12 or not aadhar_no.isdigit():
                st.error("⚠️ Aadhar must be exactly 12 numbers.")
            else:
                try:
                    photo_url = ""
                    # Handle Image Compression and Cloud Upload
                    if photo is not None:
                        compressed_bytes = compress_image(photo, max_kb=50)
                        clean_filename = photo.name.replace(" ", "_").split('.')[0] + ".jpg"
                        file_name = f"{aadhar_no}_{clean_filename}"
                        supabase.storage.from_("employee-photos").upload(file_name, compressed_bytes, {"content-type": "image/jpeg", "upsert": "true"})
                        photo_url = supabase.storage.from_("employee-photos").get_public_url(file_name)

                    # Prepare Text Data
                    emp_data = {
                        "name": name, "father_name": father_name, "aadhar_no": aadhar_no, "mobile_no": mobile_no,
                        "dob": str(dob), "joining_date": str(joining_date), "address": address,
                        "bank_name": bank_name, "account_no": account_no, "ifsc_code": ifsc_code.upper() if ifsc_code else "", 
                    }
                    if photo_url:
                        emp_data["photo_url"] = photo_url

                    # Save to Database
                    supabase.table("employees").upsert(emp_data).execute()
                    st.success(f"✅ Employee {name} saved successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"⚠️ A database error occurred: {e}")

    # --- Display HR Database ---
    st.subheader("Employee Database")
    df = df_hr
    
    if not df.empty:
        # Excel Export (Photo URL removed for cleanliness)
        excel_df = df.drop(columns=['photo_url'], errors='ignore')
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            excel_df.to_excel(writer, index=False, sheet_name='HR_Data')
        st.download_button(label="📥 Download HR Data (Excel)", data=output.getvalue(), file_name="HR_Report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
        st.divider()

        # Search Bar
        search_query = st.text_input("🔍 Search by Name, Mobile, or Aadhar")
        if search_query:
            df = df[df['name'].str.contains(search_query, case=False, na=False) | df['aadhar_no'].astype(str).str.contains(search_query, na=False)]

        # Header Columns
        header_cols = st.columns([1.5, 1.5, 2, 2, 1, 1])
        header_cols[0].markdown("**Employee Info**")
        header_cols[1].markdown("**IDs & Contact**")
        header_cols[2].markdown("**Address & Dates**") 
        header_cols[3].markdown("**Bank Details**")
        header_cols[4].markdown("**Photo**")
        header_cols[5].markdown("**Action**")
        st.divider()

        # Print Rows
        for idx, row in df.iterrows():
            cols = st.columns([1.5, 1.5, 2, 2, 1, 1])
            with cols[0]: 
                st.markdown(f"**{row.get('name', '')}**")
                if pd.notna(row.get('father_name')) and row.get('father_name') != "": st.caption(f"C/O: {row.get('father_name', '')}")
            with cols[1]: 
                st.caption(f"Aadhar: {row.get('aadhar_no', '')}")
                st.caption(f"Mob: {row.get('mobile_no', '')}")
            with cols[2]: 
                st.caption(f"DOB: {row.get('dob', '')}")
                st.caption(f"Joined: {row.get('joining_date', '')}") 
            with cols[3]: 
                st.caption(f"Bank: {row.get('bank_name', '')}")
                st.caption(f"A/C: {row.get('account_no', '')}")
            with cols[4]:
                if pd.notna(row.get('photo_url')) and row.get('photo_url') != "": st.image(row['photo_url'], width=70)
                else: st.text("No Photo")
            with cols[5]:
                if st.button("🗑️ Delete", key=f"del_hr_{row['aadhar_no']}"):
                    try:
                        # Attempt to delete the photo from storage first
                        if pd.notna(row.get('photo_url')) and row.get('photo_url') != "":
                            supabase.storage.from_("employee-photos").remove([row['photo_url'].split('/')[-1]])
                        # Delete from database
                        supabase.table("employees").delete().eq("aadhar_no", row['aadhar_no']).execute()
                        st.rerun()
                    except Exception as e:
                        st.error("⚠️ Could not delete employee. Check connection.")
    else:
        st.info("No employees found.")

# ==========================================
# PORTAL 2: FINANCE & ATTENDANCE
# ==========================================
elif department == "💰 Finance & Attendance":
    st.title("Finance & Attendance Portal")
    
    emp_df = df_hr
    
    if emp_df.empty:
        st.warning("⚠️ No employees exist yet. Please go to the HR Department to add staff first.")
    else:
        st.subheader("Process Payroll")
        # Create a mapping dictionary to show Names instead of just Aadhar numbers
        emp_dict = dict(zip(emp_df['aadhar_no'], emp_df['name']))
        
        with st.form("salary_form", clear_on_submit=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**1. Select Employee**")
                selected_aadhar = st.selectbox("Employee Name", options=emp_df['aadhar_no'], format_func=lambda x: f"{emp_dict[x]} ({x})")
                record_month = st.date_input("Month & Year").strftime("%B %Y")
                
            with col2:
                st.markdown("**2. Attendance Data**")
                total_days = st.number_input("Total Working Days in Month", min_value=1, max_value=31, value=30)
                days_present = st.number_input("Actual Days Present", min_value=0, max_value=31, value=30)
                
            with col3:
                st.markdown("**3. Salary Data**")
                base_salary = st.number_input("Monthly Base Salary (₹)", min_value=0, value=15000)
                status = st.selectbox("Payment Status", ["Pending", "Paid"])
                
            submit_salary = st.form_submit_button("Calculate & Save Record", type="primary")
            
            if submit_salary:
                try:
                    # Salary calculation logic
                    calculated_net = (base_salary / total_days) * days_present
                    
                    salary_data = {
                        "aadhar_no": selected_aadhar,
                        "record_month": record_month,
                        "total_days": total_days,
                        "days_present": days_present,
                        "base_salary": base_salary,
                        "net_salary": round(calculated_net, 2),
                        "status": status
                    }
                    supabase.table("employee_salary").upsert(salary_data).execute()
                    st.success(f"✅ Salary of ₹{round(calculated_net, 2)} saved for {emp_dict[selected_aadhar]}!")
                    st.rerun()
                except Exception as e:
                    st.error("⚠️ Error saving salary data.")

    # --- Show Salary Database ---
    st.divider()
    st.subheader("Payroll Database")
    
    sal_df = df_sal
    if not sal_df.empty:
        # Merge Salary data with HR data to append the employee's name for easy reading
        display_df = pd.merge(sal_df, emp_df[['aadhar_no', 'name']], on='aadhar_no', how='left')
        
        st.dataframe(
            display_df[['record_month', 'name', 'aadhar_no', 'days_present', 'total_days', 'base_salary', 'net_salary', 'status']],
            use_container_width=True,
            hide_index=True
        )
        
        # Finance Excel Export
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            display_df.drop(columns=['id'], errors='ignore').to_excel(writer, index=False, sheet_name='Payroll_Data')
        st.download_button("📥 Download Payroll Data (Excel)", data=output.getvalue(), file_name="Payroll_Report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("No salary records found.")
