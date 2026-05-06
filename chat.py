import os
import fitz  # PyMuPDF
from groq import Groq
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF file using PyMuPDF."""
    text = ""
    try:
        doc = fitz.open(pdf_path)
        for page in doc:
            text += page.get_text()
        doc.close()
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
    return text

def extract_text_from_txt(txt_path):
    """Extracts text from a plain text file."""
    try:
        with open(txt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading TXT {txt_path}: {e}")
    return ""

def load_documents(directory):
    """Loads text from all supported files in the directory recursively."""
    context_text = ""
    if not os.path.exists(directory):
        print(f"Directory '{directory}' does not exist.")
        return context_text

    for root, _, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            if file.lower().endswith('.pdf'):
                print(f"Loading {file}...")
                context_text += f"\n--- Start of {file} ---\n"
                context_text += extract_text_from_pdf(file_path)
                context_text += f"\n--- End of {file} ---\n"
            elif file.lower().endswith('.txt') or file.lower().endswith('.md') or file.lower().endswith('.csv'):
                print(f"Loading {file}...")
                context_text += f"\n--- Start of {file} ---\n"
                context_text += extract_text_from_txt(file_path)
                context_text += f"\n--- End of {file} ---\n"
            else:
                print(f"Skipping {file} (unsupported format for raw text extraction)")
    
    return context_text

def chat_loop():
    print("Welcome to Groq Chat! Let's talk about your downloaded files.")
    
    # Initialize Groq client
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        print("Error: GROQ_API_KEY is missing or not set in .env")
        print("Please edit the .env file and add your actual Groq API key.")
        return

    try:
        client = Groq(api_key=api_key)
    except Exception as e:
        print(f"Failed to initialize Groq client: {e}")
        return

    # Load context
    print("\nScanning for downloaded documents...")
    context = load_documents('./my_downloads')
    
    if not context.strip():
        print("No readable documents found in ./my_downloads. The bot won't have any context.")
    else:
        print(f"Successfully loaded {len(context)} characters of text context.")

    # System prompt
    messages = [
        {
            "role": "system",
            "content": f"You are a helpful assistant. Answer the user's questions based on the following context. If the answer is not in the context, just say you don't know based on the provided documents.\n\nContext Documents:\n{context}"
        }
    ]

    print("\nType 'quit' or 'exit' to end the chat.\n")
    while True:
        try:
            user_input = input("You: ")
            if user_input.lower() in ['quit', 'exit']:
                break
            if not user_input.strip():
                continue

            messages.append({"role": "user", "content": user_input})

            # Call Groq API
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.7,
                max_completion_tokens=1024
            )
            
            assistant_reply = response.choices[0].message.content
            print(f"\nGroq Assistant: {assistant_reply}\n")
            
            messages.append({"role": "assistant", "content": assistant_reply})

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            messages.pop() # remove the failed user message so they can try again

if __name__ == "__main__":
    chat_loop()
