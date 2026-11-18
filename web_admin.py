import streamlit as st

def manage_record_bar(conn, table_name, edit_fields, is_rtl, key_prefix):
    rows = conn.execute(f"SELECT id FROM {table_name} ORDER BY id DESC").fetchall()
    if not rows:
        return
    ids = [r[0] for r in rows]
    st.markdown("---")
    with st.expander("✏️ تعديل أو حذف سجل من الجدول" if is_rtl else "✏️ Edit or Delete Record"):
        c1, c2 = st.columns([2, 1])
        sel_id = c1.selectbox("اختر رقم السجل (ID)" if is_rtl else "Select Record ID", ids, key=f"{key_prefix}_id")
        if c2.button("🗑️ حذف السجل نهائياً" if is_rtl else "🗑️ Delete Record", key=f"{key_prefix}_del", type="primary"):
            conn.execute(f"DELETE FROM {table_name} WHERE id=?", (sel_id,))
            conn.commit()
            st.rerun()

        cols_sql = ", ".join(edit_fields.keys())
        cur_vals = conn.execute(f"SELECT {cols_sql} FROM {table_name} WHERE id=?", (sel_id,)).fetchone()
        if cur_vals:
            with st.form(f"{key_prefix}_edit_form"):
                new_vals = []
                f_cols = st.columns(len(edit_fields))
                for idx, ((col_name, (lbl_ar, lbl_en, f_type)), val) in enumerate(zip(edit_fields.items(), cur_vals)):
                    lbl = lbl_ar if is_rtl else lbl_en
                    if f_type == "float":
                        new_vals.append(f_cols[idx].number_input(lbl, value=float(val or 0), format="%.3f"))
                    else:
                        new_vals.append(f_cols[idx].text_input(lbl, value=str(val or "")))
                if st.form_submit_button("💾 حفظ التعديلات" if is_rtl else "💾 Save Changes"):
                    set_clause = ", ".join([f"{k}=?" for k in edit_fields.keys()])
                    conn.execute(f"UPDATE {table_name} SET {set_clause} WHERE id=?", (*new_vals, sel_id))
                    conn.commit()
                    st.rerun()
