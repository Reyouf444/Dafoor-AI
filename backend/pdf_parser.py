import re
import random
import json
import urllib.request
import urllib.error

# ---------------------------------------------------------------------------
# Arabic text processing helpers — fix reversed / garbled Arabic from PDFs
# ---------------------------------------------------------------------------

def _reshape_arabic(text: str) -> str:
    """Reshape and reorder Arabic text extracted from PDFs.
    
    PDFs often store Arabic letters in visual (LTR) order with unshaped
    glyphs. arabic_reshaper + bidi reorder them into correct logical order.
    """
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception:
        return text  # Return as-is if libraries unavailable


def _is_arabic_text(text: str) -> bool:
    """Return True if the text contains a significant amount of Arabic characters."""
    if not text:
        return False
    arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    total_alpha = sum(1 for c in text if c.isalpha())
    if total_alpha == 0:
        return False
    return (arabic_chars / total_alpha) > 0.3


# ---------------------------------------------------------------------------
# Default Arabic fallback question bank
# ---------------------------------------------------------------------------

DEFAULT_QUESTION_BANK = {
    "Easy": [
        {
            "question": "ما هي العاصمة المملكة العربية السعودية؟",
            "choices": ["جدة", "الرياض", "مكة المكرمة", "الدمام"],
            "correct_index": 1,
            "explanation": "الرياض هي عاصمة المملكة العربية السعودية ومركزها الإداري والسياسي."
        },
        {
            "question": "كم عدد أيام الأسبوع؟",
            "choices": ["خمسة", "ستة", "سبعة", "ثمانية"],
            "correct_index": 2,
            "explanation": "الأسبوع يتكون من سبعة أيام."
        },
        {
            "question": "ما هو أكبر كوكب في المجموعة الشمسية؟",
            "choices": ["زحل", "المريخ", "المشتري", "أورانوس"],
            "correct_index": 2,
            "explanation": "المشتري هو أكبر كوكب في المجموعة الشمسية."
        },
        {
            "question": "ما هو عنصر الماء الكيميائي؟",
            "choices": ["CO2", "H2O", "NaCl", "O2"],
            "correct_index": 1,
            "explanation": "الماء يتكون من ذرتي هيدروجين وذرة أكسجين ويُرمز له بـ H2O."
        },
        {
            "question": "أي من الآتي يعتبر مصدرًا للطاقة المتجددة؟",
            "choices": ["الفحم الحجري", "البترول", "الطاقة الشمسية", "الغاز الطبيعي"],
            "correct_index": 2,
            "explanation": "الطاقة الشمسية مصدر متجدد لأنها مستمدة من الشمس التي لا تنضب."
        }
    ],
    "Medium": [
        {
            "question": "ما العملية التي تستخدمها النباتات لتحويل ضوء الشمس إلى طاقة كيميائية؟",
            "choices": ["التنفس الخلوي", "التمثيل الضوئي", "التخمر", "النتح"],
            "correct_index": 1,
            "explanation": "التمثيل الضوئي هو العملية التي تستخدم فيها النباتات ضوء الشمس وثاني أكسيد الكربون والماء لإنتاج الغلوكوز والأكسجين."
        },
        {
            "question": "ما أكثر الغازات وفرةً في الغلاف الجوي للأرض؟",
            "choices": ["الأكسجين", "ثاني أكسيد الكربون", "النيتروجين", "الأرجون"],
            "correct_index": 2,
            "explanation": "يشكّل النيتروجين حوالي 78% من الغلاف الجوي للأرض."
        },
        {
            "question": "ما الذي يرمز إليه اختصار DNA؟",
            "choices": ["حمض الديوكسي ريبونيوكليك", "حمض الريبونيوكليك", "بروتين النيوكليوتيد", "جزيء الكروموسوم"],
            "correct_index": 0,
            "explanation": "DNA هو اختصار لحمض الديوكسي ريبونيوكليك، وهو الجزيء الحامل للمعلومات الوراثية."
        },
        {
            "question": "في علم الحاسوب، ماذا تعني كلمة CPU؟",
            "choices": ["وحدة معالجة الحاسوب", "وحدة المعالجة المركزية", "نواة المعالجة الفردية", "وحدة الطاقة المركزية"],
            "correct_index": 1,
            "explanation": "CPU تعني وحدة المعالجة المركزية، وهي المكوّن الرئيسي الذي ينفّذ تعليمات البرنامج."
        },
        {
            "question": "كم تبلغ سرعة الضوء في الفراغ تقريبًا؟",
            "choices": ["300,000 كم/ث", "150,000 كم/ث", "1,000,000 كم/ث", "30,000 كم/ث"],
            "correct_index": 0,
            "explanation": "سرعة الضوء في الفراغ تبلغ تقريبًا 299,792 كيلومترًا في الثانية."
        }
    ],
    "Hard": [
        {
            "question": "أي الجسيمات دون الذرية لا تتكون من كواركات؟",
            "choices": ["البروتون", "النيوترون", "الإلكترون", "الباريون"],
            "correct_index": 2,
            "explanation": "الإلكترونات من الليبتونات وهي جسيمات أساسية، بينما البروتونات والنيوترونات تتكون من كواركات."
        },
        {
            "question": "ما وظيفة إنزيم الأميليز في الجهاز الهضمي البشري؟",
            "choices": ["هضم البروتينات", "هضم الدهون", "تحليل النشا إلى سكريات", "استحلاب الدهون"],
            "correct_index": 2,
            "explanation": "الأميليز الموجود في اللعاب وعصير البنكرياس يحلّل النشا إلى سكريات أبسط كالمالتوز."
        },
        {
            "question": "في الرياضيات، ما المصطلح الذي يصف التطبيق الذي يحافظ على عمليتَي الجمع والضرب بين البنى الجبرية؟",
            "choices": ["التماثل التوبولوجي", "التشاكل", "التماثل الذاتي", "التشاكل الجزئي"],
            "correct_index": 1,
            "explanation": "التشاكل (Homomorphism) هو تطبيق بين بنيتين جبريتين من نفس النوع يحافظ على عملياتهما."
        },
        {
            "question": "ما الحدث الذي أشعل فتيل الحرب العالمية الأولى عام 1914م؟",
            "choices": ["غزو بولندا", "اغتيال الأرشيدوق فرانز فرديناند", "غرق سفينة لوزيتانيا", "توقيع معاهدة فرساي"],
            "correct_index": 1,
            "explanation": "أشعل اغتيال ولي عهد النمسا-المجر الأرشيدوق فرانز فرديناند في سراييفو فتيل الحرب العالمية الأولى."
        },
        {
            "question": "ما نموذج البرمجة الذي يمثّل البيانات والوظائف معًا داخل كيانات تُسمى 'كائنات'؟",
            "choices": ["البرمجة الوظيفية", "البرمجة كائنية التوجه", "البرمجة الإجرائية", "البرمجة المنطقية"],
            "correct_index": 1,
            "explanation": "البرمجة كائنية التوجه (OOP) تعتمد على كائنات تجمع البيانات والوظائف معًا."
        }
    ]
}


