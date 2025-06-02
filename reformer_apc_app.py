# to run the model, press the green play button in the top right corner of the screen,
# then in the terminal, run the command: python3 -m streamlit run reformer_apc_app.py

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date
from streamlit_option_menu import option_menu
import plotly.graph_objects as go
import tempfile
from fpdf import FPDF
import os
import kaleido


# ------------ MODEL DEFAULTS --------------
DEFAULT_PARAMS = {
    "RON_Base": 94.2,
    "RON_Temp_Coeff": 0.5,
    "RON_Cat_Coeff": 0.01,
    "MON_Gap": 10.0,
    "Yield_Base": 84.0,
    "Yield_Coeff": 0.5,
    "LPG_Base": 12.0,
    "LPG_Coeff": 0.6,
    "RVP_Base": 45.0,
    "RVP_Coeff": 0.11,
    "H2_Base": 89.0,
    "H2_Coeff": 0.5,
    "Cat_Deact_Coeff": 0.03
}
DEFAULT_PARAMS = {k: float(v) for k, v in DEFAULT_PARAMS.items()}
LOG_FILE = "apc_data_upload_log.csv"

def reset_params():
    return DEFAULT_PARAMS.copy()

# ------------ SESSION STATE ---------------
if "params" not in st.session_state:
    st.session_state["params"] = reset_params()
if "data" not in st.session_state:
    st.session_state["data"] = None
if "calc" not in st.session_state:
    st.session_state["calc"] = None

# ------------ SIDEBAR MENU --------------
with st.sidebar:
    selected = option_menu(
        "Reformer APC",
        ["Main Dashboard", "Data Uploading", "Optimization", "Export", "Documentation & Model Details"],
        icons=['speedometer', 'cloud-upload', 'wrench', 'cloud-download', 'book'],
        menu_icon="activity", default_index=0,
        styles={
            "container": {"background-color": "#23242a", "padding": "0"},
            "icon": {"color": "#16d9fa", "font-size": "20px"},
            "nav-link": {
                "font-size": "16px",
                "color": "#eee",
                "padding": "10px",
                "margin":"2px 0",
                "border-radius":"10px"
            },
            "nav-link-selected": {
                "background-color": "#26a9e0",
                "color": "white",
                "font-weight":"bold",
                "box-shadow":"0 4px 12px #20d0f5"
            },
            "menu-title": {"font-size": "22px", "font-weight": "bold", "color": "#00fff7", "letter-spacing":"1px"},
        }
    )
    st.markdown("<br>", unsafe_allow_html=True)
page = selected

# ------------ MODEL --------------
def calc_outputs(df, params):
    r1, r2, r3, cat_age = "R1 inlet temp", "R2 inlet temp", "R3 inlet temp", "Catalyst age"
    out = pd.DataFrame()
    out["Timestamp"] = df["Timestamp"]
    out["WABT"] = (df[r1] + df[r2] + df[r3]) / 3
    out["RON_Pred"] = params["RON_Base"] + params["RON_Temp_Coeff"] * (out["WABT"] - 500) - params["RON_Cat_Coeff"] * df[cat_age]
    out["MON_Pred"] = out["RON_Pred"] - params["MON_Gap"]
    out["Yield_Pred"] = params["Yield_Base"] - params["Yield_Coeff"] * (out["RON_Pred"] - 95)
    out["LPG_Pred"] = params["LPG_Base"] + params["LPG_Coeff"] * (out["RON_Pred"] - 95)
    out["RVP_Pred_barg"] = params["RVP_Base"] - params["RVP_Coeff"] * (out["LPG_Pred"] - 12)
    out["H2_Purity_Pred"] = params["H2_Base"] - params["H2_Coeff"] * (out["WABT"] - 500)
    out["Cat_Deact"] = params["Cat_Deact_Coeff"] * df[cat_age]
    return out

# ------------ BACKEND LOGGING -------------
def log_upload():
    now = datetime.now()
    log_exists = os.path.isfile(LOG_FILE)
    df_log = pd.DataFrame([[now.strftime("%Y-%m-%d %H:%M:%S")]], columns=["upload_datetime"])
    mode = "a" if log_exists else "w"
    header = not log_exists
    df_log.to_csv(LOG_FILE, mode=mode, header=header, index=False)
