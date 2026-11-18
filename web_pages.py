import streamlit as st
import os, io, csv
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from datetime import datetime
from database import ATTACHMENTS_DIR
from web_admin import manage_record_bar

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
    buf = io.BytesIO(); wb.save(buf); return buf.getvalue()

def render_timesheet_page(conn, is_rtl):
    st.header("⏱️ إدارة التايم شيت (حساب الإضافي والخصم تلقائياً)" if is_rtl else "⏱️ Smart Timesheet & Auto OT/Deduction")
    wks = conn.execute("SELECT id, name_ar, name_en, daily_rate, COALESCE(agreed_daily_hours,10), ot_rate, client_hourly_rate FROM workers").fetchall()
    wmap = {f"{wid} - {nar if is_rtl else nen} ({dhrs}h)": (wid, dr, dhrs, otr, cr) for wid, nar, nen, dr, dhrs, otr, cr in wks}
    with st.form("ts_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        wsel, myr, wd, ah = c1.selectbox("اختر العامل" if is_rtl else "Select Worker", list(wmap.keys()) if wmap else ["-"]), c2.text_input("الشهر" if is_rtl else "Month", value=datetime.now().strftime("%Y-%m")), c3.number_input("أيام العمل" if is_rtl else "Working Days", min_value=0.0, step=1.0), c4.number_input("الساعات الفعلية" if is_rtl else "Actual Hours", min_value=0.0, step=1.0)
        c5, c6, c7, c8 = st.columns(4)
        hol, adv, bh, rem = c5.number_input("إضافي الإجازات" if is_rtl else "Holiday OT", min_value=0.0, step=1.0), c6.number_input("السلفة (OMR)" if is_rtl else "Advance (OMR)", min_value=0.0, step=1.0, format="%.3f"), c7.number_input("ساعات الفاتورة" if is_rtl else "Billed Hours", min_value=0.0, step=1.0), c8.text_input("ملاحظات" if is_rtl else "Remarks")
        up_f = st.file_uploader("إرفاق ملف التايم شيت" if is_rtl else "Attach Timesheet", type=["pdf", "xlsx", "xls", "png", "jpg", "jpeg"])
        if st.form_submit_button("اعتماد وحساب السجل +" if is_rtl else "+ Save Timesheet", type="primary") and wmap:
            wid, dr, dhrs, otr, cr = wmap[wsel]
            req = wd * dhrs; act = ah if ah > 0 else req
            tot_ot = round(max(0.0, act - req) + hol, 2); sh_h = round(max(0.0, req - act), 2)
            ded = round(sh_h * (dr / dhrs if dhrs > 0 else 0), 3); net = round(max(0.0, (wd * dr) - ded + (tot_ot * otr) - adv), 3)
            b_hrs = bh if bh > 0 else (act + hol); inv = round(b_hrs * cr, 3)
            att_p = os.path.join(ATTACHMENTS_DIR, f"{wid}_{myr}_{up_f.name}") if up_f else ""
            if up_f:
                with open(att_p, "wb") as f: f.write(up_f.getbuffer())
            conn.execute("INSERT INTO timesheets (worker_id,month_year,working_days,actual_hours,ot_hours,advance_salary,shortage_days,shortage_hours,deduction_amount,net_salary,billed_hours,invoice_amount,remarks,attachment_path) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (wid, myr.strip(), wd, act, tot_ot, adv, hol, sh_h, ded, net, b_hrs, inv, rem.strip(), att_p)); conn.commit(); st.rerun()
    q_ts = "SELECT t.id AS الرقم, t.month_year AS الشهر, COALESCE(w.name_ar,'محذوف') AS العامل, t.working_days AS الأيام, COALESCE(t.actual_hours,0) AS 'الساعات الفعلية', COALESCE(t.shortage_hours,0) AS 'نقص الساعات', t.deduction_amount AS الخصم, t.ot_hours AS الإضافي, t.advance_salary AS السلفة, t.net_salary AS 'صافي الراتب', t.billed_hours AS 'ساعات الفاتورة', t.invoice_amount AS الفاتورة FROM timesheets t LEFT JOIN workers w ON t.worker_id=w.id ORDER BY t.id DESC" if is_rtl else "SELECT t.id AS ID, t.month_year AS Month, COALESCE(w.name_en,'Deleted') AS Worker, t.working_days AS Days, COALESCE(t.actual_hours,0) AS 'Actual Hrs', COALESCE(t.shortage_hours,0) AS 'Short Hrs', t.deduction_amount AS Deduction, t.ot_hours AS OT, t.advance_salary AS Advance, t.net_salary AS 'Net Salary', t.billed_hours AS 'Billed Hrs', t.invoice_amount AS Invoice FROM timesheets t LEFT JOIN workers w ON t.worker_id=w.id ORDER BY t.id DESC"
    st.dataframe(pd.read_sql_query(q_ts, conn), width="stretch", hide_index=True)
    manage_record_bar(conn, "timesheets", {"month_year": ("الشهر", "Month", "text"), "working_days": ("الأيام", "Days", "float"), "advance_salary": ("السلفة", "Advance", "float"), "net_salary": ("صافي الراتب", "Net Salary", "float"), "invoice_amount": ("الفاتورة", "Invoice", "float")}, is_rtl, "ts")

def render_invoices_page(conn, is_rtl):
    st.header("🧾 فواتير كل شهر - خطوط العالمية ش ش و" if is_rtl else "🧾 Monthly Invoices - GLOBAL LINES SPC")
    inv_rows = conn.execute("SELECT t.month_year, COALESCE(c.name_ar,'-'), COALESCE(c.name_en,'-'), COUNT(t.id), SUM(t.billed_hours), ROUND(SUM(t.invoice_amount),3), ROUND(SUM(t.invoice_amount)*0.05,3), ROUND(SUM(t.invoice_amount)*1.05,3) FROM timesheets t LEFT JOIN workers w ON t.worker_id=w.id LEFT JOIN clients c ON w.client_id=c.id GROUP BY t.month_year, c.id ORDER BY t.month_year DESC").fetchall()
    if inv_rows:
        xls_inv = build_styled_xlsx("GLOBAL LINES SPC - Monthly Client Invoices", ["Month", "Client (AR)", "Client (EN)", "Records", "Hours", "Subtotal (OMR)", "VAT 5%", "Grand Total (OMR)"], inv_rows, (6, 7, 8))
        st.download_button("⬇️ تصدير الفواتير إلى إكسل (.XLSX)" if is_rtl else "⬇️ Export Invoices (.XLSX)", data=xls_inv, file_name=f"GLOBAL_LINES_Invoices_{datetime.now().strftime('%Y%m')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
    cols = ["الشهر", "الشركة عربي", "Company EN", "السجلات", "الساعات", "المبلغ الأساسي", "ضريبة 5%", "الإجمالي النهائي"] if is_rtl else ["Month", "Client (AR)", "Client (EN)", "Records", "Hours", "Subtotal (OMR)", "VAT 5%", "Grand Total (OMR)"]
    st.dataframe(pd.DataFrame(inv_rows, columns=cols), width="stretch", hide_index=True)

def render_payroll_page(conn, is_rtl):
    st.header("🏦 كشف الرواتب وملف حماية الأجور العُماني (SIF)" if is_rtl else "🏦 Payroll & Official Oman CBO WPS Export")
    c1, c2, c3, c4 = st.columns(4)
    nm_v, cr_v, bk_v, ac_v = c1.text_input("الشركة الدافعة" if is_rtl else "Employer Name", value="GLOBAL LINES SPC"), c2.text_input("السجل التجاري" if is_rtl else "CR No.", value="1430392"), c3.text_input("رمز البنك" if is_rtl else "Bank", value="BMUS"), c4.text_input("حساب بنك مسقط" if is_rtl else "Payer Account", value="0423060354940014")
    data = conn.execute("SELECT t.month_year, COALESCE(w.id,0), COALESCE(w.name_ar,'-'), COALESCE(w.name_en,'Worker'), COALESCE(w.id_type,'C'), COALESCE(w.passport_id,''), COALESCE(w.bank_bic,'BMUSOMRX'), COALESCE(w.bank_account,''), COALESCE(w.trade,'-'), COALESCE(w.salary_due_day,28), COALESCE(c.name_ar,'-'), COALESCE(c.name_en,'-'), t.working_days, COALESCE(w.daily_rate,0), t.ot_hours, COALESCE(w.ot_rate,0), t.deduction_amount, t.advance_salary, t.net_salary, t.invoice_amount, t.remarks FROM timesheets t LEFT JOIN workers w ON t.worker_id=w.id LEFT JOIN clients c ON w.client_id=c.id ORDER BY t.id DESC").fetchall()
    if data:
        tot_net, first_m, xls_rows = 0.0, "", []
        for myr, wid, nar, nen, idt, pid, bic, iban, trd, due, car, cen, wd, dr, oth, otr, ded, adv, net, inv, rem in data:
            tot_net += float(net or 0); first_m = first_m or str(myr)
            xls_rows.append((myr, nar, nen, trd, cen, float(wd), float(ded), float(adv), float(net), float(inv)))
        yr_s, mo_s = first_m.split("-") if "-" in first_m else (datetime.now().strftime("%Y"), datetime.now().strftime("%m"))
        buf = io.StringIO(); w = csv.writer(buf)
        w.writerow(["Employer CR-NO", "Employer Name", "Payer Bank Short Name", "Payer Account Number", "Salary Year", "Salary Month", "Total Salaries", "Number of Records", "Payment Type"])
        w.writerow([cr_v, nm_v, bk_v, ac_v, yr_s, mo_s, f"{tot_net:.3f}", len(data), "Salary"])
        w.writerow(["Employee ID Type", "Employee ID", "Reference Number", "Employee Name", "Employee Bank BIC", "Employee Account", "Salary Frequency", "Number of Working Days", "Net Salary", "Basic Salary", "Extra Hours", "Extra Income", "Deductions", "Social Security Ded.", "Notes / Comments"])
        for myr, wid, nar, nen, idt, pid, bic, iban, trd, due, car, cen, wd, dr, oth, otr, ded, adv, net, inv, rem in data:
            w.writerow([idt, pid, f"GL-{wid:03d}", nen, bic, iban, "M", int(wd), f"{net:.3f}", f"{round(wd*dr,3):.3f}", oth, f"{round(oth*otr,3):.3f}", f"{round(adv,3):.3f}", "0.000", rem or f"Salary {myr}"])
        b1, b2 = st.columns(2)
