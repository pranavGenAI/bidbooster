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

st.set_page_config(page_title="BidBooster ", layout="wide")

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

        .animated-gradient-text_ {
            font-family: "Graphik Semibold";
            font-size: 42px;
            background: linear-gradient(45deg, rgb(245, 58, 126) 30%, rgb(200, 1, 200) 55%, rgb(197, 45, 243) 20%);
            background-size: 300% 200%;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: gradientAnimation 10s ease-in-out infinite;
        }
        @keyframes animate_ {
            0%, 18%, 20%, 50.1%,60%, 65.1%, 80%,90.1%,92% {
                color: #0e3742;
                text-shadow: none;
                }
            18.1%, 20.1%, 30%,50%,60.1%,65%,80.1%,90%, 92.1%,100% {
                color: #fff;
                text-shadow: 0 0 10px rgb(197, 45, 243),
                             0 0 20px rgb(197, 45, 243);
                }
            }
        
        .animated-gradient-text_ {
                    font-family: "Graphik Semibold";
                    font-size: 42px;
                    color: #FFF;
                    transition: color 0.5s, text-shadow 0.5s;
                }

        .animated-gradient-text_:hover {
                    animation: animate_ 5s linear infinite;
                }

        
    </style>
    <p class="animated-gradient-text_">
        BidBooster: Simplifying Your Bid Process!
    </p>
""", unsafe_allow_html=True)


#st.image("https://media1.tenor.com/m/6o864GYN6wUAAAAC/interruption-sorry.gif", width=1000)
# st.image("https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExcjl2dGNiYThobHplMG81aGNqMjdsbWwwYWJmbTBncGp6dHFtZTFzMSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/CGP9713UVzQ0BQPhSf/giphy.gif", width=50)


# This is the first API key input; no need to repeat it in the main function.
api_key = st.secrets['GEMINI_API_KEY']

if 'responses' not in st.session_state:
    st.session_state['responses'] = ["How can I assist you?"]

if 'requests' not in st.session_state:
    st.session_state['requests'] = []


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
    prompt_template = """
    Answer the question as detailed as possible from the provided context. Change the wording of answer and start in the most polite way. Write the summary of answer and then provide the detail answer. Start with polite and nice statement. You can use greetings if you want. Don't provide the wrong answer. If you are giving answer and not using context to frame the answer then let the user know that the answer is not from the context.\n\n. And remember to format your answer in nicer way. End your response with disclaimer telling about the answer is from the context. Remember to be polite and start answer with assistant greetings. 
    Context:\n {context}?\n
    Question: \n{question}\n .Make sure you are summarizing and changing the wording of context before you write answer in easy to understand language and format it in better way. Provide the disclaimer in best possible way at the of question saying the answer is based on the context and accuracy needs to be checked from the source.

    Answer:
    """
    model = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3, google_api_key=api_key)
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    print("Prompt ***** --->", prompt)
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    return chain

def user_input(user_question, api_key):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
    #new_db = FAISS.load_local("faiss_index", embeddings)
    new_db = FAISS.load_local("faiss_index", embeddings,allow_dangerous_deserialization=True)
    docs = new_db.similarity_search(user_question)
    chain = get_conversational_chain()
    response = chain({"input_documents": docs, "question": user_question}, return_only_outputs=True)
    # speed = 10
    # container = st.empty()
    # tokens = response["output_text"].split()
    # for index in range(len(tokens) + 1):
    #     curr_full_text = " ".join(tokens[:index])
    #     container.markdown(curr_full_text)
    #     time.sleep(1 / speed)
    
    #Sample Example
    print('response is here......',response["output_text"])
    st.write("BidBooster: ", response["output_text"])
    #st.write("BidBooster: ", response["output_text"])

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

st.markdown("""
<style>
.small-font {
    font-size:13px !important;
    color: lightgrey !important;
}

""", unsafe_allow_html=True)

def main():
    st.header("Chat with BidBooster")
    st.markdown("""
    <style>
    input {
      border-radius: 15px;
    }
    </style>
    """, unsafe_allow_html=True)
    user_question = st.text_input("Ask a Question from the RFP Files", key="user_question")

    if user_question and api_key:  # Ensure API key and user question are provided
        if user_question:
            if st.button("Ask Question"):
                user_input(user_question, api_key)
        



    with st.sidebar:
        st.image("https://www.vgen.it/wp-content/uploads/2021/04/logo-accenture-ludo.png", width=150)
        st.markdown("")
        st.markdown("")
        
        st.markdown("""
            <style>
                @keyframes animate {
                    0%, 18%, 20%, 50.1%,60%, 65.1%, 80%,90.1%,92% {
                        color: #0e3742;
                        text-shadow: none;
                    }
                    18.1%, 20.1%, 30%,50%,60.1%,65%,80.1%,90%, 92.1%,100% {
                        color: #fff;
                        text-shadow: 0 0 10px #03bcf4,
                                    0 0 20px #03bcf4,
                                    0 0 40px #03bcf4,
                                    0 0 80px #03bcf4,
                                    0 0 160px #03bcf4;
                    }
                }

                .animated-gradient-text {
                    font-family: "Graphik Semibold";
                    font-size: 26px;
                    color: #FFF;
                    transition: color 0.5s, text-shadow 0.5s;
                }

                .animated-gradient-text:hover {
                    animation: animate 5s linear infinite;
                }

            </style>
            <p class = animated-gradient-text> BidBooster 💬 </p>    

        """, unsafe_allow_html=True)
        pdf_docs = st.file_uploader("Upload your RFP Files and Click on the Submit & Process Button", accept_multiple_files=True, key="pdf_uploader")
        if st.button("Submit & Process", key="process_button") and api_key:  # Check if API key is provided before processing
            with st.spinner("Processing..."):
                raw_text = get_pdf_text(pdf_docs)
                text_chunks = get_text_chunks(raw_text)
                get_vector_store(text_chunks, api_key)
                st.success("Done")
      #  st.image("https://media.tenor.com/s1Y9XfdN08EAAAAi/bot.gif", width=200)


if __name__ == "__main__":
    # with open('https://github.com/pranavGenAI/bidbooster/blob/475ae18b3c1f5a05a45ff983e06b025943137576/wave.css') as f:
        # css = f.read()

    st.markdown('''<style>
        .stApp > header {
        background-color: transparent;
    }
    .stApp {
        background: linear-gradient(45deg, #0a1621 20%, #0E1117 45%, #0E1117 55%, #3a5683 90%);
        animation: my_animation 20s ease infinite;
        background-size: 200% 200%;
        background-attachment: fixed;
    }
    @keyframes my_animation {
        0% {background-position: 0% 0%;}
        50% {background-position: 100% 100%;}
        100% {background-position: 0% 0%;}
    }
    [data-testid=stSidebar] {
        background: linear-gradient(360deg, #1a2631 95%, #161d29 10%);
    }
    div.stButton > button:first-child {
        background:linear-gradient(45deg, #c9024b 45%, #ba0158 55%, #cd006d 70%);
        color: white;
        border: none;
    }
    div.stButton > button:hover {
        background:linear-gradient(45deg, #ce026f 45%, #970e79 55%, #6c028d 70%);
        background-color:#ce1126;
    }
    div.stButton > button:active {
        position:relative;
        top:3px;
    }    


    </style>''', unsafe_allow_html=True)
    main()
