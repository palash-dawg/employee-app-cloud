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
    st.title("🔒 KBP ENERGY PVT LTD")
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
st.sidebar.write(f"User: **{st.session_state.username}**")
role = st.session_state.role
nav = {"Admin": ["📊 Dashboard", "👥 HR Portal", "📝 Attendance", "💰 Payroll"],
       "HR": ["👥 HR Portal"], "Attendance": ["📝 Attendance"], "Finance": ["💰 Payroll"]}
choice = st.sidebar.radio("Navigation", nav.get(role, []))

if st.sidebar.button("Logout"):
    st.session_state.update({"logged_in": False, "role": None})
    st.rerun()

# ==========================================
# 📊 MODULE: DASHBOARD (Admin)
# ==========================================
if choice == "📊 Dashboard":
    st.title("📊 Enterprise Overview")
    try:
        res = supabase.table("employees").select("base_salary").execute()
        df = pd.DataFrame(res.data)
        c1, c2 = st.columns(2)
        c1.metric("Total Workforce", len(df))
        c2.metric("Monthly Salary Liability", f"₹ {df['base_salary'].sum():,.2f}")
    except: st.info("Add employees to see metrics.")

# ==========================================
# 👥 MODULE: HR PORTAL (Full Details)
# ==========================================
elif choice == "👥 HR Portal":
    st.title("👥 Employee Management")
    
    with st.expander("➕ Register New Staff (Full Details)"):
        with st.form("full_hr_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            # Personal
            name = col1.text_input("Full Name")
            f_name = col1.text_input("Father's Name")
            aadhar = col1.text_input("Aadhar Card No", max_chars=12)
            mob = col1.text_input("Mobile No")
            addr = col1.text_area("Full Address")
            
            # Professional/Bank
            dob = col2.date_input("Date of Birth", value=datetime.date(1995,1,1))
            doj = col2.date_input("Joining Date")
            base_sal = col2.number_input("Monthly Base Salary", min_value=0, value=15000)
            b_name = col2.text_input("Bank Name")
            acc_no = col2.text_input("Account Number")
            ifsc = col2.text_input("IFSC Code").upper()
            
            if st.form_submit_button("Save Employee Record"):
                if not name or len(aadhar) != 12:
                    st.error("Name and 12-digit Aadhar are mandatory.")
                else:
                    data = {
                        "aadhar_no": aadhar, "name": name, "father_name": f_name,
                        "mobile_no": mob, "address": addr, "dob": str(dob),
                        "joining_date": str(doj), "base_salary": base_sal,
                        "bank_name": b_name, "account_no": acc_no, "ifsc_code": ifsc
                    }
                    supabase.table("employees").upsert(data).execute()
                    st.success(f"Record for {name} saved!"); st.rerun()

    # --- Display Directory ---
    st.subheader("Staff Directory")
    res = supabase.table("employees").select("*").execute()
    if res.data:
        df_display = pd.DataFrame(res.data)
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else: st.write("No records found.")

# ==========================================
# 📝 MODULE: ATTENDANCE
# ==========================================
elif choice == "📝 Attendance":
    st.title("📝 Daily Attendance")
    dt = st.date_input("Date", datetime.date.today())
    res_e = supabase.table("employees").select("aadhar_no, name").execute()
    
    if not res_e.data:
        st.warning("No employees found.")
    else:
        res_a = supabase.table("daily_attendance").select("*").eq("date", str(dt)).execute()
        logs = {item['aadhar_no']: item['status'] for item in res_a.data}
        
        att_updates = []
        for emp in res_e.data:
            c1, c2 = st.columns([3, 2])
            c1.write(f"**{emp['name']}**")
            status = c2.selectbox("Status", ["Present", "Absent", "Half-Day", "Leave"], 
                                  index=["Present", "Absent", "Half-Day", "Leave"].index(logs.get(emp['aadhar_no'], "Present")),
                                  key=emp['aadhar_no'])
            att_updates.append({"date": str(dt), "aadhar_no": emp['aadhar_no'], "status": status})
            
        if st.button("Save Attendance", type="primary"):
            supabase.table("daily_attendance").upsert(att_updates).execute()
            st.success("Attendance updated!")

# ==========================================
# 💰 MODULE: PAYROLL
# ==========================================
elif choice == "💰 Payroll":
    st.title("💰 Monthly Payroll")
    sel_date = st.date_input("Select Month", datetime.date.today())
    if st.button("Generate Reports"):
        res_e = supabase.table("employees").select("name, aadhar_no, base_salary, bank_name, account_no").execute()
        # Fetch month-wide logs
        start = sel_date.replace(day=1)
        res_a = supabase.table("daily_attendance").select("*").gte("date", str(start)).execute()
        
        if not res_a.data: st.error("No attendance found for this month.")
        else:
            df_a = pd.DataFrame(res_a.data)
            report = []
            for emp in res_e.data:
                emp_logs = df_a[df_a['aadhar_no'] == emp['aadhar_no']]
                points = emp_logs['status'].map({"Present":1, "Half-Day":0.5, "Absent":0, "Leave":0}).sum()
                net = round((emp['base_salary'] / 30) * points, 2)
                report.append({
                    "Name": emp['name'], "Aadhar": emp['aadhar_no'], 
                    "Working Days": points, "Net Salary": net,
                    "Bank": emp['bank_name'], "A/C": emp['account_no']
                })
            st.table(report)
            # Excel Export
            out = io.BytesIO()
            pd.DataFrame(report).to_excel(out, index=False)
            st.download_button("📥 Download Report", out.getvalue(), "Payroll.xlsx")
