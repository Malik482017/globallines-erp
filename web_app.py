import streamlit as st
import pandas as pd
from datetime import datetime
from database import init_db, get_conn
from web_pages import render_timesheet_page, render_invoices_page, render_payroll_page
from web_admin import manage_record_bar

st.set_page_config(page_title="خطوط العالمية ش ش و | GLOBAL LINES SPC", page_icon="🏢", layout="wide", initial_sidebar_state="collapsed")
if "db_ready" not in st.session_state:
    init_db(); st.session_state.db_ready = True

if "lang" not in st.session_state: st.session_state.lang = "ar"
if "role" not in st.session_state: st.session_state.role = None
is_rtl = (st.session_state.lang == "ar")
align = "right" if is_rtl else "left"

st.markdown(f"""<style>
.block-container h1, .block-container h2, .block-container h3, .block-container p, .block-container label {{ text-align: {align} !important; }}
div[data-testid="stMetric"] {{ background-color: #0F172A; border: 1px solid #38BDF8; padding: 12px; border-radius: 12px; margin-bottom: 8px; text-align: {align}; }}
div[data-testid="stMetric"] label, div[data-testid="stMetric"] div {{ color: #FFFFFF !important; }}
section[data-testid="stSidebar"] {{ min-width: 260px !important; }}
</style>""", unsafe_allow_html=True)

if not st.session_state.role:
    c1, c2, c3 = st.columns((1, 2, 1))
    with c2:
        st.title("🏢 خطوط العالمية ش ش و")
        st.subheader("GLOBAL LINES SPC - Cloud ERP")
        st.caption("Salalah - Sultanate of Oman | CR No: 1430392")
        pwd = st.text_input("رمز الدخول (PIN) | Access PIN", type="password")
        if st.button("دخول النظام | Login", width="stretch", type="primary"):
            if pwd == "1430392": st.session_state.role = "admin"; st.rerun()
            elif pwd == "2026": st.session_state.role = "staff"; st.rerun()
            else: st.error("رمز الدخول غير صحيح | Invalid PIN")
    st.stop()

with st.sidebar:
    st.markdown("### 🏢 خطوط العالمية ش ش و\n**GLOBAL LINES SPC**")
    role_lbl = ("المدير العام" if is_rtl else "General Manager (Admin)") if st.session_state.role == "admin" else ("موظف إدخال" if is_rtl else "Data Entry Staff")
    st.caption(f"{'الصلاحية:' if is_rtl else 'Role:'} {role_lbl}")
    if st.button("🌐 English" if is_rtl else "🌐 العربية", width="stretch"):
        st.session_state.lang = "en" if is_rtl else "ar"; st.rerun()
    pages = (["لوحة التحكم والمصروفات", "الشركات المستأجرة", "سجل العمال والبنوك", "التايم شيت والخصومات", "فواتير كل شهر", "كشف الرواتب وحماية الأجور"] if is_rtl else ["Dashboard & Expenses", "Client Companies", "Workers & Banks", "Timesheet & OT", "Monthly Invoices", "Payroll & Oman WPS"]) if st.session_state.role == "admin" else (["التايم شيت والخصومات", "المصروفات التشغيلية", "سجل العمال والبنوك"] if is_rtl else ["Timesheet & OT", "Operational Expenses", "Workers & Banks"])
    page = st.radio("القائمة الرئيسية" if is_rtl else "Main Navigation", pages)
    st.divider()
    if st.button("تسجيل خروج" if is_rtl else "Logout", width="stretch"):
        st.session_state.role = None; st.rerun()

conn = get_conn()

