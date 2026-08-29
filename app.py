import json
import html
from typing import Any

import requests
import streamlit as st
from groq import Groq

# ============================================================
# DYNAMIC PROMPT BUILDER WITH MATCHING CLASSIFICATIONS
# ============================================================

def build_audit_prompt(
    order_id: int,
    order_data: dict[str, Any],
    audit_type: str,
) -> str:

    tickets_str = clean_and_minify(order_data.get("tickets"), max_items=10, max_chars=2000)
    comments_str = clean_and_minify(order_data.get("comments"), max_items=20, max_chars=3500)
    status_history_str = clean_and_minify(order_data.get("status_history"), max_items=15, max_chars=2000)
    pricing_str = clean_and_minify(order_data.get("pricing"), max_items=10, max_chars=2000)

    # 🛑 حصر قوائم التصنيفات حسب المرحلة بالضبط
    if audit_type == "تأخير مرحلة [جاري التسعير]":
        allowed_categories = """
- التصنيف: قطع الغيار
- التصنيف: تشغيل
- التصنيف: لا يوجد تاخير
- التصنيف: المركز
- التصنيف: مكرر
- التصنيف: يوم الجمعه
- التصنيف: العميل
- التصنيف: الوكاله
- التصنيف: المركز والتشغيل
- التصنيف: نقل بين مركزين
- التصنيف: المركز وقطع الغيار
- التصنيف: قطع الغيار والتشغيل
- التصنيف: المركز والوكاله
"""
    else:  # الفحص والتشخيص + جاري العمل / الصيانة + العام
        allowed_categories = """
- التصنيف: قطع الغيار
- التصنيف: التشغيل
- التصنيف: العميل
- التصنيف: مركز
- التصنيف: لا يوجد تاخير وفق خطه العميل
- التصنيف: يوم الجمعه
- التصنيف: مكرر
- التصنيف: قطع الغيار او المركز
- التصنيف: نقل مركز اخر
- التصنيف: تشغيل او المركز
- التصنيف: قطع الغيار او التشغيل
"""

    prompt_text = f"""
أنت Senior Operations & CX Forensic Auditor في شركة (مسمار - MisMar).
مهمتك كتابة تبرير تشغيلي مباشر لمدير العمليات للطلب رقم #{order_id} للتحقيق في مرحلة: [{audit_type}].

🛑 تنبيه جنائي حاسم للتحقيق الزمني:
قد يكون الطلب حالياً مكتملاً أو في حالة سابقة/لاحقة (مثلاً: تم التسليم)، ولكن المراجعة استقصائية وموجهة حصراً لمرحلة [{audit_type}].
ابحث في السجل الزمني للحالات (`status_history`) عن **أحدث/أطول فترة** كان فيها الطلب في هذه المرحلة بالذات [{audit_type}]، واربط التعليقات والتذاكر والتسعير التي وقعت داخل النطاق الزمني لهذه المرحلة خصيصاً.

البيانات المتاحة للطلب:
1. 🎫 تذاكر الشكاوى والمتابعة: {tickets_str}
2. 💬 محادثات الشات والتعليقات الداخلية: {comments_str}
3. ⏱️ التسلسل الزمني للحالات والمدد: {status_history_str}
4. 💰 طلبات التسعير وعروض الأسعار: {pricing_str}

=== 🛑 القواعد الصارمة والتنسيق المطلوب ===
اقسم إجابتك لقسمين بينهما الكلمة المفتاحية `===SPLIT===`:

القسم الأول:
اكتب السبب الرئيسي مباشرة دون أي عناوين أو تكرار أو ديباجات، متبوعاً بالتصنيف في السطر الأخير فقط.

📌 **نموذج إجباري للتنسيق في القسم الأول (التزم بالنموذج حرفياً):**
تأخير في توريد قطع الغيار اللازمة للعملية وإتمام الفحص النهائي من جهة المورد، مما تسبب في توقف الطلب لمدة تزيد عن 115 ساعة قبل بدء الصيانة الفعلية دون متابعة لتسريع الاستلام.
التصنيف: قطع الغيار

🛑 **شروط القسم الأول:**
- اكتب فقرة واحدة فقط من 2-4 سطور تمثل السبب الرئيسي والأقوى فقط خلال فترة مرحلة [{audit_type}].
- ممنوع كتابة أي عناوين مثل "التبرير التشغيلي المباشر" وممنوع تكرار سطر التصنيف أكثر من مرة.
- يُمنع ذكر أسامي أفراد (استخدم الألقاب: التشغيل / المركز).
- السطر الأخير يجب أن يحتوي على خيار واحد فقط من القائمة التالية:
{allowed_categories}

===SPLIT===

القسم الثاني:
أدلة وقائع تفصيلية وحساب التوقيتات والأدلة من التذاكر والشات باختصار للمرحلة المحددة [{audit_type}].
"""
    return prompt_text

