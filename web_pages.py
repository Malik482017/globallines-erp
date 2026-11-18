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
