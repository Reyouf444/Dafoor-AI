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
# Sentence-BERT (SBERT) Semantic Ranking & Noise Filtering Engine
# Uses lightweight 'all-MiniLM-L6-v2' (~80MB) for fast CPU execution
# ---------------------------------------------------------------------------

_sbert_model = None

def _get_sbert_model():
    global _sbert_model
    if _sbert_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _sbert_model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            print(f"Notice: sentence-transformers SBERT model unavailable ({e}). Using rule-based semantic filter.")
            _sbert_model = False
    return _sbert_model if _sbert_model is not False else None


def _is_meaningful_sentence(sent: str) -> bool:
    """Filter out noisy, trivial, pronoun-heavy, and boilerplate filler sentences."""
    s = sent.strip()
    if len(s) < 25 or len(s) > 250:
        return False

    words = s.split()
    if len(words) < 5:
        return False

    first_word = words[0].lower().strip(".,;:!?\"'()")
    # Exclude sentences starting with low-quality filler pronouns or meaningless noise
    trivial_starts = {
        "you", "he", "she", "her", "him", "his", "hers", "them", "they",
        "it", "its", "we", "us", "our", "me", "my", "myself", "yourself",
        "himself", "herself", "themselves", "this", "these", "those", "that",
        "who", "whom", "whose", "which", "what", "where", "when", "why", "how"
    }
    if first_word in trivial_starts:
        return False

    # Count filler pronoun density
    pronoun_count = sum(1 for w in words if w.lower().strip(".,;:!?\"'()") in trivial_starts)
    if pronoun_count / len(words) > 0.25:
        return False

    # Filter out common header/footer/page number patterns
    if re.search(r'^(page|\d+|chapter|figure|table|contents|index|copyright|all rights reserved)\b', s, re.I):
        return False

    # Filter out legal/boilerplate/disclaimer text
    s_lower = s.lower()
    boilerplate_phrases = [
        "all rights reserved", "provided on an", "as is", "without warranty",
        "no liability", "disclaimer", "terms of use", "terms and conditions",
        "permission is granted", "may not be reproduced", "proprietary",
        "confidential", "trade secret", "published by", "printed in",
        "isbn", "edition", "acknowledgment", "about the author",
        "table of contents", "visit us at", "www.", "http://", "https://",
        ".com", ".org", ".net", "click here", "for more information",
        "unauthorized", "written permission", "redistributed",
    ]
    for phrase in boilerplate_phrases:
        if phrase in s_lower:
            return False

    return True


def _is_quality_term(term: str) -> bool:
    """Check if a matched term is a real concept, not an article/filler phrase."""
    t = term.strip()
    if len(t) < 3:
        return False
    first_word = t.split()[0].lower() if t.split() else ""
    # Reject terms that start with articles, prepositions, or common filler
    bad_starts = {
        "the", "a", "an", "some", "any", "all", "each", "every",
        "no", "not", "but", "and", "or", "if", "so", "for",
        "in", "on", "at", "to", "of", "by", "as", "up", "out",
        "its", "our", "your", "my", "his", "her", "their",
    }
    if first_word in bad_starts:
        return False
    # Reject purely lowercase terms (not a proper noun or acronym)
    if t[0].islower():
        return False
    # Reject single very common words
    single_rejects = {
        "information", "data", "example", "note", "result", "value",
        "section", "part", "step", "point", "list", "name", "type",
    }
    if t.lower() in single_rejects:
        return False
    return True


