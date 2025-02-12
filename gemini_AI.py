import streamlit as st
import base64
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai
#from langchain.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
import os
from langchain_community.vectorstores import FAISS
from langchain.chains import LLMChain
import time
import hashlib
import json

st.set_page_config(page_title="Bid Query Bot ", layout="wide")

st.markdown(
    """
    <style>
    .stButton button {
        background: linear-gradient(120deg,#FF007F, #A020F0 100%) !important;
        color: white !important;
    }
    body {
        color: white;
        background-color: #1E1E1E;
    }
    .stTextInput, .stSelectbox, .stTextArea, .stFileUploader {
        color: white;
        background-color: #FFFFFF;
    }
    </style>
    """,
    unsafe_allow_html=True
)
st.markdown("""
<style>
    iframe {
        position: fixed;
        left: 0;
        right: 0;
        top: 0;
        bottom: 0;
        border: none;
        height: 100%;
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
    <style>
        @keyframes gradientAnimation {
            0% {
                background-position: 0% 50%;
            }
            50% {
                background-position: 100% 50%;
            }
            100% {
                background-position: 0% 50%;
            }
        }

        .animated-gradient-text {
            font-family: "Graphik Semibold";
            font-size: 42px;
            background: linear-gradient(45deg, #22ebe8 30%, #dc14b7 55%, #fe647b 20%);
            background-size: 300% 200%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: gradientAnimation 20s ease-in-out infinite;
        }
    </style>
    <h2>
        Bid Response Evaluation AI: Evaluates Bid responses!
    </h2>
""", unsafe_allow_html=True)

api_key = 'AIzaSyBJJfXHfC80NWtiKGA57aO2mGsT-aD9fhQ'
if 'responses' not in st.session_state:
    st.session_state['responses'] = ["How can I assist you?"]

if 'requests' not in st.session_state:
    st.session_state['requests'] = []


# Helper function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# Define users and hashed passwords for simplicity
users = {
    "user": hash_password("user"),
    "admin": hash_password("admin")
}


TOKEN_FILE = "./data/token_counts.json"


def read_token_counts():
    try:
        with open("./data/token_counts.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def write_token_counts(token_counts):
    with open("./data/token_counts.json", "w") as f:
        json.dump(token_counts, f)


def get_token_count(username):
    token_counts = read_token_counts()
    return token_counts.get(username, 1000)  # Default to 1000 tokens if not found

def update_token_count(username, count):
    token_counts = read_token_counts()
    token_counts[username] = count
    write_token_counts(token_counts)

def login():
    col1, col2, col3 = st.columns([1, 1, 1])  # Create three columns with equal width
    with col2:  # Center the input fields in the middle column
        st.title("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Sign in"):
            hashed_password = hash_password(password)
            if username in users and users[username] == hashed_password:
                token_counts = read_token_counts()
                tokens_remaining = token_counts.get(username, 500)  # Default to 500 tokens if not found
                
                if tokens_remaining > 0:
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.tokens_remaining = tokens_remaining
                    st.session_state.tokens_consumed = 0
                    st.success("Logged in successfully!")
                    st.experimental_rerun()  # Refresh to show logged-in state
                else:
                    st.error("No tokens remaining. Please contact support.")
            else:
                st.error("Invalid username or password")
    # Add the footer section
    col4, col5, col6, col7, col8, col9 = st.columns([1, 1, 1, 1, 1, 1])
    st.markdown("")
    st.markdown("")
    with col7:
        st.markdown("")
        st.markdown("")
        st.markdown("")
        st.write("**Design & Developed by:**")
    with col9:
        st.image("https://i.ibb.co/YRH1647/Pranav-Baviskar.png", width=150)
    with col8:
        st.image("https://i.ibb.co/0ssNpmD/Ritwick-Das.png", width=150)


def logout():
    # Clear session state on logout
    st.session_state.logged_in = False
    del st.session_state.username
    del st.session_state.tokens_remaining
    del st.session_state.tokens_consumed
    st.success("Logged out successfully!")
    st.experimental_rerun()  # Refresh to show logged-out state

def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    chunks = text_splitter.split_text(text)
    return chunks

def get_vector_store(text_chunks, api_key):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local("faiss_index")

def get_conversational_chain():
    prompt_template = """Consider yourself as bid query resolver. Vendor will ask you question and your job is to answer the user question based on the context provided. Answer should end with disclaimer that this is AI generated content.
    Context:\n {context}?\n
    Question: \n{question}\n .
    Answer:
    """
    model = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3, google_api_key=api_key)
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    print("Prompt ***** --->", prompt)
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    return chain

def user_input(user_question, api_key):
    # Embeddings and vector store initialization omitted for brevity
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
    new_db = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
    
    # Perform similarity search and get response
    docs = new_db.similarity_search(user_question)
    chain = get_conversational_chain()
    response = chain({"input_documents": docs, "question": user_question}, return_only_outputs=True)
    
    # Calculate number of words in the response
    num_words = len(response["output_text"].split())

    # Deduct tokens based on number of words
    token_cost = num_words  # Each word in the response costs 1 token (adjust as needed)
    
    # Check if enough tokens are available
    if st.session_state.tokens_remaining > 0:
        # Proceed with displaying the response and deducting tokens
        st.write("Bid Query Bot: ", response["output_text"])
        st.session_state.tokens_consumed += token_cost  # Deduct tokens based on response length
        st.session_state.tokens_remaining -= token_cost

        # Update token count in JSON file
        token_counts = read_token_counts()
        token_counts[st.session_state.username] = st.session_state.tokens_remaining
        write_token_counts(token_counts)
    else:
        st.warning("You don't have enough tokens. Please contact your administrator.")

    # Display remaining tokens to the user
    st.sidebar.text(f"Tokens Remaining: {st.session_state.tokens_remaining}")


