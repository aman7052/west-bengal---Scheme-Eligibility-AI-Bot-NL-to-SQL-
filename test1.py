import psycopg2
import ollama
import json

# 1. Memory Store - Sab kuch yahan save rahega
REQUIRED_FIELDS = ['gender', 'age', 'education', 'occupation', 'income', 'marital_status']
user_data = {field: None for field in REQUIRED_FIELDS}

def get_db_connection():
    return psycopg2.connect(
        dbname="demodb", user="postgres", password="705219", host="localhost", port="5432"
    )

# --- AI Extraction (Improved for Hinglish & Memory) ---
def extract_entities(user_input):
    prompt = f"""
    You are a data extractor. 
    User said: "{user_input}"
    Current Memory: {user_data}

    Task:
    - Extract age (as number), gender, occupation, income, and education.
    - If user says '20 saal', age is 20. If 'student', occupation is 'student'.
    - If user asks about general topics (history, science, etc.), set "out_of_scope": true.
    
    Return ONLY JSON.
    """
    try:
        response = ollama.generate(model='llama3', prompt=prompt, format='json')
        return json.loads(response['response'])
    except:
        return {}

# --- Strict SQL Logic (Sirf Eligible Schemes dikhayega) ---
def run_eligible_query():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Base query: Jahan saari conditions match karein
        query = "SELECT * FROM wb_schemes WHERE 1=1"
        params = []

        # 1. Age Filter (Sabse zaroori: Agar 20 hai toh 60 wali scheme filter out ho jayegi)
        if user_data['age'] is not None:
            query += " AND %s >= min_age AND %s <= max_age"
            params.extend([user_data['age'], user_data['age']])

        # 2. Gender Filter
        if user_data['gender']:
            query += " AND LOWER(gender) = LOWER(%s)"
            params.append(user_data['gender'])

        # 3. Occupation Filter
        if user_data['occupation']:
            query += " AND (LOWER(occupation) = LOWER(%s) OR LOWER(occupation) = 'any')"
            params.append(user_data['occupation'])

        # 4. Income Filter
        if user_data['income'] is not None:
            query += " AND %s <= max_income"
            params.append(user_data['income'])

        # 5. Marital Status (Widow pension ko block karne ke liye)
        if user_data['marital_status']:
            query += " AND (LOWER(marital_status) = LOWER(%s) OR LOWER(marital_status) = 'any')"
            params.append(user_data['marital_status'])
        else:
            # Agar user ne kuch nahi bola, toh widow schemes mat dikhao
            query += " AND LOWER(marital_status) != 'widow'"

        cursor.execute(query, tuple(params))
        results = cursor.fetchall()
        conn.close()
        return results
    except Exception as e:
        return []

# --- Main Bot Loop ---
def start_smart_bot():
    print("Bot: System Ready. ")
    
    while True:
        user_input = input("\nUser: ").strip()
        if not user_input: continue

        # 1. Extract Details
        extracted = extract_entities(user_input)
        
        # 2. Scope Guard (History/GK ignore karne ke liye)
        if extracted.get('out_of_scope'):
            print("Bot: Not Found.")
            continue

        # 3. Update Memory (Purani baatein yaad rakhega)
        for field in REQUIRED_FIELDS:
            if extracted.get(field) is not None:
                user_data[field] = extracted[field]
        
        # 4. Show RESULTS (Sirf Eligible wali)
        results = run_eligible_query()
        
        if results:
            print(f"\n[Bot]: Based on your profile (Age: {user_data['age']}, Gender: {user_data['gender']},), you are eligible for:")
            for row in results:
                print(f" - {row[1]}") # scheme_name
        else:
            print("\nBot: Not Found.")

if __name__ == "__main__":
    start_smart_bot()