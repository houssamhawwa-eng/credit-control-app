import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Credit Control Pro", layout="wide")

st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>المنصة الذكية لمراقبة الائتمان | Smart Credit Intelligence</h1>", unsafe_allow_html=True)
st.markdown("---")

uploaded_file = st.file_uploader("Upload Master Data (Raw Sheets Only)", type=["xlsx"])

if uploaded_file:
    # 1. قراءة كل الصفحات الخام
    all_sheets = pd.read_excel(uploaded_file, sheet_name=None)
    df_cust = all_sheets.get('Customers Master', pd.DataFrame())
    df_inv = all_sheets.get('Orders & Invoices', pd.DataFrame())
    df_bal = all_sheets.get('Daily Balance Snapshot', pd.DataFrame())

    # تنظيف البيانات وتجهيز الأرقام
    df_inv['Net Total'] = pd.to_numeric(df_inv['Net Total'], errors='coerce').fillna(0)
    df_bal['Closing Balance'] = pd.to_numeric(df_bal['Closing Balance'], errors='coerce').fillna(0)
    
    # 2. العمليات الحسابية (Engine)
    # حساب مبيعات السنة لكل عميل
    sales_summary = df_inv.groupby('Customer ID')['Net Total'].sum().reset_index()
    sales_summary.columns = ['Customer ID', 'YTD Sales']
    
    # حساب الرصيد الحالي لكل عميل
    balance_summary = df_bal.groupby('Customer ID')['Closing Balance'].sum().reset_index()
    balance_summary.columns = ['Customer ID', 'Total Balance']
    
    # دمج البيانات مع قائمة العملاء الأساسية
    final_df = df_cust.merge(sales_summary, on='Customer ID', how='left').merge(balance_summary, on='Customer ID', how='left')
    final_df[['YTD Sales', 'Total Balance']] = final_df[['YTD Sales', 'Total Balance']].fillna(0)

    # تطبيق قوانين شروط الدفع (Business Rules)
    def apply_terms(row):
        ch = str(row['Channel']).upper()
        if any(x in ch for x in ['WS', 'WHOLESALE', 'NT', 'AGENT']): return 45
        if 'EXP' in ch: return 21
        return row.get('Payment Terms (Days)', 30)

    final_df['Payment Terms (Days)'] = final_df.apply(apply_terms, axis=1)

    # حساب الـ DSO والتوقعات (DSO Calculated on 133 days as of May 13)
    final_df['Current DSO'] = (final_df['Total Balance'] / final_df['YTD Sales'].replace(0, 1)) * 133
    final_df['Forecast EOY'] = (final_df['YTD Sales'] / 5) * 12
    
    # حساب Action Status
    final_df['Action Status'] = final_df.apply(lambda r: '🔴 Block' if r['Current DSO'] > r['Payment Terms (Days)'] else 
                                              ('🟡 Watchlist' if r['Current DSO'] > (r['Payment Terms (Days)'] * 0.8) else '🟢 Safe'), axis=1)

    # 3. واجهة العرض التنفيذية
    total_market_credit = final_df['Total Balance'].sum()
    target = 30000000
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Current Market Exposure", f"{total_market_credit:,.0f} SAR")
    col2.metric("Target 2026", "30,000,000 SAR")
    col3.metric("Reduction Required", f"{max(0, total_market_credit - target):,.0f} SAR", delta_color="inverse")

    st.markdown("---")

    # الرسوم البيانية المتطورة
    tab1, tab2, tab3 = st.tabs(["📉 Risk Analysis", "🏢 Channel Performance", "📋 Action Plan"])
    
    with tab1:
        st.subheader("Risk Distribution")
        fig_pie = px.pie(final_df[final_df['Total Balance'] > 0], names='Action Status', values='Total Balance',
                         color='Action Status', color_discrete_map={'🔴 Block': '#E11D48', '🟡 Watchlist': '#F59E0B', '🟢 Safe': '#10B981'})
        st.plotly_chart(fig_pie, use_container_width=True)

    with tab2:
        st.subheader("Concentration Risk (Top 10 Overdue per Channel)")
        channels = final_df['Channel'].unique()
        selected_ch = st.selectbox("Select Channel:", channels)
        ch_data = final_df[final_df['Channel'] == selected_ch].nlargest(10, 'Total Balance')
        fig_bar = px.bar(ch_data, x='Customer Name', y='Total Balance', color='Action Status', text_auto='.2s')
        st.plotly_chart(fig_bar, use_container_width=True)

    with tab3:
        st.subheader("Immediate Execution List")
        st.write("Customers violating credit terms and requiring immediate hold:")
        blocked = final_df[final_df['Action Status'] == '🔴 Block'][['Customer ID', 'Customer Name', 'Channel', 'Total Balance', 'Current DSO']]
        st.dataframe(blocked.sort_values(by='Total Balance', ascending=False), use_container_width=True)