def was_data_uploaded_today():
    if not os.path.isfile(LOG_FILE):
        return False
    log = pd.read_csv(LOG_FILE)
    log['date'] = pd.to_datetime(log['upload_datetime']).dt.date
    return date.today() in log['date'].values

# ------------ DATA UPLOADING --------------
if page == "Data Uploading":
    st.title("Data Uploading")
    uploaded_file = st.file_uploader(
        "Drag and drop your daily data (Excel or CSV)", 
        type=["xlsx", "xls", "csv"]
    )
    if uploaded_file is not None:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file, header=1 if "Timestamp" not in pd.read_excel(uploaded_file, nrows=1).columns else 0)
        try:
            df["Timestamp"] = pd.to_datetime(df["Timestamp"])
            for c in ["R1 inlet temp", "R2 inlet temp", "R3 inlet temp", "Catalyst age"]:
                df[c] = pd.to_numeric(df[c], errors='coerce')
            st.session_state["data"] = df
            log_upload()
            st.success("Data uploaded and preprocessed successfully.")
            st.dataframe(df)
        except Exception as e:
            st.error(f"Data format error: {e}")
    elif st.session_state["data"] is not None:
        st.info("Current session data:")
        st.dataframe(st.session_state["data"])
    else:
        st.info("Please upload a data file to continue.")

