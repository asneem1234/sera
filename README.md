# ✨ Sera-Talk to you Documents ✨

An engaging, voice-enabled AI tutor that helps you learn from your PDF study materials through natural conversation.

![AI Study Buddy](https://i.imgur.com/placeholder-image.jpg)

## 🚀 Features

- **PDF Analysis**: Upload your textbooks, notes, or study materials in PDF format
- **Natural Conversations**: Chat with your AI tutor about specific topics in your materials
- **Voice Interaction**: Speak your questions and hear responses with lifelike voices
- **Customizable Experience**: Choose different tutor voices and characters
- **Beautiful UI**: Engaging, animated interface that makes learning enjoyable

## 📋 Prerequisites

- Python 3.8 or higher
- Google API key for Gemini AI
- ElevenLabs API key for realistic voice responses (optional)

## 🔧 Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/interactive-ai-study-buddy.git
   cd interactive-ai-study-buddy
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project directory with the following content:
   ```
   GOOGLE_API_KEY=your_google_api_key_here
   ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
   ```

## 🎓 How to Use

1. Run the application:
   ```bash
   streamlit run appy.py
   ```

2. Enter your name when prompted to personalize your learning experience.

3. Upload your PDF study materials. The application will process and analyze them.

4. Start asking questions about the content! You can:
   - Type your questions in the chat input
   - Toggle voice mode and use the microphone to speak your questions

5. Your AI tutor will provide conversational, informative responses based on your materials.

## 🛠️ Technologies Used

- **Streamlit**: For the web interface
- **LangChain**: For document processing and retrieval
- **Google Generative AI (Gemini)**: For generating intelligent responses
- **FAISS**: For vector storage and similarity search
- **ElevenLabs API**: For lifelike text-to-speech (optional, falls back to gTTS)
- **Speech Recognition**: For converting spoken questions to text

## 🎭 Voice and Character Options

The application offers several voice options through ElevenLabs:
- Rachel (Friendly Female)
- Adam (Professional Male)
- Clyde (Wise Elder)
- Domi (Young Enthusiastic)
- Bella (Supportive Mentor)

You can also choose from different animated characters:
- Owl (Default)
- Cat
- Robot

## 🔑 API Keys

- **Google API Key**: Required for Gemini AI. Get it from [Google AI Studio](https://ai.google.dev/).
- **ElevenLabs API Key**: Optional for high-quality voices. Get it from [ElevenLabs](https://elevenlabs.io/).

## 📝 Example Questions

After uploading your learning materials, try asking:
- "Can you summarize the main concepts in Chapter 3?"
- "Explain the process of photosynthesis mentioned in the document."
- "What are the key differences between the theories discussed on page 42?"
- "Give me a simple explanation of [complex topic] from the material."

## 📷 Screenshots

![Welcome Screen](https://i.imgur.com/placeholder-welcome.jpg)
![Chat Interface](https://i.imgur.com/placeholder-chat.jpg)

## 📜 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ✨ Acknowledgements

- Special thanks to the developers of all the open-source libraries used in this project.
- Icons and animations inspired by various open-source projects.

---

Made with 💙 for enhanced learning
