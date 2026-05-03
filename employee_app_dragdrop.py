import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime
from PIL import Image
import io

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
    st.error("⚠️ Failed to connect to the database. Please check your internet connection.")
    st.stop()

# ==========================================
# 2. MULTI-USER LOGIN SYSTEM
# ==========================================
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
                # Check credentials against Supabase 'app_users' table
                try:
                    user_data = supabase.table("app_users").select("*").eq("username", username).eq("password", password).execute()
                    
                    if len(user_data.data) > 0:
                        st.session_state.logged_in = True
                        st.session_state.role = user_data.data[0]['role']
                        st.session_state.username = username
                        st.rerun()
                    else:
                        st.error("❌ Incorrect Username or Password!")
                except Exception as e:
                    st.error("⚠️ Database error during login.")
    st.stop()

# --- Helper Functions ---
def fetch_hr_data():
    try:
        response = supabase.table("employees").select("*").execute()
        return pd.DataFrame(response.data)
    except: return pd.DataFrame()

def fetch_salary_data():
    try:
        response = supabase.table("employee_salary").select("*").execute()
        return pd.DataFrame(response.data)
    except: return pd.DataFrame()

def compress_image(uploaded_file, max_kb=50):
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"): img = img.convert("RGB")
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
# 3. DYNAMIC ROLE-BASED SIDEBAR
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

department = st.sidebar.radio("Select Menu:", allowed_menus)
st.sidebar.divider()

if st.sidebar.button("🚪 Secure Logout"):
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = None
    st.rerun()

df_hr = fetch_hr_data()
df_sal = fetch_salary_data()

# ==========================================
# PORTAL 0: EXECUTIVE DASHBOARD (Admin Only)
# ==========================================
if department == "📊 Executive Dashboard":
    st.title("📊 Executive Overview")
    if df_hr.empty: st.info("No data available.")
    else:
        st.subheader("Company Metrics")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Active Employees", f"👤 {len(df_hr)}")
        if not df_sal.empty:
            m2.metric("Total Payroll Dispensed", f"₹ {df_sal['net_salary'].sum():,.2f}")
            m3.metric("Average Net Salary", f"₹ {df_sal['net_salary'].mean():,.2f}")
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
            name = st.text_input("Full Name")
            father_name = st.text_input("Father's Name")
            aadhar_no = st.text_input("Aadhar Number (12 Digits)", max_chars=12) 
            mobile_no = st.text_input("Mobile Number (10 Digits)", max_chars=10)
            dob = st.date_input("Date of Birth", value=datetime.date(1990, 1, 1))
            joining_date = st.date_input("Joining Date", value=datetime.date.today())
        with col2:
            bank_name = st.text_input("Bank Name")
            account_no = st.text_input("Account Number") 
            ifsc_code = st.text_input("IFSC Code", max_chars=11)
            address = st.text_input("Address")
        with col3:
            photo = st.file_uploader("Upload Photo (<50KB)", type=['jpg','jpeg','png'])
        
        if st.form_submit_button("Save Employee", type="primary"):
            if not name or not aadhar_no or len(aadhar_no) != 12: st.error("⚠️ Invalid Name or Aadhar.")
            else:
                photo_url = ""
                if photo is not None:
                    compressed = compress_image(photo)
                    file_name = f"{aadhar_no}_photo.jpg"
                    supabase.storage.from_("employee-photos").upload(file_name, compressed, {"content-type": "image/jpeg", "upsert": "true"})
                    photo_url = supabase.storage.from_("employee-photos").get_public_url(file_name)
                
                emp_data = {"name": name, "father_name": father_name, "aadhar_no": aadhar_no, "mobile_no": mobile_no, "dob": str(dob), "joining_date": str(joining_date), "address": address, "bank_name": bank_name, "account_no": account_no, "ifsc_code": ifsc_code}
                if photo_url: emp_data["photo_url"] = photo_url
                supabase.table("employees").upsert(emp_data).execute()
                st.success("✅ Saved!"); st.rerun()

    # Show HR DB
    st.subheader("Employee Database")
    if not df_hr.empty:
        search = st.text_input("🔍 Search")
        if search: df_hr = df_hr[df_hr['name'].str.contains(search, case=False) | df_hr['aadhar_no'].str.contains(search)]
        
        for idx, row in df_hr.iterrows():
            cols = st.columns([2, 2, 2, 1, 1])
            cols[0].write(f"**{row.get('name','')}**\n{row.get('aadhar_no','')}")
            cols[1].write(f"Joined: {row.get('joining_date','')}\nMob: {row.get('mobile_no','')}")
            cols[2].write(f"{row.get('bank_name','')} - {row.get('account_no','')}")
            if pd.notna(row.get('photo_url')) and row.get('photo_url') != "": cols[3].image(row['photo_url'], width=60)
            if cols[4].button("🗑️", key=f"del_{row['aadhar_no']}"):
                supabase.table("employees").delete().eq("aadhar_no", row['aadhar_no']).execute()
                st.rerun()

# ==========================================
# PORTAL 2: FINANCE & ATTENDANCE (Admin & Finance)
# ==========================================
elif department == "💰 Finance & Attendance":
    st.title("Finance & Attendance Portal")
    if df_hr.empty: st.warning("⚠️ Add employees in HR first.")
    else:
        emp_dict = dict(zip(df_hr['aadhar_no'], df_hr['name']))
        with st.form("salary_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                aadhar = st.selectbox("Employee", df_hr['aadhar_no'], format_func=lambda x: f"{emp_dict[x]} ({x})")
                month = st.date_input("Month").strftime("%B %Y")
            with c2:
                total_days = st.number_input("Total Days", value=30)
                present = st.number_input("Days Present", value=30)
            with c3:
                base = st.number_input("Base Salary", value=15000)
                status = st.selectbox("Status", ["Pending", "Paid"])
            
            if st.form_submit_button("Save Payroll", type="primary"):
                net = (base / total_days) * present
                supabase.table("employee_salary").upsert({"aadhar_no": aadhar, "record_month": month, "total_days": total_days, "days_present": present, "base_salary": base, "net_salary": net, "status": status}).execute()
                st.success("✅ Saved!"); st.rerun()

        st.subheader("Payroll Database")
        if not df_sal.empty:
            disp_df = pd.merge(df_sal, df_hr[['aadhar_no', 'name']], on='aadhar_no', how='left')
            st.dataframe(disp_df[['record_month', 'name', 'days_present', 'base_salary', 'net_salary', 'status']], use_container_width=True, hide_index=True)