def _sbert_rank_sentences(text: str, top_k: int = 35) -> list:
    """Rank candidate sentences by semantic centrality using Sentence-BERT embeddings."""
    raw_sentences = re.split(r'(?<=[.!?\n])\s+', text)
    clean_candidates = [s.strip() for s in raw_sentences if _is_meaningful_sentence(s)]

    if not clean_candidates:
        return [s.strip() for s in raw_sentences if len(s.strip()) > 30][:top_k]

    model = _get_sbert_model()
    if not model:
        return clean_candidates[:top_k]

    try:
        import numpy as np
        # Compute SBERT embeddings for candidate sentences
        embeddings = model.encode(clean_candidates, convert_to_numpy=True, show_progress_bar=False)
        
        # Calculate overall document centroid embedding
        doc_centroid = np.mean(embeddings, axis=0, keepdims=True)
        
        # Compute Cosine Similarities between sentence embeddings and document centroid
        norm_emb = embeddings / (np.linalg.norm(embeddings, axis=1, keepdims=True) + 1e-9)
        norm_centroid = doc_centroid / (np.linalg.norm(doc_centroid, axis=1, keepdims=True) + 1e-9)
        scores = np.dot(norm_emb, norm_centroid.T).flatten()

        # Sort sentences by semantic importance score (highest first)
        ranked_indices = np.argsort(-scores)
        ranked_sentences = [clean_candidates[idx] for idx in ranked_indices[:top_k]]
        return ranked_sentences
    except Exception as e:
        print(f"SBERT ranking fallback: {e}")
        return clean_candidates[:top_k]


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
    """SBERT-enhanced question extraction for English text."""
    questions = []
    sentences = _sbert_rank_sentences(text, top_k=40)
    definitions = []
    fill_blanks = []

    trivial_words = {
        "it", "this", "they", "there", "these", "that", "which", "you", "she", "he",
        "her", "him", "his", "hers", "them", "we", "us", "our", "the", "with", "from"
    }

    for sent in sentences:
        match = re.search(
            r'\b([A-Z][a-zA-Z0-9\s-]{2,25})\b\s+(is|are|refers to|is defined as|means)\s+([^.!?]+)',
            sent
        )
        if match:
            term = match.group(1).strip()
            meaning = match.group(3).strip()
            if _is_quality_term(term) and len(meaning) >= 10:
                definitions.append({"term": term, "definition": meaning, "sentence": sent})
                continue

        match_cloze = re.search(r'\b([A-Z][a-zA-Z0-9-]{3,15})\b', sent)
        if match_cloze:
            kw = match_cloze.group(1)
            if _is_quality_term(kw):
                blanked = sent.replace(kw, "_____", 1)
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

