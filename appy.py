import os
import tempfile
import streamlit as st
import speech_recognition as sr
from io import BytesIO
import time
import requests
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from dotenv import load_dotenv
import streamlit.components.v1 as components
import random

# Load environment variables
load_dotenv()

# Check if API key is set
if not os.getenv("GOOGLE_API_KEY"):
    st.error("Please set your GOOGLE_API_KEY environment variable")
    st.stop()

# Check for ElevenLabs API key
if not os.getenv("ELEVENLABS_API_KEY"):
    st.warning("ElevenLabs API key not found. Voice will use fallback TTS")
    USE_ELEVENLABS = False
else:
    USE_ELEVENLABS = True

# Initialize session state variables
if 'history' not in st.session_state:
    st.session_state.history = []
if 'vectorstore' not in st.session_state:
    st.session_state.vectorstore = None
if 'user_name' not in st.session_state:
    st.session_state.user_name = ""
if 'setup_complete' not in st.session_state:
    st.session_state.setup_complete = False
if 'voice_mode' not in st.session_state:
    st.session_state.voice_mode = False
if 'voice_id' not in st.session_state:
    # Default ElevenLabs voice ID
    st.session_state.voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel (friendly, warm teacher)
if 'pdf_info' not in st.session_state:
    st.session_state.pdf_info = ""
if 'pdf_names' not in st.session_state:
    st.session_state.pdf_names = []
if 'theme_color' not in st.session_state:
    st.session_state.theme_color = "#A0D8EF"  # Default sky blue
if 'character' not in st.session_state:
    st.session_state.character = "owl"  # Default character

