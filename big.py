import psycopg2
import ollama

# 1. Globals
REQUIRED_FIELDS = ['age', 'gender', 'education', 'income', 'caste', 'category', 'residence', 'school_type', 'marital_status']
user_data = {field: None for field in REQUIRED_FIELDS}

# 2. Database Connection
def get_db_connection():
    return psycopg2.connect(
        dbname="demodb", 
        user="postgres", 
        password="705219", # enter your postgresql password
        host="localhost", 
        port="5432"
    )
# define clean income
def clean_income(income_val):
    try:
        # clean String and convert into integer
        clean_val = str(income_val).lower().replace('k', '000').replace(',', '').strip()
        return int(clean_val)
    except:
        return 0 

# 3. Logic to fetch Data from DB
def generate_and_run_sql():
    try:
        clean_income_val = clean_income(user_data['income'])
        
        # make strict Query
        query = f"""
        SELECT * FROM schemes 
        WHERE LOWER(gender) = LOWER('{user_data['gender']}')
        AND {user_data['age']} >= min_age 
        AND {user_data['age']} <= max_age
        AND (LOWER(marital_status) = LOWER('{user_data['marital_status']}') OR LOWER(marital_status) = 'any')
        AND {clean_income_val} <= max_income
        AND (LOWER(caste) = LOWER('{user_data['caste']}') OR LOWER(caste) = 'any')
        AND (LOWER(scheme_category) = LOWER('{user_data['category']}') OR LOWER(scheme_category) = 'any')
        AND (school_type ILIKE '%{user_data['school_type']}%' OR school_type = 'Any')
        AND (residence_area ILIKE '%{user_data['residence']}%' OR residence_area = 'Any')
        AND (min_education = 'Any' OR {user_data['education']} >= min_education::integer)
        AND (max_education = 'Any' OR {user_data['education']} <= max_education::integer)
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
                print(f"- {row[1]}") # row[1] scheme name
        else:
            print("\n[Bot]: No specific scheme matching your details was found in the database.")
            
    except Exception as e:
        print(f"\n[Bot]: Error aaya: {e}")

# 4. Main Bot Loop
def start_smart_bot():
    print("Bot: Hello! welcome to you..")
    
    while True:
        # Check any detail are missing ?
        missing = [f for f in REQUIRED_FIELDS if user_data[f] is None]
        
        if missing:
            field_to_ask = missing[0]
            val = input(f"Bot: Please provide your {field_to_ask}: ")
            user_data[field_to_ask] = val
        else:
            print("\nBot: All the details are available! Checking database...")
            generate_and_run_sql()
            break

# 5. Entry Point
if __name__ == "__main__":
    start_smart_bot()