def generate_quiz_via_gemini(text: str, count: int, difficulty: str, api_key: str, question_types: list = None) -> list:
    """Generate quiz using Gemini API with support for multiple question types."""
    is_arabic = _is_arabic_text(text)
    truncated_text = text[:40000]

    # Normalize question_types
    if not question_types:
        question_types = ["mcq"]
    if "mixed" in question_types:
        question_types = ["mcq", "truefalse", "fillblank"]

    # Build type description for the prompt
    if is_arabic:
        type_map = {"mcq": "اختيار متعدد (4 خيارات)", "truefalse": "صح أو خطأ", "fillblank": "أكمل الفراغ"}
        type_list_str = " و ".join(type_map[t] for t in question_types if t in type_map)
        difficulty_ar = {"Easy": "سهل", "Medium": "متوسط", "Hard": "صعب"}.get(difficulty, "متوسط")
        type_schema = """كل كائن سؤال يجب أن يحتوي على:
- "type": نوع السؤال: "mcq" أو "truefalse" أو "fillblank"
- "question": نص السؤال (لنوع أكمل الفراغ، استخدم ___ مكان الإجابة)
- "choices": مصفوفة الخيارات (4 خيارات لـ mcq، ["صح", "خطأ"] لـ truefalse، مصفوفة فارغة [] لـ fillblank)
- "correct_index": رقم صحيح (0-3 لـ mcq، 0 أو 1 لـ truefalse، -1 لـ fillblank)
- "correct_answer_text": الإجابة الدقيقة كنص (فقط لـ fillblank، وإلا "")
- "explanation": شرح موجز"""
        prompt = (
            f"أنت خبير تعليمي. أنشئ اختباراً دراسياً عالي الجودة بناءً على النص التالي.\n"
            f"النص المقدم باللغة العربية. يجب أن تكون جميع الأسئلة والخيارات والشرح باللغة العربية الفصحى.\n"
            f"أنشئ بالضبط {count} سؤالاً من أنواع: {type_list_str}. مستوى الصعوبة: {difficulty_ar}.\n"
            f"وزّع الأسئلة بالتساوي بين الأنواع المطلوبة.\n"
            f"أعد فقط مصفوفة JSON صالحة. لا تضعها داخل ```json.\n"
            f"{type_schema}\n"
            f"النص:\n{truncated_text}"
        )
    else:
        type_map = {"mcq": "multiple choice (4 options)", "truefalse": "true/false", "fillblank": "fill in the blank"}
        type_list_str = " and ".join(type_map[t] for t in question_types if t in type_map)
        type_schema = """Each question object must have:
- "type": "mcq" | "truefalse" | "fillblank"
- "question": question text (for fillblank, use ___ where the answer goes)
- "choices": ["Option A","Option B","Option C","Option D"] for mcq, ["True","False"] for truefalse, [] for fillblank
- "correct_index": 0-3 for mcq, 0 or 1 for truefalse, -1 for fillblank
- "correct_answer_text": exact expected answer string for fillblank only, else ""
- "explanation": brief explanation"""
        prompt = (
            f"You are an expert AI educator. Generate a high-quality study quiz based on the following text.\n"
            f"Generate exactly {count} questions using these types: {type_list_str}. Difficulty: {difficulty}.\n"
            f"Distribute questions evenly across the requested types.\n"
            f"Return ONLY a valid JSON array. Do NOT wrap in ```json or any markdown.\n"
            f"{type_schema}\n"
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

            if text_response.startswith("```"):
                lines = text_response.splitlines()
                if lines[0].startswith("```"): lines = lines[1:]
                if lines and lines[-1].startswith("```"): lines = lines[:-1]
                text_response = "\n".join(lines).strip()

            parsed_questions = json.loads(text_response)

            if isinstance(parsed_questions, list) and len(parsed_questions) > 0:
                validated = []
                none_label = "لا شيء مما سبق" if is_arabic else "None of the above"
                for q in parsed_questions:
                    if "question" not in q or "type" not in q:
                        continue
                    qtype = q.get("type", "mcq")
                    if qtype == "mcq":
                        if "choices" not in q or "correct_index" not in q:
                            continue
                        choices = list(q["choices"])
                        while len(choices) < 4: choices.append(none_label)
                        validated.append({
                            "type": "mcq",
                            "question": q["question"],
                            "choices": choices[:4],
                            "correct_index": int(q["correct_index"]),
                            "correct_answer_text": "",
                            "explanation": q.get("explanation", "Based on the text." if not is_arabic else "استناداً للنص.")
                        })
                    elif qtype == "truefalse":
                        if "correct_index" not in q:
                            continue
                        tf_choices = ["صح", "خطأ"] if is_arabic else ["True", "False"]
                        validated.append({
                            "type": "truefalse",
                            "question": q["question"],
                            "choices": tf_choices,
                            "correct_index": int(q["correct_index"]),
                            "correct_answer_text": "",
                            "explanation": q.get("explanation", "")
                        })
                    elif qtype == "fillblank":
                        ans_text = str(q.get("correct_answer_text", "")).strip()
                        if not ans_text:
                            continue
                        validated.append({
                            "type": "fillblank",
                            "question": q["question"],
                            "choices": [],
                            "correct_index": -1,
                            "correct_answer_text": ans_text,
                            "explanation": q.get("explanation", "")
                        })
                if validated:
                    return validated[:count]

    except Exception as e:
        print(f"Gemini API failed: {e}. Falling back to local heuristic generator.")

    # Heuristic fallback — all MCQ, add type/correct_answer_text fields
    fallback = parse_pdf_heuristically(text, count, difficulty)
    for q in fallback:
        if "type" not in q: q["type"] = "mcq"
        if "correct_answer_text" not in q: q["correct_answer_text"] = ""
    return fallback


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
    pre_extracted_text: str = None,
    question_types: list = None,
) -> list:
    """Generate a quiz from a PDF file (or general knowledge if no file given).
    
    Args:
        pdf_path: Local path to a PDF file (already downloaded from GCS).
        count: Number of questions to generate.
        difficulty: 'Easy' | 'Medium' | 'Hard'
        api_key: Optional Gemini API key for AI-powered generation.
        language_mode: 'auto' | 'arabic' | 'translate' — controls question language.
        pre_extracted_text: If provided, skips PDF reading and uses this text directly.
        question_types: List of types to generate: 'mcq', 'truefalse', 'fillblank', 'mixed'.
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
        result = bank_copy[:count]
        for q in result:
            if "type" not in q: q["type"] = "mcq"
            if "correct_answer_text" not in q: q["correct_answer_text"] = ""
        return result

    if api_key:
        return generate_quiz_via_gemini(text, count, difficulty, api_key, question_types=question_types)
    else:
        fallback = parse_pdf_heuristically(text, count, difficulty)
        for q in fallback:
            if "type" not in q: q["type"] = "mcq"
            if "correct_answer_text" not in q: q["correct_answer_text"] = ""
        return fallback


# ---------------------------------------------------------------------------
# Flashcard generator — term/definition pairs via Gemini
# ---------------------------------------------------------------------------

def generate_flashcards(text: str, count: int = 20, api_key: str = None) -> list:
    """Generate flashcard term/definition pairs from text using Gemini.
    
    Falls back to heuristic extraction if no API key or Gemini fails.
    Returns: [{"front": "term", "back": "definition"}, ...]
    """
    if not text or len(text) < 50:
        return []

    is_arabic = _is_arabic_text(text)
    truncated_text = text[:40000]

    if api_key:
        if is_arabic:
            prompt = (
                f"أنت خبير تعليمي. استخرج {count} مصطلحاً وتعريفاً من النص التالي لإنشاء بطاقات دراسية.\n"
                f"أعد فقط مصفوفة JSON صالحة. لا تضعها داخل ```json.\n"
                f"كل كائن يجب أن يحتوي على:\n"
                f'- "front": المصطلح أو المفهوم الرئيسي (موجز، 1-5 كلمات)\n'
                f'- "back": التعريف أو الشرح (جملة أو جملتان)\n'
                f"النص:\n{truncated_text}"
            )
        else:
            prompt = (
                f"You are an expert educator. Extract {count} key terms and definitions from the following text to create study flashcards.\n"
                f"Return ONLY a valid JSON array. Do NOT wrap in ```json or any markdown.\n"
                f"Each object must have:\n"
                f'- "front": The key term or concept (concise, 1-5 words)\n'
                f'- "back": The definition or explanation (1-2 sentences)\n'
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

                if text_response.startswith("```"):
                    lines = text_response.splitlines()
                    if lines[0].startswith("```"): lines = lines[1:]
                    if lines and lines[-1].startswith("```"): lines = lines[:-1]
                    text_response = "\n".join(lines).strip()

                parsed = json.loads(text_response)
                if isinstance(parsed, list):
                    cards = [
                        {"front": str(item["front"]).strip(), "back": str(item["back"]).strip()}
                        for item in parsed if "front" in item and "back" in item
                    ]
                    if cards:
                        return cards[:count]
        except Exception as e:
            print(f"Gemini flashcard generation failed: {e}. Falling back to heuristic.")

    # Heuristic fallback
    return _heuristic_flashcards(text, count, is_arabic)


def _heuristic_flashcards(text: str, count: int, is_arabic: bool) -> list:
    """Extract term/definition pairs using quality filters and smart extraction."""
    cards = []
    seen_terms = set()  # Prevent duplicate terms
    top_sentences = _sbert_rank_sentences(text, top_k=60)

    if is_arabic:
        pattern = re.compile(
            r'([\u0600-\u06FF\s]{3,30})\s+(هو|هي|يعني|تعني|يُعرَّف بأنه|هي عبارة عن)\s+([\u0600-\u06FF\s،.]{10,150})'
        )
        for s in top_sentences:
            match = pattern.search(s)
            if match:
                term = match.group(1).strip()
                definition = match.group(3).strip()
                if len(term) > 2 and len(definition) > 10 and term not in seen_terms:
                    cards.append({"front": term, "back": definition})
                    seen_terms.add(term)
            if len(cards) >= count:
                break
    else:
        # Step 1: Extract clean term/definition pairs from "X is/are/means Y" patterns
        pattern = re.compile(
            r'\b([A-Z][a-zA-Z0-9\s-]{2,30})\b\s+(is|are|refers to|is defined as|means)\s+([^.!?]{10,150})'
        )
        for s in top_sentences:
            match = pattern.search(s)
            if match:
                term = match.group(1).strip()
                definition = match.group(3).strip()
                if _is_quality_term(term) and len(definition) > 10 and term.lower() not in seen_terms:
                    cards.append({"front": term, "back": definition})
                    seen_terms.add(term.lower())
            if len(cards) >= count:
                break

        # Step 2: Extract "Term: definition" colon-separated pairs
        if len(cards) < count:
            for s in top_sentences:
                if len(cards) >= count:
                    break
                parts = s.split(':', 1)
                if len(parts) == 2:
                    t = parts[0].strip()
                    d = parts[1].strip()
                    if _is_quality_term(t) and 3 <= len(t) <= 40 and len(d) >= 15 and t.lower() not in seen_terms:
                        cards.append({"front": t, "back": d})
                        seen_terms.add(t.lower())

        # Step 3: Extract key technical terms from sentences and use the sentence as the definition
        if len(cards) < count:
            # Find capitalized multi-word terms or acronyms in sentences
            term_pattern = re.compile(r'\b([A-Z][a-zA-Z]{2,}(?:\s[A-Z][a-zA-Z]+){0,3})\b')
            acronym_pattern = re.compile(r'\b([A-Z]{2,6})\b')
            for s in top_sentences:
                if len(cards) >= count:
                    break
                # Try multi-word proper noun terms first
                term_match = term_pattern.search(s)
                if term_match:
                    term = term_match.group(1).strip()
                    if _is_quality_term(term) and term.lower() not in seen_terms:
                        # Use the full sentence as the definition/explanation
                        cards.append({"front": term, "back": s.strip()})
                        seen_terms.add(term.lower())
                        continue
                # Try acronyms (e.g. TCP, VLAN, OSPF)
                acr_match = acronym_pattern.search(s)
                if acr_match:
                    acr = acr_match.group(1).strip()
                    if len(acr) >= 2 and acr not in seen_terms and acr not in {"THE", "AND", "FOR", "NOT", "BUT", "ALL", "ANY"}:
                        cards.append({"front": acr, "back": s.strip()})
                        seen_terms.add(acr)

    return cards[:count]
