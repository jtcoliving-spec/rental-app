import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- CONFIGURATION ---
RATE_PER_UNIT = 0.60
# PASTE YOUR GOOGLE SHEET LINK BELOW
SHEET_URL = "https://docs.google.com/spreadsheets/d/1UGG66jyHsNoPwAINcdsgg6oXyEq4WslAOnxLmiTJ7Z0/edit?usp=sharing"

st.set_page_config(page_title="Room Rental & AC Tracker", layout="wide")

# Establish connection to Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

# Helper function to read data
def load_data(sheet_name):
    return conn.read(spreadsheet=SHEET_URL, worksheet=sheet_name, ttl=0)

# Helper function to save data
def save_data(df, sheet_name):
    conn.update(spreadsheet=SHEET_URL, worksheet=sheet_name, data=df)
    st.cache_data.clear()

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("Management Menu")
page = st.sidebar.radio("Go to:", ["Tenant Portal", "Owner Admin"])

# --- OWNER ADMIN PAGE ---
if page == "Owner Admin":
    st.header("🔑 Owner Management")
    password = st.text_input("Enter Admin Password", type="password")
    
    if password == "admin123":
        st.subheader("Register a New Tenant")
        with st.form("registration_form"):
            t_name = st.text_input("Full Name")
            t_unit = st.selectbox("Assign Unit", [f"Unit {i}" for i in range(1, 8)])
            t_room = st.selectbox("Assign Room", [f"Room {i}" for i in range(1, 6)])
            submit_reg = st.form_submit_button("Add Tenant")
            
            if submit_reg and t_name:
                tenants_df = load_data("tenants")
                new_tenant = pd.DataFrame([{"Name": t_name, "Unit": t_unit, "Room": t_room}])
                updated_tenants = pd.concat([tenants_df, new_tenant], ignore_index=True)
                save_data(updated_tenants, "tenants")
                st.success(f"Registered {t_name} to {t_unit}, {t_room}!")

# --- TENANT PORTAL PAGE ---
else:
    st.header("📱 Tenant Payment & AC Portal")
    tenants_list = load_data("tenants")
    
    if tenants_list.empty:
        st.warning("No tenants registered yet. Owner must register tenants in Admin mode first.")
    else:
        # Tenant "Login"
        selected_user = st.selectbox("Identify Yourself (Select Name)", [""] + tenants_list['Name'].tolist())
        
        if selected_user:
            # Auto-find their Unit and Room
            user_info = tenants_list[tenants_list['Name'] == selected_user].iloc[0]
            my_unit, my_room = user_info['Unit'], user_info['Room']
            
            st.success(f"Hello {selected_user}! Logging for **{my_unit}, {my_room}**")
            
            # Fetch last reading from history
            history = load_data("records")
            my_history = history[(history['Unit'] == my_unit) & (history['Room'] == my_room)]
            last_val = my_history.iloc[-1]['AC_Reading'] if not my_history.empty else 0.0
            
            # Billing Section
            st.info(f"Last month's meter reading: **{last_val}**")
            current_reading = st.number_input("Enter Current Meter Reading", min_value=float(last_val), step=0.1)
            
            units_used = current_reading - last_val
            ac_charge = units_used * RATE_PER_UNIT
            rent_fixed = st.number_input("Enter Agreed Monthly Rent (RM)", min_value=0.0)
            
            total_payable = rent_fixed + ac_charge
            st.metric(label="Total to Pay", value=f"RM {total_payable:.2f}", delta=f"AC: RM {ac_charge:.2f}")

            # Submission with Receipt Record
            if st.button("Confirm & Log Payment"):
                new_entry = pd.DataFrame([{
                    "Date": datetime.now().strftime("%Y-%m-%d"),
                    "Unit": my_unit,
                    "Room": my_room,
                    "Tenant": selected_user,
                    "Prev_Reading": last_val,
                    "AC_Reading": current_reading,
                    "Units_Used": units_used,
                    "AC_Cost": ac_charge,
                    "Rent_Paid": rent_fixed,
                    "Total_Paid": total_payable
                }])
                updated_history = pd.concat([history, new_entry], ignore_index=True)
                save_data(updated_history, "records")
                st.balloons()
                st.success("Your payment and reading have been recorded. Thank you!")
