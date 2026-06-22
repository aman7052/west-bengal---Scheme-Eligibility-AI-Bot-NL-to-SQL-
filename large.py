import psycopg2
import ollama

# 1. Globals
REQUIRED_FIELDS = ['gender', 'age', 'education', 'occupation', 'income']
user_data = {field: None for field in REQUIRED_FIELDS}

# 2. Database Connection
def get_db_connection():
    return psycopg2.connect(
        dbname="demodb", 
        user="postgres", 
        password="705219",   
        host="localhost", 
        port="5432"
    )

# define clean income
def clean_income(income_val):
    try:
        clean_val = str(income_val).lower().replace('k', '000').replace(',', '').strip()
        return int(clean_val)
    except:
        return 0 

# 3. Logic to fetch Data from DB
def generate_and_run_sql():
    try:
        clean_income_val = clean_income(user_data['income'])
        
        query = f"""
        SELECT * FROM wb_schemes 
        WHERE LOWER(gender) = LOWER('{user_data['gender']}')
        AND {user_data['age']} >= min_age 
        AND {user_data['age']} <= max_age
        AND {clean_income_val} <= max_income
        AND (LOWER(occupation) = LOWER('{user_data['occupation']}') OR LOWER(occupation) = 'any')
        AND (education = 'Any' OR {user_data['education']} >= education::integer)
        """
        
        print(f"\n[Bot]: Querying Database: {query}")
    
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        
        if results:
            print("\n[Bot]: These schemes may be eligible for you:")
            for row in results:
                print(f"- {row[1]}")  # row[1] scheme_name
        else:
            print("\n[Bot]: No specific scheme matching your details was found in the database.")
            
    except Exception as e:
        print(f"\n[Bot]: Error aaya: {e}")

# 4. Main Bot Loop
def start_smart_bot():
    print("Bot: Hello! Welcome to you..")
    
    while True:
        missing = [f for f in REQUIRED_FIELDS if user_data[f] is None]
        
        if missing:
            field_to_ask = missing[0]
            val = input(f"Bot: Please provide your {field_to_ask}: ")
            user_data[field_to_ask] = val
        else:
            print("\nBot:  Checking database...")
            generate_and_run_sql()
            break

# 5. Entry Point
if __name__ == "__main__":
    start_smart_bot()
