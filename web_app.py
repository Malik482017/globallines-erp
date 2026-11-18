import streamlit as st
import sqlite3, os, io, csv
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from datetime import datetime
from database import init_db, DB_NAME, ATTACHMENTS_DIR

st.set_page_config(page_title="خطوط العالمية ش ش و | GLOBAL LINES SPC", page_icon="🏢", layout="wide", initial_sidebar_state="auto")
init_db()

if "lang" not in st.session_state: st.session_state.lang = "ar"
if "role" not in st.session_state: st.session_state.role = None
is_rtl = (st.session_state.lang == "ar")

st.markdown(f"""<style>
.stApp {{ direction: {'rtl' if is_rtl else 'ltr'}; text-align: {'right' if is_rtl else 'left'}; }}
div[data-testid="stMetric"] {{ background-color: #0F172A; border: 1px solid #38BDF8; padding: 12px; border-radius: 12px; margin-bottom: 8px; }}
div[data-testid="stMetric"] label, div[data-testid="stMetric"] div {{ color: #FFFFFF !important; }}
@media (max-width: 768px) {{
    div[data-testid="column"] {{ width: 100% !important; flex: 1 1 100% !important; min-width: 100% !important; }}
}}
</style>""", unsafe_allow_html=True)

def build_styled_xlsx(title_txt, headers, rows_list, money_cols):
    wb = Workbook(); ws = wb.active; ws.title = "Report"
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
    ws.cell(1, 1, title_txt).font = Font(size=13, bold=True, color="FFFFFF")
    ws.cell(1, 1).fill = PatternFill("solid", fgColor="0F172A")
    ws.cell(1, 1).alignment = Alignment(horizontal="center")
    thin = Side(border_style="thin", color="CBD5E1"); bdr = Border(left=thin, right=thin, top=thin, bottom=thin)
    for ci, h in enumerate(headers, start=1):
        c = ws.cell(3, ci, h); c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="1D4ED8"); c.alignment = Alignment(horizontal="center"); c.border = bdr
        ws.column_dimensions[c.column_letter].width = 18
    for idx, r in enumerate(rows_list, start=4):
        for ci, v in enumerate(r, start=1):
            c = ws.cell(idx, ci, v); c.border = bdr; c.alignment = Alignment(horizontal="center")
            if ci in money_cols: c.number_format = "0.000"
    er = 3 + len(rows_list); tr = er + 1; ws.cell(tr, 1, "TOTAL").font = Font(bold=True)
    for ci in money_cols:
        col_let = ws.cell(3, ci).column_letter
        c = ws.cell(tr, ci, f"=SUM({col_let}4:{col_let}{er})")
        c.font = Font(bold=True); c.fill = PatternFill("solid", fgColor="E2E8F0"); c.border = bdr; c.number_format = "0.000"; c.alignment = Alignment(horizontal="center")
    buf = io.BytesIO(); wb.save(buf)
    return buf.getvalue()

if not st.session_state.role:
    c1, c2, c3 = st.columns((1, 2, 1))
    with c2:
        st.title("🏢 خطوط العالمية ش ش و")
        st.subheader("GLOBAL LINES SPC - Cloud ERP")
        st.caption("Salalah - Sultanate of Oman | CR No: 1430392")
        pwd = st.text_input("رمز الدخول (PIN)", type="password")
        if st.button("دخول النظام | Login", use_container_width=True, type="primary"):
            if pwd == "1430392": st.session_state.role = "admin"; st.rerun()
            elif pwd == "2026": st.session_state.role = "staff"; st.rerun()
            else: st.error("رمز الدخول غير صحيح")
    st.stop()