# ---------------------------------------------------------------------------
# PDF text extraction — pdfminer (Arabic-aware) with pypdf fallback
# ---------------------------------------------------------------------------

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from a PDF file, with special handling for Arabic.
    
    Strategy:
      1. Try pdfminer.six — best Unicode / Arabic glyph support
      2. Fall back to pypdf if pdfminer fails
      3. Post-process with arabic_reshaper + python-bidi if Arabic detected
    """
    text = _extract_with_pdfminer(pdf_path)
    if not text:
        text = _extract_with_pypdf(pdf_path)

    if text and _is_arabic_text(text):
        text = _reshape_arabic(text)

    return text.strip()


def _extract_with_pdfminer(pdf_path: str) -> str:
    """Use pdfminer.six for robust Unicode / Arabic extraction."""
    try:
        from pdfminer.high_level import extract_text as pdfminer_extract
        text = pdfminer_extract(pdf_path)
        return text or ""
    except Exception as e:
        print(f"[pdfminer] Failed on {pdf_path}: {e}")
        return ""


def _extract_with_pypdf(pdf_path: str) -> str:
    """Fallback: use pypdf for text extraction."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        print(f"[pypdf] Failed on {pdf_path}: {e}")
        return ""


# ---------------------------------------------------------------------------
# Local heuristic quiz generator (Arabic + English)
# ---------------------------------------------------------------------------

