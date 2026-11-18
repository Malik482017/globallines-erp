import csv
import io
import os
from datetime import datetime

import pandas as pd
import streamlit as st
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

from database import ATTACHMENTS_DIR
from web_admin import manage_record_bar


def build_styled_xlsx(title_txt, headers, rows_list, money_cols):
    wb = Workbook()
    ws = wb.active
    ws.title = "Report"

    # Title Row
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
    title_cell = ws.cell(1, 1, title_txt)
    title_cell.font = Font(size=13, bold=True, color="FFFFFF")
    title_cell.fill = PatternFill("solid", fgColor="0F172A")
    title_cell.alignment = Alignment(horizontal="center")

    # Styles
    thin = Side(border_style="thin", color="CBD5E1")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    header_fill = PatternFill("solid", fgColor="1D4ED8")
    header_font = Font(bold=True, color="FFFFFF")
    center_align = Alignment(horizontal="center")

    # Headers
    for ci, header in enumerate(headers, start=1):
        cell = ws.cell(3, ci, header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align
        cell.border = border
        ws.column_dimensions[cell.column_letter].width = 18

    # Data Rows
    for idx, row in enumerate(rows_list, start=4):
        for ci, val in enumerate(row, start=1):
            cell = ws.cell(idx, ci, val)
            cell.border = border
            cell.alignment = center_align
            if ci in money_cols:
                cell.number_format = "0.000"

    # Total Row
    end_row = 3 + len(rows_list)
    total_row = end_row + 1
    ws.cell(total_row, 1, "TOTAL").font = Font(bold=True)

    for ci in money_cols:
        col_letter = ws.cell(3, ci).column_letter
        cell = ws.cell(total_row, ci, f"=SUM({col_letter}4:{col_letter}{end_row})")
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="E2E8F0")
        cell.border = border
        cell.number_format = "0.000"
        cell.alignment = center_align

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def render_timesheet_page(conn, is_rtl):
    header_txt = (
        "⏱️ إدارة التايم شيت (حساب الإضافي والخصم تلقائياً)"
        if is_rtl
        else "⏱️ Smart Timesheet & Auto OT/Deduction"
    )
    st.header(header_txt)

    workers = conn.execute(
        """
        SELECT id, name_ar, name_en, daily_rate,
               COALESCE(agreed_daily_hours, 10), ot_rate, client_hourly_rate
        FROM workers
        """
    ).fetchall()

    worker_map = {
        f"{wid} - {nar if is_rtl else nen} ({dhrs}h)": (wid, dr, dhrs, otr, cr)
        for wid, nar, nen, dr, dhrs, otr, cr in workers
    }

    with st.form("ts_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns(4)
        wsel = c1.selectbox(
            "اختر العامل" if is_rtl else "Select Worker",
            list(worker_map.keys()) if worker_map else ["-"],
        )
        myr = c2.text_input(
            "الشهر" if is_rtl else "Month",
            value=datetime.now().strftime("%Y-%m"),
        )
        wd = c3.number_input(
            "أيام العمل" if is_rtl else "Working Days",
            min_value=0.0,
            step=1.0,
        )
        ah = c4.number_input(
            "الساعات الفعلية" if is_rtl else "Actual Hours",
            min_value=0.0,
            step=1.0,
        )

        c5, c6, c7, c8 = st.columns(4)
        hol = c5.number_input(
            "إضافي الإجازات" if is_rtl else "Holiday OT",
            min_value=0.0,
            step=1.0,
        )
        adv = c6.number_input(
            "السلفة (OMR)" if is_rtl else "Advance (OMR)",
            min_value=0.0,
            step=1.0,
            format="%.3f",
        )
        bh = c7.number_input(
            "ساعات الفاتورة" if is_rtl else "Billed Hours",
            min_value=0.0,
            step=1.0,
        )
        rem = c8.text_input("ملاحظات" if is_rtl else "Remarks")

        up_f = st.file_uploader(
            "إرفاق ملف التايم شيت" if is_rtl else "Attach Timesheet",
            type=["pdf", "xlsx", "xls", "png", "jpg", "jpeg"],
        )

        submit_lbl = "اعتماد وحساب السجل +" if is_rtl else "+ Save Timesheet"
        if st.form_submit_button(submit_lbl, type="primary") and worker_map:
            wid, dr, dhrs, otr, cr = worker_map[wsel]
            req_hours = wd * dhrs
            act_hours = ah if ah > 0 else req_hours

            tot_ot = round(max(0.0, act_hours - req_hours) + hol, 2)
            short_hours = round(max(0.0, req_hours - act_hours), 2)
            hourly_rate = (dr / dhrs) if dhrs > 0 else 0.0

            ded = round(short_hours * hourly_rate, 3)
            net = round(max(0.0, (wd * dr) - ded + (tot_ot * otr) - adv), 3)
            billed_hrs = bh if bh > 0 else (act_hours + hol)
            inv_amount = round(billed_hrs * cr, 3)

            att_path = ""
            if up_f:
                os.makedirs(ATTACHMENTS_DIR, exist_ok=True)
                safe_name = os.path.basename(up_f.name)
                att_path = os.path.join(
                    ATTACHMENTS_DIR, f"{wid}_{myr.strip()}_{safe_name}"
                )
                with open(att_path, "wb") as f:
                    f.write(up_f.getbuffer())

            conn.execute(
                """
                INSERT INTO timesheets (
                    worker_id, month_year, working_days, actual_hours,
                    ot_hours, advance_salary, shortage_days, shortage_hours,
                    deduction_amount, net_salary, billed_hours, invoice_amount,
                    remarks, attachment_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    wid,
                    myr.strip(),
                    wd,
                    act_hours,
                    tot_ot,
                    adv,
                    hol,
                    short_hours,
                    ded,
                    net,
                    billed_hrs,
                    inv_amount,
                    rem.strip(),
                    att_path,
                ),
            )
            conn.commit()
            st.rerun()

    if is_rtl:
        q_ts = """
            SELECT t.id AS الرقم, t.month_year AS الشهر,
                   COALESCE(w.name_ar, 'محذوف') AS العامل,
                   t.working_days AS الأيام,
                   COALESCE(t.actual_hours, 0) AS 'الساعات الفعلية',
                   COALESCE(t.shortage_hours, 0) AS 'نقص الساعات',
                   t.deduction_amount AS الخصم, t.ot_hours AS الإضافي,
                   t.advance_salary AS السلفة, t.net_salary AS 'صافي الراتب',
                   t.billed_hours AS 'ساعات الفاتورة', t.invoice_amount AS الفاتورة
            FROM timesheets t
            LEFT JOIN workers w ON t.worker_id = w.id
            ORDER BY t.id DESC
        """
    else:
        q_ts = """
            SELECT t.id AS ID, t.month_year AS Month,
                   COALESCE(w.name_en, 'Deleted') AS Worker,
                   t.working_days AS Days,
                   COALESCE(t.actual_hours, 0) AS 'Actual Hrs',
                   COALESCE(t.shortage_hours, 0) AS 'Short Hrs',
                   t.deduction_amount AS Deduction, t.ot_hours AS OT,
                   t.advance_salary AS Advance, t.net_salary AS 'Net Salary',
                   t.billed_hours AS 'Billed Hrs', t.invoice_amount AS Invoice
            FROM timesheets t
            LEFT JOIN workers w ON t.worker_id = w.id
            ORDER BY t.id DESC
        """

    st.dataframe(
        pd.read_sql_query(q_ts, conn),
        use_container_width=True,
        hide_index=True,
    )

    manage_record_bar(
        conn,
        "timesheets",
        {
            "month_year": ("الشهر", "Month", "text"),
            "working_days": ("الأيام", "Days", "float"),
            "advance_salary": ("السلفة", "Advance", "float"),
            "net_salary": ("صافي الراتب", "Net Salary", "float"),
            "invoice_amount": ("الفاتورة", "Invoice", "float"),
        },
        is_rtl,
        "ts",
    )


def render_invoices_page(conn, is_rtl):
    st.header(
        "🧾 فواتير كل شهر - خطوط العالمية ش ش و"
        if is_rtl
        else "🧾 Monthly Invoices - GLOBAL LINES SPC"
    )

    inv_rows = conn.execute(
        """
        SELECT t.month_year,
               COALESCE(c.name_ar, '-'),
               COALESCE(c.name_en, '-'),
               COUNT(t.id),
               SUM(t.billed_hours),
               ROUND(SUM(t.invoice_amount), 3),
               ROUND(SUM(t.invoice_amount) * 0.05, 3),
               ROUND(SUM(t.invoice_amount) * 1.05, 3)
        FROM timesheets t
        LEFT JOIN workers w ON t.worker_id = w.id
        LEFT JOIN clients c ON w.client_id = c.id
        GROUP BY t.month_year, c.id
        ORDER BY t.month_year DESC
        """
    ).fetchall()

    if inv_rows:
        en_headers = [
            "Month",
            "Client (AR)",
            "Client (EN)",
            "Records",
            "Hours",
            "Subtotal (OMR)",
            "VAT 5%",
            "Grand Total (OMR)",
        ]
        ar_headers = [
            "الشهر",
            "الشركة عربي",
            "Company EN",
            "السجلات",
            "الساعات",
            "المبلغ الأساسي",
            "ضريبة 5%",
            "الإجمالي النهائي",
        ]

        xls_inv = build_styled_xlsx(
            "GLOBAL LINES SPC - Monthly Client Invoices",
            en_headers,
            inv_rows,
            (6, 7, 8),
        )

        btn_lbl = (
            "⬇️ تصدير الفواتير إلى إكسل (.XLSX)"
            if is_rtl
            else "⬇️ Export Invoices (.XLSX)"
        )
        st.download_button(
            btn_lbl,
            data=xls_inv,
