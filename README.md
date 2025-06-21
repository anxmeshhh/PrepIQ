# PrepIQ - AI Interview Simulator

🎯 **Master Your Interviews with AI-Powered Simulation**

PrepIQ is an advanced AI-powered interview simulator that provides realistic, domain-specific interviews with real-time feedback, emotion analysis, and personalized improvement recommendations.

## ✨ Features

- **🎤 Voice Interaction**: Real-time speech recognition and text-to-speech
- **🧠 AI Question Generation**: Dynamic questions using Google Gemini AI
- **😊 Emotion Detection**: Real-time confidence and engagement analysis
- **📊 Instant Feedback**: Detailed evaluation with improvement suggestions
- **📈 Analytics**: Comprehensive performance tracking and trends
- **🎓 Personalized Learning**: Curated resources based on your performance

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Microphone access
- Google AI API key

### Installation

1. **Clone the repository**
   \`\`\`bash
   git clone https://github.com/your-username/prepiq-interview-simulator.git
   cd prepiq-interview-simulator
   \`\`\`

2. **Run the setup script**
   \`\`\`bash
   chmod +x setup.sh
   ./setup.sh
   \`\`\`

3. **Configure your API key**
   - Copy `.env.example` to `.env`
   - Add your Google AI API key:
     \`\`\`
     GOOGLE_AI_API_KEY=your_api_key_here
     \`\`\`

4. **Start the application**
   \`\`\`bash
   python app.py
   \`\`\`

5. **Open your browser**
   Navigate to `http://localhost:5000`

## 🎯 Supported Domains

- **💻 Web Development**: Frontend, Backend, Full-stack
- **🤖 AI/Machine Learning**: Data Science, ML Engineering
- **⚡ Core Electrical**: Power Systems, Electronics, Control
- **👥 Human Resources**: Recruitment, Employee Relations

## 🛠️ Technology Stack

- **Backend**: Flask, SocketIO, Google Gemini AI
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Speech**: SpeechRecognition, gTTS, pyttsx3
- **Audio**: WebRTC, MediaRecorder API
- **Emotion**: MediaPipe (optional)

## 📁 Project Structure

\`\`\`
PrepIQ-Interview-Simulator/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── setup.sh              # Setup script
├── static/
│   ├── css/style.css     # Styling
│   ├── js/
│   │   ├── interview.js  # Interview logic
│   │   └── emotion-detection.js
│   └── audio/            # Generated audio files
├── templates/
│   ├── index.html        # Landing page
│   ├── interview.html    # Interview interface
│   └── results.html      # Results page
└── utils/                # Utility modules
\`\`\`

## 🔧 Configuration

### Environment Variables

\`\`\`bash
# Required
GOOGLE_AI_API_KEY=your_google_ai_api_key

# Optional
FLASK_ENV=development
SECRET_KEY=your_secret_key
TTS_ENGINE=gtts
TTS_LANGUAGE=en
TTS_SPEED=150
\`\`\`

### Audio Settings

The application supports multiple TTS engines:
- **gTTS**: Google Text-to-Speech (requires internet)
- **pyttsx3**: Offline text-to-speech

## 🎮 Usage

1. **Select Domain**: Choose your interview domain
2. **Set Difficulty**: Pick your experience level
3. **Start Interview**: Answer 10 AI-generated questions
4. **Get Feedback**: Receive detailed evaluation and recommendations
5. **View Results**: Analyze your performance and improvement areas

## 📊 Features in Detail

### AI Question Generation
- Domain-specific questions using Google Gemini
- Adaptive difficulty based on your level
- Mix of technical and behavioral questions

### Speech Recognition
- Real-time transcription
- Multiple engine fallback (Google, Sphinx)
- Audio quality optimization

### Emotion Analysis
- Confidence level tracking
- Engagement measurement
- Nervousness detection

### Performance Analytics
- Score breakdown by category
- Performance trends
- Response time analysis
- Personalized recommendations

## 🔒 Privacy & Security

- No audio data is stored permanently
- Session data is temporary
- API keys are securely managed
- Local processing when possible

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the `/docs` folder
- **Issues**: Report bugs on GitHub Issues
- **Discussions**: Join our GitHub Discussions

## 🙏 Acknowledgments

- Google Gemini AI for question generation
- MediaPipe for emotion detection
- SpeechRecognition library contributors
- Flask and SocketIO communities

---

**Made with ❤️ for better interview preparation**
\`\`\`
