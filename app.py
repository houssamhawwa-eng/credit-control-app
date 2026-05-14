import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Credit Control Pro", layout="wide")

st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>المنصة الذكية لمراقبة الائتمان | Smart Credit Intelligence</h1>", unsafe_allow_html=True)
st.markdown("---")

uploaded_file = st.file_uploader("Upload Master Data (Raw Sheets Only)", type=["xlsx"])

if uploaded_file:
    all_sheets = pd.read_excel(uploaded_file, sheet_name=None)
    df_cust = all_sheets.get('Customers Master', pd.DataFrame())
    df_inv = all_sheets.get('Orders & Invoices', pd.DataFrame())
    df_bal = all_sheets.get('Daily Balance Snapshot', pd.DataFrame())

    # تنظيف أسماء الأعمدة من المسافات المخفية اللي بتعمل مشاكل
    df_inv.columns = df_inv.columns.str.strip()
    df_bal.columns = df_bal.columns.str.strip()
    df_cust.columns = df_cust.columns.str.strip()

    # تحديد عامود المبيعات بذكاء (حتى لو السيستم غير اسمه)
    net_col = 'Net Total' if 'Net Total' in df_inv.columns else ('Total' if 'Total' in df_inv.columns else None)
    if not net_col:
        st.error("لم يتم العثور على عامود المبيعات (Total أو Net Total) في صفحة الفواتير.")
        st.stop()

    df_inv[net_col] = pd.to_numeric(df_inv[net_col], errors='coerce').fillna(0)
    
    # تحديد عامود الرصيد بذكاء
    bal_col = 'Closing Balance' if 'Closing Balance' in df_bal.columns else df_bal.columns[-1]
    df_bal[bal_col] = pd.to_numeric(df_bal[bal_col], errors='coerce').fillna(0)
    
    # العمليات الحسابية
    sales_summary = df_inv.groupby('Customer ID')[net_col].sum().reset_index()
    sales_summary.columns = ['Customer ID', 'YTD Sales']
    
    balance_summary = df_bal.groupby('Customer ID')[bal_col].sum().reset_index()
    balance_summary.columns = ['Customer ID', 'Total Balance']
    
    final_df = df_cust.merge(sales_summary, on='Customer ID', how='left').merge(balance_summary, on='Customer ID', how='left')
    final_df[['YTD Sales', 'Total Balance']] = final_df[['YTD Sales', 'Total Balance']].fillna(0)

    # تطبيق القواعد
    def apply_terms(row):
        ch = str(row.get('Channel', '')).upper()
        if any(x in ch for x in ['WS', 'WHOLESALE', 'NT', 'AGENT']): return 45
        if 'EXP' in ch: return 21
        return row.get('Payment Terms (Days)', 30)

    if 'Payment Terms (Days)' not in final_df.columns:
        final_df['Payment Terms (Days)'] = 30
        
    final_df['Payment Terms (Days)'] = final_df.apply(apply_terms, axis=1)

    final_df['Current DSO'] = (final_df['Total Balance'] / final_df['YTD Sales'].replace(0, 1)) * 133
    final_df['Forecast EOY'] = (final_df['YTD Sales'] / 5) * 12
    
    final_df['Action Status'] = final_df.apply(lambda r: '🔴 Block' if r['Current DSO'] > r['Payment Terms (Days)'] else 
                                              ('🟡 Watchlist' if r['Current DSO'] > (r['Payment Terms (Days)'] * 0.8) else '🟢 Safe'), axis=1)

    # واجهة العرض التنفيذية
    total_market_credit = final_df['Total Balance'].sum()
    target = 30000000
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Current Market Exposure", f"{total_market_credit:,.0f} SAR")
    col2.metric("Target 2026", "30,000,000 SAR")
    col3.metric("Reduction Required", f"{max(0, total_market_credit - target):,.0f} SAR", delta_color="inverse")

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["📉 Risk Analysis", "🏢 Channel Performance", "📋 Action Plan"])
    
    with tab1:
        st.subheader("Risk Distribution")
        filtered_for_pie = final_df[final_df['Total Balance'] > 0]
        if not filtered_for_pie.empty:
            fig_pie = px.pie(filtered_for_pie, names='Action Status', values='Total Balance',
                             color='Action Status', color_discrete_map={'🔴 Block': '#E11D48', '🟡 Watchlist': '#F59E0B', '🟢 Safe': '#10B981'})
            st.plotly_chart(fig_pie, use_container_width=True)

    with tab2:
        st.subheader("Concentration Risk (Top 10 Overdue per Channel)")
        if 'Channel' in final_df.columns:
            channels = final_df['Channel'].dropna().unique()
            selected_ch = st.selectbox("Select Channel:", channels)
            ch_data = final_df[final_df['Channel'] == selected_ch].nlargest(10, 'Total Balance')
            if not ch_data.empty:
                fig_bar = px.bar(ch_data, x='Customer Name', y='Total Balance', color='Action Status', text_auto='.2s')
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("لا توجد بيانات متاحة لهذه القناة.")

    with tab3:
        st.subheader("Immediate Execution List")
        st.write("العملاء الذين تجاوزوا شروط الائتمان ويجب إيقافهم فوراً:")
        blocked = final_df[final_df['Action Status'] == '🔴 Block']
        if not blocked.empty:
            cols_to_show = [c for c in ['Customer ID', 'Customer Name', 'Channel', 'Total Balance', 'Current DSO'] if c in blocked.columns]
            st.dataframe(blocked[cols_to_show].sort_values(by='Total Balance', ascending=False), use_container_width=True)
