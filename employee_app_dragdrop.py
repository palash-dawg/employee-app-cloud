import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime
import io

# --- APP CONFIG ---
st.set_page_config(page_title="KBP ENERGY PVT LTD", layout="wide")

# --- DATABASE CONNECTION ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

# --- SESSION STATE & AUTH ---
if "logged_in" not in st.session_state:
    st.session_state.update({"logged_in": False, "role": None, "username": None})

if not st.session_state.logged_in:
    st.title("🏢 KBP ENERGY PVT LTD")
    with st.form("login_gate"):
        u = st.text_input("Username").strip().lower()
        p = st.text_input("Password", type="password").strip()
        if st.form_submit_button("Login"):
            # Universal Access (Bypasses table issues for now)
            access = {"admin": ("admin123", "Admin"), "hr": ("hr123", "HR"), 
                      "fin": ("fin123", "Finance"), "att": ("att123", "Attendance")}
            if u in access and p == access[u][0]:
                st.session_state.update({"logged_in": True, "role": access[u][1], "username": u.upper()})
                st.rerun()
            else: st.error("❌ Invalid Credentials")
    st.stop()

# --- REUSABLE DATA FUNCTIONS ---
def get_employees():
    try:
        res = supabase.table("employees").select("aadhar_no, name, base_salary").execute()
        return pd.DataFrame(res.data)
    except Exception: return pd.DataFrame(columns=["aadhar_no", "name", "base_salary"])

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("KBP ENERGY")
st.sidebar.write(f"Logged in as: **{st.session_state.username}**")

role = st.session_state.role
nav_options = {
    "Admin": ["📊 Dashboard", "👥 HR Portal", "📝 Attendance", "💰 Payroll"],
    "HR": ["👥 HR Portal"],
    "Attendance": ["📝 Attendance"],
    "Finance": ["💰 Payroll"]
}
choice = st.sidebar.radio("Navigation", nav_options.get(role, []))

if st.sidebar.button("Logout"):
    st.session_state.update({"logged_in": False, "role": None})
    st.rerun()

# ==========================================
# 📊 MODULE: DASHBOARD (Admin)
# ==========================================
if choice == "📊 Dashboard":
    st.title("📊 Enterprise Overview")
    df = get_employees()
    if not df.empty:
        c1, c2 = st.columns(2)
        c1.metric("Total Workforce", len(df))
        c2.metric("Total Monthly Liability", f"₹ {df['base_salary'].sum():,.2f}")
    else: st.info("Welcome! Start by adding employees in the HR Portal.")

# ==========================================
# 👥 MODULE: HR (Employee Registry)
# ==========================================
elif choice == "👥 HR Portal":
    st.title("👥 Employee Registry")
    with st.expander("➕ Register New Staff"):
        with st.form("hr_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            name = c1.text_input("Name")
            aadhar = c1.text_input("Aadhar No", max_chars=12)
            mob = c2.text_input("Mobile")
            sal = c2.number_input("Base Salary", min_value=0, value=15000)
            if st.form_submit_button("Save Employee"):
                supabase.table("employees").upsert({"aadhar_no": aadhar, "name": name, 
                                                   "mobile_no": mob, "base_salary": sal}).execute()
                st.success("Staff Registered!"); st.rerun()
    
    st.dataframe(get_employees(), use_container_width=True, hide_index=True)

# ==========================================
# 📝 MODULE: ADVANCED ATTENDANCE (Attendance Role)
# ==========================================
elif choice == "📝 Attendance":
    st.title("📝 Staff Attendance")
    date_pick = st.date_input("Attendance Date", datetime.date.today())
    emps = get_employees()
    
    if emps.empty:
        st.warning("Please add employees first.")
    else:
        st.info(f"Marking logs for: {date_pick}")
        attendance_data = []
        
        # Load existing logs for the day
        res = supabase.table("daily_attendance").select("*").eq("date", str(date_pick)).execute()
        current_logs = {item['aadhar_no']: item['status'] for item in res.data}

        for _, row in emps.iterrows():
            col_name, col_status = st.columns([3, 2])
            col_name.write(f"**{row['name']}**")
            
            # Selectbox with existing data or default 'Present'
            idx = ["Present", "Absent", "Half-Day", "Leave"].index(current_logs.get(row['aadhar_no'], "Present"))
            status = col_status.selectbox("Status", ["Present", "Absent", "Half-Day", "Leave"], index=idx, key=row['aadhar_no'])
            
            attendance_data.append({"date": str(date_pick), "aadhar_no": row['aadhar_no'], "status": status})

        if st.button("💾 Save Today's Logs", type="primary"):
            supabase.table("daily_attendance").upsert(attendance_data).execute()
            st.success("Logs updated in database!")

# ==========================================
# 💰 MODULE: PAYROLL (Finance Role)
# ==========================================
elif choice == "💰 Payroll":
    st.title("💰 Monthly Payroll")
    target_month = st.date_input("Select Month (Select any date in that month)", datetime.date.today())
    
    if st.button("⚙️ Calculate Wages"):
        emps = get_employees()
        # Fetch attendance for the entire month
        start_date = target_month.replace(day=1)
        end_date = (start_date + datetime.timedelta(days=32)).replace(day=1) - datetime.timedelta(days=1)
        
        res = supabase.table("daily_attendance").select("*").gte("date", str(start_date)).lte("date", str(end_date)).execute()
        logs = pd.DataFrame(res.data)
        
        if logs.empty:
            st.error("No attendance records found for this month.")
        else:
            payroll_report = []
            for _, emp in emps.iterrows():
                p_logs = logs[logs['aadhar_no'] == emp['aadhar_no']]
                # Calculation: Present=1, Half-Day=0.5, Absent/Leave=0
                points = p_logs['status'].map({"Present": 1, "Half-Day": 0.5, "Absent": 0, "Leave": 0}).sum()
                net_pay = (emp['base_salary'] / 30) * points # Assuming 30-day base
                
                payroll_report.append({
                    "Name": emp['name'],
                    "Aadhar": emp['aadhar_no'],
                    "Days Marked": len(p_logs),
                    "Worked Days": points,
                    "Net Salary": round(net_pay, 2)
                })
            
            pay_df = pd.DataFrame(payroll_report)
            st.table(pay_df)
            
            # Excel Download
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                pay_df.to_excel(writer, index=False)
            st.download_button("📥 Export Payroll (Excel)", output.getvalue(), f"KBP_Payroll_{target_month.strftime('%B_%Y')}.xlsx")
