import psycopg2
import ollama
import json

# 1. Memory Store (This will remember the data until the session ends)
REQUIRED_FIELDS = ['gender', 'age', 'education', 'occupation', 'income']
user_data = {field: None for field in REQUIRED_FIELDS}

def get_db_connection():
    return psycopg2.connect(
        dbname="demodb", 
        user="postgres", 
        password="705219", 
        host="localhost", 
        port="5432"
    )

def clean_income(income_val):
    if income_val is None: return None
    try:
        clean_val = str(income_val).lower().replace('k', '000').replace(',', '').strip()
        return int(''.join(filter(str.isdigit, clean_val)))
    except:
        return 0 

# --- AI Extraction with Guardrails ---
def extract_and_validate(user_input):
    prompt = f"""
    You are a specialized assistant for a West Bengal Scheme Database. 
    Task 1: Extract {REQUIRED_FIELDS} from the input.
    Task 2: If the user asks anything NOT related to personal details for schemes (e.g., general knowledge, social mobility, science), set 'out_of_scope' to true.
    
    Rules:
    - Age/Income: Numbers only.
    - Education: 10th=10, 12th=12, Graduate=15.
    - Only return JSON.
    
    User Text: "{user_input}"
    """
    
    try:
        response = ollama.generate(model='llama3', prompt=prompt, format='json')
        return json.loads(response['response'])
    except:
        return {}

# --- Dynamic SQL (Fills based on available memory) ---
def run_dynamic_query():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Base Query
        query = "SELECT * FROM wb_schemes WHERE 1=1"
        params = []

        # Let's check one by one what is in memory
        if user_data['gender']:
            query += " AND LOWER(gender) = LOWER(%s)"
            params.append(user_data['gender'])
            
        if user_data['age']:
            query += " AND %s >= min_age AND %s <= max_age"
            params.extend([user_data['age'], user_data['age']])
            
        if user_data['income']:
            c_income = clean_income(user_data['income'])
            query += " AND %s <= max_income"
            params.append(c_income)
            
        if user_data['occupation']:
            query += " AND (LOWER(occupation) = LOWER(%s) OR LOWER(occupation) = 'any')"
            params.append(user_data['occupation'])
            
        if user_data['education']:
            query += " AND (education = 'Any' OR %s >= education::integer)"
            params.append(user_data['education'])

        cursor.execute(query, tuple(params))
        results = cursor.fetchall()
        conn.close()
        
        return results
    except Exception as e:
        print(f"Database Error: {e}")
        return []

# --- Main Bot Logic ---
def start_smart_bot():
    print("Bot: Namaste! ")
    
    while True:
        user_input = input("\nUser: ").strip()
        
        # 1. AI se data nikalwao
        extracted = extract_and_validate(user_input)
        
        # 2. Guardrail Check (Faltu sawalon ke liye)
        if extracted.get('out_of_scope'):
            print("Bot:  not found.")
            continue

        # 3. Memory Update (Prompt Chaining logic -  old data will retain)
        for field in REQUIRED_FIELDS:
            if extracted.get(field) is not None:
                user_data[field] = extracted[field]
        
        # 4. show result based on details
        print("\n[System]: Checking schemes for provided details...")
        results = run_dynamic_query()
        
        if results:
            print(f"Bot:  acccording to your details these schemes is for you")
            for row in results:
                print(f" - {row[1]}")
        else:
            print("Bot:  data not found.")

        # 5. Missing data ke liye reminder
        missing = [f for f in REQUIRED_FIELDS if user_data[f] is None]
        if missing:
            print(f"\n(Note: Behtar results ke liye mujhe apna {', '.join(missing)} bhi bataiye.)")
        else:
            print("\nBot: acccording to your details these schemes is for you .")

if __name__ == "__main__":
    start_smart_bot()