# ============================================================
# GROQ ANALYSIS RUNNER
# ============================================================

def analyze_order_rating(
    api_key: str,
    order_id: int,
    audit_type: str,
    model_name: str,
) -> str:

    order_data = fetch_order_data(order_id)
    prompt = build_audit_prompt(order_id, order_data, audit_type)

    client = Groq(api_key=api_key.strip())

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": "أنت Senior Operations وCX Forensic Auditor. اكتب تبريراً واحداً حاسماً دون تكرار أو عناوين فرعية ملتزماً بالتصنيف المحدد فقط.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,  # درجة منخفضة جداً لمنع التكرار والتشتت
            top_p=0.9,
            max_tokens=1500,
        )
    except Exception as exc:
        raise Exception(f"خطأ في الاتصال بالذكاء الاصطناعي عبر Groq ({model_name}):\n{str(exc)}")

    if not response or not response.choices:
        raise Exception("Groq returned an empty response.")

    content = response.choices[0].message.content
    return content.strip() if content else ""

# ============================================================
# SIDEBAR UI
# ============================================================

with st.sidebar:
    st.image("https://mismarapp.com/static/media/logo.f6cf70e4.svg", width=200)
    st.markdown("### ⚙️ إعدادات النظام")

    try:
        secret_key = st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        secret_key = ""

    api_key_input = st.text_input("Groq API Key", value=str(secret_key).strip(), type="password")
    api_key = api_key_input.strip()

    available_models = []
    selected_model = None

    if api_key:
        try:
            available_models = get_model_ids(api_key)
            if available_models:
                recommended_model = choose_best_model(available_models)
                default_index = available_models.index(recommended_model) if recommended_model in available_models else 0
                selected_model = st.selectbox("🤖 اختر موديل Groq", options=available_models, index=default_index)
        except Exception as exc:
            st.error("❌ فشل اكتشاف الموديلات")

# ============================================================
# MAIN LAYOUT & INPUTS
# ============================================================

col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("📋 بيانات الطلب ونوع التدقيق")

    order_id = st.number_input("رقم الطلب (Order ID)", min_value=1, value=1000006, step=1)

    audit_type = st.radio(
        "🔍 اختر المرحلة المطلوب تدقيقها:",
        options=[
            "تأخير مرحلة [جاري الفحص والتشخيص]",
            "تأخير مرحلة [جاري التسعير]",
            "تأخير مرحلة [جاري العمل / الصيانة]",
            "تدقيق التقييمات المنخفضة (عام)"
        ],
        index=2,
    )

    st.markdown("<br>", unsafe_allow_html=True)
    analyze_btn = st.button("🚀 بدء التدقيق واستخراج التبرير المباشر")

# ============================================================
# OUTPUT & RENDERING
# ============================================================

with col2:
    st.subheader("📊 مخرجات التقرير والتدقيق")

    if analyze_btn:
        if not api_key:
            st.error("⚠️ يرجى إدخال Groq API Key.")
        elif not selected_model:
            st.error("⚠️ لم يتم العثور على موديل متاح.")
        else:
            with st.spinner(f"⏳ جاري استخراج التبرير المباشر لـ ({audit_type})..."):
                try:
                    full_response = analyze_order_rating(
                        api_key=api_key,
                        order_id=int(order_id),
                        audit_type=audit_type,
                        model_name=selected_model,
                    )

                    if "===SPLIT===" in full_response:
                        justification, evidence = full_response.split("===SPLIT===", 1)
                    else:
                        justification = full_response
                        evidence = "لم يتم تفكيك الأدلة بشكل منفصل."

                    st.session_state["audit_result"] = {
                        "justification": justification.strip(),
                        "evidence": evidence.strip(),
                        "order_id": int(order_id),
                        "audit_type": audit_type,
                        "model": selected_model,
                    }
                    st.success("✅ اكتمل التدقيق بنجاح.")

                except Exception as exc:
                    st.error("❌ حدث خطأ أثناء التحليل:")
                    st.code(str(exc), language="text")

if "audit_result" in st.session_state and st.session_state["audit_result"]:
    result = st.session_state["audit_result"]
    justification = result["justification"]
    evidence = result["evidence"]

    st.markdown("### 📝 التبرير التشغيلي المباشر:")
    safe_justification = html.escape(justification)

    st.markdown(f'<div class="justification-card">{safe_justification}</div>', unsafe_allow_html=True)

    st.text_area("📋 اضغط Ctrl+A ثم Ctrl+C للنسخ المباشر:", value=justification, height=150)

    st.markdown("### 🔍 الأدلة والوقائع التفصيلية:")
    safe_evidence = html.escape(evidence)

    st.markdown(f'<div class="evidence-card">{safe_evidence}</div>', unsafe_allow_html=True)
else:
    if not analyze_btn:
        st.info("👈 اختر نوع المرحلة ثم اضغط على زر التحليل.")