def get_conversation_string():
    conversation_string = ""
    for i in range(len(st.session_state['responses'])-1):
        
        conversation_string += "Human: "+st.session_state['requests'][i] + "\n"
        conversation_string += "Bot: "+ st.session_state['responses'][i+1] + "\n"
    return conversation_string

def query_refiner(conversation, user_question):
    prompt=f"""
    Given the following user query and conversation log, formulate a question that would be the most relevant to provide the user with an answer from a knowledge base.\n\nCONVERSATION LOG: \n{conversation}\n\nQuery: {user_question}\n\nRefined Query:"

    """
    prompt = PromptTemplate(template=prompt, input_variables=["conversation","user_question"])
    print("Prompt is....",prompt)
    model = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3, google_api_key=api_key)
    chat_llm_chain = LLMChain(
        llm=model,
        prompt=prompt,
        verbose=True
    )    
    response = chat_llm_chain.predict(user_question=user_question)
    print("Response of refined query is ----->",response)
    return response

def main():
    st.header("Chat with Bid Query Bot")
    st.markdown("""
    <style>
        /* Ensure the entire label has no background */
        label[data-testid="stWidgetLabel"] {
            background: none !important;
            background-color: transparent !important;
        }

        /* Target the inner div container */
        label[data-testid="stWidgetLabel"] div[data-testid="stMarkdownContainer"] {
            background: none !important;
            background-color: transparent !important;
        }

        /* Ensure the paragraph inside has no background */
        label[data-testid="stWidgetLabel"] p {
            background: none !important;
            background-color: transparent !important;

        }

        /* Change the input box background to white */
        div[data-baseweb="input"] {
            background-color: white !important;
            border-radius: 5px !important;
            padding: 5px !important;
        }
    </style>
    """, unsafe_allow_html=True)

    user_question = st.text_input("How can I help you?", key="user_question")

    if user_question and api_key:  # Ensure API key and user question are provided
        if user_question:
            if st.button("Ask Question"):
                user_input(user_question, api_key)
        
    with st.sidebar:
        st.image("https://www.clutch.com/wp-content/uploads/2018/04/Accenture-logo-no-background.png", width=150)
        st.markdown("")
        st.markdown("")
        
        pdf_docs = st.file_uploader("Upload your RFP Files and Click on the Submit & Process Button", accept_multiple_files=True, key="pdf_uploader")
        if st.button("Submit & Process", key="process_button") and api_key:  # Check if API key is provided before processing
            with st.spinner("Processing..."):
                raw_text = get_pdf_text(pdf_docs)
                text_chunks = get_text_chunks(raw_text)
                get_vector_store(text_chunks, api_key)
                st.success("Done")

if __name__ == "__main__":

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "tokens_consumed" not in st.session_state:
        st.session_state.tokens_consumed = 0
    if "tokens_remaining" not in st.session_state:
        st.session_state.tokens_remaining = 0
    
    if st.session_state.logged_in:
        st.sidebar.write(f"Welcome, {st.session_state.username}")
        st.sidebar.write(f"Tokens remaining: {st.session_state.tokens_remaining}")
        if st.sidebar.button("Logout"):
            logout()
        main()
    else:
        login()


st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Graphik:wght@400;700&display=swap');

    body {
        background-color: #ffffff;
        color: black;
        font-family: 'Graphik', sans-serif;
    }
    .main {
        background-color: #ffffff;
    }
    .stApp {
        background-color: #ffffff;
    }
    header {
        background-color: #660094 !important;
        padding: 10px 40px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .logo {
        height: 30px;
        width: auto;
        margin-right: 20px;  /* Space between logo and next item */
    }
    .header-content {
        display: flex;
        align-items: center;
    }
    .header-right {
        display: flex;
        align-items: center;
    }

    h1 {
        color: black;
        margin: 0;
        padding: 0;
    }

    .generated-text-box {
        border: 3px solid #A020F0; /* Thick border */
        padding: 20px;  
        border-radius: 10px; /* Rounded corners */
        color: black; /* Text color */
        background-color: #FFFFFF; /* Background color matching theme */
    }
    </style>
    """,
    unsafe_allow_html=True
)


# Adding the logo and other elements in the header st-emotion-cache-18ni7ap ezrtsby2
st.markdown(
    f"""
    <header tabindex="-1" data-testid="stHeader" class="st-emotion-cache-18ni7ap ezrtsby2">
        <div data-testid="stDecoration" id="stDecoration" class="st-emotion-cache-1dp5vir ezrtsby1"></div>
        <div class="header-content">
            <!-- Add the logo here -->
            <img src="https://www.vgen.it/wp-content/uploads/2021/04/logo-accenture-ludo.png" class="logo" alt="Logo">
        
    </header>

    """,
    unsafe_allow_html=True
)