# Custom CSS and JavaScript for animations
def load_css_and_js():
    # Custom CSS for animations and styling
    st.markdown("""
    <style>
    /* Main theme colors */
    :root {
        --primary-color: """ + st.session_state.theme_color + """;
        --secondary-color: #66c2ff;
        --accent-color: #ff9ee5;
        --background-color: #f0faff;
        --text-color: #2c3e50;
    }
    
    /* Overall app styling */
    .main {
        background-color: var(--background-color);
        background-image: 
            radial-gradient(circle at 10% 20%, rgba(255, 255, 255, 0.6) 0%, rgba(255, 255, 255, 0.1) 40%), 
            linear-gradient(to bottom, rgba(160, 216, 239, 0.2) 0%, rgba(160, 216, 239, 0.1) 100%);
        color: var(--text-color);
    }
    
    /* Header styling */
    h1, h2, h3 {
        color: #2980b9;
        font-family: 'Poppins', sans-serif;
        font-weight: 600;
        text-shadow: 1px 1px 2px rgba(0,0,0,0.1);
    }
    
    h1 {
        background: linear-gradient(45deg, #2980b9, #6dd5fa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.8rem !important;
    }
    
    /* Button styling */
    .stButton > button {
        background-color: var(--primary-color);
        color: white;
        border-radius: 20px;
        padding: 0.5rem 1rem;
        font-weight: 500;
        border: none;
        box-shadow: 0 4px 6px rgba(50, 50, 93, 0.11), 0 1px 3px rgba(0, 0, 0, 0.08);
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 7px 14px rgba(50, 50, 93, 0.1), 0 3px 6px rgba(0, 0, 0, 0.08);
        background-color: var(--secondary-color);
    }
    
    /* Chat container styling */
    .css-1cypcdb, .css-fblp2m {
        border-radius: 15px !important;
        border: 2px solid rgba(160, 216, 239, 0.3) !important;
        box-shadow: 0 4px 6px rgba(50, 50, 93, 0.11), 0 1px 3px rgba(0, 0, 0, 0.08) !important;
    }
    
    /* Chat bubbles for assistant and user */
    .stChatMessage {
        padding: 1rem;
        border-radius: 15px;
        margin-bottom: 0.5rem;
        animation: fadeIn 0.5s ease-in-out;
    }
    
    /* Animations */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes float {
        0% { transform: translateY(0px); }
        50% { transform: translateY(-10px); }
        100% { transform: translateY(0px); }
    }
    
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    
    /* Character animation */
    .character {
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 100px;
        height: 100px;
        z-index: 1000;
        animation: float 3s ease-in-out infinite;
    }
    
    /* Floating particles */
    .particle {
        position: fixed;
        background-color: var(--primary-color);
        border-radius: 50%;
        opacity: 0.6;
        z-index: -1;
        animation: float 4s infinite ease-in-out;
    }
    
    /* File uploader */
    .uploadedFile {
        background-color: rgba(255, 255, 255, 0.7);
        border-radius: 10px;
        padding: 10px;
        margin-bottom: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    
    .uploadedFile:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    /* Sidebar styling */
    .css-1d391kg, .css-1544g2n {
        background-color: rgba(255, 255, 255, 0.85);
        border-right: 1px solid rgba(160, 216, 239, 0.3);
    }
    
    /* Progress bars and spinners */
    .stProgress > div > div {
        background-color: var(--primary-color);
    }
    
    .stSpinner > div {
        border-top-color: var(--primary-color) !important;
    }
    
    /* Custom cursor */
     * {
     cursor: default;
# }
    </style>
    """, unsafe_allow_html=True)
    
    # JavaScript for interactive elements and particles
    components.html("""
    <script>
    // Create floating particles
    function createParticles() {
        const container = document.querySelector('body');
        const particleCount = 15;
        
        for (let i = 0; i < particleCount; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';
            
            // Random size between 5-20px
            const size = Math.random() * 15 + 5;
            particle.style.width = `${size}px`;
            particle.style.height = `${size}px`;
            
            // Random position
            particle.style.left = `${Math.random() * 100}vw`;
            particle.style.top = `${Math.random() * 100}vh`;
            
            // Random animation duration
            const duration = Math.random() * 10 + 5;
            particle.style.animationDuration = `${duration}s`;
            
            // Random delay
            particle.style.animationDelay = `${Math.random() * 5}s`;
            
            // Random opacity
            particle.style.opacity = Math.random() * 0.5 + 0.1;
            
            container.appendChild(particle);
        }
    }
    
    // Mouse follow effect
    function setupMouseFollow() {
        const body = document.querySelector('body');
        
        body.addEventListener('mousemove', (e) => {
            const trail = document.createElement('div');
            trail.className = 'particle';
            trail.style.width = '8px';
            trail.style.height = '8px';
            trail.style.left = `${e.clientX}px`;
            trail.style.top = `${e.clientY}px`;
            trail.style.opacity = '0.6';
            trail.style.position = 'fixed';
            trail.style.pointerEvents = 'none';
            trail.style.zIndex = '9999';
            trail.style.backgroundColor = '#A0D8EF';
            trail.style.borderRadius = '50%';
            
            body.appendChild(trail);
            
            // Remove after animation
            setTimeout(() => {
                trail.style.transition = 'all 0.5s ease';
                trail.style.opacity = '0';
                trail.style.transform = 'scale(2)';
                
                setTimeout(() => {
                    body.removeChild(trail);
                }, 500);
            }, 100);
        });
    }
    
    // Initialize animations when DOM is loaded
    document.addEventListener('DOMContentLoaded', () => {
        createParticles();
        setupMouseFollow();
        
        // Refresh particles every minute
        setInterval(() => {
            const oldParticles = document.querySelectorAll('.particle');
            oldParticles.forEach(particle => {
                if (!particle.style.left.includes('clientX')) {
                    particle.remove();
                }
            });
            createParticles();
        }, 60000);
    });
    </script>
    """, height=0)

