# Reformer_APC
Reformer APC model built in cursor using AI 

# Web page to use:
https://reformerapc-zwuvadgerjr4h3v3bh7pxg.streamlit.app

# documantaion for the model:
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
