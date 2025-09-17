from google.cloud import aiplatform

# Initialize Vertex AI
aiplatform.init(project="genai-demo", location="us-central1")

# Import the GenerativeModel
from vertexai.generative_models import GenerativeModel

# Load Gemini model
model = GenerativeModel("gemini-1.5-flash")

def chat_with_bot(user_input):
    response = model.generate_content(user_input)
    return response.text

if __name__ == "__main__":
    print(" Chatbot is running! Type 'exit' to quit.\n")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break
        reply = chat_with_bot(user_input)
        print(f"Bot: {reply}\n")
