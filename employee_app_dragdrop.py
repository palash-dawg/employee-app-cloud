import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime
from PIL import Image
import io

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Enterprise HR & Finance Portal", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# 1. DATABASE CONNECTION
# ==========================================
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase: Client = init_connection()
except Exception as e:
    st.error("⚠️ Failed to connect to the database. Please check your internet connection or Streamlit secrets.")
    st.stop()

# ==========================================
# 2. MULTI-USER LOGIN SYSTEM
# ==========================================
# Initialize session states
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = None

if not st.session_state.logged_in:
    st.title("🔒 Enterprise Portal Login")
    st.markdown("Please enter your department credentials.")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", type="primary")
            
            if submit:
                try:
                    # Check credentials against Supabase 'app_users' table
                    user_data = supabase.table("app_users").select("*").eq("username", username).eq("password", password).execute()
                    
                    if len(user_data.data) > 0:
                        st.session_state.logged_in = True
                        st.session_state.role = user_data.data[0]['role']
                        st.session_state.username = username
                        st.rerun()
                    else:
                        st.error("❌ Incorrect Username or Password! (Check capitalization and spaces)")
                except Exception as e:
                    st.error("⚠️ Database error during login. Make sure RLS is disabled on the app_users table!")
    st.stop()

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
def fetch_hr_data():
    try:
        response = supabase.table("employees").select("*").execute()
        return pd.DataFrame(response.data)
    except: 
        return pd.DataFrame()

def fetch_salary_data():
    try:
        response = supabase.table("employee_salary").select("*").execute()
        return pd.DataFrame(response.data)
    except: 
        return pd.DataFrame()

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

# ==========================================
# 4. DYNAMIC ROLE-BASED SIDEBAR
# ==========================================
st.sidebar.title("🏢 Enterprise Portal")
st.sidebar.caption(f"Logged in as: **{st.session_state.username}** ({st.session_state.role})")

# Determine which menus they are allowed to see based on their role
allowed_menus = []
if st.session_state.role == "Admin":
    allowed_menus = ["📊 Executive Dashboard", "👤 HR Department", "💰 Finance & Attendance"]
elif st.session_state.role == "HR":
    allowed_menus = ["👤 HR Department"]
elif st.session_state.role == "Finance":
    allowed_menus = ["💰 Finance & Attendance"]

department = st.sidebar.radio("Select Portal:", allowed_menus)
st.sidebar.divider()

if st.sidebar.button("🚪 Secure Logout"):
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = None
    st.rerun()

# Fetch data globally for the active session
df_hr = fetch_hr_data()
df_sal = fetch_salary_data()

# ==========================================
# PORTAL 0: EXECUTIVE DASHBOARD (Admin Only)
# ==========================================
if department == "📊 Executive Dashboard":
    st.title("📊 Executive Overview")
    
    if df_hr.empty: 
        st.info("No data available yet. Add employees in the HR Department.")
    else:
        st.subheader("Company Metrics")
        m1, m2, m3 = st.columns(3)
        
        m1.metric("Total Active Employees", f"👤 {len(df_hr)}")
        
        if not df_sal.empty:
            total_payroll = df_sal['net_salary'].sum()
            avg_salary = df_sal['net_salary'].mean()
            m2.metric("Total Payroll Dispensed", f"₹ {total_payroll:,.2f}")
            m3.metric("Average Net Salary", f"₹ {avg_salary:,.2f}")
        else:
            m2.metric("Total Payroll Dispensed", "₹ 0")
            m3.metric("Average Net Salary", "₹ 0")