def parse_pdf_heuristically(text: str, count: int, difficulty: str) -> list:
    """Extract quiz questions from PDF text using pattern matching.
    Handles both Arabic and English content.
    """
    is_arabic = _is_arabic_text(text)
    questions = []

    # Clean and normalise whitespace
    text = re.sub(r'\s+', ' ', text)

    if is_arabic:
        questions = _heuristic_arabic(text, count)
    else:
        questions = _heuristic_english(text, count)

    # Shuffle and pad with fallback bank if needed
    random.shuffle(questions)
    selected = questions[:count]

    needed = count - len(selected)
    if needed > 0:
        bank = DEFAULT_QUESTION_BANK.get(difficulty, DEFAULT_QUESTION_BANK["Medium"])
        bank_copy = list(bank)
        random.shuffle(bank_copy)
        selected += bank_copy[:needed]

    return selected[:count]


def _heuristic_arabic(text: str, count: int) -> list:
    """Heuristic question extraction for Arabic text."""
    questions = []

    # Split on Arabic sentence endings
    sentences = re.split(r'[.،؟!]\s+', text)

    definitions = []
    fill_blanks = []

    for sent in sentences:
        sent = sent.strip()
        if len(sent) < 20 or len(sent) > 300:
            continue

        # Arabic definition pattern: "X هو/هي/يعني/تعني ..."
        match = re.search(
            r'([\u0600-\u06FF\s]{3,30})\s+(هو|هي|يعني|تعني|يُعرَّف بأنه|تُعرَّف بأنها|يُعرَّف|هي عبارة عن|هو عبارة عن)\s+([\u0600-\u06FF\s،]{10,120})',
            sent
        )
        if match:
            term = match.group(1).strip()
            meaning = match.group(3).strip()
            if term and meaning:
                definitions.append({"term": term, "definition": meaning, "sentence": sent})
                continue

        # Fill-in-the-blank: pick a meaningful Arabic word (4+ letters)
        match_cloze = re.search(r'\b([\u0600-\u06FF]{4,15})\b', sent)
        if match_cloze:
            kw = match_cloze.group(1)
            blanked = sent.replace(kw, "_____", 1)
            fill_blanks.append({"keyword": kw, "blanked": blanked, "sentence": sent})

    # Build definition questions
    for d in definitions:
        q_text = f"وفقًا للمادة الدراسية، ما هو تعريف أو دور '{d['term']}'؟"
        correct_choice = d['definition']
        other_meanings = [x['definition'] for x in definitions if x['term'] != d['term']]
        if len(other_meanings) < 3:
            other_meanings += [
                "حالة مؤقتة من التوازن الكيميائي الحيوي.",
                "أسلوب تحليلي يُستخدم لحساب المتغيرات في النظام.",
                "بروتوكول أساسي طُوِّر لمعايير الأمان.",
                "العنصر الجوهري للبنية التحتية للنظام."
            ]
        choices = [correct_choice] + random.sample(other_meanings, 3)
        random.shuffle(choices)
        correct_idx = choices.index(correct_choice)
        questions.append({
            "question": q_text,
            "choices": [c[:120] + "..." if len(c) > 120 else c for c in choices],
            "correct_index": correct_idx,
            "explanation": f"استنادًا إلى النص: \"{d['sentence']}\""
        })

    # Build fill-in-the-blank questions
    for fb in fill_blanks:
        q_text = f"أكمل الفراغ: \"{fb['blanked']}\""
        correct_choice = fb['keyword']
        other_kws = list(set(x['keyword'] for x in fill_blanks if x['keyword'] != fb['keyword']))
        if len(other_kws) < 3:
            other_kws += ["مفهوم", "تحليل", "نظرية", "متغير", "معامل"]
        choices = [correct_choice] + random.sample(other_kws, 3)
        random.shuffle(choices)
        correct_idx = choices.index(correct_choice)
        questions.append({
            "question": q_text,
            "choices": choices[:4],
            "correct_index": correct_idx,
            "explanation": f"الجملة الكاملة: \"{fb['sentence']}\""
        })

    return questions


