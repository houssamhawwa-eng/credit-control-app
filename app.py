import streamlit as st
import pandas as pd
import plotly.express as px

# إعدادات الصفحة
st.set_page_config(page_title="Credit Control Dashboard", layout="wide")

st.title("📊 Credit Control & Collection Machine")
st.markdown("---")

# رفع الملف
uploaded_file = st.file_uploader("Upload your Master Excel Template", type=["xlsx"])

if uploaded_file:
    # قراءة البيانات
    df_analysis = pd.read_excel(uploaded_file, sheet_name='Analysis Dashboard')
    
    # 1. المقياس الرئيسي (KPIs)
    total_balance = df_analysis['Total Balance'].sum()
    target = 30000000
    gap = total_balance - target
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Current Market Credit", f"{total_balance:,.0f} SAR")
    col2.metric("Year-End Target", f"{target:,.0f} SAR")
    col3.metric("Reduction Needed", f"{gap:,.0f} SAR", delta_color="inverse")

    st.markdown("---")

    # 2. فلاتر القنوات والـ Top 10
    st.subheader("🔝 Top 10 Overdue by Channel")
    channel_list = df_analysis['Channel'].unique()
    selected_channel = st.selectbox("Select Sales Channel:", channel_list)
    
    channel_data = df_analysis[df_analysis['Channel'] == selected_channel]
    top_10 = channel_data.sort_values(by='Total Balance', ascending=False).head(10)
    
    fig = px.bar(top_10, x='Customer Name', y='Total Balance', 
                 color='Action Status', title=f"Top 10 Exposure in {selected_channel}")
    st.plotly_chart(fig, use_container_width=True)

# 3. جدول البيانات الذكي
    st.subheader("📋 Detailed Analysis & Risk Segmentation")
    st.dataframe(df_analysis.style.map(lambda x: 'background-color: #ffcccc' if x == '🔴 Block' else 
                                            ('background-color: #ffffcc' if x == '🟡 Watchlist' else ''), 
                                            subset=['Action Status']))
