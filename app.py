import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px


st.set_page_config(page_title="Consumer Spending Explorer", layout="wide")


# Connect to database
@st.cache_resource
def get_connection():
    conn = sqlite3.connect('consumer_spending.db', check_same_thread=False)
    return conn


conn = get_connection()


st.title("Consumer Market Spending Analysis")
st.markdown("Explore how household demographics impact spending priorities based on BLS Consumer Expenditure Survey data.")


# --- SIDEBAR FILTERS ---
st.sidebar.header("Filter Demographics")


income_options = ["All"] + ['Under $35,000', '$35,000-$50,000', '$50,000-$75,000', '$75,000-$100,000', 'Over $100,000']
age_options = ["All"] + ['Under 25', '25-34', '35-44', '45-54', '55-64', '65+']
size_options = ["All"] + ['1 Person', '2 People', '3-4 People', '5+ People']
region_options = ["All"] + ['Northeast', 'Midwest', 'South', 'West']


selected_income = st.sidebar.selectbox("Household Income", income_options)
selected_age = st.sidebar.selectbox("Age of Reference Person", age_options)
selected_size = st.sidebar.selectbox("Household Size", size_options)
selected_region = st.sidebar.selectbox("Region", region_options)


# --- BUILD SQL QUERY ---
query = """
    SELECT 
        c.category_name,
        c.expense_type,
        AVG(s.annual_amount) as avg_spending,
        COUNT(DISTINCT h.household_id) as sample_size
    FROM household h
    JOIN spending s ON h.household_id = s.household_id
    JOIN categories c ON s.category_id = c.category_id
    WHERE 1=1
"""
params = []


if selected_income != "All":
    query += " AND h.income_bracket = ?"
    params.append(selected_income)
if selected_age != "All":
    query += " AND h.age_group = ?"
    params.append(selected_age)
if selected_size != "All":
    query += " AND h.household_size = ?"
    params.append(selected_size)
if selected_region != "All":
    query += " AND h.region = ?"
    params.append(selected_region)


query += " GROUP BY c.category_name, c.expense_type ORDER BY avg_spending DESC"


# Execute Query
results = pd.read_sql(query, conn, params=params)


# --- DASHBOARD VISUALIZATIONS ---
if results.empty or results['sample_size'].iloc[0] == 0:
    st.warning("No households match this specific combination of filters. Try broadening your selection.")
else:
    sample_size = results['sample_size'].iloc[0]
    total_avg_spending = results['avg_spending'].sum()
    
    # Top Metrics
    col1, col2 = st.columns(2)
    col1.metric("Households in Segment", f"{sample_size:,}")
    col2.metric("Avg. Quarterly Tracked Spending", f"${total_avg_spending:,.2f}")
    
    st.markdown("---")
    
    # Charts
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.subheader("Average Spending by Category")
        fig_bar = px.bar(
            results, 
            x='category_name', 
            y='avg_spending',
            color='expense_type',
            labels={'category_name': 'Category', 'avg_spending': 'Avg Spending ($)', 'expense_type': 'Type'},
            color_discrete_map={'Essential': '#1f77b4', 'Discretionary': '#ff7f0e'}
        )
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with chart_col2:
        st.subheader("Budget Allocation")
        fig_pie = px.pie(
            results, 
            names='category_name', 
            values='avg_spending',
            hole=0.4
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        
    # Data Table
    st.subheader("Detailed Breakdown")
    formatted_results = results.drop(columns=['sample_size'])
    formatted_results['avg_spending'] = formatted_results['avg_spending'].apply(lambda x: f"${x:,.2f}")
    st.dataframe(formatted_results, use_container_width=True)