# ------------ MAIN DASHBOARD --------------
elif page == "Main Dashboard":
    st.title("Catalytic Reformer APC System - Main Dashboard")
    if st.session_state["data"] is None:
        st.warning("No data found. Please upload data in the 'Data Uploading' page.")
    else:
        df = st.session_state["data"]
        params = st.session_state["params"]
        calc = calc_outputs(df, params)
        st.session_state["calc"] = calc
        latest = calc.iloc[-1]
        # KPI cards
        st.subheader("KPI Dashboard")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("RON (Pred)", f"{latest['RON_Pred']:.2f}")
        kpi2.metric("Yield (Pred)", f"{latest['Yield_Pred']:.2f} %")
        kpi3.metric("LPG (Pred)", f"{latest['LPG_Pred']:.2f} %")
        kpi4.metric("H2 Purity (Pred)", f"{latest['H2_Purity_Pred']:.2f} %")
        kpi5, kpi6, kpi7 = st.columns(3)
        kpi5.metric("RVP (Pred, barg)", f"{latest['RVP_Pred_barg']:.2f}")
        kpi6.metric("MON (Pred)", f"{latest['MON_Pred']:.2f}")
        kpi7.metric("Cat Deact", f"{latest['Cat_Deact']:.2f} %")
        st.subheader("Trend Charts")
        # 1. RON/MON plot
        fig1 = go.Figure()
        if "RON (lab)" in df.columns:
            fig1.add_trace(go.Scatter(x=df["Timestamp"], y=df["RON (lab)"], name="RON Actual", mode="lines+markers", line=dict(color="royalblue")))
        if "MON (lab)" in df.columns:
            fig1.add_trace(go.Scatter(x=df["Timestamp"], y=df["MON (lab)"], name="MON Actual", mode="lines+markers", line=dict(color="magenta")))
        fig1.add_trace(go.Scatter(x=calc["Timestamp"], y=calc["RON_Pred"], name="RON Pred", mode="lines+markers", line=dict(color="deepskyblue", dash="dot")))
        fig1.add_trace(go.Scatter(x=calc["Timestamp"], y=calc["MON_Pred"], name="MON Pred", mode="lines+markers", line=dict(color="hotpink", dash="dot")))
        fig1.update_layout(title="RON/MON Actual vs Predicted", xaxis_title="Timestamp", yaxis_title="Octane Number")
        st.plotly_chart(fig1, use_container_width=True)
        # 2. Yield & RVP (actual and predicted)
        fig2 = go.Figure()
        if "C5+ Yield" in df.columns:
            fig2.add_trace(go.Scatter(x=df["Timestamp"], y=df["C5+ Yield"], name="Yield Actual", mode="lines+markers", line=dict(color="forestgreen")))
        if "Reformate RVP" in df.columns:
            fig2.add_trace(go.Scatter(x=df["Timestamp"], y=df["Reformate RVP"], name="RVP Actual (barg)", mode="lines+markers", line=dict(color="mediumblue")))
        fig2.add_trace(go.Scatter(x=calc["Timestamp"], y=calc["Yield_Pred"], name="Yield Pred", mode="lines+markers", line=dict(color="limegreen", dash="dot")))
        fig2.add_trace(go.Scatter(x=calc["Timestamp"], y=calc["RVP_Pred_barg"], name="RVP Pred (barg)", mode="lines+markers", line=dict(color="blue", dash="dot")))
        fig2.update_layout(
            title="Yield, RVP (barg) Actual vs Predicted",
            xaxis=dict(title="Timestamp"),
            yaxis=dict(title="Yield (%)/RVP (barg)"),
        )
        st.plotly_chart(fig2, use_container_width=True)
        # 3. WABT + Reactor Inlet Temps (all on one plot)
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(x=df["Timestamp"], y=df["R1 inlet temp"], name="R1 Inlet", line=dict(color="red")))
        fig3.add_trace(go.Scatter(x=df["Timestamp"], y=df["R2 inlet temp"], name="R2 Inlet", line=dict(color="gold")))
        fig3.add_trace(go.Scatter(x=df["Timestamp"], y=df["R3 inlet temp"], name="R3 Inlet", line=dict(color="green")))
        fig3.add_trace(go.Scatter(x=calc["Timestamp"], y=calc["WABT"], name="WABT (actual)", line=dict(color="black", width=2, dash="dot")))
        fig3.add_trace(go.Scatter(x=calc["Timestamp"], y=calc["WABT"], name="WABT (predicted)", line=dict(color="blue", width=2, dash="dash")))
        fig3.update_layout(title="Reactor Inlet Temperatures and WABT", xaxis_title="Timestamp", yaxis_title="Temperature (°C)")
        st.plotly_chart(fig3, use_container_width=True)
        # 4. H2 Purity + LPG Pred
        fig4 = go.Figure()
        if "H2 Purity Actual" in df.columns:
            fig4.add_trace(go.Scatter(x=df["Timestamp"], y=df["H2 Purity Actual"], name="H2 Purity Actual", mode="lines+markers", line=dict(color="blue")))
        fig4.add_trace(go.Scatter(x=calc["Timestamp"], y=calc["H2_Purity_Pred"], name="H2 Purity Pred", mode="lines+markers", line=dict(color="navy", dash="dot")))
        fig4.add_trace(go.Scatter(x=calc["Timestamp"], y=calc["LPG_Pred"], name="LPG Pred", yaxis="y2", mode="lines+markers", line=dict(color="red", dash="dot")))
        fig4.update_layout(
            title="H₂ Purity Actual vs Predicted and LPG Predicted",
            xaxis_title="Timestamp",
            yaxis=dict(title="H₂ Purity (%)"),
            yaxis2=dict(title="LPG (%)", overlaying="y", side="right"),
            legend=dict(orientation="h", y=-0.18)
        )
        st.plotly_chart(fig4, use_container_width=True)
        # -- Store figures for PDF export --
        st.session_state["dashboard_figs"] = [fig1, fig2, fig3, fig4]