with st.sidebar:
    st.markdown("### 🏢 خطوط العالمية ش ش و\n**GLOBAL LINES SPC**")
    st.caption(f"الصلاحية: {'المدير العام' if st.session_state.role == 'admin' else 'موظف إدخال'}")
    if st.button("🌐 English / العربية", use_container_width=True):
        st.session_state.lang = "en" if is_rtl else "ar"; st.rerun()
    pages = (["لوحة التحكم والمصروفات", "الشركات المستأجرة", "سجل العمال والبنوك", "التايم شيت والخصومات", "فواتير كل شهر", "كشف الرواتب وحماية الأجور"] if is_rtl else ["Dashboard & Expenses", "Client Companies", "Workers & Banks", "Timesheet & OT", "Monthly Invoices", "Payroll & Oman WPS"]) if st.session_state.role == "admin" else (["التايم شيت والخصومات", "المصروفات التشغيلية", "سجل العمال والبنوك"] if is_rtl else ["Timesheet & OT", "Operational Expenses", "Workers & Banks"])
    page = st.radio("القائمة الرئيسية", pages)
    st.divider()
    if st.button("تسجيل خروج | Logout", use_container_width=True):
        st.session_state.role = None; st.rerun()

conn = sqlite3.connect(DB_NAME)

if page in ("لوحة التحكم والمصروفات", "Dashboard & Expenses", "المصروفات التشغيلية", "Operational Expenses"):
    st.header("📊 لوحة التحكم والإحصائيات المالية" if is_rtl else "📊 Executive Dashboard")
    m_rows = conn.execute("SELECT DISTINCT month_year FROM timesheets UNION SELECT DISTINCT month_year FROM expenses ORDER BY month_year DESC").fetchall()
    all_lbl = "جميع الأشهر" if is_rtl else "All Months"
    sel_m = st.selectbox("تصفية حسب الشهر", [all_lbl] + [m for (m,) in m_rows])
    if st.session_state.role == "admin":
        q_ts = "SELECT COALESCE(SUM(invoice_amount),0), COALESCE(SUM(net_salary),0), COALESCE(SUM(deduction_amount),0) FROM timesheets" + ("" if sel_m == all_lbl else " WHERE month_year=?")
        q_ex = "SELECT COALESCE(SUM(amount),0) FROM expenses" + ("" if sel_m == all_lbl else " WHERE month_year=?")
        inv, sal, ded = conn.execute(q_ts, () if sel_m == all_lbl else (sel_m,)).fetchone()
        (exp,) = conn.execute(q_ex, () if sel_m == all_lbl else (sel_m,)).fetchone()
        prof = float(inv) - (float(sal) + float(exp))
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("إجمالي الفواتير", f"{float(inv):,.3f} OMR")
        m2.metric("إجمالي الرواتب", f"{float(sal):,.3f} OMR")
        m3.metric("المصروفات", f"{float(exp):,.3f} OMR")
        m4.metric("الخصومات", f"{float(ded):,.3f} OMR")
        m5.metric("صافي الربح", f"{prof:,.3f} OMR")

    st.subheader("💸 تسجيل المصروفات التشغيلية")
    with st.form("exp_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        em, ec, ea, en = c1.text_input("الشهر", value=datetime.now().strftime("%Y-%m")), c2.selectbox("البند", ["سكن العمال", "نقل ووقود", "بطاقات وإقامات", "مصاريف إدارية", "أخرى"]), c3.number_input("المبلغ (OMR)", min_value=0.0, step=1.0, format="%.3f"), c4.text_input("البيان")
        if st.form_submit_button("إضافة مصروف +", type="primary"):
            conn.execute("INSERT INTO expenses (month_year, category, amount, notes) VALUES (?,?,?,?)", (em.strip(), ec, ea, en.strip())); conn.commit(); st.rerun()
    st.dataframe(pd.read_sql_query("SELECT id AS الرقم, month_year AS الشهر, category AS البند, amount AS المبلغ, notes AS البيان FROM expenses ORDER BY id DESC", conn), use_container_width=True, hide_index=True)

elif page in ("الشركات المستأجرة", "Client Companies"):
    st.header("🏭 الشركات المستأجرة للعمالة")
    with st.form("cl_form", clear_on_submit=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        nar, nen, cr, ph, lc = c1.text_input("اسم الشركة (عربي)"), c2.text_input("Company Name (EN)"), c3.text_input("السجل التجاري"), c4.text_input("الهاتف"), c5.text_input("الموقع")
        if st.form_submit_button("حفظ الشركة +", type="primary") and nar:
            conn.execute("INSERT INTO clients (name_ar, name_en, cr_number, phone, location) VALUES (?,?,?,?,?)", (nar.strip(), (nen or nar).strip(), cr.strip(), ph.strip(), lc.strip())); conn.commit(); st.rerun()
    st.dataframe(pd.read_sql_query("SELECT id AS الرقم, name_ar AS 'الشركة عربي', name_en AS 'Company EN', cr_number AS 'السجل التجاري', phone AS الهاتف, location AS الموقع FROM clients ORDER BY id DESC", conn), use_container_width=True, hide_index=True)

elif page in ("سجل العمال والبنوك", "Workers & Banks"):
    st.header("👷 سجل العمال والبيانات البنكية")
    cls = conn.execute("SELECT id, name_ar, name_en FROM clients").fetchall()
    cmap = {f"{cid} - {nar if is_rtl else nen}": cid for cid, nar, nen in cls}
    with st.form("wk_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        war, wen, idt, pid = c1.text_input("الاسم بالعربي"), c2.text_input("Full Name (EN)"), c3.selectbox("نوع الهوية", ["C", "P"]), c4.text_input("الرقم المدني / الجواز")
        c5, c6, c7, c8 = st.columns(4)
        bic, iban, trd, cl_sel = c5.text_input("رمز البنك BIC", value="BMUSOMRX"), c6.text_input("الحساب البنكي IBAN"), c7.selectbox("المهنة", ["MASON", "HELPER", "TECHNICIAN", "DRIVER"]), c8.selectbox("الشركة المستأجرة", list(cmap.keys()) if cmap else ["-"])
        c9, c10, c11, c12 = st.columns(4)
        dr, dhrs, otr, cr_rate = c9.number_input("أجر اليوم (OMR)", value=4.333, format="%.3f"), c10.number_input("ساعات اليوم المتفق عليها", value=10.0, step=1.0), c11.number_input("أجر الإضافي/ساعة", value=0.600, format="%.3f"), c12.number_input("سعر الساعة للشركة", value=1.200, format="%.3f")
        if st.form_submit_button("إضافة عامل +", type="primary") and war and cmap:
            conn.execute("INSERT INTO workers (name_ar,name_en,id_type,passport_id,bank_bic,bank_account,trade,daily_rate,agreed_daily_hours,ot_rate,standard_days,client_hourly_rate,client_id,salary_due_day) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (war.strip(), (wen or war).strip(), idt, pid.strip(), bic.strip(), iban.strip(), trd, dr, dhrs, otr, 30, cr_rate, cmap[cl_sel], 28)); conn.commit(); st.rerun()
    st.dataframe(pd.read_sql_query("SELECT w.id AS الرقم, w.name_ar AS 'الاسم عربي', w.name_en AS 'Name EN', w.trade AS المهنة, c.name_ar AS الشركة, w.daily_rate AS 'أجر اليوم', COALESCE(w.agreed_daily_hours,10) AS 'ساعات اليوم', w.client_hourly_rate AS 'سعر الشركة', w.passport_id AS الهوية, w.bank_account AS الحساب FROM workers w LEFT JOIN clients c ON w.client_id=c.id ORDER BY w.id DESC", conn), use_container_width=True, hide_index=True)

elif page in ("التايم شيت والخصومات", "Timesheet & OT"):
    st.header("⏱️ إدارة التايم شيت (حساب الإضافي والخصم تلقائياً)")
    wks = conn.execute("SELECT id, name_ar, name_en, daily_rate, COALESCE(agreed_daily_hours,10), ot_rate, client_hourly_rate FROM workers").fetchall()
    wmap = {f"{wid} - {nar if is_rtl else nen} ({dhrs}h)": (wid, dr, dhrs, otr, cr) for wid, nar, nen, dr, dhrs, otr, cr in wks}
