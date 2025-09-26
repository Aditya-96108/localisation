OPENAI_API_KEY =""
FACEBOOK_USERNAME = "adityab12@hexaware.com"
FACEBOOK_PASSWORD = "Password@123"

client = OpenAI(api_key=OPENAI_API_KEY)
model = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')