# ------------ OPTIMIZATION --------------
elif page == "Optimization":
    st.title("Optimization & What-If Scenarios")
    if st.session_state["data"] is None:
        st.warning("No data found. Please upload data in the 'Data Uploading' page.")
    else:
        df = st.session_state["data"]
        params = st.session_state["params"]
        # Model Tuning in 3 Rows
        st.subheader("Model Coefficients (Tuning)")
        param_keys = list(params.keys())
        n = len(param_keys)
        row1, row2, row3 = param_keys[:5], param_keys[5:10], param_keys[10:]
        cols1 = st.columns(len(row1))
        for i, key in enumerate(row1):
            params[key] = cols1[i].number_input(f"{key}", value=float(params[key]), format="%.4f")
        cols2 = st.columns(len(row2))
        for i, key in enumerate(row2):
            params[key] = cols2[i].number_input(f"{key}", value=float(params[key]), format="%.4f")
        cols3 = st.columns(len(row3))
        for i, key in enumerate(row3):
            params[key] = cols3[i].number_input(f"{key}", value=float(params[key]), format="%.4f")
        if st.button("Reset Model Coefficients to Default"):
            st.session_state["params"] = reset_params()
            st.experimental_rerun()
        st.markdown("---")
        # What-If Scenario and Predicted Results, side-by-side
        col1, col2 = st.columns([1,1])
        with col1:
            st.subheader("What-If Inputs")
            temp1 = st.slider("R1 Inlet Temp (°C)", 480, 530, int(df["R1 inlet temp"].iloc[-1]))
            temp2 = st.slider("R2 Inlet Temp (°C)", 480, 530, int(df["R2 inlet temp"].iloc[-1]))
            temp3 = st.slider("R3 Inlet Temp (°C)", 480, 530, int(df["R3 inlet temp"].iloc[-1]))
            catage = st.slider("Catalyst Age (days)", 0, 1000, int(df["Catalyst age"].iloc[-1]))
            whatif_row = df.iloc[-1].copy()
            whatif_row["R1 inlet temp"], whatif_row["R2 inlet temp"], whatif_row["R3 inlet temp"], whatif_row["Catalyst age"] = temp1, temp2, temp3, catage
            whatif_df = pd.DataFrame([whatif_row])
            whatif_pred = calc_outputs(whatif_df, params).iloc[0]
        with col2:
            st.subheader("Predicted Results")
            # Use st.metric for each predicted value
            pred_keys = [k for k in whatif_pred.index if k != "Timestamp"]
            # Arrange in 3 columns per row
            for i in range(0, len(pred_keys), 3):
                cols = st.columns(min(3, len(pred_keys)-i))
                for j, k in enumerate(pred_keys[i:i+3]):
                    display_name = k.replace('_', ' ')
                    st_val = f"{whatif_pred[k]:.2f}"
                    cols[j].metric(display_name, st_val)

        # --- Operating Mode Optimization ---
        st.markdown("---")
        st.subheader("Operating Mode Optimization")
        st.markdown("""
        Select an operating mode to receive recommended setpoints for maximizing RON, maximizing Yield, or maximizing Cycle Length. Recommendations are based on the current model and data.\
        **Note:** These are data-driven suggestions and should be validated by process engineers before implementation.
        """)
        mode = st.selectbox(
            "Select Operating Mode",
            ["-- Select --", "Maximize RON", "Maximize Yield", "Maximize Cycle Length"]
        )
        if mode != "-- Select --":
            # Use the last row as a base
            base_row = df.iloc[-1].copy()
            best_row = base_row.copy()
            # Define bounds for optimization
            temp_bounds = (480, 530)
            cat_bounds = (0, 1000)
            # Simple grid search (for demo, not for production)
            best_score = None
            best_inputs = None
            for t1 in range(temp_bounds[0], temp_bounds[1]+1, 5):
                for t2 in range(temp_bounds[0], temp_bounds[1]+1, 5):
                    for t3 in range(temp_bounds[0], temp_bounds[1]+1, 5):
                        for cat in [base_row["Catalyst age"]]:  # keep catalyst age fixed for RON/Yield, vary for cycle
                            test_row = base_row.copy()
                            test_row["R1 inlet temp"] = t1
                            test_row["R2 inlet temp"] = t2
                            test_row["R3 inlet temp"] = t3
                            test_row["Catalyst age"] = cat
                            pred = calc_outputs(pd.DataFrame([test_row]), params).iloc[0]
                            if mode == "Maximize RON":
                                score = pred["RON_Pred"]
                            elif mode == "Maximize Yield":
                                score = pred["Yield_Pred"]
                            elif mode == "Maximize Cycle Length":
                                # For cycle length, minimize catalyst deactivation (lower temps, lower cat deact)
                                score = -pred["Cat_Deact"]
                            if (best_score is None) or (score > best_score):
                                best_score = score
                                best_inputs = (t1, t2, t3, cat)
            # For Maximize Cycle Length, also try lower temps and higher cat age
            if mode == "Maximize Cycle Length":
                for t1 in range(temp_bounds[0], temp_bounds[1]+1, 5):
                    for t2 in range(temp_bounds[0], temp_bounds[1]+1, 5):
                        for t3 in range(temp_bounds[0], temp_bounds[1]+1, 5):
                            for cat in range(int(base_row["Catalyst age"])+1, cat_bounds[1]+1, 100):
                                test_row = base_row.copy()
                                test_row["R1 inlet temp"] = t1
                                test_row["R2 inlet temp"] = t2
                                test_row["R3 inlet temp"] = t3
                                test_row["Catalyst age"] = cat
                                pred = calc_outputs(pd.DataFrame([test_row]), params).iloc[0]
                                score = -pred["Cat_Deact"]
                                if (best_score is None) or (score > best_score):
                                    best_score = score
                                    best_inputs = (t1, t2, t3, cat)
            if best_inputs:
                t1, t2, t3, cat = best_inputs
                st.info(f"**Recommended Setpoints for {mode}:**\n- R1 Inlet Temp: {t1} °C\n- R2 Inlet Temp: {t2} °C\n- R3 Inlet Temp: {t3} °C\n- Catalyst Age: {cat}")
                # Show predicted results for these setpoints
                opt_row = base_row.copy()
                opt_row["R1 inlet temp"] = t1
                opt_row["R2 inlet temp"] = t2
                opt_row["R3 inlet temp"] = t3
                opt_row["Catalyst age"] = cat
                opt_pred = calc_outputs(pd.DataFrame([opt_row]), params).iloc[0]
                st.markdown("**Predicted Results for Recommended Setpoints:**")
                pred_keys = [k for k in opt_pred.index if k != "Timestamp"]
                for i in range(0, len(pred_keys), 3):
                    cols = st.columns(min(3, len(pred_keys)-i))
                    for j, k in enumerate(pred_keys[i:i+3]):
                        display_name = k.replace('_', ' ')
                        st_val = f"{opt_pred[k]:.2f}"
                        cols[j].metric(display_name, st_val)
            else:
                st.warning("No optimal setpoints found for the selected mode.")

