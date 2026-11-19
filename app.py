import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px


st.set_page_config(page_title="Advanced Consumer Spending Explorer", layout="wide", initial_sidebar_state="expanded")


st.markdown(
    """
    <style>
    /* Main app background */
    .stApp {
        background-color: #fce4ec;
    }
    /* Sidebar background */
    [data-testid="stSidebar"] {
        background-color: #fce4ec; 
    }
    </style>
    """,
    unsafe_allow_html=True
)


@st.cache_data
def load_data():
    conn = sqlite3.connect('/workspaces/Consumer-Spending-App/expanded_consumer_data (1).db', check_same_thread=False)
    query = """
        SELECT 
            d.household_id, d.income_before_taxes, d.age, d.family_size, 
            d.num_earners, d.num_vehicles, d.region, d.sex, d.marital_status, 
            d.race, d.housing_tenure, d.education_level,
            s.annual_amount,
            c.category_name, c.expense_type
        FROM demographics d
        JOIN spending s ON d.household_id = s.household_id
        JOIN categories c ON s.category_id = c.category_id
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df


df = load_data()


st.title("Advanced Consumer Market Spending Analysis")
st.markdown("Explore how household demographics impact spending priorities.")


st.sidebar.header("Filter Demographics")


def add_filter(column_name, label):
    options = ["All"] + sorted(df[column_name].dropna().unique().tolist())
    choice = st.sidebar.selectbox(label, options)
    return choice


sel_region = add_filter('region', 'Region')
sel_education = add_filter('education_level', 'Education Level')
sel_marital = add_filter('marital_status', 'Marital Status')
sel_housing = add_filter('housing_tenure', 'Housing Tenure')
sel_sex = add_filter('sex', 'Reference Person Sex')


min_inc, max_inc = int(df['income_before_taxes'].min()), int(df['income_before_taxes'].max())
sel_income = st.sidebar.slider("Income Before Taxes ($)", min_value=min_inc, max_value=max_inc, value=(min_inc, max_inc))


min_age, max_age = int(df['age'].min()), int(df['age'].max())
sel_age = st.sidebar.slider("Age of Reference Person", min_value=min_age, max_value=max_age, value=(min_age, max_age))


filtered_df = df.copy()
if sel_region != "All": filtered_df = filtered_df[filtered_df['region'] == sel_region]
if sel_education != "All": filtered_df = filtered_df[filtered_df['education_level'] == sel_education]
if sel_marital != "All": filtered_df = filtered_df[filtered_df['marital_status'] == sel_marital]
if sel_housing != "All": filtered_df = filtered_df[filtered_df['housing_tenure'] == sel_housing]
if sel_sex != "All": filtered_df = filtered_df[filtered_df['sex'] == sel_sex]


filtered_df = filtered_df[
    (filtered_df['income_before_taxes'] >= sel_income[0]) & 
    (filtered_df['income_before_taxes'] <= sel_income[1]) &
    (filtered_df['age'] >= sel_age[0]) &
    (filtered_df['age'] <= sel_age[1])
]


if filtered_df.empty:
    st.warning("No households match this specific combination of filters. Try broadening your selection.")
    st.stop()


unique_households = filtered_df['household_id'].nunique()
avg_income = filtered_df.drop_duplicates(subset=['household_id'])['income_before_taxes'].mean()
avg_total_spending = filtered_df.groupby('household_id')['annual_amount'].sum().mean()


col1, col2, col3, col4 = st.columns(4)
col1.metric("Households in Segment", f"{unique_households:,}")
col2.metric("Avg. Household Income", f"${avg_income:,.0f}")
col3.metric("Avg. Tracked Spending", f"${avg_total_spending:,.0f}")
col4.metric("Savings/Unallocated Margin", f"${(avg_income - avg_total_spending):,.0f}")


st.subheader("Correlation: Income vs. Spending by Education Level")
scatter_df = filtered_df.groupby(['household_id', 'education_level', 'income_before_taxes'])['annual_amount'].sum().reset_index()
fig_scatter = px.scatter(
    scatter_df, 
    x="income_before_taxes", 
    y="annual_amount", 
    color="education_level",
    opacity=0.6,
    labels={"income_before_taxes": "Income Before Taxes ($)", "annual_amount": "Total Annual Spending ($)", "education_level": "Education"},
    template="plotly_white"
)
fig_scatter.update_traces(marker=dict(size=8, line=dict(width=0.5, color='DarkSlateGrey')))
st.plotly_chart(fig_scatter, use_container_width=True)


tab1, tab2, tab3, tab4 = st.tabs(["Core Visualizations", "Demographic Deep Dives", "Detailed Data Tables", "Extremes Analysis"])


with tab1:
    st.subheader("Spending Breakdown by Category")
    
    cat_spending = filtered_df.groupby(['category_name', 'expense_type'])['annual_amount'].mean().reset_index()
    
    fig_bar = px.bar(
        cat_spending.sort_values(by='annual_amount', ascending=True), 
        x='annual_amount', 
        y='category_name', 
        color='expense_type',
        orientation='h', 
        height=500,
        text='annual_amount',
        labels={'annual_amount': 'Avg Annual Spending ($)', 'category_name': '', 'expense_type': 'Expense Type'},
        color_discrete_map={'Essential': '#C2185B', 'Discretionary': '#F48FB1'},
        template="plotly_white"
    )
    
    fig_bar.update_traces(
        texttemplate='$%{text:,.0f}', 
        textposition='outside',
        marker_line_width=0 
    )
    
    fig_bar.update_layout(
        xaxis=dict(showgrid=False, showticklabels=False, title=''), 
        yaxis=dict(title='', tickfont=dict(size=13)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=0, r=80, t=30, b=0)
    )
    
    st.plotly_chart(fig_bar, use_container_width=True)


with tab2:
    col_pie, col_sun = st.columns(2)
    
    with col_pie:
        st.subheader("Budget Allocation")
        type_spending = filtered_df.groupby('expense_type')['annual_amount'].sum().reset_index()
        
        fig_pie = px.pie(
            type_spending, 
            names='expense_type', 
            values='annual_amount', 
            hole=0.65,  # Wider hole for a more elegant donut shape
            color='expense_type',
            color_discrete_map={'Essential': '#C2185B', 'Discretionary': '#F48FB1'}
        )
        
        # Professional upgrades: outside labels, white slice borders, custom hover text
        fig_pie.update_traces(
            textposition='outside', 
            textinfo='label+percent',
            marker=dict(line=dict(color='#FFFFFF', width=2.5)), 
            hovertemplate="<b>%{label}</b><br>Amount: $%{value:,.0f}<extra></extra>"
        )
        
        fig_pie.update_layout(
            showlegend=False, # Removed legend since labels are outside
            margin=dict(t=30, b=30, l=30, r=30),
            annotations=[dict(text='Total<br>Spending', x=0.5, y=0.5, font_size=16, showarrow=False, font=dict(color='#C2185B'))]
        )
        
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col_sun:
        st.subheader("Demographic Sunburst")
        # Sunburst Chart: Region -> Education Level -> Expense Type
        sun_df = filtered_df.groupby(['region', 'education_level', 'expense_type'])['annual_amount'].sum().reset_index()
        
        fig_sun = px.sunburst(
            sun_df, 
            path=['region', 'education_level', 'expense_type'], 
            values='annual_amount',
            color='expense_type', 
            color_discrete_map={'Essential': '#C2185B', 'Discretionary': '#F48FB1', '(?)': '#F8BBD0'}
        )
        
        # Professional upgrades: clean white borders, radial text, advanced hover tooltips
        fig_sun.update_traces(
            textinfo='label',
            insidetextorientation='radial',
            marker=dict(line=dict(color='#FFFFFF', width=1.5)),
            hovertemplate="<b>%{label}</b><br>Total Spending: $%{value:,.0f}<br>Share of Parent Category: %{percentParent:.1%}<extra></extra>"
        )
        
        fig_sun.update_layout(
            margin=dict(t=20, b=20, l=20, r=20)
        )
        
        st.plotly_chart(fig_sun, use_container_width=True)


with tab3:
    st.markdown("Explore the detailed numbers behind the visualizations. These tables break down average category costs and summarize individual household financial profiles.")
    col_table1, col_table2 = st.columns(2)
    
    with col_table1:
        st.subheader("Category Spend Matrix")
        st.caption("Average annual spending per category, split by essential vs. discretionary needs.")
        
        pivot_df = filtered_df.pivot_table(
            index='category_name', columns='expense_type', 
            values='annual_amount', aggfunc='mean', fill_value=0
        ).reset_index()
        
        pivot_df['Total Avg Spending'] = pivot_df.sum(axis=1, numeric_only=True)
        pivot_df = pivot_df.sort_values(by='Total Avg Spending', ascending=False)
        
        # Rename columns for a professional display
        pivot_df = pivot_df.rename(columns={
            'category_name': 'Category',
            'Discretionary': 'Discretionary ($)',
            'Essential': 'Essential ($)'
        })
        
        st.dataframe(
            pivot_df.style.format({col: "${:,.2f}" for col in pivot_df.columns if col != 'Category'})
                          .background_gradient(cmap='RdPu', subset=['Total Avg Spending']),
            use_container_width=True, hide_index=True
        )


    with col_table2:
        st.subheader("Household Financial Summary")
        st.caption("A summary of individual household incomes, education, and the percentage of their income dedicated to tracked spending.")
        
        hh_df = filtered_df.groupby(['household_id', 'income_before_taxes', 'education_level'])['annual_amount'].sum().reset_index()
        
        # Rename columns for a professional display
        hh_df.rename(columns={
            'household_id': 'Household ID',
            'income_before_taxes': 'Pre-Tax Income',
            'education_level': 'Education',
            'annual_amount': 'Total Tracked Spend'
        }, inplace=True)
        
        hh_df['Spend % of Income'] = (hh_df['Total Tracked Spend'] / hh_df['Pre-Tax Income']) * 100
        
        st.dataframe(
            hh_df.style.format({
                'Pre-Tax Income': "${:,.0f}", 
                'Total Tracked Spend': "${:,.0f}",
                'Spend % of Income': "{:.1f}%"
            }).background_gradient(cmap='RdPu', subset=['Spend % of Income']),
            use_container_width=True, hide_index=True
        )


    with col_table2:
        st.subheader("Household Financial Summary")
        hh_df = filtered_df.groupby(['household_id', 'income_before_taxes', 'education_level'])['annual_amount'].sum().reset_index()
        hh_df.rename(columns={'annual_amount': 'Total Tracked Spend'}, inplace=True)
        hh_df['Spend % of Income'] = (hh_df['Total Tracked Spend'] / hh_df['income_before_taxes']) * 100
        
        st.dataframe(
            hh_df.style.format({
                'income_before_taxes': "${:,.0f}", 
                'Total Tracked Spend': "${:,.0f}",
                'Spend % of Income': "{:.1f}%"
            }).background_gradient(cmap='Oranges', subset=['Spend % of Income']),
            use_container_width=True, hide_index=True
        )


with tab4:
    st.subheader("High Rollers vs. Budget Savers")
    st.markdown("Comparing the average categorical spending of the top 10% highest spenders versus the bottom 10% lowest spenders in your current filtered view.")
    
    # Calculate total spending per household to find percentiles
    hh_totals = filtered_df.groupby('household_id')['annual_amount'].sum().reset_index()
    
    if len(hh_totals) < 10:
        st.info("Not enough households in the current filter to calculate meaningful top/bottom 10% percentiles. Broaden your filters to view this chart.")
    else:
        p90 = hh_totals['annual_amount'].quantile(0.9)
        p10 = hh_totals['annual_amount'].quantile(0.1)
        
        # Isolate household IDs
        high_ids = hh_totals[hh_totals['annual_amount'] >= p90]['household_id']
        low_ids = hh_totals[hh_totals['annual_amount'] <= p10]['household_id']
        
        # Get full data for these specific households
        hr_df = filtered_df[filtered_df['household_id'].isin(high_ids)]
        bs_df = filtered_df[filtered_df['household_id'].isin(low_ids)]
        
        # Calculate average categorical spend for both groups
        hr_cat = hr_df.groupby('category_name')['annual_amount'].mean().reset_index()
        hr_cat['Cohort'] = 'High Rollers (Top 10%)'
        
        bs_cat = bs_df.groupby('category_name')['annual_amount'].mean().reset_index()
        bs_cat['Cohort'] = 'Budget Savers (Bottom 10%)'
        
        # Combine for plotting
        radar_df = pd.concat([hr_cat, bs_cat])
        
        # Build the Radar Chart
        fig_radar = px.line_polar(
            radar_df, 
            r='annual_amount', 
            theta='category_name', 
            color='Cohort',
            line_close=True,
            color_discrete_map={'High Rollers (Top 10%)': '#C2185B', 'Budget Savers (Bottom 10%)': '#F48FB1'},
            template="plotly_white"
        )
        
        # Professional upgrades: fill the areas with opacity, format tooltips
        fig_radar.update_traces(
            fill='toself', 
            opacity=0.75,
            hovertemplate="<b>%{theta}</b><br>Avg Spend: $%{r:,.0f}<extra></extra>"
        )
        
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, showticklabels=True, tickfont=dict(size=10)),
                angularaxis=dict(tickfont=dict(size=13, color='black'))
            ),
            legend=dict(orientation="h", yanchor="bottom", y=1.1, xanchor="center", x=0.5)
        )
        
        st.plotly_chart(fig_radar, use_container_width=True)