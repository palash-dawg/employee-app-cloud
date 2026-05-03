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

# --- AUTH SYSTEM ---
if "logged_in" not in st.session_state:
    st.session_state.update({"logged_in": False, "role": None, "username": None})

if not st.session_state.logged_in:
    st.title("🏢 KBP ENERGY PVT LTD")
    with st.form("login_gate"):
        u = st.text_input("Username").strip().lower()
        p = st.text_input("Password", type="password").strip()
        if st.form_submit_button("Login"):
            access = {"admin": ("admin123", "Admin"), "hr": ("hr123", "HR"), 
                      "fin": ("fin123", "Finance"), "att": ("att123", "Attendance")}
            if u in access and p == access[u][0]:
                st.session_state.update({"logged_in": True, "role": access[u][1], "username": u.upper()})
                st.rerun()
            else: st.error("❌ Invalid Credentials")
    st.stop()

# --- SIDEBAR ---
st.sidebar.title("KBP ENERGY")
role = st.session_state.role
nav = {"Admin": ["📊 Dashboard", "👥 HR Portal", "📝 Attendance", "💰 Payroll"],
       "HR": ["👥 HR Portal"], "Attendance": ["📝 Attendance"], "Finance": ["💰 Payroll"]}
choice = st.sidebar.radio("Navigation", nav.get(role, []))

if st.sidebar.button("Logout"):
    st.session_state.update({"logged_in": False, "role": None})
    st.rerun()

# ==========================================
# 👥 MODULE: HR PORTAL (Registry)
# ==========================================
if choice == "👥 HR Portal":
    st.title("👥 Employee Management")
    
    with st.expander("➕ Register New Staff"):
        with st.form("full_hr_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            name = col1.text_input("Full Name")
            f_name = col1.text_input("Father's Name")
            aadhar = col1.text_input("Aadhar Card No", max_chars=12)
            mob = col1.text_input("Mobile No")
            addr = col1.text_area("Full Address")
            
            dob = col2.date_input("Date of Birth", value=datetime.date(1995,1,1))
            doj = col2.date_input("Joining Date")
            base_sal = col2.number_input("Monthly Base Salary", min_value=0, value=15000)
            b_name = col2.text_input("Bank Name")
            acc_no = col2.text_input("Account Number")
            ifsc = col2.text_input("IFSC Code").upper()
            
            if st.form_submit_button("Save Employee"):
                data = {"aadhar_no": aadhar, "name": name, "father_name": f_name, "mobile_no": mob, 
                        "address": addr, "dob": str(dob), "joining_date": str(doj), "base_salary": base_sal,
                        "bank_name": b_name, "account_no": acc_no, "ifsc_code": ifsc}
                supabase.table("employees").upsert(data).execute()
                st.success("Staff Registered!"); st.rerun()

    res = supabase.table("employees").select("*").execute()
    if res.data:
        st.dataframe(pd.DataFrame(res.data), use_container_width=True, hide_index=True)

# ==========================================
# 📝 MODULE: ATTENDANCE (Optimized for 100+ People)
# ==========================================
elif choice == "📝 Attendance":
    st.title("📝 Batch Attendance")
    dt = st.date_input("Date", datetime.date.today())
    
    # 1. Fetch Employees and Existing Attendance
    emps = supabase.table("employees").select("aadhar_no, name").execute()
    existing = supabase.table("daily_attendance").select("aadhar_no, status").eq("date", str(dt)).execute()
    
    if not emps.data:
        st.warning("No employees in system.")
    else:
        # Create a working dataframe
        df_emps = pd.DataFrame(emps.data)
        att_map = {item['aadhar_no']: item['status'] for item in existing.data}
        df_emps['Status'] = df_emps['aadhar_no'].map(lambda x: att_map.get(x, "Present"))
        
        st.info("💡 Tip: Everything is 'Present' by default. Just change the people who are Absent/Half-Day.")
        
        # 2. Spreadsheet-style Editing
        edited_df = st.data_editor(
            df_emps,
            column_config={
                "aadhar_no": st.column_config.TextColumn("Aadhar", disabled=True),
                "name": st.column_config.TextColumn("Employee Name", disabled=True),
                "Status": st.column_config.SelectboxColumn("Status", options=["Present", "Absent", "Half-Day", "Leave"], required=True)
            },
            hide_index=True,
            use_container_width=True,
            key="attendance_editor"
        )
        
        if st.button("💾 Save All Attendance", type="primary"):
            final_data = []
            for _, row in edited_df.iterrows():
                final_data.append({"date": str(dt), "aadhar_no": row['aadhar_no'], "status": row['Status']})
            
            try:
                supabase.table("daily_attendance").upsert(final_data).execute()
                st.success(f"Successfully saved attendance for {len(final_data)} employees.")
            except Exception as e:
                st.error(f"Database Error: {e}")

# ==========================================
# 💰 MODULE: PAYROLL (Automated Batch)
# ==========================================
elif choice == "💰 Payroll":
    st.title("💰 Batch Payroll Generation")
    sel_date = st.date_input("Select Month", datetime.date.today())
    
    if st.button("⚡ Generate Payroll for 100+ Staff", type="primary"):
        with st.spinner("Processing attendance logs..."):
            # Fetch Data
            e_res = supabase.table("employees").select("name, aadhar_no, base_salary, bank_name, account_no").execute()
            start = sel_date.replace(day=1)
            # Fetch all records for the month
            a_res = supabase.table("daily_attendance").select("*").gte("date", str(start)).execute()
            
            if not a_res.data:
                st.error("No attendance records found for this month.")
            else:
                df_a = pd.DataFrame(a_res.data)
                payroll = []
                for emp in e_res.data:
                    emp_logs = df_a[df_a['aadhar_no'] == emp['aadhar_no']]
                    # Automatic point calculation
                    points = emp_logs['status'].map({"Present":1, "Half-Day":0.5, "Absent":0, "Leave":0}).sum()
                    net = round((emp['base_salary'] / 30) * points, 2)
                    
                    payroll.append({
                        "Name": emp['name'], "Aadhar": emp['aadhar_no'], 
                        "Worked Days": points, "Net Salary": net,
                        "Bank": emp['bank_name'], "Account": emp['account_no']
                    })
                
                df_pay = pd.DataFrame(payroll)
                st.success(f"Generated payroll for {len(df_pay)} employees.")
                st.dataframe(df_pay, use_container_width=True, hide_index=True)
                
                # Batch Export
                csv = df_pay.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Download Payroll CSV", csv, "KBP_Monthly_Payroll.csv", "text/csv")