# Character animations
def load_character(character="owl"):
    characters = {
        "owl": """
            <div style="position: fixed; bottom: 20px; right: 20px; z-index: 1000; animation: float 3s ease-in-out infinite;">
                <svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="50" cy="50" r="40" fill="#A0D8EF" />
                    <circle cx="35" cy="40" r="10" fill="white" />
                    <circle cx="65" cy="40" r="10" fill="white" />
                    <circle cx="35" cy="40" r="5" fill="black" />
                    <circle cx="65" cy="40" r="5" fill="black" />
                    <ellipse cx="50" cy="60" rx="8" ry="5" fill="#FF9EE5" />
                    <path d="M30 25 L40 10 L50 25" fill="#A0D8EF" stroke="#5D8AA8" stroke-width="2" />
                    <path d="M70 25 L60 10 L50 25" fill="#A0D8EF" stroke="#5D8AA8" stroke-width="2" />
                </svg>
            </div>
        """,
        "cat": """
            <div style="position: fixed; bottom: 20px; right: 20px; z-index: 1000; animation: float 3s ease-in-out infinite;">
                <svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="50" cy="50" r="40" fill="#FFC0CB" />
                    <circle cx="35" cy="40" r="8" fill="white" />
                    <circle cx="65" cy="40" r="8" fill="white" />
                    <circle cx="35" cy="40" r="4" fill="black" />
                    <circle cx="65" cy="40" r="4" fill="black" />
                    <ellipse cx="50" cy="60" rx="6" ry="4" fill="#FF6B6B" />
                    <path d="M25 30 L10 10 L30 20" fill="#FFC0CB" stroke="#FF6B6B" stroke-width="2" />
                    <path d="M75 30 L90 10 L70 20" fill="#FFC0CB" stroke="#FF6B6B" stroke-width="2" />
                </svg>
            </div>
        """,
        "robot": """
            <div style="position: fixed; bottom: 20px; right: 20px; z-index: 1000; animation: float 3s ease-in-out infinite;">
                <svg width="100" height="100" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                    <rect x="25" y="25" width="50" height="60" rx="10" fill="#A0D8EF" />
                    <rect x="35" y="45" width="10" height="5" rx="2" fill="#5D8AA8" />
                    <rect x="55" y="45" width="10" height="5" rx="2" fill="#5D8AA8" />
                    <rect x="40" y="60" width="20" height="5" rx="2" fill="#5D8AA8" />
                    <circle cx="40" cy="35" r="5" fill="#FFD700" />
                    <circle cx="60" cy="35" r="5" fill="#FFD700" />
                    <rect x="45" y="15" width="10" height="10" fill="#A0D8EF" />
                </svg>
            </div>
        """
    }
    
    return characters.get(character, characters["owl"])

# Function to convert speech to text
def speech_to_text():
    r = sr.Recognizer()
    with st.spinner("Listening..."):
        with sr.Microphone() as source:
            st.info("Speak now...")
            r.adjust_for_ambient_noise(source)
            audio = r.listen(source)
            st.success("Recording complete!")
        
        try:
            with st.spinner("Processing your speech..."):
                text = r.recognize_google(audio)
                return text
        except sr.UnknownValueError:
            st.error("Sorry, I couldn't understand what you said.")
            return None
        except sr.RequestError:
            st.error("Could not request results; check your network connection")
            return None

# ElevenLabs TTS function
def elevenlabs_tts(text, voice_id=None):
    if voice_id is None:
        voice_id = st.session_state.voice_id
        
    # Define the API endpoint
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    # Define the headers
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": os.getenv("ELEVENLABS_API_KEY")
    }
    
    # Define the data to be sent in the request
    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.25,  # Slightly more expressive
            "use_speaker_boost": True
        }
    }
    
    try:
        # Make the request
        response = requests.post(url, json=data, headers=headers)
        
        # Check if the request was successful
        if response.status_code == 200:
            return BytesIO(response.content)
        else:
            st.error(f"Error with ElevenLabs API: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error with ElevenLabs API: {str(e)}")
        return None

# Fallback to gTTS if ElevenLabs is not available
def fallback_tts(text):
    from gtts import gTTS
    tts = gTTS(text=text, lang='en', slow=False)
    fp = BytesIO()
    tts.write_to_fp(fp)
    fp.seek(0)
    return fp

# Unified text to speech function
def text_to_speech(text):
    if USE_ELEVENLABS:
        audio_data = elevenlabs_tts(text)
        if audio_data is not None:
            return audio_data
        
    # Fallback to gTTS if ElevenLabs fails or is not available
    return fallback_tts(text)

# Preprocess AI response to be more conversational for speech
def prepare_for_tts(text, user_name):
    # Simple preprocessing to make the response more conversational
    # Remove markdown formatting and unnecessary punctuation
    text = text.replace('*', '')
    text = text.replace('#', '')
    text = text.replace('`', '')
    
    # Add pauses for better speech rhythm (using commas)
    text = text.replace('. ', ', ')
    
    # Personalize even more by adding interjections
    interjections = [
        f"Alright {user_name}, ",
        f"So {user_name}, ",
        f"Now {user_name}, ",
        f"You know {user_name}, ",
        f"Let me explain this to you {user_name}. ",
        f"Here's the thing {user_name}, "
    ]
    
    if random.random() > 0.7:  # Randomly add interjections (30% chance)
        text = random.choice(interjections) + text
    
    return text

