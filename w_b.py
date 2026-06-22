import sqlite3    

# Setup
db_path = r"C:\Users\user\OneDrive\Desktop\scheme.db"
def get_user_details():
    print("Bot: Tell me...")
    intro = input("You: ")
    name = "User"
    if "my name is" in intro.lower():
        name = intro.lower().split("my name is")[1].strip().capitalize()
    
    print(f"Bot: Hello {name}! Mujhe kuch jankari chahiye.")
    details = {"age": None, "income": None, "gender": None}
    
    if not details["age"]: details["age"] = int(input("Bot: Aapki age kya hai?: "))
    if not details["income"]: details["income"] = input("Bot: Aapki family income kya hai? (e.g., 10k): ")
    if not details["gender"]: details["gender"] = input("Bot: Aapka gender kya hai? (Male/Female): ")
    return details, name

# 1. User Details
details, user_name = get_user_details()
raw_income = int(details['income'].lower().replace('k', '000'))

# 2. Direct SQL Query
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

query = """
SELECT scheme_name 
FROM schemes 
WHERE min_age <= ? AND max_age >= ? 
AND max_income >= ? 
AND (gender = ? OR gender = 'everyone' OR gender = 'All')
"""

cursor.execute(query, (details['age'], details['age'], raw_income, details['gender']))
results = cursor.fetchall()
conn.close()

# 3. Use LLM to format the response nicely
if results:
    schemes_list = ", ".join([r[0] for r in results])
    
    # Updated Professional Prompt
    prompt = f"""
    You are a government help-desk assistant. 
    User details: {details['age']} years old, {details['gender']}, income {raw_income}. 
    The eligible schemes are: {schemes_list}. 
    Instructions: Provide a concise, professional list of the eligible schemes. 
    Do not act like a salesman. Keep the response under 50 words.
    """
    
   