import streamlit as st
import sqlite3, os, io, csv
import pandas as pd
from datetime import datetime
from database import init_db, DB_NAME, ATTACHMENTS_DIR

st.set_page_config(page_title="خطوط العالمية ش ش و | GLOBAL LINES SPC", page_icon="🏢", layout="wide")
init_db()

if "lang" not in st.session_state:
    st.session_state.lang = "ar"
if "role" not in st.session_state:
    st.session_state.role = None

is_rtl = (st.session_state.lang == "ar")

st.markdown(f"""
<style>
    .stApp {{ direction: {'rtl' if is_rtl else 'ltr'}; text-align: {'right' if is_rtl else 'left'}; }}
    div[data-testid="stMetric"] {{ background-color: #0F172A; border: 1px solid #38BDF8; padding: 14px; border-radius: 12px; color: #FFFFFF !important; }}
    div[data-testid="stMetric"] label, div[data-testid="stMetric"] div {{ color: #FFFFFF !important; }}
</style>
""", unsafe_allow_html=True)

if not st.session_state.role:
    c1, c2, c3 = st.columns((1, 2, 1))
    with c2:
        st.title("🏢 خطوط العالمية ش ش و")
        st.subheader("GLOBAL LINES SPC - Manpower & Billing Cloud ERP")
        st.caption("Salalah - Sultanate of Oman | CR No: 1430392")
        pwd = st.text_input("أدخل رمز الدخول (المدير أو الموظف) | Enter Access PIN", type="password")
        if st.button("دخول النظام | Login", use_container_width=True, type="primary"):
            if pwd == "1430392":
                st.session_state.role = "admin"; st.rerun()
            elif pwd == "2026":
                st.session_state.role = "staff"; st.rerun()
            else:
                st.error("رمز الدخول غير صحيح | Invalid PIN")
    st.stop()

with st.sidebar:
    st.markdown("### 🏢 خطوط العالمية ش ش و\n**GLOBAL LINES SPC**")
    st.caption(f"الصلاحية: {'المدير العام (Admin)' if st.session_state.role == 'admin' else 'موظف إدخال (Staff)'}")
    if st.button("🌐 English / العربية", use_container_width=True):
        st.session_state.lang = "en" if is_rtl else "ar"; st.rerun()

    if st.session_state.role == "admin":
        pages = ["لوحة التحكم والمصروفات", "الشركات المستأجرة", "سجل العمال والبنوك", "التايم شيت والخصومات", "فواتير كل شهر", "كشف الرواتب وحماية الأجور"] if is_rtl else ["Dashboard & Expenses", "Client Companies", "Workers & Banks", "Timesheet & OT", "Monthly Invoices", "Payroll & Oman WPS"]
    else:
        pages = ["التايم شيت والخصومات", "المصروفات التشغيلية", "سجل العمال والبنوك"] if is_rtl else ["Timesheet & OT", "Operational Expenses", "Workers & Banks"]

    page = st.radio("القائمة الرئيسية | Navigation", pages)
    st.divider()
    if st.button("تسجيل خروج | Logout", use_container_width=True):
        st.session_state.role = None; st.rerun()

conn = sqlite3.connect(DB_NAME)

