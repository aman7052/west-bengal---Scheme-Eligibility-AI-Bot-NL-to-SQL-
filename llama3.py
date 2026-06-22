import ollama
import psycopg2

# --- 1. Database Connection ---
def query_database(sql_query):
    try:
        conn = psycopg2.connect(
            dbname="demodb", user="postgres", 
            password="705219", host="localhost"
        )
        cur = conn.cursor()
        cur.execute(sql_query)
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return rows
    except Exception as e:
        return f"Error: {e}"

# --- 2. Memory System (Simple Python List) ---
chat_history = []

def get_llama_response(user_input):
    global chat_history
    
    # System Instructions
    system_prompt = """
    You are a West Bengal Government Assistant. Follow these STRICT RULES:
    1. If any info is missing (Age, Gender, Occupation, Income), ask ONLY the question for that missing info.
    Example: "What is your monthly income?" or "What is your gender?"
    2. DO NOT explain what you found. DO NOT say "Thank you" or "I have extracted".
    3. ONLY ask for ONE missing detail at a time.
    4. If ALL info is present, generate ONLY the SQL query. No conversational text.
    If the user provides multiple details in a single sentence, extract all of them. If any information is still missing, ask for the rest. If everything is provided, generate the SQL immediately
    """

    # Add user message to history
    chat_history.append({'role': 'user', 'content': user_input})

    # Call Llama 3 directly via Ollama
    response = ollama.chat(model='llama3', messages=[
        {'role': 'system', 'content': system_prompt},
        *chat_history
    ])

    bot_message = response['message']['content']
    chat_history.append({'role': 'assistant', 'content': bot_message})
    
    return bot_message

# --- 3. Main Loop ---
print("Bot: Namaste!")

while True:
    user_input = input("You: ")
    if user_input.lower() in ['exit', 'quit', 'bye']:
        break

    bot_res = get_llama_response(user_input)

    # Check if Llama 3 generated SQL
    if "SELECT" in bot_res.upper():
        print(f"\n[System: Executing SQL...]")
        # Clean the SQL string
        sql = bot_res.replace("```sql", "").replace("```", "").strip()
        result = query_database(sql)
        print(f"Bot: You are eligible for this scheme: {result}")
        chat_history = [] # Reset after success
    else:
        print(f"Bot: {bot_res}")