# ==========================================
# PORTAL 1: HR DEPARTMENT (Admin & HR Only)
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
                dob = st.date_input("Date of Birth", value=datetime.date(1990, 1, 1))
            with date_col2:
                joining_date = st.date_input("Joining Date", value=datetime.date.today())
                
        with col2:
            st.markdown("**Bank & Address**")
            bank_name = st.text_input("Bank Name (e.g., SBI)")
            account_no = st.text_input("Account Number") 
            ifsc_code = st.text_input("IFSC Code", max_chars=11)
            address = st.text_input("Full Address")
            
        with col3:
            st.markdown("**Documents**")
            photo = st.file_uploader("Upload Photo (<50KB)", type=['jpg','jpeg','png'])
            
        if st.form_submit_button("Save Employee", type="primary"):
            if not name or not aadhar_no or len(aadhar_no) != 12: 
                st.error("⚠️ Name and 12-digit Aadhar are required.")
            else:
                try:
                    photo_url = ""
                    if photo is not None:
                        compressed = compress_image(photo)
                        file_name = f"{aadhar_no}_photo.jpg"
                        supabase.storage.from_("employee-photos").upload(file_name, compressed, {"content-type": "image/jpeg", "upsert": "true"})
                        photo_url = supabase.storage.from_("employee-photos").get_public_url(file_name)
                    
                    emp_data = {
                        "name": name, "father_name": father_name, "aadhar_no": aadhar_no, "mobile_no": mobile_no, 
                        "dob": str(dob), "joining_date": str(joining_date), "address": address, 
                        "bank_name": bank_name, "account_no": account_no, "ifsc_code": ifsc_code.upper() if ifsc_code else ""
                    }
                    if photo_url: 
                        emp_data["photo_url"] = photo_url
                        
                    supabase.table("employees").upsert(emp_data).execute()
                    st.success(f"✅ Saved {name}!"); st.rerun()
                except Exception as e:
                    st.error(f"⚠️ Database Error: {e}")

    # --- HR Database Display ---
    st.subheader("Employee Database")
    if not df_hr.empty:
        # Excel Export
        excel_df = df_hr.drop(columns=['photo_url'], errors='ignore')
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            excel_df.to_excel(writer, index=False, sheet_name='HR_Data')
        st.download_button("📥 Download HR Data (Excel)", data=output.getvalue(), file_name="HR_Report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
        st.divider()

        search = st.text_input("🔍 Search by Name or Aadhar")
        if search: 
            df_hr = df_hr[df_hr['name'].str.contains(search, case=False, na=False) | df_hr['aadhar_no'].astype(str).str.contains(search, na=False)]
        
        # Display Rows
        for idx, row in df_hr.iterrows():
            cols = st.columns([2, 2, 2, 1, 1])
            with cols[0]:
                st.markdown(f"**{row.get('name','')}**")
                if pd.notna(row.get('father_name')) and row.get('father_name') != "": st.caption(f"C/O: {row.get('father_name','')}")
                st.caption(f"Aadhar: {row.get('aadhar_no','')}")
            with cols[1]:
                st.write(f"Joined: {row.get('joining_date','')}")
                st.write(f"Mob: {row.get('mobile_no','')}")
            with cols[2]:
                st.write(f"Bank: {row.get('bank_name','')}")
                st.write(f"A/C: {row.get('account_no','')}")
            with cols[3]:
                if pd.notna(row.get('photo_url')) and row.get('photo_url') != "": st.image(row['photo_url'], width=60)
            with cols[4]:
                if st.button("🗑️ Delete", key=f"del_{row['aadhar_no']}"):
                    try:
                        if pd.notna(row.get('photo_url')) and row.get('photo_url') != "":
                            supabase.storage.from_("employee-photos").remove([row['photo_url'].split('/')[-1]])
                        supabase.table("employees").delete().eq("aadhar_no", row['aadhar_no']).execute()
                        st.rerun()
                    except Exception as e: st.error("⚠️ Delete failed.")
    else:
        st.info("No employees found.")

# ==========================================
# PORTAL 2: FINANCE & ATTENDANCE (Admin & Finance)
# ==========================================
elif department == "💰 Finance & Attendance":
    st.title("Finance & Attendance Portal")
    
    if df_hr.empty: 
        st.warning("⚠️ No employees exist yet. Add staff in the HR Department first.")
    else:
        st.subheader("Process Payroll")
        emp_dict = dict(zip(df_hr['aadhar_no'], df_hr['name']))
        
        with st.form("salary_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("**1. Select Employee**")
                aadhar = st.selectbox("Employee Name", df_hr['aadhar_no'], format_func=lambda x: f"{emp_dict[x]} ({x})")
                month = st.date_input("Month & Year").strftime("%B %Y")
            with c2:
                st.markdown("**2. Attendance**")
                total_days = st.number_input("Total Working Days", min_value=1, value=30)
                present = st.number_input("Days Present", min_value=0, value=30)
            with c3:
                st.markdown("**3. Salary**")
                base = st.number_input("Monthly Base Salary (₹)", min_value=0, value=15000)
                status = st.selectbox("Status", ["Pending", "Paid"])
            
            if st.form_submit_button("Save Payroll Record", type="primary"):
                try:
                    net = (base / total_days) * present
                    supabase.table("employee_salary").upsert({
                        "aadhar_no": aadhar, "record_month": month, "total_days": total_days, 
                        "days_present": present, "base_salary": base, "net_salary": round(net, 2), "status": status
                    }).execute()
                    st.success(f"✅ Saved salary for {emp_dict[aadhar]}!"); st.rerun()
                except Exception as e:
                    st.error("⚠️ Error saving data.")

        # --- Finance Database Display ---
        st.divider()
        st.subheader("Payroll Database")
        if not df_sal.empty:
            disp_df = pd.merge(df_sal, df_hr[['aadhar_no', 'name']], on='aadhar_no', how='left')
            st.dataframe(disp_df[['record_month', 'name', 'days_present', 'base_salary', 'net_salary', 'status']], use_container_width=True, hide_index=True)
            
            # Excel Export
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                disp_df.drop(columns=['id'], errors='ignore').to_excel(writer, index=False, sheet_name='Payroll_Data')
            st.download_button("📥 Download Payroll Data (Excel)", data=output.getvalue(), file_name="Payroll_Report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.info("No salary records found.")