# Function to extract and summarize PDF content
def extract_pdf_summary(all_pages, pdf_names):
    total_pages = len(all_pages)
    pdf_summary = f"I've processed {total_pages} pages from {len(pdf_names)} document(s): {', '.join(pdf_names)}."
    
    # Get a sample of content to confirm processing
    sample_texts = []
    for i, page in enumerate(all_pages[:5]):  # Just look at first 5 pages
        # Extract just the first 100 chars from each page
        sample = page.page_content[:100].replace('\n', ' ').strip()
        if sample:
            sample_texts.append(sample + "...")
    
    content_sample = "\n\nSample content includes: " + " ".join(sample_texts[:2])
    return pdf_summary + content_sample

# Add confetti animation
def show_confetti():
    components.html("""
    <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.5.1/dist/confetti.browser.min.js"></script>
    <script>
        confetti({
            particleCount: 100,
            spread: 70,
            origin: { y: 0.6 }
        });
    </script>
    """, height=0)

# Load CSS and JS
load_css_and_js()

# Title and description with animation
st.markdown("""
<h1 style="text-align: center; animation: pulse 2s infinite ease-in-out;">✨ Interactive AI Study Buddy ✨</h1>
<p style="text-align: center; font-size: 1.2rem; color: #5D8AA8; animation: fadeIn 1s;">Upload your learning materials and have a fun, natural conversation with your AI tutor!</p>
""", unsafe_allow_html=True)



# Inject the selected character into the main area
st.markdown(load_character(st.session_state.character), unsafe_allow_html=True)

