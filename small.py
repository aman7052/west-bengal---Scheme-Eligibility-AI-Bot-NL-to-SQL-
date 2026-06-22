import psycopg2
import ollama
import json

# 1. Globals
REQUIRED_FIELDS = ['gender', 'age', 'education', 'occupation', 'income']
user_data = {field: None for field in REQUIRED_FIELDS}

# 2. Database Connection
def get_db_connection():
    return psycopg2.connect(
        dbname="demodb", 
        user="postgres", 
        password="your_password",  # Apna password yahan dalein
        host="localhost", 
        port="5432"
    )

def clean_income(income_val):
    try:
        # Handling strings like '10k' or '10,000'
        clean_val = str(income_val).lower().replace('k', '000').replace(',', '').strip()
        return int(''.join(filter(str.isdigit, clean_val)))
    except:
        return 0 

# --- NEW: Entity Extraction Function ---
def extract_entities(user_input):
    """LLM ka use karke text se details nikalne ke liye"""
    prompt = f"""
    You are an information extractor. Extract the following fields from the user's text: 
    {REQUIRED_FIELDS}.
    
    Rules:
    - Age and Income must be numbers.
    - Education should be a number (e.g., 10th = 10, 12th = 12, Graduate = 15).
    - If a field is missing, return null for it.
    - Respond ONLY in valid JSON format.
    
    User Text: "{user_input}"
    """
    
    try:
        response = ollama.generate(model='llama3', prompt=prompt, format='json')
        extracted = json.loads(response['response'])
        return extracted
    except Exception as e:
        print(f"Error extracting data: {e}")
        return {}

# 3. Logic to fetch Data from DB
def generate_and_run_sql():
    try:
        clean_income_val = clean_income(user_data['income'])
        
        # SQL Injection se bachne ke liye parameterized query use karna behtar hai, 
        # par aapke format ke hisab se niche filter hai:
        query = f"""
        SELECT * FROM wb_schemes 
        WHERE LOWER(gender) = LOWER('{user_data['gender']}')
        AND {user_data['age']} >= min_age 
        AND {user_data['age']} <= max_age
        AND {clean_income_val} <= max_income
        AND (LOWER(occupation) = LOWER('{user_data['occupation']}') OR LOWER(occupation) = 'any')
        AND (education = 'Any' OR {user_data['education']} >= education::integer)
        """
        
        print(f"\n[Bot]: Querying Database...")
    
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        
        if results:
            print("\n[Bot]: You are eligible for this scheme:")
            for row in results:
                print(f"✅ {row[1]}")
        else:
            print("\n[Bot]: Sorry, no matching schemes found for your profile.")
            
    except Exception as e:
        print(f"\n[Bot]: Database Error: {e}")

# 4. Main Bot Loop (Updated)
def start_smart_bot():
    print("Bot: Hello!  how can i help you)")
    
    while True:
        # Check missing fields
        missing = [f for f in REQUIRED_FIELDS if user_data[f] is None]
        
        if not missing:
            print("\nBot: Sabhi details mil gayi hain. Processing...")
            generate_and_run_sql()
            break
        
        # User se input lena
        user_input = input("\nUser: ")
        
        # AI se data extract karna
        extracted_data = extract_entities(user_input)
        
        # Global user_data update karna
        for field in REQUIRED_FIELDS:
            if extracted_data.get(field):
                user_data[field] = extracted_data[field]
        
        # Phir se check karna ki kuch bacha toh nahi
        still_missing = [f for f in REQUIRED_FIELDS if user_data[f] is None]
        
        if still_missing:
            print(f"Bot: Shukriya! Magar mujhe abhi bhi aapka {', '.join(still_missing)} chahiye. Please batayein:")
        else:
            continue # Loop check karega aur query run karega

if __name__ == "__main__":
    start_smart_bot()