def _heuristic_english(text: str, count: int) -> list:
    """Heuristic question extraction for English text."""
    questions = []
    sentences = re.split(r'(?<=[.!?])\s+', text)
    definitions = []
    fill_blanks = []

    for sent in sentences:
        sent = sent.strip()
        if len(sent) < 30 or len(sent) > 200:
            continue

        match = re.search(
            r'\b([A-Z][a-zA-Z0-9\s-]{2,25})\b\s+(is|are|refers to|is defined as|means)\s+([^.!?]+)',
            sent
        )
        if match:
            term = match.group(1).strip()
            meaning = match.group(3).strip()
            if term.lower() not in ["it", "this", "they", "there", "these", "that", "which"]:
                definitions.append({"term": term, "definition": meaning, "sentence": sent})
                continue

        match_cloze = re.search(r'\b([A-Z][a-zA-Z0-9-]{3,15})\b', sent)
        if match_cloze:
            kw = match_cloze.group(1)
            if kw.lower() not in ["the", "this", "that", "with", "from", "when", "what", "where", "whom"]:
                blanked = sent.replace(kw, "_____")
                fill_blanks.append({"keyword": kw, "blanked": blanked, "sentence": sent})

    for d in definitions:
        q_text = f"According to the study material, what is the definition or role of '{d['term']}'?"
        correct_choice = d['definition']
        other_meanings = [x['definition'] for x in definitions if x['term'] != d['term']]
        if len(other_meanings) < 3:
            other_meanings += [
                "A temporary state of biochemical equilibrium.",
                "An analytical method used to calculate variables in a system.",
                "A foundational protocol developed for security standards.",
                "The core element of system infrastructure."
            ]
        choices = [correct_choice] + random.sample(other_meanings, 3)
        random.shuffle(choices)
        correct_idx = choices.index(correct_choice)
        questions.append({
            "question": q_text,
            "choices": [c[:100] + "..." if len(c) > 100 else c for c in choices],
            "correct_index": correct_idx,
            "explanation": f"Based on the text: \"{d['sentence']}\""
        })

    for fb in fill_blanks:
        q_text = f"Fill in the blank: \"{fb['blanked']}\""
        correct_choice = fb['keyword']
        other_kws = list(set(x['keyword'] for x in fill_blanks if x['keyword'] != fb['keyword']))
        if len(other_kws) < 3:
            other_kws += ["Hypothesis", "Synthesis", "Framework", "Variables", "Parameter"]
        choices = [correct_choice] + random.sample(other_kws, 3)
        random.shuffle(choices)
        correct_idx = choices.index(correct_choice)
        questions.append({
            "question": q_text,
            "choices": choices[:4],
            "correct_index": correct_idx,
            "explanation": f"The full sentence is: \"{fb['sentence']}\""
        })

    return questions


# ---------------------------------------------------------------------------
# Gemini API quiz generator (Arabic + English aware)
# ---------------------------------------------------------------------------

