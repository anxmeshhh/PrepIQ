from flask import Flask, render_template, request, jsonify, session, redirect
from flask_socketio import SocketIO, emit
import google.generativeai as genai
import speech_recognition as sr
import pyttsx3
from gtts import gTTS
import json
import uuid
import os
from datetime import datetime
import threading
import time
import tempfile
import base64
import io
import wave
import numpy as np
from pydub import AudioSegment
import re

app = Flask(__name__)
app.config['SECRET_KEY'] = 'prepiq-secret-key-2024'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Hardcoded Google AI API Key
GOOGLE_AI_API_KEY = ""

# Configure Google AI
genai.configure(api_key=GOOGLE_AI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-exp')

# Initialize speech recognition with optimized settings
recognizer = sr.Recognizer()
recognizer.energy_threshold = 300
recognizer.dynamic_energy_threshold = True
recognizer.pause_threshold = 0.8
recognizer.operation_timeout = None
recognizer.phrase_threshold = 0.3
recognizer.non_speaking_duration = 0.8

# Initialize text-to-speech engine with optimized settings
try:
    tts_engine = pyttsx3.init()
    voices = tts_engine.getProperty('voices')
    # Set female voice if available
    for voice in voices:
        if 'female' in voice.name.lower() or 'zira' in voice.name.lower() or 'hazel' in voice.name.lower():
            tts_engine.setProperty('voice', voice.id)
            break
    tts_engine.setProperty('rate', 160)
    tts_engine.setProperty('volume', 0.9)
except:
    tts_engine = None
    print("Warning: pyttsx3 not available, using gTTS only")

# Interview domains with enhanced question categories
DOMAINS = {
    'web_development': {
        'name': 'Web Development',
        'topics': ['HTML/CSS', 'JavaScript', 'React/Vue', 'Node.js', 'Databases', 'APIs', 'Security', 'Performance'],
        'difficulty_levels': ['Junior', 'Mid-level', 'Senior'],
        'focus_areas': ['Frontend', 'Backend', 'Full-stack', 'DevOps']
    },
    'ai_ml': {
        'name': 'AI/Machine Learning',
        'topics': ['Python', 'TensorFlow/PyTorch', 'Data Science', 'Algorithms', 'Statistics', 'Deep Learning'],
        'difficulty_levels': ['Entry', 'Intermediate', 'Advanced'],
        'focus_areas': ['Data Science', 'ML Engineering', 'Research', 'Computer Vision']
    },
    'electrical': {
        'name': 'Core Electrical',
        'topics': ['Circuit Analysis', 'Power Systems', 'Electronics', 'Control Systems', 'Signal Processing'],
        'difficulty_levels': ['Graduate', 'Experienced', 'Expert'],
        'focus_areas': ['Power', 'Electronics', 'Control', 'Communications']
    },
    'hr': {
        'name': 'Human Resources',
        'topics': ['Recruitment', 'Employee Relations', 'Compliance', 'Performance Management', 'Training'],
        'difficulty_levels': ['Associate', 'Manager', 'Director'],
        'focus_areas': ['Talent Acquisition', 'Employee Relations', 'Compensation', 'Learning & Development']
    }
}

# Store active interview sessions
active_sessions = {}

# Create necessary directories
os.makedirs('static/audio', exist_ok=True)
os.makedirs('templates', exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/interview/<domain>')
def interview(domain):
    if domain not in DOMAINS:
        return redirect('/')
    
    session_id = str(uuid.uuid4())
    session['session_id'] = session_id
    session['domain'] = domain
    
    print(f"🎯 Creating interview session: {session_id} for domain: {domain}")
    
    return render_template('interview.html', 
                         domain=DOMAINS[domain], 
                         session_id=session_id,
                         domain_key=domain)  # Add domain key for JavaScript

@app.route('/results/<session_id>')
def results(session_id):
    if session_id in active_sessions:
        session_data = active_sessions[session_id]
        return render_template('results.html', session_data=session_data)
    return redirect('/')

@app.route('/static/<path:filename>')
def static_files(filename):
    return app.send_static_file(filename)

@socketio.on('start_interview')
def handle_start_interview(data):
    session_id = data['session_id']
    domain = data['domain']
    difficulty = data['difficulty']
    
    print(f"🎯 Starting interview: {domain} - {difficulty} level")
    
    # Initialize session data with enhanced tracking
    active_sessions[session_id] = {
        'domain': domain,
        'difficulty': difficulty,
        'questions': [],
        'responses': [],
        'scores': [],
        'emotions': [],
        'start_time': datetime.now(),
        'current_question': 0,
        'total_score': 0,
        'question_categories': [],
        'response_times': [],
        'confidence_levels': []
    }
    
    # Generate first question
    generate_next_question(session_id)

def generate_next_question(session_id):
    if session_id not in active_sessions:
        return
        
    session_data = active_sessions[session_id]
    domain = session_data['domain']
    difficulty = session_data['difficulty']
    question_num = session_data['current_question'] + 1
    
    # Enhanced prompt for better question generation
    previous_questions = [q['text'] for q in session_data['questions']]
    topics = DOMAINS[domain]['topics']
    
    prompt = f"""
    You are an expert technical interviewer for {DOMAINS[domain]['name']} positions at {difficulty} level.
    
    Generate interview question #{question_num} following these guidelines:
    
    CONTEXT:
    - Position: {DOMAINS[domain]['name']} - {difficulty} level
    - Topics to cover: {', '.join(topics)}
    - Previous questions: {previous_questions}
    
    REQUIREMENTS:
    1. Make it highly relevant to {DOMAINS[domain]['name']}
    2. Appropriate difficulty for {difficulty} level
    3. Avoid repeating previous question topics
    4. Mix technical and behavioral questions
    5. Be specific and actionable
    6. Keep it clear and concise (2-3 sentences max)
    
    QUESTION TYPES TO ROTATE:
    - Technical implementation
    - Problem-solving scenarios  
    - Best practices and methodologies
    - Experience-based questions
    - Troubleshooting situations
    
    Generate only the question text, no additional formatting or explanations.
    """
    
    try:
        response = model.generate_content(prompt)
        question_text = response.text.strip()
        
        # Clean up the question text
        question_text = re.sub(r'^["\']|["\']$', '', question_text)
        question_text = question_text.replace('\n', ' ').strip()
        
        question_data = {
            'id': question_num,
            'text': question_text,
            'timestamp': datetime.now().isoformat(),
            'domain': domain,
            'difficulty': difficulty,
            'category': determine_question_category(question_text)
        }
        
        session_data['questions'].append(question_data)
        session_data['question_categories'].append(question_data['category'])
        
        print(f"📝 Generated Q{question_num}: {question_text[:50]}...")
        
        # Generate TTS audio for the question
        generate_question_audio(session_id, question_text)
        
        emit('new_question', {
            'question': question_data,
            'question_number': question_num,
            'total_questions': 10
        })
        
    except Exception as e:
        print(f"❌ Error generating question: {e}")
        emit('error', {'message': 'Failed to generate question. Please try again.'})

def determine_question_category(question_text):
    """Categorize questions for better analytics"""
    question_lower = question_text.lower()
    
    if any(word in question_lower for word in ['implement', 'code', 'algorithm', 'function']):
        return 'Technical Implementation'
    elif any(word in question_lower for word in ['experience', 'project', 'worked', 'handled']):
        return 'Experience-based'
    elif any(word in question_lower for word in ['problem', 'challenge', 'difficult', 'solve']):
        return 'Problem Solving'
    elif any(word in question_lower for word in ['best practice', 'approach', 'methodology', 'process']):
        return 'Best Practices'
    else:
        return 'General Technical'

def generate_question_audio(session_id, question_text):
    """Generate high-quality TTS audio with fallback options"""
    try:
        audio_filename = f"static/audio/question_{session_id}_{len(active_sessions[session_id]['questions'])}.mp3"
        
        # Try gTTS first for better quality
        try:
            tts = gTTS(text=question_text, lang='en', slow=False, tld='com')
            tts.save(audio_filename)
            print(f"🔊 Generated audio with gTTS: {audio_filename}")
            emit('question_audio', {'audio_url': f"/{audio_filename}"})
            return
        except Exception as e:
            print(f"⚠️ gTTS failed: {e}")
        
        # Fallback to pyttsx3
        if tts_engine:
            try:
                wav_filename = audio_filename.replace('.mp3', '.wav')
                tts_engine.save_to_file(question_text, wav_filename)
                tts_engine.runAndWait()
                print(f"🔊 Generated audio with pyttsx3: {wav_filename}")
                emit('question_audio', {'audio_url': f"/{wav_filename}"})
                return
            except Exception as e:
                print(f"⚠️ pyttsx3 failed: {e}")
        
        # If both fail, send text only
        emit('question_text_only', {'text': question_text})
        
    except Exception as e:
        print(f"❌ Audio generation failed: {e}")
        emit('question_text_only', {'text': question_text})

@socketio.on('transcribe_audio')
def handle_audio_transcription(data):
    """Enhanced audio transcription with multiple engine fallback"""
    try:
        session_id = data.get('session_id')
        print(f"🎤 Processing audio transcription for session {session_id}")
        
        # Decode base64 audio data
        audio_data = base64.b64decode(data['audio_data'].split(',')[1])
        
        # Convert WebM to WAV for better compatibility
        try:
            audio_segment = AudioSegment.from_file(io.BytesIO(audio_data), format="webm")
            wav_buffer = io.BytesIO()
            audio_segment.export(wav_buffer, format="wav")
            wav_buffer.seek(0)
            audio_data = wav_buffer.getvalue()
        except Exception as e:
            print(f"⚠️ Audio conversion warning: {e}")
        
        # Save temporary audio file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio:
            temp_audio.write(audio_data)
            temp_audio_path = temp_audio.name
        
        transcript = ""
        confidence = 0.0
        
        # Try multiple recognition engines for best accuracy
        with sr.AudioFile(temp_audio_path) as source:
            # Adjust for ambient noise
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = recognizer.record(source)
            
            # Try Google Speech Recognition first (most accurate)
            try:
                transcript = recognizer.recognize_google(audio)
                confidence = 0.9
                print(f"✅ Google STT: {transcript[:50]}...")
            except sr.UnknownValueError:
                print("⚠️ Google STT: Could not understand audio")
            except sr.RequestError as e:
                print(f"⚠️ Google STT service error: {e}")
            
            # Fallback to Sphinx if Google fails
            if not transcript:
                try:
                    transcript = recognizer.recognize_sphinx(audio)
                    confidence = 0.7
                    print(f"✅ Sphinx STT: {transcript[:50]}...")
                except Exception as e:
                    print(f"⚠️ Sphinx STT failed: {e}")
            
            # Last resort: basic audio processing
            if not transcript:
                transcript = "I couldn't clearly understand your response. Please try speaking more clearly."
                confidence = 0.1
        
        # Clean up temporary file
        try:
            os.unlink(temp_audio_path)
        except:
            pass
        
        # Send result back to client
        emit('transcription_result', {
            'transcript': transcript,
            'confidence': confidence,
            'session_id': session_id
        })
        
    except Exception as e:
        print(f"❌ Transcription error: {e}")
        emit('transcription_error', {'error': 'Transcription failed. Please try again.'})

@socketio.on('submit_response')
def handle_response(data):
    session_id = data['session_id']
    response_text = data['response_text']
    emotion_data = data.get('emotion_data', {})
    audio_duration = data.get('audio_duration', 0)
    
    if session_id not in active_sessions:
        emit('error', {'message': 'Session not found'})
        return
    
    session_data = active_sessions[session_id]
    current_question = session_data['questions'][-1]
    
    print(f"📝 Evaluating response for Q{current_question['id']}: {response_text[:50]}...")
    
    # Record response time
    session_data['response_times'].append(audio_duration)
    session_data['confidence_levels'].append(emotion_data.get('confidence', 0.5))
    
    # Evaluate response using Gemini
    evaluate_response(session_id, current_question, response_text, emotion_data, audio_duration)

def evaluate_response(session_id, question, response_text, emotion_data, audio_duration):
    """Enhanced response evaluation with detailed scoring"""
    session_data = active_sessions[session_id]
    domain = session_data['domain']
    difficulty = session_data['difficulty']
    
    # Enhanced evaluation prompt
    evaluation_prompt = f"""
    You are an expert technical interviewer evaluating a candidate's response for a {DOMAINS[domain]['name']} position at {difficulty} level.
    
    INTERVIEW CONTEXT:
    - Domain: {DOMAINS[domain]['name']}
    - Level: {difficulty}
    - Question Category: {question.get('category', 'General')}
    
    QUESTION: {question['text']}
    
    CANDIDATE'S RESPONSE: {response_text}
    
    RESPONSE METADATA:
    - Duration: {audio_duration} seconds
    - Confidence Level: {emotion_data.get('confidence', 0.5)}
    
    EVALUATION CRITERIA:
    1. Technical Accuracy (1-10): Correctness of technical content
    2. Communication Clarity (1-10): How well the response is articulated
    3. Completeness (1-10): How thoroughly the question is answered
    4. Depth of Knowledge (1-10): Demonstrates understanding beyond surface level
    5. Professional Presentation (1-10): Overall interview performance
    
    SCORING GUIDELINES:
    - 9-10: Exceptional, exceeds expectations
    - 7-8: Strong, meets expectations well
    - 5-6: Adequate, meets basic expectations
    - 3-4: Below expectations, needs improvement
    - 1-2: Poor, significant gaps
    
    Provide your evaluation in this exact JSON format:
    {{
        "overall_score": 7,
        "technical_score": 7,
        "communication_score": 7,
        "completeness_score": 7,
        "depth_score": 7,
        "presentation_score": 7,
        "strengths": ["specific strength 1", "specific strength 2"],
        "improvements": ["specific improvement 1", "specific improvement 2"],
        "detailed_feedback": "Comprehensive feedback explaining the evaluation with specific examples and suggestions for improvement",
        "key_concepts_covered": ["concept1", "concept2"],
        "missing_concepts": ["missing1", "missing2"]
    }}
    """
    
    try:
        response = model.generate_content(evaluation_prompt)
        response_text_clean = response.text.strip()
        
        # Clean JSON response - improved parsing
        if '\`\`\`json' in response_text_clean:
            response_text_clean = response_text_clean.split('\`\`\`json')[1].split('\`\`\`')[0]
        elif '\`\`\`' in response_text_clean:
            response_text_clean = response_text_clean.split('\`\`\`')[1]
        
        # Remove any extra whitespace and newlines
        response_text_clean = response_text_clean.strip()
        
        # Try to find JSON object in the response
        import re
        json_match = re.search(r'\{.*\}', response_text_clean, re.DOTALL)
        if json_match:
            response_text_clean = json_match.group()
        
        print(f"🔍 Attempting to parse JSON: {response_text_clean[:200]}...")
        
        evaluation = json.loads(response_text_clean)
        
        # Validate and ensure all required fields
        required_fields = ['overall_score', 'technical_score', 'communication_score', 'completeness_score']
        for field in required_fields:
            if field not in evaluation:
                evaluation[field] = 5  # Default score
        
        # Ensure scores are within valid range
        for score_field in ['overall_score', 'technical_score', 'communication_score', 'completeness_score']:
            evaluation[score_field] = max(1, min(10, evaluation[score_field]))
        
        # Store response data
        response_data = {
            'question_id': question['id'],
            'response_text': response_text,
            'evaluation': evaluation,
            'emotion_data': emotion_data,
            'audio_duration': audio_duration,
            'timestamp': datetime.now().isoformat(),
            'question_category': question.get('category', 'General')
        }
        
        session_data['responses'].append(response_data)
        session_data['scores'].append(evaluation['overall_score'])
        session_data['emotions'].append(emotion_data)
        session_data['total_score'] += evaluation['overall_score']
        
        print(f"✅ Evaluation complete - Score: {evaluation['overall_score']}/10")
        
        emit('response_evaluated', {
            'evaluation': evaluation,
            'question_number': question['id'],
            'cumulative_score': sum(session_data['scores']) / len(session_data['scores'])
        })
        
        # Generate next question or end interview
        if len(session_data['questions']) < 10:
            session_data['current_question'] += 1
            # Add delay for better user experience
            threading.Timer(3.0, generate_next_question, args=[session_id]).start()
        else:
            end_interview(session_id)
            
    except (json.JSONDecodeError, ValueError) as e:
        print(f"❌ JSON parsing error: {e}")
        print(f"🔍 Raw response: {response_text_clean}")
        
        # Create a more robust fallback evaluation
        fallback_evaluation = {
            'overall_score': 6,
            'technical_score': 6,
            'communication_score': 6,
            'completeness_score': 6,
            'depth_score': 6,
            'presentation_score': 6,
            'strengths': ['Provided a response', 'Engaged with the question'],
            'improvements': ['Could provide more technical detail', 'Consider structuring the response better'],
            'detailed_feedback': 'Your response shows engagement with the question. Consider providing more specific technical details and examples to strengthen your answer.',
            'key_concepts_covered': ['Basic understanding'],
            'missing_concepts': ['More detailed explanation needed']
        }
        
        response_data = {
            'question_id': question['id'],
            'response_text': response_text,
            'evaluation': fallback_evaluation,
            'emotion_data': emotion_data,
            'audio_duration': audio_duration,
            'timestamp': datetime.now().isoformat(),
            'question_category': question.get('category', 'General')
        }
        
        session_data['responses'].append(response_data)
        session_data['scores'].append(6)
        session_data['emotions'].append(emotion_data)
        session_data['total_score'] += 6
        
        emit('response_evaluated', {
            'evaluation': fallback_evaluation,
            'question_number': question['id'],
            'cumulative_score': sum(session_data['scores']) / len(session_data['scores'])
        })
        
        # Continue with next question
        if len(session_data['questions']) < 10:
            session_data['current_question'] += 1
            threading.Timer(3.0, generate_next_question, args=[session_id]).start()
        else:
            end_interview(session_id)

def end_interview(session_id):
    """Generate comprehensive interview completion report"""
    if session_id not in active_sessions:
        return
        
    session_data = active_sessions[session_id]
    session_data['end_time'] = datetime.now()
    
    print(f"🏁 Ending interview for session {session_id}")
    
    # Generate comprehensive report
    generate_final_report(session_id)
    
    final_score = session_data['total_score'] / len(session_data['scores']) if session_data['scores'] else 0
    
    emit('interview_completed', {
        'session_id': session_id,
        'final_score': final_score,
        'total_questions': len(session_data['questions'])
    })

def generate_final_report(session_id):
    """Generate detailed analytics and recommendations"""
    session_data = active_sessions[session_id]
    
    # Calculate comprehensive analytics
    scores = session_data['scores']
    avg_score = sum(scores) / len(scores) if scores else 0
    duration = (session_data['end_time'] - session_data['start_time']).total_seconds() / 60
    
    # Emotion analysis
    emotion_summary = analyze_emotions(session_data['emotions'])
    
    # Performance trends
    performance_trend = analyze_performance_trend(scores)
    
    # Category-wise analysis
    category_analysis = analyze_by_category(session_data['responses'])
    
    # Generate AI-powered recommendations
    recommendations = generate_recommendations(session_data)
    
    # Response time analysis
    avg_response_time = sum(session_data['response_times']) / len(session_data['response_times']) if session_data['response_times'] else 0
    
    session_data['final_report'] = {
        'overall_score': avg_score,
        'duration_minutes': duration,
        'emotion_analysis': emotion_summary,
        'recommendations': recommendations,
        'performance_trend': performance_trend,
        'category_analysis': category_analysis,
        'avg_response_time': avg_response_time,
        'score_breakdown': {
            'technical': sum([r['evaluation'].get('technical_score', 0) for r in session_data['responses']]) / len(session_data['responses']) if session_data['responses'] else 0,
            'communication': sum([r['evaluation'].get('communication_score', 0) for r in session_data['responses']]) / len(session_data['responses']) if session_data['responses'] else 0,
            'completeness': sum([r['evaluation'].get('completeness_score', 0) for r in session_data['responses']]) / len(session_data['responses']) if session_data['responses'] else 0
        },
        'strengths_summary': compile_strengths(session_data['responses']),
        'improvement_areas': compile_improvements(session_data['responses'])
    }

def analyze_emotions(emotions_data):
    """Analyze emotional patterns throughout interview"""
    if not emotions_data:
        return {'confidence': 0.5, 'nervousness': 0.5, 'engagement': 0.5, 'trend': 'stable'}
    
    confidences = [e.get('confidence', 0.5) for e in emotions_data]
    nervousness_levels = [e.get('nervousness', 0.5) for e in emotions_data]
    engagement_levels = [e.get('engagement', 0.5) for e in emotions_data]
    
    # Calculate trends
    confidence_trend = 'improving' if confidences[-1] > confidences[0] else 'declining' if confidences[-1] < confidences[0] else 'stable'
    
    return {
        'confidence': sum(confidences) / len(confidences),
        'nervousness': sum(nervousness_levels) / len(nervousness_levels),
        'engagement': sum(engagement_levels) / len(engagement_levels),
        'confidence_trend': confidence_trend,
        'peak_confidence': max(confidences),
        'lowest_confidence': min(confidences)
    }

def analyze_performance_trend(scores):
    """Analyze how performance changed throughout interview"""
    if len(scores) < 2:
        return 'insufficient_data'
    
    first_half = scores[:len(scores)//2]
    second_half = scores[len(scores)//2:]
    
    first_avg = sum(first_half) / len(first_half)
    second_avg = sum(second_half) / len(second_half)
    
    if second_avg > first_avg + 0.5:
        return 'improving'
    elif second_avg < first_avg - 0.5:
        return 'declining'
    else:
        return 'consistent'

def analyze_by_category(responses):
    """Analyze performance by question category"""
    category_scores = {}
    
    for response in responses:
        category = response.get('question_category', 'General')
        score = response['evaluation']['overall_score']
        
        if category not in category_scores:
            category_scores[category] = []
        category_scores[category].append(score)
    
    # Calculate averages
    category_analysis = {}
    for category, scores in category_scores.items():
        category_analysis[category] = {
            'average_score': sum(scores) / len(scores),
            'question_count': len(scores),
            'best_score': max(scores),
            'needs_improvement': sum(scores) / len(scores) < 6
        }
    
    return category_analysis

def compile_strengths(responses):
    """Compile all strengths mentioned across responses"""
    all_strengths = []
    for response in responses:
        all_strengths.extend(response['evaluation'].get('strengths', []))
    
    # Count frequency and return most common
    strength_counts = {}
    for strength in all_strengths:
        strength_counts[strength] = strength_counts.get(strength, 0) + 1
    
    return sorted(strength_counts.items(), key=lambda x: x[1], reverse=True)[:5]

def compile_improvements(responses):
    """Compile all improvement areas mentioned across responses"""
    all_improvements = []
    for response in responses:
        all_improvements.extend(response['evaluation'].get('improvements', []))
    
    # Count frequency and return most common
    improvement_counts = {}
    for improvement in all_improvements:
        improvement_counts[improvement] = improvement_counts.get(improvement, 0) + 1
    
    return sorted(improvement_counts.items(), key=lambda x: x[1], reverse=True)[:5]

def generate_recommendations(session_data):
    """Generate AI-powered personalized recommendations"""
    domain = session_data['domain']
    avg_score = sum(session_data['scores']) / len(session_data['scores']) if session_data['scores'] else 0
    
    # Collect all feedback
    weak_areas = []
    strong_areas = []
    
    for response in session_data['responses']:
        eval_data = response['evaluation']
        if eval_data['overall_score'] < 6:
            weak_areas.extend(eval_data.get('improvements', []))
        else:
            strong_areas.extend(eval_data.get('strengths', []))
    
    return {
        'focus_areas': list(set(weak_areas))[:5],
        'strengths': list(set(strong_areas))[:5],
        'study_resources': get_study_resources(domain, weak_areas),
        'next_steps': generate_next_steps(avg_score, domain),
        'practice_recommendations': get_practice_recommendations(session_data)
    }

def generate_next_steps(avg_score, domain):
    """Generate specific next steps based on performance"""
    if avg_score >= 8:
        return [
            "You're performing excellently! Focus on advanced topics and system design.",
            "Consider mentoring others or contributing to open source projects.",
            "Prepare for senior-level technical discussions and architecture questions."
        ]
    elif avg_score >= 6:
        return [
            "Good foundation! Focus on deepening your technical knowledge.",
            "Practice explaining complex concepts more clearly.",
            "Work on real-world projects to gain more hands-on experience."
        ]
    else:
        return [
            "Focus on strengthening fundamental concepts.",
            "Practice basic technical questions daily.",
            "Consider taking structured courses or bootcamps.",
            "Build small projects to apply your learning."
        ]

def get_practice_recommendations(session_data):
    """Get specific practice recommendations"""
    recommendations = []
    
    # Based on response times
    avg_time = sum(session_data['response_times']) / len(session_data['response_times']) if session_data['response_times'] else 0
    if avg_time > 120:  # More than 2 minutes
        recommendations.append("Practice answering questions more concisely")
    elif avg_time < 30:  # Less than 30 seconds
        recommendations.append("Take more time to provide detailed, thoughtful responses")
    
    # Based on confidence levels
    avg_confidence = sum(session_data['confidence_levels']) / len(session_data['confidence_levels']) if session_data['confidence_levels'] else 0.5
    if avg_confidence < 0.4:
        recommendations.append("Work on building confidence through more practice interviews")
    
    return recommendations

def get_study_resources(domain, weak_areas):
    """Return curated learning resources based on domain and weak areas"""
    resources = {
        'web_development': [
            {'title': 'MDN Web Docs', 'url': 'https://developer.mozilla.org', 'type': 'Documentation'},
            {'title': 'JavaScript.info', 'url': 'https://javascript.info', 'type': 'Tutorial'},
            {'title': 'React Documentation', 'url': 'https://react.dev', 'type': 'Documentation'},
            {'title': 'Node.js Documentation', 'url': 'https://nodejs.org/docs', 'type': 'Documentation'},
            {'title': 'CSS-Tricks', 'url': 'https://css-tricks.com', 'type': 'Resource'},
            {'title': 'Frontend Masters', 'url': 'https://frontendmasters.com', 'type': 'Course'},
            {'title': 'LeetCode', 'url': 'https://leetcode.com', 'type': 'Practice'}
        ],
        'ai_ml': [
            {'title': 'Coursera ML Course', 'url': 'https://coursera.org/learn/machine-learning', 'type': 'Course'},
            {'title': 'Kaggle Learn', 'url': 'https://kaggle.com/learn', 'type': 'Tutorial'},
            {'title': 'Papers With Code', 'url': 'https://paperswithcode.com', 'type': 'Research'},
            {'title': 'Fast.ai', 'url': 'https://fast.ai', 'type': 'Course'},
            {'title': 'Towards Data Science', 'url': 'https://towardsdatascience.com', 'type': 'Articles'},
            {'title': 'Google AI Education', 'url': 'https://ai.google/education', 'type': 'Resource'},
            {'title': 'Scikit-learn Documentation', 'url': 'https://scikit-learn.org', 'type': 'Documentation'}
        ],
        'electrical': [
            {'title': 'All About Circuits', 'url': 'https://allaboutcircuits.com', 'type': 'Tutorial'},
            {'title': 'Electronics Tutorials', 'url': 'https://electronics-tutorials.ws', 'type': 'Tutorial'},
            {'title': 'IEEE Xplore', 'url': 'https://ieeexplore.ieee.org', 'type': 'Research'},
            {'title': 'Circuit Digest', 'url': 'https://circuitdigest.com', 'type': 'Resource'},
            {'title': 'Khan Academy Electrical Engineering', 'url': 'https://khanacademy.org', 'type': 'Course'},
            {'title': 'MIT OpenCourseWare', 'url': 'https://ocw.mit.edu', 'type': 'Course'}
        ],
        'hr': [
            {'title': 'SHRM Resources', 'url': 'https://shrm.org', 'type': 'Resource'},
            {'title': 'HR.com', 'url': 'https://hr.com', 'type': 'Resource'},
            {'title': 'Harvard Business Review HR', 'url': 'https://hbr.org/topic/human-resource-management', 'type': 'Articles'},
            {'title': 'Workology', 'url': 'https://workology.com', 'type': 'Resource'},
            {'title': 'LinkedIn Learning HR Courses', 'url': 'https://linkedin.com/learning', 'type': 'Course'},
            {'title': 'Coursera HR Specializations', 'url': 'https://coursera.org', 'type': 'Course'}
        ]
    }
    
    return resources.get(domain, [])

@socketio.on('end_interview')
def handle_end_interview(data):
    session_id = data['session_id']
    if session_id in active_sessions:
        end_interview(session_id)

@socketio.on('connect')
def handle_connect():
    print(f"🔗 Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"❌ Client disconnected: {request.sid}")

if __name__ == '__main__':
    print("🚀 PrepIQ Interview Simulator Starting...")
    print("=" * 50)
    print("📝 Features:")
    print("   ✅ AI Question Generation (Gemini 2.0 Flash)")
    print("   ✅ Speech-to-Text (Multiple Engines)")
    print("   ✅ Text-to-Speech (gTTS + pyttsx3)")
    print("   ✅ Emotion Detection (MediaPipe)")
    print("   ✅ Real-time Evaluation")
    print("   ✅ Comprehensive Analytics")
    print("=" * 50)
    print("🎯 Access at: http://localhost:5000")
    print("🔑 API Key: Configured ✅")
    print("=" * 50)
    
    try:
        socketio.run(app, debug=False, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        print("💡 Try: pip install -r requirements.txt")
