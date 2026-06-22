import psycopg2
import ollama
import json

# Connection Details
def get_db_connection():
    return psycopg2.connect(dbname="demodb", user="postgres", password="705219", host="localhost", port="5432")

# LINK 1: Extracting data using LLM
def extract_entities(user_input):
    try:
        prompt = f"""
        Extract these details: gender, occupation, education, age, income, caste.
        Input: "{user_input}"
        Return ONLY a JSON object. If a field is missing, set value to null.
        """
        response = ollama.chat(model='llama3', messages=[{'role': 'user', 'content': prompt}])
        content = response['message']['content']
        start = content.find('{')
        end = content.rfind('}') + 1
        return json.loads(content[start:end])
    except Exception as e:
        print(f"\n[Warning]: LLM extraction failed: {e}")
        return {}

# LINK 2: Dynamic SQL Generator
def generate_and_run_sql(user_data):
    query = "SELECT * FROM schemes WHERE 1=1"
    params = []

    # Filters
    if user_data.get('gender'):
        query += " AND LOWER(gender) = LOWER(%s)"
        params.append(user_data['gender'])
    
    if user_data.get('occupation'):
        query += " AND LOWER(occupation) = LOWER(%s)"
        params.append(user_data['occupation'])
        
    if user_data.get('education'):
        query += " AND LOWER(education) = LOWER(%s)"
        params.append(str(user_data['education']))

    # Numeric/Age filtering (Safely handled)
    if user_data.get('age') and str(user_data['age']).isdigit():
        query += " AND %s BETWEEN min_age AND max_age"
        params.append(int(user_data['age']))
        
    if user_data.get('income') and str(user_data['income']).isdigit():
        query += " AND %s <= max_income"
        params.append(int(user_data['income']))

    if user_data.get('caste'):
        query += " AND (LOWER(caste) = LOWER(%s) OR caste = 'Any')"
        params.append(user_data['caste'])

    print(f"\n[Bot]: Querying Database...")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    return results

# LINK 3: Smart Adaptive Loop
def start_smart_bot():
    print("Bot: Namaste! ")
    raw_input = input("You: ")
    user_data = extract_entities(raw_input)
    
    # Yahan 'age' add kar diya hai
    REQUIRED_FIELDS = ['gender', 'occupation', 'education', 'age', 'income', 'caste'] 
    
    while True:
        # Check if any field is missing or 'null' string
        missing_fields = [f for f in REQUIRED_FIELDS if not user_data.get(f) or user_data.get(f) == 'null']
        
        if missing_fields:
            field = missing_fields[0]
            val = input(f"Bot: Aapka {field} kya hai? ")
            user_data[field] = val
        else:
            print("\n[Bot]: Checking schemes...")
            results = generate_and_run_sql(user_data)
            
            if results:
                print("\n[Bot]: You are eligible for these schemes:")
                for r in results:
                    print(f"- {r[1]}") 
            else:
                print("\n[Bot]: No schemes matched your criteria.")
            break 

if __name__ == "__main__":
    start_smart_bot()