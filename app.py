import streamlit as st
import requests
import json

# ==========================================
# 1. إعدادات الصفحة والهوية البصرية لشركة مسمار (MisMar)
# ==========================================
st.set_page_config(
    page_title="نظام تدقيق الطلبات وتجربة العملاء - مسمار",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# هيدر التطبيق
st.markdown("""
<div style="background-color: #0d233a; padding: 20px; border-radius: 12px; border-right: 6px solid #2ecc71; margin-bottom: 25px; text-align: center; color: white;">
    <h1 style="margin: 0; font-size: 28px;">🔍 نظام تدقيق الطلبات وتجربة العملاء (MisMar CX Audit)</h1>
    <p style="margin-top: 8px; color: #bdc3c7; font-size: 15px;">استخراج التبريرات التشغيلية والأسباب الجذرية بدقة عالية</p>
</div>
""", unsafe_allow_html=True)

# ==========================================
# 2. القائمة الجانبية وإدارة الـ API Key
# ==========================================
st.sidebar.title("⚙️ إعدادات النظام")

secret_key = st.secrets.get("GEMINI_API_KEY", "")
api_key_input = st.sidebar.text_input("Gemini API Key / Token", value=secret_key, type="password")

api_key = api_key_input.strip() if api_key_input else secret_key.strip()

if not api_key:
    st.sidebar.warning("⚠️ يرجى التأكد من إدخال المفتاح في Secrets أو القائمة الجانبية.")

st.sidebar.markdown("---")
st.sidebar.info("💡 هذا التطبيق مخصص لفريق الجودة والتدقيق التشغيلي لتسهيل تحليل الأسباب الجذرية لتقييمات العملاء.")

# ==========================================
# 3. إدخال بيانات الطلب والتقييمات
# ==========================================
col_input, col_result = st.columns([1, 1], gap="large")

with col_input:
    st.subheader("📋 بيانات الطلب والتقييمات")
    
    order_id = st.number_input("رقم الطلب (Order ID)", min_value=1000000, max_value=9999999, value=1005354, step=1)
    
    st.markdown("##### ⭐️ تقييمات العميل المدخلة:")
    
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        time_rating = st.slider("الوقت ⏳", 1, 5, 3)
        price_rating = st.slider("السعر 💰", 1, 5, 4)
        quality_rating = st.slider("الجودة 🛠️", 1, 5, 4)
    with col_r2:
        cs_rating = st.slider("خدمة العملاء 🎧", 1, 5, 4)
        overall_rating = st.slider("التقييم العام ⭐️", 1, 5, 3)

    analyze_btn = st.button("🚀 بدء التدقيق العميق واستخراج التبرير", use_container_width=True, type="primary")

# ==========================================
# 4. البرومبت والمحرك الذكي للتواصل مع API
# ==========================================
PROMPT_TEMPLATE = """
أنت خبير تدقيق تشغيلي وتجربة عملاء (Senior CX & Operations Auditor) في شركة "مسمار".
مهمتك إجراء تدقيق عميق وشامل لبيانات الطلب رقم #{order_id}.

التقييمات المدخلة للطلب:
- الوقت: {time_rating}/5
- السعر: {price_rating}/5
- الجودة: {quality_rating}/5
- خدمة العملاء: {cs_rating}/5
- التقييم العام: {overall_rating}/5

التعليمات الصارمة للتحليل:
1. ابدأ فوراً بالسبب التشغيلي المباشر للتقييمات المنخفضة دون ذكر ديباجة درجات التقييمات أو سرد الأرقام في البداية.
2. تتبع الأسباب الجذرية الحقيقية من التذاكر ومحادثات الشات والتسلسل الزمني وعروض الأسعار.
3. صغ التبرير بأسلوب تشغيلي طبيعي ومباشر من 4 إلى 5 سطور فقط جاهز للنسخ لمدير العمليات.

قسّم المخرجات إلى قسمين باستخدام الفاصل بالضبط:
===SPLIT===

القسم الأول: التبرير التشغيلي المباشر (4-5 سطور صافية).
===SPLIT===
القسم الثاني: الأدلة والوقائع التفصيلية (تحليل التذاكر، الشات، التسعير، والمواعيد).
"""

if analyze_btn:
    if not api_key:
        st.error("❌ لا يمكن إجراء التحليل بدون مفتاح API!")
    else:
        with st.spinner("⏳ جاري تحليل بيانات الطلب واستخراج التبريرات..."):
            prompt_text = PROMPT_TEMPLATE.format(
                order_id=order_id,
                time_rating=time_rating,
                price_rating=price_rating,
                quality_rating=quality_rating,
                cs_rating=cs_rating,
                overall_rating=overall_rating
            )
            
            payload = {
                "contents": [{"parts": [{"text": prompt_text}]}],
                "generationConfig": {
                    "temperature": 0.45,
                    "topP": 0.9
                }
            }
            
            # تم تحديث اسم الموديل المعتمد إلى gemini-2.5-flash
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=60)
                
                # تجربة بدون Authorization Header في حال رفض المفتاح الـ Bearer
                if response.status_code != 200:
                    clean_headers = {"Content-Type": "application/json"}
                    response = requests.post(url, headers=clean_headers, json=payload, timeout=60)

                if response.status_code == 200:
                    res_data = response.json()
                    ai_text = res_data["candidates"][0]["content"]["parts"][0]["text"]
                    
                    if "===SPLIT===" in ai_text:
                        parts = ai_text.split("===SPLIT===")
                        justification = parts[1].strip() if len(parts) > 1 else ai_text
                        details = parts[2].strip() if len(parts) > 2 else ""
                    else:
                        justification = ai_text
                        details = ""
                    
                    st.session_state["justification"] = justification
                    st.session_state["details"] = details
                    st.success("✅ تم التحليل بنجاح!")
                else:
                    st.error(f"❌ خطأ من جوجل API ({response.status_code}): {response.text}")
            except Exception as e:
                st.error(f"❌ حدث خطأ أثناء الاتصال: {str(e)}")

# ==========================================
# 5. عرض النتائج
# ==========================================
with col_result:
    st.subheader("📊 مخرجات التقرير والتدقيق")
    
    if "justification" in st.session_state:
        st.markdown("##### 📝 التبرير التشغيلي (جاهز للنسخ لمدير العمليات):")
        
        st.text_area(
            label="حدد النص بالكامل واضغط Ctrl+C للنسخ",
            value=st.session_state["justification"],
            height=140
        )
        
        if st.session_state.get("details"):
            with st.expander("🔍 الأدلة والوقائع التفصيلية (للمراجعة والتحقق)", expanded=True):
                st.markdown(st.session_state["details"])
    else:
        st.info("👈 قم بإدخال رقم الطلب والتقييمات، ثم اضغط على زر التحليل لتعرض النتائج هنا.")
