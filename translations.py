import arabic_reshaper
from bidi.algorithm import get_display

def fix_ar(text):
    if text is None:
        return ""
    text = str(text)
    if any('\u0600' <= c <= '\u06FF' for c in text):
        return get_display(arabic_reshaper.reshape(text))
    return text

TEXTS = {
    "ar": {
        "brand_ar": "خطوط العالمية ش ش و",
        "brand_en": "GLOBAL LINES SPC",
        "app_title": "نظام إدارة القوى العاملة والفوترة",
        "lang_btn": "English",
        "nav_dashboard": "لوحة التحكم والإحصائيات",
        "nav_clients": "الشركات المستأجرة",
        "nav_workers": "سجل العمال والبنوك",
        "nav_timesheet": "التايم شيت والخصومات",
        "nav_invoices": "فواتير كل شهر",
        "nav_payroll": "كشف الرواتب وحماية الأجور",
        "card_invoices": "إجمالي الفواتير الصادرة",
        "card_salaries": "إجمالي الرواتب المستحقة",
        "card_deductions": "إجمالي الخصومات",
        "card_profit": "صافي الربح التقديري",
        "welcome_msg": "نظام الإدارة المتكامل لشركة خطوط العالمية ش ش و",
        "dev_note": "متوافق مع نظام حماية الأجور العُماني والفوترة الشهرية للشركات",
        "btn_add": "إضافة وحفظ",
        "btn_edit": "تعديل المحدد",
        "btn_delete": "حذف المحدد",
        "btn_update": "حفظ التعديلات",
        "select_row": "يرجى تحديد صف من الجدول أولاً.",
        "confirm_del": "هل أنت متأكد من حذف هذا السجل نهائياً؟",
        "msg_error": "يرجى التأكد من صحة البيانات والأرقام المدخلة."
    },
    "en": {
        "brand_ar": "GLOBAL LINES SPC",
        "brand_en": "Salalah - Sultanate of Oman",
        "app_title": "Manpower & Billing ERP System",
        "lang_btn": "العربية",
        "nav_dashboard": "Dashboard & Analytics",
        "nav_clients": "Client Companies",
        "nav_workers": "Workers & Bank Registry",
        "nav_timesheet": "Timesheet & Deductions",
        "nav_invoices": "Monthly Invoices",
        "nav_payroll": "Payroll & Oman WPS",
        "card_invoices": "Total Issued Invoices",
        "card_salaries": "Total Payable Salaries",
        "card_deductions": "Total Deductions",
        "card_profit": "Estimated Net Profit",
        "welcome_msg": "Integrated Management System - GLOBAL LINES SPC",
        "dev_note": "Compliant with Central Bank of Oman WPS & Monthly Client Billing.",
        "btn_add": "Add & Save",
        "btn_edit": "Edit Selected",
        "btn_delete": "Delete Selected",
        "btn_update": "Save Changes",
        "select_row": "Please select a row from the table first.",
        "confirm_del": "Are you sure you want to permanently delete this record?",
        "msg_error": "Please verify all fields and numeric values."
    }
}
