import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# إعدادات الصفحة لتكون احترافية وعريضة
st.set_page_config(page_title="Executive Credit Control", layout="wide", initial_sidebar_state="collapsed")

# العنوان الرئيسي
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>اللوحة التنفيذية لمراقبة الائتمان | Executive Credit Dashboard</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size: 18px; color: gray;'>Advanced Analytics & Phase 1 Action Plan</p>", unsafe_allow_html=True)
st.markdown("---")

# رفع الملف
uploaded_file = st.file_uploader("Upload your Master Data File (Excel)", type=["xlsx"])

if uploaded_file:
    # قراءة الداتا وتأمينها من الأخطاء
    df = pd.read_excel(uploaded_file, sheet_name='Analysis Dashboard')
    df['Total Balance'] = pd.to_numeric(df['Total Balance'], errors='coerce').fillna(0)
    df['Current DSO'] = pd.to_numeric(df['Current DSO'], errors='coerce').fillna(0)
    df['Group Credit Limit'] = pd.to_numeric(df['Group Credit Limit'], errors='coerce').fillna(0)

    # 1. Define the Situation (Executive Overview)
    st.subheader("1. 🎯 Define the Situation (Executive Overview)")
    
    total_balance = df['Total Balance'].sum()
    target_2026 = 30000000
    blocked_exposure = df[df['Action Status'] == '🔴 Block']['Total Balance'].sum()
    avg_dso = df[df['Total Balance'] > 0]['Current DSO'].mean()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Current Market Exposure", f"{total_balance:,.0f} SAR")
    col2.metric("Target Credit 2026", f"{target_2026:,.0f} SAR")
    col3.metric("Critical Overdue (Blocked)", f"{blocked_exposure:,.0f} SAR", delta_color="inverse")
    col4.metric("Avg Speed of Collection (DSO)", f"{avg_dso:.0f} Days")

    # مؤشر الأداء (Gauge Chart) لمراقبة التارجت
    fig_gauge = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = total_balance,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Reduction Target Progress (Max 30M)"},
        gauge = {
            'axis': {'range': [None, max(50000000, total_balance)]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 30000000], 'color': "lightgreen"},
                {'range': [30000000, 40000000], 'color': "navajowhite"},
                {'range': [40000000, 50000000], 'color': "lightcoral"}],
            'threshold': {'line': {'color': "black", 'width': 4}, 'thickness': 0.75, 'value': target_2026}}))
    
    st.plotly_chart(fig_gauge, use_container_width=True)
    st.markdown("---")

    # تبويبات التحليل وخطة العمل
    tab1, tab2, tab3 = st.tabs(["⚠️ Concentration Risk (Top 10)", "📊 Customer Segmentation", "🚀 Immediate Action Plan (Phase 1)"])

    with tab1:
        st.subheader("Identify Concentration Risk by Channel")
        # فلتر القنوات (بيسحب الداتا الموجودة بس)
        channels = [c for c in df['Channel'].unique() if pd.notna(c)]
        selected_channel = st.selectbox("Select Channel to Drill-Down:", ["All Channels"] + channels)

        filtered_df = df if selected_channel == "All Channels" else df[df['Channel'] == selected_channel]
        
        # ضمان إظهار أكبر 10 أرقام دائماً
        top_10 = filtered_df.nlargest(10, 'Total Balance')

        if not top_10.empty:
            fig_bar = px.bar(top_10, x='Customer Name', y='Total Balance', color='Action Status',
                             color_discrete_map={'🔴 Block': '#ff4b4b', '🟡 Watchlist': '#ffa500', '🟢 Safe': '#008000'},
                             text_auto='.2s', title=f"Top Exposure Accounts in {selected_channel}")
            fig_bar.update_traces(textfont_size=12, textangle=0, textposition="outside", cliponaxis=False)
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No data available for this channel yet.")

    with tab2:
        st.subheader("Segment Customers by Action")
        col_pie, col_table = st.columns([1, 2])
        
        with col_pie:
            status_counts = df['Action Status'].value_counts().reset_index()
            status_counts.columns = ['Status', 'Count']
            fig_pie = px.pie(status_counts, values='Count', names='Status',
                             color='Status', color_discrete_map={'🔴 Block': '#ff4b4b', '🟡 Watchlist': '#ffa500', '🟢 Safe': '#008000'},
                             hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_table:
            # عرض البيانات بشكل مرتب ومفلتر للعملاء اللي عليهم رصيد بس
            active_clients = df[df['Total Balance'] > 0].sort_values(by='Total Balance', ascending=False)
            st.dataframe(active_clients[['Customer Name', 'Channel', 'Total Balance', 'Current DSO', 'Action Status']], height=400)

    with tab3:
        st.subheader("Immediate Reduction Levers & Action Tracker")
        st.markdown("""
        **Phase 1 Actions to execute today:**
        * 🛑 **Stop Deliveries:** Automate blocks on all high-risk accounts.
        * 📉 **Limit Reduction:** Apply proposed limits to stabilize exposure.
        * 💰 **Advance Payments:** Mandate collections for Watchlist clients.
        """)
        
        # استخراج العملاء اللي لازم يتم إيقافهم فوراً للمبيعات
        st.error(f"Action Required: {len(df[df['Action Status'] == '🔴 Block'])} Accounts violating credit terms. Total at risk: {blocked_exposure:,.0f} SAR.")
        blocked_df = df[df['Action Status'] == '🔴 Block'][['Customer ID', 'Customer Name', 'Channel', 'Total Balance', 'Current DSO']].sort_values(by='Total Balance', ascending=False)
        st.dataframe(blocked_df, hide_index=True, use_container_width=True)