# User registration form with animated background
if not st.session_state.user_name:
    st.markdown("""
    <div style="
        background: linear-gradient(45deg, rgba(160, 216, 239, 0.3), rgba(255, 182, 193, 0.3));
        padding: 30px;
        border-radius: 20px;
        box-shadow: 0 8px 32px rgba(31, 38, 135, 0.2);
        backdrop-filter: blur(4px);
        border: 1px solid rgba(255, 255, 255, 0.18);
        animation: fadeIn 1s ease-in-out;
        margin-top: 50px;
    ">
        <h2 style="text-align: center; margin-bottom: 20px;">Let's Get Started!</h2>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("user_form"):
        st.markdown("<style>input {border-radius: 10px !important; padding: 10px !important;}</style>", unsafe_allow_html=True)
        user_name = st.text_input("What's your name?", placeholder="Type your name here...")
        submit_button = st.form_submit_button("Let's Start Learning! 🚀")
        
        if submit_button and user_name:
            st.session_state.user_name = user_name
            show_confetti()
            st.success(f"Welcome, {user_name}! Please upload your learning materials.")
            st.rerun()

# PDF upload section with animated cards
if st.session_state.user_name and not st.session_state.setup_complete:
    st.markdown(f"""
    <div style="
        background: linear-gradient(45deg, rgba(160, 216, 239, 0.3), rgba(255, 255, 255, 0.5));
        padding: 30px;
        border-radius: 20px;
        box-shadow: 0 8px 32px rgba(31, 38, 135, 0.2);
        backdrop-filter: blur(4px);
        border: 1px solid rgba(255, 255, 255, 0.18);
        animation: fadeIn 1s ease-in-out;
        margin: 20px 0;
    ">
        <h2 style="text-align: center; margin-bottom: 20px;">Hi {st.session_state.user_name}! Let's prepare your study materials</h2>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader("Upload PDF files", type="pdf", accept_multiple_files=True)
    
    if uploaded_files:
        st.markdown("<div class='uploadedFiles' style='margin-top: 20px;'>", unsafe_allow_html=True)
        for file in uploaded_files:
            st.markdown(f"""
            <div class="uploadedFile" style="animation: fadeIn 0.5s ease-in-out">
                <h4>📄 {file.name}</h4>
                <div style="height: 5px; border-radius: 5px; background: linear-gradient(90deg, {st.session_state.theme_color}, rgba(255,255,255,0.5))"></div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Voice selection with animated cards
    if USE_ELEVENLABS:
        st.markdown("<h3 style='margin-top: 30px;'>Customize Your Tutor's Voice</h3>", unsafe_allow_html=True)
        
        voice_options = {
            "Rachel (Friendly Female)": "21m00Tcm4TlvDq8ikWAM",
            "Adam (Professional Male)": "pNInz6obpgDQGcFmaJgB",
            "Clyde (Wise Elder)": "2EiwWnXFnvU5JabPnv8n",
            "Domi (Young Enthusiastic)": "AZnzlk1XvdvUeBnXmlld",
            "Bella (Supportive Mentor)": "EXAVITQu4vr4xnSDxMaL"
        }
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div style="padding: 15px; background: rgba(255,255,255,0.7); border-radius: 15px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: all 0.3s ease;">
                <h4>👩‍🏫 Female Voices</h4>
                <ul style="list-style-type: none; padding-left: 0;">
                    <li style="margin-bottom: 10px;">🎙️ Rachel - Friendly Teacher</li>
                    <li style="margin-bottom: 10px;">🎙️ Domi - Young & Enthusiastic</li>
                    <li style="margin-bottom: 10px;">🎙️ Bella - Supportive Mentor</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div style="padding: 15px; background: rgba(255,255,255,0.7); border-radius: 15px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: all 0.3s ease;">
                <h4>👨‍🏫 Male Voices</h4>
                <ul style="list-style-type: none; padding-left: 0;">
                    <li style="margin-bottom: 10px;">🎙️ Adam - Professional Educator</li>
                    <li style="margin-bottom: 10px;">🎙️ Clyde - Wise & Experienced</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        
        selected_voice = st.selectbox("Choose your tutor's voice:", list(voice_options.keys()), 
                                      help="Select the voice that will read the AI responses to you")
        st.session_state.voice_id = voice_options[selected_voice]
    
    # Process PDFs button with animation
    if uploaded_files:
        if st.button("🚀 Process PDFs and Start Learning!", help="Click to analyze your documents and begin learning"):
            with st.spinner("Processing your documents... This might take a minute."):
                # Create progress bar
                progress_bar = st.progress(0)
                
                # Save uploaded files to temp directory
                temp_dir = tempfile.mkdtemp()
                file_paths = []
                pdf_names = []
                
                for i, uploaded_file in enumerate(uploaded_files):
                    file_path = os.path.join(temp_dir, uploaded_file.name)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    file_paths.append(file_path)
                    pdf_names.append(uploaded_file.name)
                    # Update progress
                    progress_bar.progress((i + 1) / (len(uploaded_files) * 2))
                
                st.session_state.pdf_names = pdf_names
                
                # Load all PDFs
                all_pages = []
                for i, path in enumerate(file_paths):
                    try:
                        loader = PyPDFLoader(path)
                        pages = loader.load()
                        all_pages.extend(pages)
                    except Exception as e:
                        st.error(f"Error loading PDF {path}: {str(e)}")
                    # Update progress
                    progress_bar.progress(0.5 + (i + 1) / (len(file_paths) * 2))
                
                if not all_pages:
                    st.error("Could not extract any content from the PDFs. Please check the files and try again.")
                    st.stop()
                
                # Extract summary of PDF content
                pdf_summary = extract_pdf_summary(all_pages, pdf_names)
                st.session_state.pdf_info = pdf_summary
                
                # Split text into chunks
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=200
                )
                splits = text_splitter.split_documents(all_pages)
                
                # Create embeddings and vectorstore
                embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
                vectorstore = FAISS.from_documents(splits, embeddings)
                st.session_state.vectorstore = vectorstore
                st.session_state.setup_complete = True
                
                # Complete the progress bar
                progress_bar.progress(1.0)
                time.sleep(1)  # Pause to show completion
                
                # Add initial greeting to history
                greeting = f"Hello {st.session_state.user_name}! I'm your AI tutor. I've processed your learning materials: {', '.join(pdf_names)}. I have full access to the content and I'm ready to help you understand the material better. What would you like to learn about today?"
                st.session_state.history.append({"role": "assistant", "content": greeting})
                
                # Show confetti for completion
                show_confetti()
                
                # Auto-play the greeting
                audio_bytes = text_to_speech(greeting)
                st.audio(audio_bytes, format="audio/mp3", autoplay=True)
                
                st.success("PDF processing complete! You can now start your conversation.")
                st.rerun()

# Chat interface with animated bubbles
if st.session_state.setup_complete:
    # Apply theme color
    load_css_and_js()
    
    st.markdown(f"""
    <div style="
        background: linear-gradient(45deg, rgba(160, 216, 239, 0.2), rgba(255, 255, 255, 0.3));
        padding: 20px;
        border-radius: 20px;
        box-shadow: 0 8px 32px rgba(31, 38, 135, 0.1);
        backdrop-filter: blur(4px);
        border: 1px solid rgba(255, 255, 255, 0.18);
        animation: fadeIn 1s ease-in-out;
        margin-bottom: 20px;
    ">
        <h2 style="text-align: center; margin-bottom: 10px;">✨ {st.session_state.user_name}'s Learning Journey ✨</h2>
        <p style="text-align: center; font-size: 1rem; color: #5D8AA8;">Chat with your AI tutor about the material you've uploaded!</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Voice mode toggle with animation
    voice_col1, voice_col2 = st.columns([3, 1])
    
    with voice_col1:
        st.markdown("""
        <div style="display: flex; align-items: center;">
            <h3 style="margin-right: 15px; margin-bottom: 0;">Voice Interaction</h3>
            <div style="height: 20px; width: 20px; background-color: var(--primary-color); border-radius: 50%; animation: pulse 2s infinite;"></div>
        </div>
        """, unsafe_allow_html=True)
    
    with voice_col2:
        st.session_state.voice_mode = st.toggle("Enable Voice", st.session_state.voice_mode)
    
    # Display PDF info in a styled box
    with st.sidebar:
        st.markdown("""
        <div style="
            background: rgba(255, 255, 255, 0.7);
            padding: 15px;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-top: 20px;
            animation: fadeIn 1s ease-in-out;
        ">
            <h3 style="margin-top: 0;">📚 Study Materials</h3>
        """, unsafe_allow_html=True)
        
        for pdf_name in st.session_state.pdf_names:
            st.markdown(f"""
            <div style="
                background: linear-gradient(45deg, {st.session_state.theme_color}33, #ffffff99);
                padding: 8px 12px;
                border-radius: 10px;
                margin-bottom: 8px;
                font-size: 0.9rem;
                display: flex;
                align-items: center;
            ">
                <span>📄 {pdf_name}</span>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Display chat container with styled background
    chat_container = st.container()
    with chat_container:
        # Display chat history with animated bubbles
        for message in st.session_state.history:
            with st.chat_message(message["role"]):
                st.markdown(f"""
                <div style="animation: fadeIn 0.5s ease-in-out;">
                    {message["content"]}
                </div>
                """, unsafe_allow_html=True)
    
    # Voice input button with animation
    if st.session_state.voice_mode:
        if st.button("🎤 Speak Your Question", help="Click and speak to ask your question"):
            user_query = speech_to_text()
            if user_query:
                st.info(f"You said: {user_query}")
                time.sleep(1)  # Give user time to see what was recognized
            else:
                st.warning("No speech detected. Please try again.")
                st.rerun()
    else:
        # Text input with custom styling
        user_query = st.chat_input("Ask your question...")
    
    # Process query if available
    if 'user_query' in locals() and user_query:
        # Add user message to history
        st.session_state.history.append({"role": "user", "content": user_query})
        
        # Display user message with animation
        with st.chat_message("user"):
            st.markdown(f"""
            <div style="animation: fadeIn 0.5s ease-in-out;">
                {user_query}
            </div>
            """, unsafe_allow_html=True)
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Create a thinking animation
                components.html("""
                <div style="display: flex; justify-content: center; margin: 10px 0;">
                    <div style="width: 10px; height: 10px; background-color: var(--primary-color); border-radius: 50%; margin: 0 5px; animation: pulse 1s infinite ease-in-out;"></div>
                    <div style="width: 10px; height: 10px; background-color: var(--primary-color); border-radius: 50%; margin: 0 5px; animation: pulse 1s infinite ease-in-out 0.2s;"></div>
                    <div style="width: 10px; height: 10px; background-color: var(--primary-color); border-radius: 50%; margin: 0 5px; animation: pulse 1s infinite ease-in-out 0.4s;"></div>
                </div>
                """, height=50)
                
                # Create Gemini model instance
                llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.7)
                
                # Create retriever
                retriever = st.session_state.vectorstore.as_retriever(
                    search_type="similarity",
                    search_kwargs={"k": 5}
                )
                
                # Create prompt template with explicit PDF info
                system_template = """You are a friendly and helpful tutor who speaks naturally like a real teacher.
                
                PDF INFORMATION: {pdf_info}
                
                Use the following context from the PDFs to answer the student's question:  
                {context}
                
                You ALWAYS have access to the PDFs that were uploaded. If you don't find the exact answer in the context, 
                try to provide information based on what you do see in the context. Only if you truly can't find anything 
                related should you politely say so and offer to discuss related concepts.
                
                Your tone should be warm, encouraging, and conversational - like a supportive teacher who wants to see their students succeed.
                Use examples, analogies, and a touch of humor where appropriate to make complex concepts easier to understand.
                
                Keep your responses fairly concise so they can be comfortably spoken back to the user.
                Use contractions (don't, can't, etc.) and casual phrases like a real teacher would use.
                Break up long sentences into shorter ones. Vary your sentence structure.
                
                Sometimes use interjections like "Hmm," "Well," "You know," "So," etc. to sound more natural.
                Occasionally refer to the student by name.
                
                Remember that you're speaking to {user_name}, so address them personally and be encouraging.
                """
                
                user_template = "{input}"
                
                prompt = ChatPromptTemplate.from_messages([
                    ("system", system_template),
                    ("human", user_template)
                ])
                
                prompt = prompt.partial(user_name=st.session_state.user_name, pdf_info=st.session_state.pdf_info)
                
                # Create document chain
                document_chain = create_stuff_documents_chain(llm, prompt)
                
                # Create retrieval chain
                retrieval_chain = create_retrieval_chain(retriever, document_chain)
                
                # Run the chain
                response = retrieval_chain.invoke({"input": user_query})
                answer = response["answer"]
                
                # Display text response with animation
                st.markdown(f"""
                <div style="animation: fadeIn 0.5s ease-in-out;">
                    {answer}
                </div>
                """, unsafe_allow_html=True)
                
                # Add response to history
                st.session_state.history.append({"role": "assistant", "content": answer})
                
                # If voice mode is enabled, speak the response
                if st.session_state.voice_mode:
                    # Prepare the text for more natural speech
                    speech_text = prepare_for_tts(answer, st.session_state.user_name)
                    audio_bytes = text_to_speech(speech_text)
                    st.audio(audio_bytes, format="audio/mp3", autoplay=True)

# Add a reset button with animation
if st.session_state.setup_complete:
    with st.sidebar:
        st.markdown("""
        <div style="margin-top: 30px; animation: fadeIn 1s ease-in-out;">
            <h3>Session Controls</h3>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🔄 Start New Session", help="Clear current session and upload new materials"):
            # Show loading animation
            st.markdown("""
            <div style="display: flex; justify-content: center; margin: 20px 0;">
                <div style="width: 20px; height: 20px; border-radius: 50%; border: 3px solid #f3f3f3; border-top: 3px solid var(--primary-color); animation: spin 1s linear infinite;"></div>
            </div>
            <style>
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            </style>
            """, unsafe_allow_html=True)
            
            st.session_state.history = []
            st.session_state.vectorstore = None
            st.session_state.setup_complete = False
            st.session_state.pdf_info = ""
            st.session_state.pdf_names = []
            time.sleep(1)  # Brief pause for visual feedback
            st.rerun()

# Show voice selection in sidebar when setup is complete
if st.session_state.setup_complete and USE_ELEVENLABS:
    with st.sidebar:
        st.markdown("""
        <div style="
            background: rgba(255, 255, 255, 0.7);
            padding: 15px;
            border-radius: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-top: 20px;
            animation: fadeIn 1s ease-in-out;
        ">
            <h3 style="margin-top: 0;">🎤 Voice Settings</h3>
        """, unsafe_allow_html=True)
        
        voice_options = {
            "Rachel (Friendly Female)": "21m00Tcm4TlvDq8ikWAM",
            "Adam (Professional Male)": "pNInz6obpgDQGcFmaJgB",
            "Clyde (Wise Elder)": "2EiwWnXFnvU5JabPnv8n",
            "Domi (Young Enthusiastic)": "AZnzlk1XvdvUeBnXmlld",
            "Bella (Supportive Mentor)": "EXAVITQu4vr4xnSDxMaL"
        }
        
        selected_voice = st.selectbox("Change your tutor's voice:", list(voice_options.keys()))
        if st.session_state.voice_id != voice_options[selected_voice]:
            st.session_state.voice_id = voice_options[selected_voice]
            st.success("Voice updated!")
        
        st.markdown("</div>", unsafe_allow_html=True)

# Add footer with credits
st.markdown("""
<div style="position: fixed; bottom: 0; left: 0; width: 100%; background-color: rgba(255, 255, 255, 0.7); padding: 10px; text-align: center; font-size: 0.8rem; color: #666;">
    ✨ Interactive AI Study Buddy • Made with 💙 for learning
</div>
""", unsafe_allow_html=True)