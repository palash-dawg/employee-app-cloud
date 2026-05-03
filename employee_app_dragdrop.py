import streamlit as st
import pandas as pd
from supabase import create_client, Client
import datetime

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
            # Enterprise Tip: In production, verify this against the 'app_users' table
            access = {"admin": ("admin123", "Admin"), "hr": ("hr123", "HR"), 
                      "fin": ("fin123", "Finance"), "att": ("att123", "Attendance")}
            if u in access and p == access[u][0]:
                st.session_state.update({"logged_in": True, "role": access[u][1], "username": u.upper()})
                st.rerun()
            else: 
                st.error("❌ Invalid Credentials")
    st.stop()

# --- SIDEBAR ---
role = st.session_state.role
nav = {"Admin": ["📊 Dashboard", "👥 HR Portal", "📝 Attendance", "💰 Payroll"],
       "HR": ["👥 HR Portal"], "Attendance": ["📝 Attendance"], "Finance": ["💰 Payroll"]}
choice = st.sidebar.radio("Navigation", nav.get(role, []))

if st.sidebar.button("Logout"):
    st.session_state.update({"logged_in": False, "role": None})
    st.rerun()

# ==========================================
# 👥 MODULE: HR PORTAL
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
            b_name = col2.text_input("Bank Name")
            acc_no = col2.text_input("Account Number")
            ifsc = col2.text_input("IFSC Code").upper()
            
            if st.form_submit_button("Save Employee"):
                data = {
                    "aadhar_no": aadhar, "name": name, "father_name": f_name, 
                    "mobile_no": mob, "address": addr, "dob": str(dob), 
                    "joining_date": str(doj), "bank_name": b_name, 
                    "account_no": acc_no, "ifsc_code": ifsc
                }
                
                # --- PROTECTED DB SYNC ---
                try:
                    supabase.table("employees").upsert(data).execute()
                    st.success(f"✅ Staff {name} Registered!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Database Error: {e}")

    # View Registry
    res = supabase.table("employees").select("*").execute()
    if res.data:
        st.subheader("Employee Directory")
        st.dataframe(pd.DataFrame(res.data), use_container_width=True, hide_index=True)

# ==========================================
# 📝 MODULE: ATTENDANCE
# ==========================================
elif choice == "📝 Attendance":
    st.title("📝 Batch Attendance")
    dt = st.date_input("Date", datetime.date.today())
    
    emps = supabase.table("employees").select("aadhar_no, name").execute()
    existing = supabase.table("daily_attendance").select("aadhar_no, status").eq("attendance_date", str(dt)).execute()
    
    if not emps.data:
        st.warning("No employees found in the database.")
    else:
        df_emps = pd.DataFrame(emps.data)
        att_map = {item['aadhar_no']: item['status'] for item in existing.data}
        df_emps['status'] = df_emps['aadhar_no'].map(lambda x: att_map.get(x, "Present"))
        
        edited_df = st.data_editor(
            df_emps,
            column_config={
                "aadhar_no": st.column_config.TextColumn("Aadhar", disabled=True),
                "name": st.column_config.TextColumn("Employee Name", disabled=True),
                "status": st.column_config.SelectboxColumn("Status", options=["Present", "Absent", "Half-Day", "Leave"], required=True)
            },
            hide_index=True, use_container_width=True
        )
        
        if st.button("💾 Save All Attendance", type="primary"):
            final_data = []
            for _, row in edited_df.iterrows():
                final_data.append({"attendance_date": str(dt), "aadhar_no": row['aadhar_no'], "status": row['status']})
            
            # --- PROTECTED DB SYNC ---
            try:
                supabase.table("daily_attendance").upsert(final_data).execute()
                st.success(f"✅ Attendance synced for {len(final_data)} employees.")
            except Exception as e:
                st.error(f"❌ Sync Error: {e}")

# ==========================================
# 💰 MODULE: PAYROLL
# ==========================================
elif choice == "💰 Payroll":
    st.title("💰 Payroll Management")
    st.info("Payroll is generated based on recorded attendance and base salary logic.")
    # (Payroll logic continues using similar try-except blocks for upserting to employee_salary)
