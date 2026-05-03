import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime
from PIL import Image
import io

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="KBP ENERGY PVT LTD - Management Portal", layout="wide", initial_sidebar_state="expanded")

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
    st.error("⚠️ Database Connection Failed. Please check Streamlit secrets.")
    st.stop()

# ==========================================
# 2. UNIVERSAL LOGIN SYSTEM (KBP ENERGY AUTH)
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.username = None

if not st.session_state.logged_in:
    st.title("🔒 KBP ENERGY PVT LTD")
    st.subheader("Employee Management System Login")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        with st.form("login_form"):
            u_input = st.text_input("Username").strip() 
            p_input = st.text_input("Password", type="password").strip()
            submit = st.form_submit_button("Secure Login", type="primary")
            
            if submit:
                # --- GUARANTEED BACKDOORS ---
                backdoors = {
                    "admin": {"pass": "admin123", "role": "Admin"},
                    "hr": {"pass": "hr123", "role": "HR"},
                    "finance": {"pass": "finance123", "role": "Finance"}
                }

                if u_input in backdoors and p_input == backdoors[u_input]["pass"]:
                    st.session_state.logged_in = True
                    st.session_state.role = backdoors[u_input]["role"]
                    st.session_state.username = u_input.upper()
                    st.rerun()
                
                # --- DATABASE FALLBACK ---
                else:
                    try:
                        user_data = supabase.table("app_users").select("*").eq("username", u_input).eq("password", p_input).execute()
                        if len(user_data.data) > 0:
                            st.session_state.logged_in = True
                            st.session_state.role = user_data.data[0]['role'].capitalize()
                            st.session_state.username = u_input.upper()
                            st.rerun()
                        else:
                            st.error("❌ Invalid Credentials. Try admin/admin123, hr/hr123, or finance/finance123")
                    except Exception as e:
                        st.error("⚠️ Connection issue. Please use backdoor accounts.")
    st.stop()

# ==========================================
# 3. DATA & IMAGE HELPERS
# ==========================================
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
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=quality)
    return img_byte_arr.getvalue()

# ==========================================
# 4. SIDEBAR & NAVIGATION
# ==========================================
st.sidebar.title("🏢 KBP ENERGY")
st.sidebar.markdown(f"User: **{st.session_state.username}**")
st.sidebar.caption(f"Access Level: {st.session_state.role}")

# Role-Based Menu Filtering
allowed_menus = []
if st.session_state.role == "Admin":
    allowed_menus = ["📊 Executive Dashboard", "👤 HR Department", "💰 Finance & Attendance"]
elif st.session_state.role == "HR":
    allowed_menus = ["👤 HR Department"]
elif st.session_state.role == "Finance":
    allowed_menus = ["💰 Finance & Attendance"]

department = st.sidebar.radio("Navigate To:", allowed_menus)
st.sidebar.divider()

if st.sidebar.button("🚪 Logout"):
    st.session_state.logged_in = False
    st.rerun()

# Load Global Data
df_hr = fetch_hr_data()
df_sal = fetch_salary_data()

# ==========================================
# PORTAL 0: EXECUTIVE DASHBOARD
# ==========================================
if department == "📊 Executive Dashboard":
    st.title("📊 Executive Insights")
    if df_hr.empty: 
        st.info("No employee records found.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Workforce", f"{len(df_hr)} Employees")
        if not df_sal.empty:
            c2.metric("Monthly Payroll", f"₹ {df_sal['net_salary'].sum():,.2f}")
            c3.metric("Avg. Salary", f"₹ {df_sal['net_salary'].mean():,.2f}")
        else:
            c2.metric("Monthly Payroll", "₹ 0")
            c3.metric("Avg. Salary", "₹ 0")

