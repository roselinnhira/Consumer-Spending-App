import pandas as pd
import sqlite3
import numpy as np


def clean_and_build_db():
    print("Loading BLS FMLI data...")
    # Load the family data file
    df = pd.read_csv('fmli.csv', low_memory=False)
    
    # 1. CLEAN HOUSEHOLD DEMOGRAPHICS
    print("Cleaning household data...")
    # Using the correct FINCBTAX for income
    household = df[['NEWID', 'FINCBTAX', 'AGE_REF', 'FAM_SIZE', 'REGION']].copy()
    
    # Drop rows with missing critical demographic data
    household.dropna(subset=['FINCBTAX', 'AGE_REF', 'FAM_SIZE', 'REGION'], inplace=True)
    
    # Map Region codes (1: Northeast, 2: Midwest, 3: South, 4: West)
    region_map = {1.0: 'Northeast', 2.0: 'Midwest', 3.0: 'South', 4.0: 'West'}
    household['region'] = household['REGION'].map(region_map)
    
    # Create Age Groups
    bins = [0, 24, 34, 44, 54, 64, 120]
    labels = ['Under 25', '25-34', '35-44', '45-54', '55-64', '65+']
    household['age_group'] = pd.cut(household['AGE_REF'], bins=bins, labels=labels)
    
    # Create Income Brackets
    inc_bins = [-np.inf, 35000, 50000, 75000, 100000, np.inf]
    inc_labels = ['Under $35,000', '$35,000-$50,000', '$50,000-$75,000', '$75,000-$100,000', 'Over $100,000']
    household['income_bracket'] = pd.cut(household['FINCBTAX'], bins=inc_bins, labels=inc_labels)
    
    # Create Household Size Groups
    household['household_size'] = household['FAM_SIZE'].apply(
        lambda x: '1 Person' if x == 1 else ('2 People' if x == 2 else ('3-4 People' if x <= 4 else '5+ People'))
    )
    
    # Finalize household table
    household = household[['NEWID', 'income_bracket', 'age_group', 'household_size', 'region']]
    household.columns = ['household_id', 'income_bracket', 'age_group', 'household_size', 'region']
    
    # 2. CREATE CATEGORIES TABLE
    print("Creating categories...")
    categories = pd.DataFrame({
        'category_id': [1, 2, 3, 4, 5],
        'category_name': ['Food', 'Housing', 'Transportation', 'Healthcare', 'Entertainment'],
        'expense_type': ['Essential', 'Essential', 'Essential', 'Essential', 'Discretionary'],
        # Updated Entertainment column name to ENTERTCQ
        'bls_column': ['FOODCQ', 'HOUSCQ', 'TRANSCQ', 'HEALTHCQ', 'ENTERTCQ']
    })
    
    # 3. CREATE SPENDING TABLE (UNPIVOT)
    print("Transforming spending records...")
    # Extracted with the updated ENTERTCQ column
    spending_raw = df[['NEWID', 'FOODCQ', 'HOUSCQ', 'TRANSCQ', 'HEALTHCQ', 'ENTERTCQ']].copy()
    
    # Melt (unpivot) the data so each household has 5 separate spending records (relational format)
    spending_melted = spending_raw.melt(id_vars=['NEWID'], var_name='bls_column', value_name='amount')
    
    # Merge with categories to get category_id, then finalize columns
    spending = spending_melted.merge(categories, on='bls_column')
    spending = spending[['NEWID', 'category_id', 'amount']]
    spending.columns = ['household_id', 'category_id', 'annual_amount']
    
    # Filter out any negative or zero anomalous spending
    spending = spending[spending['annual_amount'] > 0]
    
    # Drop the mapping column from categories before saving to SQL
    categories = categories[['category_id', 'category_name', 'expense_type']]
    
    # 4. EXPORT TO SQLITE
    print("Building SQLite Database...")
    conn = sqlite3.connect('consumer_spending.db')
    
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")
    
    household.to_sql('household', conn, if_exists='replace', index=False)
    categories.to_sql('categories', conn, if_exists='replace', index=False)
    spending.to_sql('spending', conn, if_exists='replace', index=False)
    
    conn.close()
    print("Database built successfully: consumer_spending.db")


if __name__ == "__main__":
    clean_and_build_db()