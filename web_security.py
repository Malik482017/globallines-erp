import streamlit as st
import smtplib, random
from email.message import EmailMessage

def ensure_auth_table(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS app_settings (k TEXT PRIMARY KEY, v TEXT)")
    if not conn.execute("SELECT v FROM app_settings WHERE k='admin_pin'").fetchone():
        conn.execute("INSERT INTO app_settings (k, v) VALUES ('admin_pin', '1430392')")
    if not conn.execute("SELECT v FROM app_settings WHERE k='staff_pin'").fetchone():
        conn.execute("INSERT INTO app_settings (k, v) VALUES ('staff_pin', '2026')")
    conn.commit()

def get_pins(conn):
    ensure_auth_table(conn)
    a = conn.execute("SELECT v FROM app_settings WHERE k='admin_pin'").fetchone()
    s = conn.execute("SELECT v FROM app_settings WHERE k='staff_pin'").fetchone()
    adm = a[0] if isinstance(a, (tuple, list)) else (a or "1430392")
    stf = s[0] if isinstance(s, (tuple, list)) else (s or "2026")
    return str(adm), str(stf)

def send_otp_email(otp_code):
    sender = st.secrets.get("SMTP_EMAIL", "")
    app_pass = st.secrets.get("SMTP_PASS", "").replace(" ", "")
    receiver = st.secrets.get("ADMIN_EMAIL", sender)
    if not sender or not app_pass:
        return False, "يرجى إضافة SMTP_EMAIL و SMTP_PASS في إعدادات Secrets أولاً"
    msg = EmailMessage()
    msg["Subject"] = "رمز التحقق لتغيير كلمة المرور - خطوط العالمية ش ش و"
    msg["From"] = sender
    msg["To"] = receiver
    msg.set_content(f"رمز التحقق (OTP) الخاص بتغيير كلمة مرور المدير العام هو:\n\n{otp_code}")
    with smtplib.SMTP_SSL("://gmail.com", 465, timeout=15) as server:
        server.login(sender, app_pass)
        server.send_message(msg)
    return True, receiver

def render_password_change_box(conn, is_rtl):
    with st.expander("🔐 تغيير كلمة المرور (OTP)" if is_rtl else "🔐 Change Admin PIN (OTP)"):
        if st.button("📧 إرسال رمز OTP إلى الإيميل" if is_rtl else "📧 Send OTP to Email", width="stretch"):
            code = str(random.randint(100000, 999999))
            try:
                ok, info = send_otp_email(code)
                if ok:
                    st.session_state.pending_otp = code
                    st.success(f"تم إرسال الرمز إلى: {info}" if is_rtl else f"OTP sent to: {info}")
                else:
                    st.error(info)
            except Exception as e:
                st.error(f"فشل الإرسال: {e}")

        if "pending_otp" in st.session_state:
            otp_in = st.text_input("أدخل رمز OTP المرسل لإيميلك" if is_rtl else "Enter Email OTP Code", max_chars=6)
            new_pin = st.text_input("كلمة المرور الجديدة" if is_rtl else "New Admin PIN", type="password")
            conf_pin = st.text_input("تأكيد كلمة المرور الجديدة" if is_rtl else "Confirm New PIN", type="password")
            if st.button("💾 تأكيد وحفظ كلمة المرور" if is_rtl else "💾 Verify & Save PIN", type="primary", width="stretch"):
                if otp_in.strip() != st.session_state.pending_otp:
                    st.error("رمز OTP غير صحيح!" if is_rtl else "Invalid OTP code!")
                elif len(new_pin.strip()) < 4 or new_pin != conf_pin:
                    st.error("كلمة المرور قصيرة أو غير متطابقة!" if is_rtl else "PIN too short or mismatch!")
                else:
                    conn.execute("UPDATE app_settings SET v=? WHERE k='admin_pin'", (new_pin.strip(),))
                    conn.commit()
                    del st.session_state.pending_otp
                    st.success("تم تغيير كلمة المرور بنجاح!" if is_rtl else "Admin PIN updated!")