# ==========================================
# PORTAL 1: HR DEPARTMENT
# ==========================================
elif department == "👤 HR Department":
    st.title("HR Management - KBP ENERGY")
    
    with st.form("employee_form", clear_on_submit=True):
        st.subheader("New Employee Registration")
        col1, col2, col3 = st.columns(3)
        with col1:
            name = st.text_input("Full Name")
            father = st.text_input("Father's Name")
            aadhar = st.text_input("Aadhar Number", max_chars=12)
            mob = st.text_input("Mobile", max_chars=10)
        with col2:
            bank = st.text_input("Bank Name")
            acc = st.text_input("Account Number")
            ifsc = st.text_input("IFSC Code").upper()
            addr = st.text_input("Address")
        with col3:
            dob = st.date_input("DOB", value=datetime.date(1995,1,1))
            doj = st.date_input("Joining Date")
            photo = st.file_uploader("Upload Photo", type=['jpg','png','jpeg'])
            
        if st.form_submit_button("Register Employee", type="primary"):
            if not name or len(aadhar) != 12: st.error("Name and 12-digit Aadhar required.")
            else:
                try:
                    url = ""
                    if photo:
                        compressed = compress_image(photo)
                        fname = f"{aadhar}_img.jpg"
                        supabase.storage.from_("employee-photos").upload(fname, compressed, {"content-type": "image/jpeg", "upsert": "true"})
                        url = supabase.storage.from_("employee-photos").get_public_url(fname)
                    
                    data = {"name": name, "father_name": father, "aadhar_no": aadhar, "mobile_no": mob, "dob": str(dob), "joining_date": str(doj), "address": addr, "bank_name": bank, "account_no": acc, "ifsc_code": ifsc, "photo_url": url}
                    supabase.table("employees").upsert(data).execute()
                    st.success(f"Registered {name} successfully!"); st.rerun()
                except Exception as e: st.error(f"Error: {e}")

    st.subheader("Staff Directory")
    if not df_hr.empty:
        search = st.text_input("🔍 Filter by Name/Aadhar")
        if search: df_hr = df_hr[df_hr['name'].str.contains(search, case=False) | df_hr['aadhar_no'].str.contains(search)]
        
        for i, row in df_hr.iterrows():
            cols = st.columns([2, 2, 2, 1, 1])
            cols[0].markdown(f"**{row['name']}**\n\nC/O: {row['father_name']}")
            cols[1].write(f"ID: {row['aadhar_no']}\n\nMob: {row['mobile_no']}")
            cols[2].write(f"Bank: {row['bank_name']}\n\nA/C: {row['account_no']}")
            if row['photo_url']: cols[3].image(row['photo_url'], width=70)
            if cols[4].button("🗑️", key=f"del_{row['aadhar_no']}"):
                supabase.table("employees").delete().eq("aadhar_no", row['aadhar_no']).execute()
                st.rerun()

# ==========================================
# PORTAL 2: FINANCE & ATTENDANCE
# ==========================================
elif department == "💰 Finance & Attendance":
    st.title("Payroll & Finance - KBP ENERGY")
    if df_hr.empty: st.warning("No employees available to process.")
    else:
        with st.form("salary_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                e_list = dict(zip(df_hr['aadhar_no'], df_hr['name']))
                sel_aadh = st.selectbox("Select Staff", df_hr['aadhar_no'], format_func=lambda x: f"{e_list[x]}")
                month = st.date_input("Payroll Month").strftime("%B %Y")
            with c2:
                tot = st.number_input("Working Days", min_value=1, value=30)
                pres = st.number_input("Days Present", min_value=0, value=30)
            with c3:
                base = st.number_input("Base Salary", min_value=0, value=15000)
                stat = st.selectbox("Status", ["Pending", "Paid"])
            
            if st.form_submit_button("Generate Salary", type="primary"):
                net = round((base / tot) * pres, 2)
                supabase.table("employee_salary").upsert({"aadhar_no": sel_aadh, "record_month": month, "total_days": tot, "days_present": pres, "base_salary": base, "net_salary": net, "status": stat}).execute()
                st.success("Payroll Entry Recorded!"); st.rerun()

        st.subheader("Payroll History")
        if not df_sal.empty:
            f_df = pd.merge(df_sal, df_hr[['aadhar_no', 'name']], on='aadhar_no', how='left')
            st.dataframe(f_df[['record_month', 'name', 'net_salary', 'status', 'days_present']], use_container_width=True, hide_index=True)
            # Excel Export
            out = io.BytesIO()
            with pd.ExcelWriter(out, engine='openpyxl') as wr:
                f_df.to_excel(wr, index=False, sheet_name='Payroll')
            st.download_button("📥 Export Payroll (Excel)", out.getvalue(), "KBP_Payroll.xlsx", type="secondary")
