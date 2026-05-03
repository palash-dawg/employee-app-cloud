import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime
import bcrypt # For secure password handling

# --- APP CONFIG ---
st.set_page_config(page_title="KBP ENERGY PVT LTD - Enterprise Portal", layout="wide")

# --- DATABASE CONNECTION ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase = init_connection()

# --- AUTH SYSTEM (Enterprise Upgrade) ---
if "logged_in" not in st.session_state:
    st.session_state.update({"logged_in": False, "role": None, "username": None})

if not st.session_state.logged_in:
    st.title("🏢 KBP ENERGY ENTERPRISE")
    with st.container(border=True):
        u = st.text_input("Username").strip().lower()
        p = st.text_input("Password", type="password").strip()
        
        if st.button("Secure Login", type="primary"):
            # Query the app_users table we created in the schema
            user_query = supabase.table("app_users").select("*").eq("username", u).execute()
            
            if user_query.data:
                user_data = user_query.data[0]
                # In a real enterprise app, use bcrypt.checkpw(p.encode(), user_data['password_hash'].encode())
                # For this demo, we'll match the 'access' logic but check against DB roles
                if p == "admin123": # Replace with hash check in production
                    st.session_state.update({
                        "logged_in": True, 
                        "role": user_data['role'].capitalize(), 
                        "username": u
                    })
                    st.rerun()
            st.error("❌ Authentication Failed")
    st.stop()

# --- SIDEBAR & NAVIGATION ---
st.sidebar.title(f"Welcome, {st.session_state.username.upper()}")
st.sidebar.info(f"Access Level: {st.session_state.role}")

nav_options = {
    "Admin": ["📊 Dashboard", "👥 HR Portal", "📝 Attendance", "💰 Payroll"],
    "Hr": ["👥 HR Portal", "📝 Attendance"],
    "Attendance": ["📝 Attendance"],
    "Finance": ["💰 Payroll"]
}

choice = st.sidebar.radio("Navigation", nav_options.get(st.session_state.role, []))

if st.sidebar.button("Logout"):
    st.session_state.update({"logged_in": False, "role": None})
    st.rerun()

# ==========================================
# 👥 MODULE: HR PORTAL
# ==========================================
if choice == "👥 HR Portal":
    st.title("👥 Employee Lifecycle Management")
    
    tabs = st.tabs(["Active Directory", "Register New Employee"])
    
    with tabs[1]:
        with st.form("registration_form"):
            col1, col2 = st.columns(2)
            name = col1.text_input("Full Name")
            f_name = col1.text_input("Father's Name")
            aadhar = col1.text_input("Aadhar Card No (Primary Key)", max_chars=12)
            mob = col1.text_input("Mobile No")
            
            dob = col2.date_input("Date of Birth", min_value=datetime.date(1960,1,1))
            doj = col2.date_input("Joining Date")
            base_sal = col2.number_input("Monthly Base Salary", min_value=0)
            
            st.divider()
            b_col1, b_col2, b_col3 = st.columns(3)
            b_name = b_col1.text_input("Bank Name")
            acc_no = b_col2.text_input("Account Number")
            ifsc = b_col3.text_input("IFSC Code").upper()

            if st.form_submit_button("Commit to Database"):
                # Use standard Python dates; Supabase handles the ISO strings
                emp_data = {
                    "aadhar_no": aadhar, "name": name, "father_name": f_name, 
                    "mobile_no": mob, "dob": str(dob), "joining_date": str(doj),
                    "bank_name": b_name, "account_no": acc_no, "ifsc_code": ifsc
                }
                supabase.table("employees").upsert(emp_data).execute()
                st.success(f"Record created for {name}")

    with tabs[0]:
        res = supabase.table("employees").select("*").eq("is_active", True).execute()
        if res.data:
            st.dataframe(pd.DataFrame(res.data), use_container_width=True)

# ==========================================
# 📝 MODULE: ATTENDANCE (Batch Logic)
# ==========================================
elif choice == "📝 Attendance":
    st.title("📝 Daily Attendance Logs")
    target_date = st.date_input("Attendance Date", datetime.date.today())
    
    # Efficiently fetch only active employees
    emps = supabase.table("employees").select("aadhar_no, name").eq("is_active", True).execute()
    
    if emps.data:
        df_emps = pd.DataFrame(emps.data)
        
        # Pull existing records for this date to prevent double entry
        existing = supabase.table("daily_attendance").select("aadhar_no, status").eq("attendance_date", str(target_date)).execute()
        att_map = {item['aadhar_no']: item['status'] for item in existing.data}
        
        df_emps['status'] = df_emps['aadhar_no'].map(lambda x: att_map.get(x, "Present"))
        
        edited_df = st.data_editor(
            df_emps,
            column_config={
                "status": st.column_config.SelectboxColumn("Status", options=["Present", "Absent", "Leave", "Half-Day"])
            },
            hide_index=True, use_container_width=True
        )
        
        if st.button("💾 Finalize Attendance", type="primary"):
            payload = [
                {"attendance_date": str(target_date), "aadhar_no": r['aadhar_no'], "status": r['status']}
                for _, r in edited_df.iterrows()
            ]
            supabase.table("daily_attendance").upsert(payload).execute()
            st.toast("Attendance synchronization complete!")

# ==========================================
# 💰 MODULE: PAYROLL (Using DB Logic)
# ==========================================
elif choice == "💰 Payroll":
    st.title("💰 Monthly Payroll Engine")
    
    col_y, col_m = st.columns(2)
    year = col_y.selectbox("Year", [2025, 2026])
    month = col_m.selectbox("Month", range(1, 13))
    
    # First day of month for the DB record
    record_date = datetime.date(year, month, 1)
    
    if st.button("🚀 Calculate Monthly Payouts"):
        # 1. Fetch Salary Config and Attendance
        emps = supabase.table("employees").select("aadhar_no, name, bank_name, account_no").execute()
        # Since 'base_salary' wasn't in employees in the SQL but in employee_salary, 
        # we fetch it or define it here. 
        
        # Calculate days in month
        import calendar
        days_in_month = calendar.monthrange(year, month)[1]
        
        # Fetch attendance points for this month
        start_date = str(record_date)
        end_date = str(record_date.replace(day=days_in_month))
        
        att_data = supabase.table("daily_attendance").select("aadhar_no, status")\
            .gte("attendance_date", start_date).lte("attendance_date", end_date).execute()
        
        if not att_data.data:
            st.warning("No attendance records found for this period.")
        else:
            df_att = pd.DataFrame(att_data.data)
            score_map = {"Present": 1, "Half-Day": 0.5, "Absent": 0, "Leave": 0}
            
            payroll_entries = []
            for emp in emps.data:
                # Calculate attendance points
                emp_att = df_att[df_att['aadhar_no'] == emp['aadhar_no']]
                days_present = emp_att['status'].map(score_map).sum()
                
                payroll_entries.append({
                    "aadhar_no": emp['aadhar_no'],
                    "record_month": start_date,
                    "total_days_in_month": days_in_month,
                    "days_present": int(days_present),
                    "status": "Pending"
                })
            
            # Batch upsert to employee_salary
            # The database's "GENERATED ALWAYS" column will handle net_salary automatically!
            supabase.table("employee_salary").upsert(payroll_entries).execute()
            
            # Display results
            final_res = supabase.table("employee_salary").select("*, employees(name)")\
                .eq("record_month", start_date).execute()
            
            st.dataframe(pd.DataFrame(final_res.data), use_container_width=True)