def generate_quiz_via_gemini(text: str, count: int, difficulty: str, api_key: str) -> list:
    """Generate quiz using Gemini API. Instructs Gemini to use Arabic if the text is Arabic."""
    is_arabic = _is_arabic_text(text)
    truncated_text = text[:40000]

    if is_arabic:
        lang_instruction = (
            "النص المقدم باللغة العربية. يجب أن تكون جميع الأسئلة والخيارات والشرح باللغة العربية الفصحى."
        )
        difficulty_ar = {"Easy": "سهل", "Medium": "متوسط", "Hard": "صعب"}.get(difficulty, "متوسط")
        prompt = (
            f"أنت خبير تعليمي. قم بإنشاء اختبار دراسي عالي الجودة بناءً على النص التالي.\n"
            f"{lang_instruction}\n"
            f"أنشئ بالضبط {count} سؤالاً من نوع الاختيار المتعدد. مستوى الصعوبة: {difficulty_ar}.\n"
            f"المتطلبات:\n"
            f"1. أعد فقط مصفوفة JSON صالحة من كائنات الأسئلة. لا تضع JSON داخل ```json أو أي تنسيق markdown.\n"
            f"2. يجب أن يحتوي كل كائن سؤال على البنية التالية بالضبط:\n"
            f"   {{\n"
            f"     \"question\": \"نص السؤال هنا\",\n"
            f"     \"choices\": [\"الخيار أ\", \"الخيار ب\", \"الخيار ج\", \"الخيار د\"],\n"
            f"     \"correct_index\": رقم صحيح (0-3) يمثل فهرس الإجابة الصحيحة,\n"
            f"     \"explanation\": \"شرح موجز لماذا هذه الإجابة صحيحة\"\n"
            f"   }}\n"
            f"النص:\n{truncated_text}"
        )
    else:
        prompt = (
            f"You are an expert AI educator. Generate a high-quality study quiz based on the following text.\n"
            f"Generate exactly {count} multiple choice questions. Difficulty level: {difficulty}.\n"
            f"Requirements:\n"
            f"1. Return ONLY a valid JSON array of question objects. Do NOT wrap the JSON in ```json or any markdown formatting.\n"
            f"2. Each question object must have exactly the following structure:\n"
            f"   {{\n"
            f"     \"question\": \"Question text here\",\n"
            f"     \"choices\": [\"Option A\", \"Option B\", \"Option C\", \"Option D\"],\n"
            f"     \"correct_index\": integer index (0-3) of the correct choice,\n"
            f"     \"explanation\": \"Brief explanation of why this answer is correct\"\n"
            f"   }}\n"
            f"Text:\n{truncated_text}"
        )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }
    req_body = json.dumps(data).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=req_body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=45) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            text_response = res_data['candidates'][0]['content']['parts'][0]['text'].strip()

            # Strip markdown code fences if present
            if text_response.startswith("```"):
                lines = text_response.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                text_response = "\n".join(lines).strip()

            parsed_questions = json.loads(text_response)

            if isinstance(parsed_questions, list) and len(parsed_questions) > 0:
                validated = []
                for q in parsed_questions:
                    if "question" in q and "choices" in q and "correct_index" in q:
                        none_label = "لا شيء مما سبق" if is_arabic else "None of the above"
                        while len(q["choices"]) < 4:
                            q["choices"].append(none_label)
                        q["choices"] = q["choices"][:4]
                        validated.append({
                            "question": q["question"],
                            "choices": q["choices"],
                            "correct_index": int(q["correct_index"]),
                            "explanation": q.get("explanation", "استناداً إلى محتوى النص." if is_arabic else "Based on the text contents.")
                        })
                if validated:
                    return validated[:count]

    except Exception as e:
        print(f"Gemini API failed: {e}. Falling back to local heuristic generator.")

    return parse_pdf_heuristically(text, count, difficulty)


# ---------------------------------------------------------------------------
# Translation helper — Arabic text → English via Gemini
# ---------------------------------------------------------------------------

def translate_text_to_english(text: str, api_key: str) -> str:
    """Translate Arabic text to English using the Gemini API.
    
    Falls back to the original text if the API call fails.
    """
    if not text or not _is_arabic_text(text):
        return text  # Already English or empty
    
    truncated = text[:30000]  # Stay within token limits
    prompt = (
        "Translate the following Arabic text to clear, fluent English. "
        "Return ONLY the translated text, no explanations or formatting.\n\n"
        f"{truncated}"
    )

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1}
    }
    req_body = json.dumps(data).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=req_body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=60) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            translated = res_data['candidates'][0]['content']['parts'][0]['text'].strip()
            print(f"[translate] Successfully translated {len(text)} chars to English.")
            return translated
    except Exception as e:
        print(f"[translate] Translation failed: {e}. Using original text.")
        return text  # Graceful fallback


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def generate_quiz(
    pdf_path: str,
    count: int,
    difficulty: str,
    api_key: str = None,
    language_mode: str = "auto",
    pre_extracted_text: str = None
) -> list:
    """Generate a quiz from a PDF file (or general knowledge if no file given).
    
    Args:
        pdf_path: Local path to a PDF file (already downloaded from GCS).
        count: Number of questions to generate.
        difficulty: 'Easy' | 'Medium' | 'Hard'
        api_key: Optional Gemini API key for AI-powered generation.
        language_mode: 'auto' | 'arabic' | 'translate' — controls question language.
        pre_extracted_text: If provided, skips PDF reading and uses this text directly.
                            Used when Arabic text has already been translated externally.
    """
    # Use pre-extracted text if supplied (e.g., already translated Arabic)
    if pre_extracted_text:
        text = pre_extracted_text
    elif pdf_path:
        text = extract_text_from_pdf(pdf_path)
    else:
        text = ""

    if not text:
        bank = DEFAULT_QUESTION_BANK.get(difficulty, DEFAULT_QUESTION_BANK["Medium"])
        bank_copy = list(bank)
        random.shuffle(bank_copy)
        while len(bank_copy) < count:
            bank_copy += bank_copy
        return bank_copy[:count]

    if api_key:
        return generate_quiz_via_gemini(text, count, difficulty, api_key)
    else:
        return parse_pdf_heuristically(text, count, difficulty)