# ------------ EXPORT (PLOTS+PDF) --------------
elif page == "Export":
    st.title("Export Results")
    if st.session_state.get("calc") is None:
        st.warning("No calculated results found. Please upload data and visit Dashboard.")
    else:
        calc = st.session_state["calc"]
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            calc.to_excel(tmp.name, index=False)
            tmp.seek(0)
            st.download_button("Download Calculated Results (Excel)", data=tmp.read(), file_name="calculated_results.xlsx")
        st.subheader("Executive Summary PDF")
        if st.button("Generate Executive Summary PDF"):
            figs = st.session_state.get("dashboard_figs", [])
            pdf = FPDF(orientation="L", unit="mm", format="A4")
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 12, "Catalytic Reformer APC - Executive Summary", ln=True, align="C")
            pdf.set_font("Arial", size=12)
            pdf.cell(0, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
            pdf.ln(2)
            if len(calc) > 0:
                last = calc.iloc[-1]
                pdf.set_font("Arial", "B", 13)
                pdf.cell(0, 9, "Latest KPIs:", ln=True)
                pdf.set_font("Arial", size=11)
                for k in ["RON_Pred", "Yield_Pred", "LPG_Pred", "H2_Purity_Pred", "RVP_Pred_barg", "MON_Pred", "Cat_Deact"]:
                    pdf.cell(0, 8, f"{k}: {last[k]:.2f}", ln=True)
            pdf.ln(2)
            for i, fig in enumerate(figs):
                tmpimg = f"plot_{i}.png"
                fig.write_image(tmpimg, width=850, height=400)
                pdf.image(tmpimg, x=10, y=None, w=270)
                os.remove(tmpimg)
                pdf.ln(2)
            # Log note if new data uploaded today
            pdf.set_font("Arial", "I", 10)
            note = "Note: New data was uploaded today." if was_data_uploaded_today() else ""
            pdf.cell(0, 8, f"Auto-generated summary from Reformer APC System. {note}", ln=True)
            pdf_file = "executive_summary.pdf"
            pdf.output(pdf_file)
            with open(pdf_file, "rb") as f:
                st.download_button("Download Executive Summary PDF", data=f, file_name="executive_summary.pdf", mime="application/pdf")
            st.success("Executive summary PDF generated.")

# ------------ DOCUMENTATION --------------
elif page == "Documentation & Model Details":
    st.title("Project Documentation & Model Details")
    st.markdown("""
## Catalytic Reformer APC Documentation

**Scope:**  
This application provides monitoring, prediction, and operator advisory APC for a 3-reactor semi-regenerative catalytic reformer. The system is designed to be dynamic, allowing for real-time updates and providing a professional dashboard for operations.

**Key Features:**  
- Real-time monitoring of critical process parameters  
- Predictive analytics for product quality and yields  
- What-if scenario analysis for process optimization  
- Operational recommendations for setpoint adjustment  
- Historical data trending and analysis  
- Documentation of model equations and assumptions  
- **Operating Mode Optimization (NEW):** Data-driven recommendations for maximizing RON, Yield, or Cycle Length

**Workflow:**  
- Monitor the Dashboard for KPIs, alerts, and trends  
- Review historical data  
- Explore model equations in the Model section  
- Use Optimization/What-If for scenario analysis and setpoint recommendations  
- Use Operating Mode Optimization to receive recommended setpoints for business objectives

**Model Equations:**  
- WABT = (R1_Inlet_Temp + R2_Inlet_Temp + R3_Inlet_Temp)/3  
- RON_Pred = RON_Base + RON_Temp_Coeff*(WABT-500) - RON_Cat_Coeff*Cat_Age  
- MON_Pred = RON_Pred - MON_Gap  
- Yield_Pred = Yield_Base - Yield_Coeff*(RON_Pred-95)  
- LPG_Pred = LPG_Base + LPG_Coeff*(RON_Pred-95)  
- RVP_Pred_barg = RVP_Base - RVP_Coeff*(LPG_Pred-12)  
- H2_Purity_Pred = H2_Base - H2_Coeff*(WABT-500)  
- Cat_Deact = Cat_Deact_Coeff*Cat_Age  

**Operating Mode Optimization (NEW):**
- Users can select an operating mode: Maximize RON, Maximize Yield, or Maximize Cycle Length.
- The system uses the current model and data to recommend optimal setpoints for R1, R2, R3 Inlet Temperatures and Catalyst Age.
- Recommendations are data-driven and based on a grid search of feasible setpoints, using the inferential model to predict outcomes.
- The predicted results for the recommended setpoints are displayed using KPI cards.
- This approach is in line with best practices in refinery APC and optimization, where operating modes are selected based on business objectives (e.g., maximizing octane, yield, or catalyst life), and APC/inferential models are used to recommend setpoints for key variables such as reactor temperatures and catalyst age. See the references below for more details.

**References:**  
- PTQ Q3 2017, AspenTech, KBC/Shell case studies  
- Hydrocarbon Processing literature  
- Plant historical data and calibration runs  
- Industry standard correlations for naphtha reforming  
- [AZoSensors: Optimizing Refinery Catalytic Reforming Units](https://www.azosensors.com/article.aspx?ArticleID=1809)  
- [DigitalRefining: Using APC in refinery energy systems — develop your own solutions](https://www.digitalrefining.com/article/1000952/using-apc-in-refinery-energy-systems-develop-your-own-solutions)

**Optimization Methodology:**  
The optimization module uses the inferential model to recommend setpoint changes that maximize performance while respecting operational constraints.  
- Maximize reformate production (yield × throughput)  
- Minimize quality giveaway (RON > target)  
- Maintain all product specifications (RON, RVP)  
- Respect equipment constraints (temperatures, pressures)  
- Use manual/auto scenario analysis for optimization.  
- **Operating Mode Optimization:** Select business objective (RON, Yield, Cycle Length) and receive recommended setpoints based on model and data.
    """)
    st.success("All project documentation and model details are above.")

