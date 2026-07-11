import re
import random
import json
import urllib.request
import urllib.error
from pypdf import PdfReader

# Default high-quality quiz fallback banks (divided by difficulty)
DEFAULT_QUESTION_BANK = {
    "Easy": [
        {
            "question": "What is the primary function of red blood cells in the human body?",
            "choices": ["To fight infections", "To transport oxygen", "To help blood clot", "To produce hormones"],
            "correct_index": 1,
            "explanation": "Red blood cells contain hemoglobin, which binds to oxygen and carries it from the lungs to the rest of the body."
        },
        {
            "question": "Which planet in our solar system is known as the Red Planet?",
            "choices": ["Venus", "Mars", "Jupiter", "Saturn"],
            "correct_index": 1,
            "explanation": "Mars is referred to as the Red Planet due to the iron oxide (rust) on its surface, which gives it a reddish appearance."
        },
        {
            "question": "What is the chemical symbol for water?",
            "choices": ["CO2", "H2O", "NaCl", "O2"],
            "correct_index": 1,
            "explanation": "Water is composed of two hydrogen atoms bonded to one oxygen atom, represented as H2O."
        },
        {
            "question": "Who wrote the play 'Romeo and Juliet'?",
            "choices": ["Charles Dickens", "William Shakespeare", "Mark Twain", "Jane Austen"],
            "correct_index": 1,
            "explanation": "William Shakespeare wrote the famous tragedy 'Romeo and Juliet' in the late 16th century."
        },
        {
            "question": "Which of the following is a prime number?",
            "choices": ["4", "9", "13", "15"],
            "correct_index": 2,
            "explanation": "A prime number is only divisible by 1 and itself. 13 has no other factors, unlike 4, 9, and 15."
        }
    ],
    "Medium": [
        {
            "question": "What is the term for the process by which plants convert sunlight into chemical energy?",
            "choices": ["Respiration", "Photosynthesis", "Fermentation", "Transpiration"],
            "correct_index": 1,
            "explanation": "Photosynthesis is the process used by plants, algae, and certain bacteria to harness energy from sunlight and turn it into chemical energy."
        },
        {
            "question": "Which gas is the most abundant in Earth's atmosphere?",
            "choices": ["Oxygen", "Carbon Dioxide", "Nitrogen", "Argon"],
            "correct_index": 2,
            "explanation": "Nitrogen makes up approximately 78% of the Earth's atmosphere, followed by oxygen at 21%."
        },
        {
            "question": "In computer science, what does 'CPU' stand for?",
            "choices": ["Computer Processing Unit", "Central Processing Unit", "Core Processing Utility", "Central Power Unit"],
            "correct_index": 1,
            "explanation": "CPU stands for Central Processing Unit. It is the primary component of a computer that performs instructions of a computer program."
        },
        {
            "question": "Which historical document was signed in 1215 and limited the power of the English monarchy?",
            "choices": ["The Declaration of Independence", "The Magna Carta", "The Bill of Rights", "The Treaty of Versailles"],
            "correct_index": 1,
            "explanation": "The Magna Carta ('Great Charter') was signed by King John in 1215, establishing the principle that everyone, including the king, is subject to the law."
        },
        {
            "question": "What is the speed of light in a vacuum, approximately?",
            "choices": ["300,000 km/s", "150,000 km/s", "1,000,000 km/s", "30,000 km/s"],
            "correct_index": 0,
            "explanation": "The speed of light in a vacuum is approximately 299,792 kilometers per second (commonly rounded to 300,000 km/s)."
        }
    ],
    "Hard": [
        {
            "question": "Which subatomic particle is not composed of quarks?",
            "choices": ["Proton", "Neutron", "Electron", "Baryon"],
            "correct_index": 2,
            "explanation": "Electrons are leptons, which are fundamental particles. Protons and neutrons are baryons and are composed of quarks."
        },
        {
            "question": "In what year did the Western Roman Empire officially fall?",
            "choices": ["325 AD", "476 AD", "1453 AD", "1066 AD"],
            "correct_index": 1,
            "explanation": "The Western Roman Empire fell in 476 AD when Romulus Augustulus was deposed by Odoacer, a Germanic chieftain."
        },
        {
            "question": "What is the function of the enzyme 'Amylase' in human digestion?",
            "choices": ["To digest proteins", "To digest lipids", "To break down starches into sugars", "To emulsify fats"],
            "correct_index": 2,
            "explanation": "Amylase, present in saliva and pancreatic juice, catalyzes the breakdown of starch into simpler sugars like maltose."
        },
        {
            "question": "Which programming language paradigm is centered on 'objects' that contain both data and methods?",
            "choices": ["Functional Programming", "Object-Oriented Programming", "Procedural Programming", "Logical Programming"],
            "correct_index": 1,
            "explanation": "Object-Oriented Programming (OOP) is a paradigm based on the concept of 'objects', which can contain data (attributes) and code (methods)."
        },
        {
            "question": "What is the mathematical term for a mapping that preserves the operations of addition and multiplication between algebraic structures?",
            "choices": ["Homeomorphism", "Isomorphism", "Automorphism", "Homomorphism"],
            "correct_index": 3,
            "explanation": "A homomorphism is a map between two algebraic structures of the same type (like groups or rings) that preserves the operations."
        }
    ]
}

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text contents from a PDF file."""
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
        return ""

def parse_pdf_heuristically(text: str, count: int, difficulty: str) -> list:
    """Analyze the text and extract dynamic questions based on definitions and key terms."""
    questions = []
    
    # 1. Clean and normalize text
    text = re.sub(r'\s+', ' ', text)
    
    # 2. Extract potential definitions: 'A [Noun] is [definition]' or '[Noun] refers to [definition]'
    # Let's search for keywords
    sentences = re.split(r'(?<=[.!?])\s+', text)
    
    definitions = []
    fill_blanks = []
    
    # Filter and find interesting sentences
    for sent in sentences:
        sent = sent.strip()
        if len(sent) < 30 or len(sent) > 200:
            continue
            
        # Match definitions
        # Pattern like: "Mitosis is a process of..."
        match = re.search(r'\b([A-Z][a-zA-Z0-9\s-]{2,25})\b\s+(is|are|refers to|is defined as|means)\s+([^.!?]+)', sent)
        if match:
            term = match.group(1).strip()
            meaning = match.group(3).strip()
            # Ignore common pronouns/generic words
            if term.lower() not in ["it", "this", "they", "there", "these", "that", "which"]:
                definitions.append({
                    "term": term,
                    "definition": meaning,
                    "sentence": sent
                })
                continue
                
        # If not a definition, look for potential cloze/fill in the blanks
        # Find capitalized nouns/terms that we can blank out
        match_cloze = re.search(r'\b([A-Z][a-zA-Z0-9-]{3,15})\b', sent)
        if match_cloze:
            kw = match_cloze.group(1)
            # Find a sentence with this keyword and blank it out
            if kw.lower() not in ["the", "this", "that", "with", "from", "when", "what", "where", "whom"]:
                blanked = sent.replace(kw, "_____")
                fill_blanks.append({
                    "keyword": kw,
                    "blanked": blanked,
                    "sentence": sent
                })
                
    # Compile questions
    all_extracted_questions = []
    
    # Process definitions
    for d in definitions:
        # Create a definition question: "What is [term]?" or "Which of the following best defines [term]?"
        q_text = f"According to the study material, what is the definition or role of '{d['term']}'?"
        correct_choice = d['definition']
        
        # Get distractors from other definitions or custom options
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
        
        all_extracted_questions.append({
            "question": q_text,
            "choices": [c[:100] + "..." if len(c) > 100 else c for c in choices],
            "correct_index": correct_idx,
            "explanation": f"Based on the text: \"{d['sentence']}\""
        })
        
    # Process fill-in-the-blanks
    for fb in fill_blanks:
        q_text = f"Fill in the blank: \"{fb['blanked']}\""
        correct_choice = fb['keyword']
        
        other_kws = [x['keyword'] for x in fill_blanks if x['keyword'] != fb['keyword']]
        # Deduplicate
        other_kws = list(set(other_kws))
        if len(other_kws) < 3:
            other_kws += ["Hypothesis", "Synthesis", "Framework", "Variables", "Parameter"]
            
        choices = [correct_choice] + random.sample(other_kws, 3)
        random.shuffle(choices)
        correct_idx = choices.index(correct_choice)
        
        all_extracted_questions.append({
            "question": q_text,
            "choices": choices[:4],
            "correct_index": correct_idx,
            "explanation": f"The full sentence is: \"{fb['sentence']}\""
        })

    # Shuffle extracted questions
    random.shuffle(all_extracted_questions)
    
    # Take what we can get
    selected_questions = all_extracted_questions[:count]
    
    # If we don't have enough questions from the PDF, pad them using the default bank
    needed = count - len(selected_questions)
    if needed > 0:
        bank = DEFAULT_QUESTION_BANK.get(difficulty, DEFAULT_QUESTION_BANK["Medium"])
        # Avoid running out of bank questions
        bank_copy = list(bank)
        random.shuffle(bank_copy)
        selected_questions += bank_copy[:needed]
        
    return selected_questions[:count]

def generate_quiz_via_gemini(text: str, count: int, difficulty: str, api_key: str) -> list:
    """Generate quiz using Gemini API via standard Python urllib (no external dependencies)."""
    # Truncate text if too long to fit in standard request safely (e.g. limit to first ~10000 words)
    truncated_text = text[:40000]
    
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
    
    # Construct Gemini REST API URL
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # Request body structure
    data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    
    req_body = json.dumps(data).encode("utf-8")
    
    try:
        req = urllib.request.Request(url, data=req_body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            
            # Extract text response from Gemini structure
            text_response = res_data['candidates'][0]['content']['parts'][0]['text']
            
            # Clean possible markdown block wraps
            text_response = text_response.strip()
            if text_response.startswith("```"):
                # strip out ```json and ```
                lines = text_response.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                text_response = "\n".join(lines).strip()
                
            parsed_questions = json.loads(text_response)
            
            if isinstance(parsed_questions, list) and len(parsed_questions) > 0:
                # Basic validation
                validated = []
                for q in parsed_questions:
                    if "question" in q and "choices" in q and "correct_index" in q:
                        # Ensure 4 choices
                        while len(q["choices"]) < 4:
                            q["choices"].append("None of the above")
                        q["choices"] = q["choices"][:4]
                        validated.append({
                            "question": q["question"],
                            "choices": q["choices"],
                            "correct_index": int(q["correct_index"]),
                            "explanation": q.get("explanation", "Based on the text contents.")
                        })
                if validated:
                    return validated[:count]
                    
    except Exception as e:
        print(f"Failed to generate quiz via Gemini API: {e}. Falling back to local heuristic generator.")
        
    # Fallback to heuristic
    return parse_pdf_heuristically(text, count, difficulty)

def generate_quiz(pdf_path: str, count: int, difficulty: str, api_key: str = None) -> list:
    """Main function to generate a quiz from a PDF file path."""
    text = ""
    if pdf_path:
        text = extract_text_from_pdf(pdf_path)
        
    if not text:
        # Fall back directly to default question bank if no text found or no file uploaded
        bank = DEFAULT_QUESTION_BANK.get(difficulty, DEFAULT_QUESTION_BANK["Medium"])
        bank_copy = list(bank)
        random.shuffle(bank_copy)
        # Pad if count is higher than bank size
        while len(bank_copy) < count:
            bank_copy += bank_copy
        return bank_copy[:count]
        
    if api_key:
        return generate_quiz_via_gemini(text, count, difficulty, api_key)
    else:
        return parse_pdf_heuristically(text, count, difficulty)
