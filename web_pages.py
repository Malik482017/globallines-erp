import streamlit as st
import os, io, csv
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from datetime import datetime
from database import ATTACHMENTS_DIR

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

def render_timesheet_page(conn, is_rtl):
    st.header("⏱️ إدارة التايم شيت (حساب الإضافي والخصم تلقائياً)" if is_rtl else "⏱️ Smart Timesheet & Auto OT/Deduction")
    wks = conn.execute("SELECT id, name_ar, name_en, daily_rate, COALESCE(agreed_daily_hours,10), ot_rate, client_hourly_rate FROM workers").fetchall()
    wmap = {f"{wid} - {nar if is_rtl else nen} ({dhrs}h)": (wid, dr, dhrs, otr, cr) for wid, nar, nen, dr, dhrs, otr, cr in wks}
    with st.form("ts_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        wsel = c1.selectbox("اختر العامل" if is_rtl else "Select Worker", list(wmap.keys()) if wmap else ["-"])
        myr = c2.text_input("الشهر" if is_rtl else "Month (YYYY-MM)", value=datetime.now().strftime("%Y-%m"))
        wd = c3.number_input("أيام العمل الفعلية" if is_rtl else "Working Days", min_value=0.0, step=1.0)
        ah = c4.number_input("إجمالي الساعات الفعلية" if is_rtl else "Total Actual Hours", min_value=0.0, step=1.0)
        c5, c6, c7, c8 = st.columns(4)
        hol = c5.number_input("إضافي الإجازات (يدوي)" if is_rtl else "Holiday Extra Hours", min_value=0.0, step=1.0)
        adv = c6.number_input("السلفة (OMR)" if is_rtl else "Advance Salary (OMR)", min_value=0.0, step=1.0, format="%.3f")
        bh = c7.number_input("ساعات الفاتورة للشركة" if is_rtl else "Client Billed Hours", min_value=0.0, step=1.0)
        rem = c8.text_input("ملاحظات / الإجازات" if is_rtl else "Remarks / Leaves")
        up_f = st.file_uploader("إرفاق ملف التايم شيت (PDF / Excel / صورة)" if is_rtl else "Attach Timesheet (PDF / Excel / Image)", type=["pdf", "xlsx", "xls", "png", "jpg", "jpeg"])
        if st.form_submit_button("اعتماد وحساب السجل +" if is_rtl else "+ Save & Calculate Timesheet", type="primary") and wmap:
            wid, dr, dhrs, otr, cr = wmap[wsel]
            req = wd * dhrs; act = ah if ah > 0 else req
            tot_ot = round(max(0.0, act - req) + hol, 2); sh_h = round(max(0.0, req - act), 2)
            ded = round(sh_h * (dr / dhrs if dhrs > 0 else 0), 3); net = round(max(0.0, (wd * dr) - ded + (tot_ot * otr) - adv), 3)
            b_hrs = bh if bh > 0 else (act + hol); inv = round(b_hrs * cr, 3)
            att_p = os.path.join(ATTACHMENTS_DIR, f"{wid}_{myr}_{up_f.name}") if up_f else ""
            if up_f:
                with open(att_p, "wb") as f: f.write(up_f.getbuffer())
            conn.execute("INSERT INTO timesheets (worker_id,month_year,working_days,actual_hours,ot_hours,advance_salary,shortage_days,shortage_hours,deduction_amount,net_salary,billed_hours,invoice_amount,remarks,attachment_path) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (wid, myr.strip(), wd, act, tot_ot, adv, hol, sh_h, ded, net, b_hrs, inv, rem.strip(), att_p)); conn.commit(); st.rerun()
    q_ar = "SELECT t.id AS الرقم, t.month_year AS الشهر, w.name_ar AS العامل, t.working_days AS الأيام, COALESCE(t.actual_hours,0) AS 'الساعات الفعلية', COALESCE(t.shortage_hours,0) AS 'نقص الساعات', t.deduction_amount AS الخصم, t.ot_hours AS 'إجمالي الإضافي', t.advance_salary AS السلفة, t.net_salary AS 'صافي الراتب', t.billed_hours AS 'ساعات الفاتورة', t.invoice_amount AS الفاتورة FROM timesheets t JOIN workers w ON t.worker_id=w.id ORDER BY t.id DESC"
    q_en = "SELECT t.id AS ID, t.month_year AS Month, w.name_en AS Worker, t.working_days AS Days, COALESCE(t.actual_hours,0) AS 'Actual Hrs', COALESCE(t.shortage_hours,0) AS 'Short Hrs', t.deduction_amount AS Deduction, t.ot_hours AS 'Total OT', t.advance_salary AS Advance, t.net_salary AS 'Net Salary', t.billed_hours AS 'Billed Hrs', t.invoice_amount AS Invoice FROM timesheets t JOIN workers w ON t.worker_id=w.id ORDER BY t.id DESC"
    st.dataframe(pd.read_sql_query(q_ar if is_rtl else q_en, conn), use_container_width=True, hide_index=True)

def render_invoices_page(conn, is_rtl):
    st.header("🧾 فواتير كل شهر - خطوط العالمية ش ش و" if is_rtl else "🧾 Monthly Client Invoices - GLOBAL LINES SPC")
    inv_rows = conn.execute("SELECT t.month_year, c.name_ar, c.name_en, COUNT(w.id), SUM(t.billed_hours), ROUND(SUM(t.invoice_amount),3), ROUND(SUM(t.invoice_amount)*0.05,3), ROUND(SUM(t.invoice_amount)*1.05,3) FROM timesheets t JOIN workers w ON t.worker_id=w.id JOIN clients c ON w.client_id=c.id GROUP BY t.month_year, c.id ORDER BY t.month_year DESC").fetchall()
    if inv_rows:
        xls_inv = build_styled_xlsx("GLOBAL LINES SPC - Monthly Client Invoices", ["Month", "Client (AR)", "Client (EN)", "Workers", "Hours", "Subtotal (OMR)", "VAT 5%", "Grand Total (OMR)"], inv_rows, (6, 7, 8))
        st.download_button("⬇️ تصدير الفواتير إلى إكسل بالمعادلات (.XLSX)" if is_rtl else "⬇️ Export Invoices to Excel (.XLSX)", data=xls_inv, file_name=f"GLOBAL_LINES_Invoices_{datetime.now().strftime('%Y%m')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
    cols = ["الشهر", "الشركة عربي", "Company EN", "العمال", "الساعات", "المبلغ الأساسي", "ضريبة 5%", "الإجمالي النهائي"] if is_rtl else ["Month", "Client (AR)", "Client (EN)", "Workers", "Hours", "Subtotal (OMR)", "VAT 5%", "Grand Total (OMR)"]
    st.dataframe(pd.DataFrame(inv_rows, columns=cols), use_container_width=True, hide_index=True)

def render_payroll_page(conn, is_rtl):
    st.header("🏦 كشف الرواتب وملف حماية الأجور العُماني (SIF)" if is_rtl else "🏦 Payroll & Official Oman CBO WPS Export")
    c1, c2, c3, c4 = st.columns(4)
    nm_v = c1.text_input("الشركة الدافعة" if is_rtl else "Employer Name", value="GLOBAL LINES SPC")
    cr_v = c2.text_input("السجل التجاري" if is_rtl else "Employer CR No.", value="1430392")
    bk_v = c3.text_input("رمز البنك" if is_rtl else "Payer Bank", value="BMUS")
    ac_v = c4.text_input("حساب بنك مسقط" if is_rtl else "Payer Account No.", value="0423060354940014")
    data = conn.execute("SELECT t.month_year, w.id, w.name_ar, w.name_en, w.id_type, w.passport_id, w.bank_bic, w.bank_account, w.trade, w.salary_due_day, c.name_ar, c.name_en, t.working_days, w.daily_rate, t.ot_hours, w.ot_rate, t.deduction_amount, t.advance_salary, t.net_salary, t.invoice_amount, t.remarks FROM timesheets t JOIN workers w ON t.worker_id=w.id LEFT JOIN clients c ON w.client_id=c.id ORDER BY t.id DESC").fetchall()
    if data:
        tot_net, first_m, xls_rows = 0.0, "", []
        for myr, wid, nar, nen, idt, pid, bic, iban, trd, due, car, cen, wd, dr, oth, otr, ded, adv, net, inv, rem in data:
            tot_net += float(net or 0)
            if not first_m: first_m = str(myr)
            xls_rows.append((myr, nar, nen, trd, cen or "-", float(wd), float(ded), float(adv), float(net), float(inv)))
        yr_s, mo_s = first_m.split("-") if "-" in first_m else (datetime.now().strftime("%Y"), datetime.now().strftime("%m"))
        buf = io.StringIO(); w = csv.writer(buf)
        w.writerow(["Employer CR-NO", "Employer Name", "Payer Bank Short Name", "Payer Account Number", "Salary Year", "Salary Month", "Total Salaries", "Number of Records", "Payment Type"])
        w.writerow([cr_v, nm_v, bk_v, ac_v, yr_s, mo_s, f"{tot_net:.3f}", len(data), "Salary"])
        w.writerow(["Employee ID Type", "Employee ID", "Reference Number", "Employee Name", "Employee Bank BIC", "Employee Account", "Salary Frequency", "Number of Working Days", "Net Salary", "Basic Salary", "Extra Hours", "Extra Income", "Deductions", "Social Security Ded.", "Notes / Comments"])
        for myr, wid, nar, nen, idt, pid, bic, iban, trd, due, car, cen, wd, dr, oth, otr, ded, adv, net, inv, rem in data:
            w.writerow([idt or "C", pid or "", f"GL-{wid:03d}", nen, bic or "BMUSOMRX", iban or "", "M", int(wd), f"{net:.3f}", f"{round(wd*dr,3):.3f}", oth, f"{round(oth*otr,3):.3f}", f"{round(adv,3):.3f}", "0.000", rem or f"Salary {myr}"])
        b1, b2 = st.columns(2)
        b1.download_button("⬇️ تحميل ملف البنك المركزي الرسمي (SIF CSV)" if is_rtl else "⬇️ Download Oman CBO WPS (SIF CSV)", data=buf.getvalue().encode("utf-8"), file_name=f"SIF_{cr_v}_{bk_v}_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv", type="primary", use_container_width=True)