if page in ("لوحة التحكم والمصروفات", "Dashboard & Expenses", "المصروفات التشغيلية", "Operational Expenses"):
    st.header("📊 لوحة التحكم والإحصائيات المالية" if is_rtl else "📊 Executive Financial Dashboard")
    m_rows = conn.execute("SELECT DISTINCT month_year FROM timesheets UNION SELECT DISTINCT month_year FROM expenses ORDER BY month_year DESC").fetchall()
    all_lbl = "جميع الأشهر" if is_rtl else "All Months"
    sel_m = st.selectbox("تصفية حسب الشهر | Filter Month", [all_lbl] + [m for (m,) in m_rows])

    if st.session_state.role == "admin":
        if sel_m == all_lbl:
            inv, sal, ded = conn.execute("SELECT COALESCE(SUM(invoice_amount),0), COALESCE(SUM(net_salary),0), COALESCE(SUM(deduction_amount),0) FROM timesheets").fetchone()
            (exp,) = conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses").fetchone()
        else:
            inv, sal, ded = conn.execute("SELECT COALESCE(SUM(invoice_amount),0), COALESCE(SUM(net_salary),0), COALESCE(SUM(deduction_amount),0) FROM timesheets WHERE month_year=?", (sel_m,)).fetchone()
            (exp,) = conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE month_year=?", (sel_m,)).fetchone()

        prof = float(inv) - (float(sal) + float(exp))
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("إجمالي الفواتير" if is_rtl else "Invoices", f"{float(inv):,.3f} OMR")
        m2.metric("إجمالي الرواتب" if is_rtl else "Salaries", f"{float(sal):,.3f} OMR")
        m3.metric("المصروفات" if is_rtl else "Expenses", f"{float(exp):,.3f} OMR")
        m4.metric("الخصومات" if is_rtl else "Deductions", f"{float(ded):,.3f} OMR")
        m5.metric("صافي الربح" if is_rtl else "Net Profit", f"{prof:,.3f} OMR")

    st.subheader("💸 تسجيل المصروفات التشغيلية" if is_rtl else "💸 Operational Expenses")
    with st.form("exp_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        em = c1.text_input("الشهر | Month", value=datetime.now().strftime("%Y-%m"))
        ec = c2.selectbox("البند | Category", ["سكن العمال", "نقل ووقود", "بطاقات وإقامات", "مصاريف إدارية", "أخرى"])
        ea = c3.number_input("المبلغ (OMR) | Amount", min_value=0.0, step=1.0, format="%.3f")
        en = c4.text_input("البيان | Notes")
        if st.form_submit_button("إضافة مصروف + | Add Expense", type="primary"):
            conn.execute("INSERT INTO expenses (month_year, category, amount, notes) VALUES (?,?,?,?)", (em.strip(), ec, ea, en.strip()))
            conn.commit(); st.rerun()

    st.dataframe(pd.read_sql_query("SELECT id AS الرقم, month_year AS الشهر, category AS البند, amount AS المبلغ, notes AS البيان FROM expenses ORDER BY id DESC", conn), use_container_width=True, hide_index=True)

elif page in ("الشركات المستأجرة", "Client Companies"):
    st.header("🏭 إدارة الشركات المستأجرة للعمالة" if is_rtl else "🏭 Client Companies Management")
    with st.form("cl_form", clear_on_submit=True):
        c1, c2, c3, c4, c5 = st.columns(5)
        nar, nen, cr, ph, lc = c1.text_input("اسم الشركة (عربي)"), c2.text_input("Company Name (EN)"), c3.text_input("السجل التجاري CR"), c4.text_input("الهاتف Phone"), c5.text_input("الموقع Location")
        if st.form_submit_button("حفظ الشركة + | Save Client", type="primary") and nar:
            conn.execute("INSERT INTO clients (name_ar, name_en, cr_number, phone, location) VALUES (?,?,?,?,?)", (nar.strip(), (nen or nar).strip(), cr.strip(), ph.strip(), lc.strip()))
            conn.commit(); st.rerun()
    st.dataframe(pd.read_sql_query("SELECT id AS الرقم, name_ar AS 'الشركة عربي', name_en AS 'Company EN', cr_number AS 'السجل التجاري', phone AS الهاتف, location AS الموقع FROM clients ORDER BY id DESC", conn), use_container_width=True, hide_index=True)

elif page in ("سجل العمال والبنوك", "Workers & Banks"):
    st.header("👷 سجل العمال والبيانات البنكية" if is_rtl else "👷 Workers & Bank Registry")
    cls = conn.execute("SELECT id, name_ar, name_en FROM clients").fetchall()
    cmap = {f"{cid} - {nar if is_rtl else nen}": cid for cid, nar, nen in cls}
    with st.form("wk_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        war, wen, idt, pid = c1.text_input("الاسم بالعربي"), c2.text_input("Full Name (EN)"), c3.selectbox("نوع الهوية", ["C", "P"]), c4.text_input("الرقم المدني / الجواز")
        c5, c6, c7, c8 = st.columns(4)
        bic, iban, trd, cl_sel = c5.text_input("رمز البنك BIC", value="BMUSOMRX"), c6.text_input("الحساب البنكي IBAN"), c7.selectbox("المهنة", ["MASON", "HELPER", "TECHNICIAN", "DRIVER"]), c8.selectbox("الشركة المستأجرة", list(cmap.keys()) if cmap else ["-"])
        c9, c10, c11, c12 = st.columns(4)
        dr, dhrs, otr, cr_rate = c9.number_input("أجر اليوم (OMR)", value=4.333, format="%.3f"), c10.number_input("ساعات اليوم المتفق عليها", value=10.0, step=1.0), c11.number_input("أجر الإضافي/ساعة", value=0.600, format="%.3f"), c12.number_input("سعر الساعة للشركة", value=1.200, format="%.3f")
        if st.form_submit_button("إضافة عامل + | Add Worker", type="primary") and war and cmap:
            conn.execute("INSERT INTO workers (name_ar,name_en,id_type,passport_id,bank_bic,bank_account,trade,daily_rate,agreed_daily_hours,ot_rate,standard_days,client_hourly_rate,client_id,salary_due_day) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (war.strip(), (wen or war).strip(), idt, pid.strip(), bic.strip(), iban.strip(), trd, dr, dhrs, otr, 30, cr_rate, cmap[cl_sel], 28))
            conn.commit(); st.rerun()
    st.dataframe(pd.read_sql_query("SELECT w.id AS الرقم, w.name_ar AS 'الاسم عربي', w.name_en AS 'Name EN', w.trade AS المهنة, c.name_ar AS الشركة, w.daily_rate AS 'أجر اليوم', COALESCE(w.agreed_daily_hours,10) AS 'ساعات اليوم', w.client_hourly_rate AS 'سعر الشركة', w.passport_id AS الهوية, w.bank_account AS الحساب FROM workers w LEFT JOIN clients c ON w.client_id=c.id ORDER BY w.id DESC", conn), use_container_width=True, hide_index=True)

elif page in ("التايم شيت والخصومات", "Timesheet & OT"):
    st.header("⏱️ إدارة التايم شيت (حساب الإضافي والخصم تلقائياً)" if is_rtl else "⏱️ Smart Timesheet & Auto OT/Deduction")
    wks = conn.execute("SELECT id, name_ar, name_en, daily_rate, COALESCE(agreed_daily_hours,10), ot_rate, client_hourly_rate FROM workers").fetchall()
    wmap = {f"{wid} - {nar if is_rtl else nen} ({dhrs}h)": (wid, dr, dhrs, otr, cr) for wid, nar, nen, dr, dhrs, otr, cr in wks}
    with st.form("ts_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        wsel, myr, wd, ah = c1.selectbox("اختر العامل", list(wmap.keys()) if wmap else ["-"]), c2.text_input("الشهر", value=datetime.now().strftime("%Y-%m")), c3.number_input("أيام العمل الفعلية", min_value=0.0, step=1.0), c4.number_input("إجمالي الساعات الفعلية", min_value=0.0, step=1.0)
        c5, c6, c7, c8 = st.columns(4)
        hol, adv, bh, rem = c5.number_input("إضافي الإجازات (يدوي)", min_value=0.0, step=1.0), c6.number_input("السلفة (OMR)", min_value=0.0, step=1.0, format="%.3f"), c7.number_input("ساعات الفاتورة للشركة", min_value=0.0, step=1.0), c8.text_input("ملاحظات / الإجازات")
        up_f = st.file_uploader("إرفاق ملف التايم شيت (PDF / Excel / صورة)", type=["pdf", "xlsx", "xls", "png", "jpg", "jpeg"])
        if st.form_submit_button("اعتماد وحساب السجل + | Save Timesheet", type="primary") and wmap:
            wid, dr, dhrs, otr, cr = wmap[wsel]
            req = wd * dhrs; act = ah if ah > 0 else req
            tot_ot = round(max(0.0, act - req) + hol, 2); sh_h = round(max(0.0, req - act), 2)
            ded = round(sh_h * (dr / dhrs if dhrs > 0 else 0), 3); net = round(max(0.0, (wd * dr) - ded + (tot_ot * otr) - adv), 3)
            b_hrs = bh if bh > 0 else (act + hol); inv = round(b_hrs * cr, 3)
            att_p = os.path.join(ATTACHMENTS_DIR, f"{wid}_{myr}_{up_f.name}") if up_f else ""
            if up_f:
                with open(att_p, "wb") as f: f.write(up_f.getbuffer())
            conn.execute("INSERT INTO timesheets (worker_id,month_year,working_days,actual_hours,ot_hours,advance_salary,shortage_days,shortage_hours,deduction_amount,net_salary,billed_hours,invoice_amount,remarks,attachment_path) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (wid, myr.strip(), wd, act, tot_ot, adv, hol, sh_h, ded, net, b_hrs, inv, rem.strip(), att_p))
            conn.commit(); st.rerun()
    st.dataframe(pd.read_sql_query("SELECT t.id AS الرقم, t.month_year AS الشهر, w.name_ar AS العامل, t.working_days AS الأيام, COALESCE(t.actual_hours,0) AS 'الساعات الفعلية', COALESCE(t.shortage_hours,0) AS 'نقص الساعات', t.deduction_amount AS الخصم, t.ot_hours AS 'إجمالي الإضافي', t.advance_salary AS السلفة, t.net_salary AS 'صافي الراتب', t.billed_hours AS 'ساعات الفاتورة', t.invoice_amount AS الفاتورة FROM timesheets t JOIN workers w ON t.worker_id=w.id ORDER BY t.id DESC", conn), use_container_width=True, hide_index=True)

elif page in ("فواتير كل شهر", "Monthly Invoices"):
    st.header("🧾 فواتير كل شهر - خطوط العالمية ش ش و" if is_rtl else "🧾 Monthly Invoices - GLOBAL LINES SPC")
    df_inv = pd.read_sql_query("SELECT t.month_year AS الشهر, c.name_ar AS 'الشركة عربي', c.name_en AS 'Company EN', COUNT(w.id) AS العمال, SUM(t.billed_hours) AS الساعات, ROUND(SUM(t.invoice_amount),3) AS 'المبلغ الأساسي', ROUND(SUM(t.invoice_amount)*0.05,3) AS 'ضريبة 5%', ROUND(SUM(t.invoice_amount)*1.05,3) AS 'الإجمالي النهائي' FROM timesheets t JOIN workers w ON t.worker_id=w.id JOIN clients c ON w.client_id=c.id GROUP BY t.month_year, c.id ORDER BY t.month_year DESC", conn)
    st.dataframe(df_inv, use_container_width=True, hide_index=True)

elif page in ("كشف الرواتب وحماية الأجور", "Payroll & Oman WPS"):
    st.header("🏦 كشف الرواتب وملف حماية الأجور العُماني (SIF)" if is_rtl else "🏦 Payroll & Official Oman CBO WPS Export")
    c1, c2, c3, c4 = st.columns(4)
    nm_v, cr_v, bk_v, ac_v = c1.text_input("الشركة الدافعة", value="GLOBAL LINES SPC"), c2.text_input("السجل التجاري", value="1430392"), c3.text_input("رمز البنك", value="BMUS"), c4.text_input("حساب بنك مسقط", value="0423060354940014")
    data = conn.execute("SELECT t.month_year, w.id, w.name_ar, w.name_en, w.id_type, w.passport_id, w.bank_bic, w.bank_account, w.trade, w.salary_due_day, c.name_ar, c.name_en, t.working_days, w.daily_rate, t.ot_hours, w.ot_rate, t.deduction_amount, t.advance_salary, t.net_salary, t.invoice_amount, t.remarks FROM timesheets t JOIN workers w ON t.worker_id=w.id LEFT JOIN clients c ON w.client_id=c.id ORDER BY t.id DESC").fetchall()
    if data:
        tot_net, first_m = 0.0, ""
        for myr, wid, nar, nen, idt, pid, bic, iban, trd, due, car, cen, wd, dr, oth, otr, ded, adv, net, inv, rem in data:
            tot_net += float(net or 0)
            if not first_m: first_m = str(myr)
        yr_s, mo_s = first_m.split("-") if "-" in first_m else (datetime.now().strftime("%Y"), datetime.now().strftime("%m"))
        buf = io.StringIO(); w = csv.writer(buf)
        w.writerow(["Employer CR-NO", "Employer Name", "Payer Bank Short Name", "Payer Account Number", "Salary Year", "Salary Month", "Total Salaries", "Number of Records", "Payment Type"])
        w.writerow([cr_v, nm_v, bk_v, ac_v, yr_s, mo_s, f"{tot_net:.3f}", len(data), "Salary"])
        w.writerow(["Employee ID Type", "Employee ID", "Reference Number", "Employee Name", "Employee Bank BIC", "Employee Account", "Salary Frequency", "Number of Working Days", "Net Salary", "Basic Salary", "Extra Hours", "Extra Income", "Deductions", "Social Security Ded.", "Notes / Comments"])
        for myr, wid, nar, nen, idt, pid, bic, iban, trd, due, car, cen, wd, dr, oth, otr, ded, adv, net, inv, rem in data:
            w.writerow([idt or "C", pid or "", f"GL-{wid:03d}", nen, bic or "BMUSOMRX", iban or "", "M", int(wd), f"{net:.3f}", f"{round(wd*dr,3):.3f}", oth, f"{round(oth*otr,3):.3f}", f"{round(adv,3):.3f}", "0.000", rem or f"Salary {myr}"])
        st.download_button("⬇️ تحميل ملف البنك المركزي الرسمي (SIF CSV)", data=buf.getvalue().encode("utf-8"), file_name=f"SIF_{cr_v}_{bk_v}_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv", type="primary")
    st.dataframe(pd.read_sql_query("SELECT t.month_year AS الشهر, w.name_ar AS العامل, w.trade AS المهنة, c.name_ar AS الشركة, t.working_days AS الأيام, t.deduction_amount AS الخصم, t.advance_salary AS السلفة, t.net_salary AS 'صافي الراتب', t.invoice_amount AS الفاتورة FROM timesheets t JOIN workers w ON t.worker_id=w.id LEFT JOIN clients c ON w.client_id=c.id ORDER BY t.id DESC", conn), use_container_width=True, hide_index=True)

conn.close()