if page in ("لوحة التحكم والمصروفات", "Dashboard & Expenses", "المصروفات التشغيلية", "Operational Expenses"):
    st.header("📊 لوحة التحكم والإحصائيات المالية" if is_rtl else "📊 Executive Financial Dashboard")
    m_rows = conn.execute("SELECT DISTINCT month_year FROM timesheets UNION SELECT DISTINCT month_year FROM expenses ORDER BY month_year DESC").fetchall()
    all_lbl = "جميع الأشهر" if is_rtl else "All Months"
    sel_m = st.selectbox("تصفية حسب الشهر" if is_rtl else "Filter by Month", [all_lbl] + [m for (m,) in m_rows])
    if st.session_state.role == "admin":
        q_ts = "SELECT COALESCE(SUM(invoice_amount),0), COALESCE(SUM(net_salary),0), COALESCE(SUM(deduction_amount),0) FROM timesheets" + ("" if sel_m == all_lbl else " WHERE month_year=?")
        q_ex = "SELECT COALESCE(SUM(amount),0) FROM expenses" + ("" if sel_m == all_lbl else " WHERE month_year=?")
        inv, sal, ded = conn.execute(q_ts, () if sel_m == all_lbl else (sel_m,)).fetchone()
        (exp,) = conn.execute(q_ex, () if sel_m == all_lbl else (sel_m,)).fetchone()
        prof = float(inv) - (float(sal) + float(exp))
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("إجمالي الفواتير" if is_rtl else "Issued Invoices", f"{float(inv):,.3f}")
        m2.metric("إجمالي الرواتب" if is_rtl else "Payable Salaries", f"{float(sal):,.3f}")
        m3.metric("المصروفات" if is_rtl else "Total Expenses", f"{float(exp):,.3f}")
        m4.metric("الخصومات" if is_rtl else "Total Deductions", f"{float(ded):,.3f}")
        m5.metric("صافي الربح" if is_rtl else "Net Profit", f"{prof:,.3f}")

    st.subheader("💸 تسجيل المصروفات التشغيلية" if is_rtl else "💸 Operational Expenses Registry")
    with st.form("exp_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        em = c1.text_input("الشهر" if is_rtl else "Month", value=datetime.now().strftime("%Y-%m"))
        cats = ["سكن العمال", "نقل ووقود", "بطاقات وإقامات", "مصاريف إدارية", "أخرى"] if is_rtl else ["Accommodation", "Transport & Fuel", "Visas & Cards", "Admin Expenses", "Other"]
        ec = c2.selectbox("البند" if is_rtl else "Category", cats)
        ea = c3.number_input("المبلغ (OMR)" if is_rtl else "Amount (OMR)", min_value=0.0, step=1.0, format="%.3f")
        en = c4.text_input("البيان" if is_rtl else "Notes")
        if st.form_submit_button("إضافة مصروف +" if is_rtl else "+ Add Expense", type="primary"):
            conn.execute("INSERT INTO expenses (month_year, category, amount, notes) VALUES (?,?,?,?)", (em.strip(), ec, ea, en.strip())); conn.commit(); st.rerun()
    ex_rows = conn.execute("SELECT id, month_year, category, amount, notes FROM expenses ORDER BY id DESC").fetchall()
    ex_cols = ["الرقم", "الشهر", "البند", "المبلغ", "البيان"] if is_rtl else ["ID", "Month", "Category", "Amount", "Notes"]
    st.dataframe(pd.DataFrame(ex_rows, columns=ex_cols), width="stretch", hide_index=True)
    manage_record_bar(conn, "expenses", {"month_year": ("الشهر", "Month", "text"), "category": ("البند", "Category", "text"), "amount": ("المبلغ", "Amount", "float"), "notes": ("البيان", "Notes", "text")}, is_rtl, "exp")
elif page in ("الشركات المستأجرة", "Client Companies"):
    st.header("🏭 الشركات المستأجرة للعمالة" if is_rtl else "🏭 Client Companies Management")
    with st.form("cl_form", clear_on_submit=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        nar = c1.text_input("اسم الشركة (عربي)" if is_rtl else "Client Name (AR)")
        nen = c2.text_input("اسم الشركة (إنجليزي)" if is_rtl else "Company Name (EN)")
        cr = c3.text_input("السجل التجاري" if is_rtl else "CR Number")
        ph = c4.text_input("الهاتف" if is_rtl else "Phone Number")
        lc = c5.text_input("الموقع" if is_rtl else "Location")
        if st.form_submit_button("حفظ الشركة +" if is_rtl else "+ Save Client", type="primary") and nar:
            conn.execute("INSERT INTO clients (name_ar, name_en, cr_number, phone, location) VALUES (?,?,?,?,?)", (nar.strip(), (nen or nar).strip(), cr.strip(), ph.strip(), lc.strip())); conn.commit(); st.rerun()
    cl_rows = conn.execute("SELECT id, name_ar, name_en, cr_number, phone, location FROM clients ORDER BY id DESC").fetchall()
    cl_cols = ["الرقم", "الشركة عربي", "Company EN", "السجل التجاري", "الهاتف", "الموقع"] if is_rtl else ["ID", "Client (AR)", "Company (EN)", "CR No.", "Phone", "Location"]
    st.dataframe(pd.DataFrame(cl_rows, columns=cl_cols), width="stretch", hide_index=True)
    manage_record_bar(conn, "clients", {"name_ar": ("الاسم عربي", "Name AR", "text"), "name_en": ("الاسم إنجليزي", "Name EN", "text"), "cr_number": ("السجل التجاري", "CR No", "text"), "phone": ("الهاتف", "Phone", "text"), "location": ("الموقع", "Location", "text")}, is_rtl, "cl")

elif page in ("سجل العمال والبنوك", "Workers & Banks"):
    st.header("👷 سجل العمال والبيانات البنكية" if is_rtl else "👷 Workers & Bank Registry")
    cls = conn.execute("SELECT id, name_ar, name_en FROM clients").fetchall()
    cmap = {f"{cid} - {nar if is_rtl else nen}": cid for cid, nar, nen in cls}
    with st.form("wk_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        war = c1.text_input("الاسم بالعربي" if is_rtl else "Full Name (AR)")
        wen = c2.text_input("الاسم بالإنجليزي" if is_rtl else "Full Name (EN)")
        idt = c3.selectbox("نوع الهوية" if is_rtl else "ID Type", ["C", "P"])
        pid = c4.text_input("الرقم المدني / الجواز" if is_rtl else "Civil ID / Passport")
        c5, c6, c7, c8 = st.columns(4)
        bic = c5.text_input("رمز البنك BIC" if is_rtl else "Bank BIC", value="BMUSOMRX")
        iban = c6.text_input("الحساب البنكي IBAN" if is_rtl else "Bank Account / IBAN")
        trd = c7.selectbox("المهنة" if is_rtl else "Trade", ["MASON", "HELPER", "TECHNICIAN", "DRIVER"])
        cl_sel = c8.selectbox("الشركة المستأجرة" if is_rtl else "Assigned Client", list(cmap.keys()) if cmap else ["-"])
        c9, c10, c11, c12 = st.columns(4)
        dr = c9.number_input("أجر اليوم (OMR)" if is_rtl else "Daily Rate (OMR)", value=4.333, format="%.3f")
        dhrs = c10.number_input("ساعات اليوم المتفق عليها" if is_rtl else "Agreed Daily Hours", value=10.0, step=1.0)
        otr = c11.number_input("أجر الإضافي/ساعة" if is_rtl else "OT Rate / Hr", value=0.600, format="%.3f")
        cr_rate = c12.number_input("سعر الساعة للشركة" if is_rtl else "Client Hourly Rate", value=1.200, format="%.3f")
        if st.form_submit_button("إضافة عامل +" if is_rtl else "+ Add Worker", type="primary") and war and cmap:
            conn.execute("INSERT INTO workers (name_ar,name_en,id_type,passport_id,bank_bic,bank_account,trade,daily_rate,agreed_daily_hours,ot_rate,standard_days,client_hourly_rate,client_id,salary_due_day) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (war.strip(), (wen or war).strip(), idt, pid.strip(), bic.strip(), iban.strip(), trd, dr, dhrs, otr, 30, cr_rate, cmap[cl_sel], 28)); conn.commit(); st.rerun()
    wk_rows = conn.execute("SELECT w.id, w.name_ar, w.name_en, w.trade, COALESCE(c.name_ar if ? else c.name_en, '-'), w.daily_rate, COALESCE(w.agreed_daily_hours,10), w.client_hourly_rate, w.passport_id, w.bank_account FROM workers w LEFT JOIN clients c ON w.client_id=c.id ORDER BY w.id DESC", (1 if is_rtl else 0,)).fetchall()
    wk_cols = ["الرقم", "الاسم عربي", "Name EN", "المهنة", "الشركة", "أجر اليوم", "ساعات اليوم", "سعر الشركة", "الهوية", "الحساب"] if is_rtl else ["ID", "Name (AR)", "Name (EN)", "Trade", "Client", "Daily Rate", "Daily Hrs", "Client Rate", "ID/Pass", "Account"]
    st.dataframe(pd.DataFrame(wk_rows, columns=wk_cols), width="stretch", hide_index=True)
    manage_record_bar(conn, "workers", {"name_ar": ("الاسم عربي", "Name AR", "text"), "name_en": ("الاسم إنجليزي", "Name EN", "text"), "passport_id": ("الهوية", "ID/Pass", "text"), "bank_account": ("الحساب البنكي", "Account", "text"), "daily_rate": ("أجر اليوم", "Daily Rate", "float"), "client_hourly_rate": ("سعر الشركة", "Client Rate", "float")}, is_rtl, "wk")

elif page in ("التايم شيت والخصومات", "Timesheet & OT"):
    render_timesheet_page(conn, is_rtl)

elif page in ("فواتير كل شهر", "Monthly Invoices"):
    render_invoices_page(conn, is_rtl)

elif page in ("كشف الرواتب وحماية الأجور", "Payroll & Oman WPS"):
    render_payroll_page(conn, is_rtl)

conn.close()
