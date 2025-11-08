import os
import glob
from flask import Flask, render_template, jsonify, request
import google.generativeai as genai
from PyPDF2 import PdfReader
from dotenv import load_dotenv

# --- 1. CONFIGURATION & INITIALIZATION ---

# Load environment variables (for the GOOGLE_API_KEY)
load_dotenv()

# Configure the Gemini API
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY not found. Please set it in your .env file.")
genai.configure(api_key=api_key)

# --- 2. PROMPT ENGINEERING (THE "PERSONALITY") ---

SYSTEM_INSTRUCTION = """
You are a helpful and friendly assistant for the "Adventure Pathways Early Learning Centre".
Your name is 'Turmeric the Cat'.
You must answer questions based *only* on the context provided.
If the answer is not in the provided documents, you MUST say:
"I'm sorry, I don't have that information. Please contact the centre directly for more details."

---
FORMATTING RULES:
- Always use Markdown for formatting (like bolding, new lines, and bullet points) to make your answers easy to read.
- For any lists, you MUST use bullet points (using a * or -).
---

Do not make up information. Be professional, cheerful, and helpful.
"""

# Initialize the Gemini Model *with* the system instruction
# This fixes the 'system_instruction' error
model = genai.GenerativeModel(
    'gemini-2.5-pro',
    system_instruction=SYSTEM_INSTRUCTION
)

# Create the Flask app
app = Flask(__name__, static_folder='static', template_folder='static')

# --- 3. DOCUMENT LOADING (THE "BRAIN") ---

# Global variable to hold all document text
document_context = ""

def extract_text_from_file(file_path):
    """Extracts text from PDF or TXT files."""
    text = ""
    if file_path.endswith('.pdf'):
        try:
            reader = PdfReader(file_path)
            for page in reader.pages:
                text += page.extract_text() or ""
        except Exception as e:
            print(f"Error reading PDF {file_path}: {e}")
    elif file_path.endswith('.txt'):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            print(f"Error reading TXT {file_path}: {e}")
    return text

def load_documents_on_startup():
    """
    Loads all documents from the 'documents' folder into the
    global 'document_context' variable.
    """
    global document_context
    doc_texts = []
    document_folder = 'documents'
    
    search_path = os.path.join(document_folder, '*.*')
    files = glob.glob(search_path)
    
    if not files:
        print("WARNING: No documents found in the 'documents' folder.")
        document_context = "No documents have been loaded for context."
        return

    print(f"Loading {len(files)} document(s)...")
    for file_path in files:
        if file_path.endswith('.pdf') or file_path.endswith('.txt'):
            print(f" - Processing {file_path}")
            doc_texts.append(extract_text_from_file(file_path))
    
    document_context = "\n\n--- END OF DOCUMENT ---\n\n".join(doc_texts)
    print("All documents loaded into context successfully.")

# --- 4. FLASK ROUTES (THE API) ---

@app.route('/')
def index():
    """Serves the main index.html file."""
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    """Handles chat messages from the user."""
    
    data = request.json
    user_message = data.get('message')
    # This is the simple history from the browser:
    # [ {'role': 'user', 'text': '...'}, {'role': 'model', 'text': '...'} ]
    chat_history = data.get('history', []) 

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    try:
        # --- THIS IS THE FIX for the ['role', 'text'] error ---
        # We must reformat the simple history into the format
        # the Google API library expects.
        
        formatted_history = []
        for message in chat_history:
            # The API expects {'role': '...', 'parts': [{'text': '...'}]}
            formatted_history.append({
                "role": message["role"],
                "parts": [{"text": message["text"]}]
            })
        # --- END OF THE FIX ---
        
        # Start a chat session with the *formatted* history
        chat_session = model.start_chat(
            history=formatted_history
        )
        
        # Build the RAG prompt
        rag_prompt = f"""
        Here is the context from our centre's documents:
        --- CONTEXT START ---
        {document_context}
        --- CONTEXT END ---
        
        Please answer this question based *only* on the context above:
        Question: "{user_message}"
        """

        # Send the message to Gemini
        response = chat_session.send_message(rag_prompt)
        
        # Return only the AI's reply
        return jsonify({"reply": response.text})

    except Exception as e:
        print(f"An error occurred during chat: {e}")
        return jsonify({"error": f"An internal error occurred: {e}"}), 500

# --- 5. RUN THE APP ---

if __name__ == '__main__':
    load_documents_on_startup()
    app.run(port=5000, debug=True)