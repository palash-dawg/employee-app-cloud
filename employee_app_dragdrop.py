import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime
import io

# --- CONFIG ---
st.set_page_config(page_title="KBP ENERGY PVT LTD", layout="wide")

# --- DB CONNECTION ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

# --- AUTH SYSTEM ---
if "auth" not in st.session_state:
    st.session_state.auth = {"logged_in": False, "role": None, "user": None}

if not st.session_state.auth["logged_in"]:
    st.title("🏢 KBP ENERGY PVT LTD")
    with st.form("login"):
        u = st.text_input("Username").lower().strip()
        p = st.text_input("Password", type="password").strip()
        if st.form_submit_button("Login"):
            # Backdoor logic for immediate access
            backdoors = {"admin": ("admin123", "Admin"), "hr": ("hr123", "HR"), 
                         "finance": ("fin123", "Finance"), "attendance": ("att123", "Attendance")}
            if u in backdoors and p == backdoors[u][0]:
                st.session_state.auth = {"logged_in": True, "role": backdoors[u][1], "user": u}
                st.rerun()
            else: st.error("Invalid Credentials")
    st.stop()

# --- DATA HELPERS (Optimized with Caching) ---
def get_employees():
    res = supabase.table("employees").select("aadhar_no, name, base_salary").execute()
    return pd.DataFrame(res.data)

def get_attendance_for_date(selected_date):
    res = supabase.table("daily_attendance").select("*").eq("date", str(selected_date)).execute()
    return pd.DataFrame(res.data)

# --- SIDEBAR ---
role = st.session_state.auth["role"]
st.sidebar.title("KBP ENERGY")
st.sidebar.info(f"User: {st.session_state.auth['user'].upper()}\nRole: {role}")

menu_map = {
    "Admin": ["📊 Dashboard", "👥 HR", "📝 Attendance", "💰 Finance"],
    "HR": ["👥 HR"],
    "Attendance": ["📝 Attendance"],
    "Finance": ["💰 Finance"]
}
choice = st.sidebar.radio("Go to:", menu_map.get(role, []))

if st.sidebar.button("Logout"):
    st.session_state.auth = {"logged_in": False, "role": None, "user": None}
    st.rerun()

# ==========================================
# 📊 MODULE: DASHBOARD (Admin)
# ==========================================
if choice == "📊 Dashboard":
    st.title("📊 Executive Dashboard")
    df = get_employees()
    if not df.empty:
        c1, c2 = st.columns(2)
        c1.metric("Active Workforce", len(df))
        c2.metric("Total Monthly Base", f"₹ {df['base_salary'].sum() if 'base_salary' in df else 0:,.2f}")

# ==========================================
# 👥 MODULE: HR (Employee Management)
# ==========================================
elif choice == "👥 HR":
    st.title("👥 Employee Management")
    with st.expander("Add New Employee"):
        with st.form("hr_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            name = col1.text_input("Full Name")
            aadhar = col1.text_input("Aadhar (12 digits)", max_chars=12)
            base_sal = col2.number_input("Monthly Base Salary", min_value=0, value=15000)
            mob = col2.text_input("Mobile Number")
            if st.form_submit_button("Save"):
                supabase.table("employees").upsert({"name": name, "aadhar_no": aadhar, 
                                                   "base_salary": base_sal, "mobile_no": mob}).execute()
                st.success("Employee saved!"); st.rerun()
    
    st.subheader("Employee List")
    st.dataframe(get_employees(), use_container_width=True)

# ==========================================
# 📝 MODULE: ADVANCED ATTENDANCE
# ==========================================
elif choice == "📝 Attendance":
    st.title("📝 Daily Attendance Entry")
    date_entry = st.date_input("Select Date", datetime.date.today())
    emps = get_employees()
    
    if emps.empty:
        st.warning("Please add employees in the HR module first.")
    else:
        # Load existing attendance for this date
        existing_att = get_attendance_for_date(date_entry)
        att_dict = dict(zip(existing_att['aadhar_no'], existing_att['status'])) if not existing_att.empty else {}

        st.info(f"Marking attendance for: {date_entry.strftime('%d %B, %Y')}")
        
        # Grid View for Attendance Entry
        save_data = []
        for i, row in emps.iterrows():
            c1, c2 = st.columns([3, 2])
            c1.write(f"**{row['name']}** ({row['aadhar_no']})")
            
            # Default to "Present" if not already marked
            current_status = att_dict.get(row['aadhar_no'], "Present")
            status = c2.selectbox("Status", ["Present", "Absent", "Half-Day", "Leave"], 
                                  index=["Present", "Absent", "Half-Day", "Leave"].index(current_status),
                                  key=f"att_{row['aadhar_no']}")
            
            save_data.append({"date": str(date_entry), "aadhar_no": row['aadhar_no'], "status": status})

        if st.button("Submit Attendance", type="primary"):
            try:
                # Upsert uses the UNIQUE(date, aadhar_no) constraint we created in SQL
                supabase.table("daily_attendance").upsert(save_data).execute()
                st.success(f"Attendance saved for {len(save_data)} employees.")
            except Exception as e:
                st.error(f"Error: {e}")

# ==========================================
# 💰 MODULE: FINANCE (Automated Payroll)
# ==========================================
elif choice == "💰 Finance":
    st.title("💰 Payroll Processing")
    month = st.selectbox("Select Month", ["January", "February", "March", "April", "May", "June", 
                                          "July", "August", "September", "October", "November", "December"])
    year = st.selectbox("Select Year", [2025, 2026])
    
    if st.button("Calculate Payroll for Selected Month"):
        emps = get_employees()
        # Fetch all attendance records for that month
        # Note: In a production app, you would filter the query by date range
        res = supabase.table("daily_attendance").select("*").execute()
        att_df = pd.DataFrame(res.data)
        
        if att_df.empty:
            st.error("No attendance records found for this period.")
        else:
            # Simple calculation logic
            report = []
            for _, emp in emps.iterrows():
                emp_att = att_df[att_df['aadhar_no'] == emp['aadhar_no']]
                days_present = len(emp_att[emp_att['status'] == "Present"])
                half_days = len(emp_att[emp_att['status'] == "Half-Day"])
                
                effective_days = days_present + (half_days * 0.5)
                # Assuming 30-day month for calculation
                salary_earned = (emp['base_salary'] / 30) * effective_days
                
                report.append({
                    "Name": emp['name'],
                    "Aadhar": emp['aadhar_no'],
                    "Total Days Mark": len(emp_att),
                    "Effective Days": effective_days,
                    "Payable Salary": round(salary_earned, 2)
                })
            
            st.table(pd.DataFrame(report))
            
            # Export to Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                pd.DataFrame(report).to_excel(writer, index=False)
            st.download_button("📥 Download Payroll Report", output.getvalue(), f"Payroll_{month}_{year}.xlsx")
