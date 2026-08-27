import streamlit as st
import google.generativeai as genai

# ==========================================
# 1. إعدادات الصفحة والهوية البصرية لشركة مسمار
# ==========================================
st.set_page_config(
    page_title="نظام تدقيق الطلبات - مسمار",
    page_icon="🔧",
    layout="wide"
)

st.markdown("""
<div style="background-color: #0d233a; padding: 20px; border-radius: 12px; border-right: 6px solid #2ecc71; margin-bottom: 25px; text-align: center; color: white;">
    <h1 style="margin: 0; font-size: 28px;">🔍 نظام تدقيق الطلبات وتجربة العملاء (MisMar CX Audit)</h1>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 2. القائمة الجانبية والـ API Key
# ==========================================
st.sidebar.title("⚙️ الإعدادات")

secret_key = st.secrets.get("GEMINI_API_KEY", "")
api_key_input = st.sidebar.text_input("Gemini API Key", value=secret_key, type="password")

api_key = api_key_input.strip() if api_key_input else secret_key.strip()

if not api_key:
    st.sidebar.warning("⚠️ يرجى إدخال المفتاح للبدء.")

# ==========================================
# 3. بيانات الطلب
# ==========================================
col_input, col_result = st.columns([1, 1], gap="large")

with col_input:
    st.subheader("📋 بيانات الطلب والتقييمات")
    order_id = st.number_input("رقم الطلب", min_value=1000000, max_value=9999999, value=1005354)
    
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        time_rating = st.slider("الوقت ⏳", 1, 5, 3)
        price_rating = st.slider("السعر 💰", 1, 5, 4)
        quality_rating = st.slider("الجودة 🛠️", 1, 5, 4)
    with col_r2:
        cs_rating = st.slider("خدمة العملاء 🎧", 1, 5, 4)
        overall_rating = st.slider("التقييم العام ⭐️", 1, 5, 3)

    analyze_btn = st.button("🚀 بدء التدقيق العميق", use_container_width=True, type="primary")

PROMPT_TEMPLATE = """
أنت خبير تدقيق تشغيلي وتجربة عملاء في شركة "مسمار".
مهمتك إجراء تدقيق عميق لبيانات الطلب رقم #{order_id}.

التقييمات:
- الوقت: {time_rating}/5, السعر: {price_rating}/5, الجودة: {quality_rating}/5, خدمة العملاء: {cs_rating}/5, التقييم العام: {overall_rating}/5

التعليمات:
1. ابدأ فوراً بالسبب التشغيلي المباشر للتقييمات المنخفضة بدون ديباجة.
2. تتبع الأسباب الجذرية وصغ التبرير في 4-5 سطور جاهزة للنسخ.

قسّم المخرجات بـ:
===SPLIT===
القسم الأول: التبرير المباشر.
===SPLIT===
القسم الثاني: الأدلة والوقائع التفصيلية.
"""

# ==========================================
# 4. معالجة الطلب
# ==========================================
if analyze_btn:
    if not api_key:
        st.error("❌ المفتاح مفقود!")
    else:
        with st.spinner("⏳ جاري التحليل..."):
            try:
                genai.configure(api_key=api_key)
                
                # ربط بالموديل المباشر المتاح
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                prompt_text = PROMPT_TEMPLATE.format(
                    order_id=order_id,
                    time_rating=time_rating,
                    price_rating=price_rating,
                    quality_rating=quality_rating,
                    cs_rating=cs_rating,
                    overall_rating=overall_rating
                )
                
                response = model.generate_content(prompt_text)
                ai_text = response.text
                
                if "===SPLIT===" in ai_text:
                    parts = ai_text.split("===SPLIT===")
                    st.session_state["justification"] = parts[1].strip()
                    st.session_state["details"] = parts[2].strip() if len(parts) > 2 else ""
                else:
                    st.session_state["justification"] = ai_text
                    st.session_state["details"] = ""
                
                st.success("✅ تم التحليل بنجاح!")

            except Exception as e:
                st.error(f"❌ حدث خطأ: {str(e)}")

# ==========================================
# 5. عرض النتائج
# ==========================================
with col_result:
    st.subheader("📊 المخرجات")
    if "justification" in st.session_state:
        st.text_area("التبرير التشغيلي (Ctrl+C للنسخ):", value=st.session_state["justification"], height=140)
        if st.session_state.get("details"):
            with st.expander("🔍 الأدلة التفصيلية", expanded=True):
                st.markdown(st.session_state["details"])
