// Interview Management System
const io = window.io // Declare io variable
const SESSION_ID = window.SESSION_ID // Declare SESSION_ID variable
const DOMAIN = window.DOMAIN // Declare DOMAIN variable

class InterviewManager {
  constructor() {
    console.log("🎯 InterviewManager constructor called")
    console.log("Available globals:", {
      SESSION_ID: window.SESSION_ID,
      DOMAIN: window.DOMAIN,
      io: typeof window.io,
      socketio: typeof io,
    })

    // Check if session variables are available
    if (!window.SESSION_ID || !window.DOMAIN) {
      console.error("❌ Session variables not available")
      console.log("SESSION_ID:", window.SESSION_ID)
      console.log("DOMAIN:", window.DOMAIN)
      this.handleError("Session initialization failed. Please refresh the page.")
      return
    }

    // Check if Socket.IO is available
    if (typeof io === "undefined") {
      console.error("❌ Socket.IO not loaded")
      this.handleError("Socket.IO failed to load. Please refresh the page.")
      return
    }

    try {
      this.socket = io({
        transports: ["websocket", "polling"],
        timeout: 20000,
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
      })
      console.log("✅ Socket.IO initialized successfully")
    } catch (error) {
      console.error("❌ Socket.IO initialization failed:", error)
      this.handleError("Failed to connect to server. Please refresh the page.")
      return
    }
    this.sessionId = window.SESSION_ID
    this.domain = window.DOMAIN
    this.currentQuestion = 0
    this.totalQuestions = 10
    this.isRecording = false
    this.mediaRecorder = null
    this.audioChunks = []
    this.startTime = null
    this.currentScore = 0
    this.recordingStartTime = null
    this.currentAudioBlob = null
    this.currentAudioDuration = 0
    this.speechRecognition = null

    console.log("🎯 Initializing Interview Manager...")
    console.log("Session ID:", this.sessionId)
    console.log("Domain:", this.domain)

    this.initializeEventListeners()
    this.initializeSocketListeners()
    this.hideLoading() // Hide initial loading
  }

  initializeEventListeners() {
    console.log("📝 Setting up event listeners...")

    // Difficulty selection
    document.querySelectorAll(".difficulty-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        this.selectDifficulty(e.target.dataset.level)
      })
    })

    // Recording controls
    const startBtn = document.getElementById("start-recording")
    const stopBtn = document.getElementById("stop-recording")

    if (startBtn) {
      startBtn.addEventListener("click", () => this.startRecording())
    }

    if (stopBtn) {
      stopBtn.addEventListener("click", () => this.stopRecording())
    }

    // Response actions
    const submitBtn = document.getElementById("submit-response")
    const retryBtn = document.getElementById("retry-response")
    const nextBtn = document.getElementById("next-question")
    const endBtn = document.getElementById("end-interview-btn")

    if (submitBtn) {
      submitBtn.addEventListener("click", () => this.submitResponse())
    }

    if (retryBtn) {
      retryBtn.addEventListener("click", () => this.retryResponse())
    }

    if (nextBtn) {
      nextBtn.addEventListener("click", () => this.nextQuestion())
    }

    if (endBtn) {
      endBtn.addEventListener("click", () => this.endInterview())
    }

    console.log("✅ Event listeners initialized")
  }

  initializeSocketListeners() {
    console.log("🔌 Setting up socket listeners...")

    this.socket.on("connect", () => {
      console.log("✅ Connected to server")
    })

    this.socket.on("disconnect", () => {
      console.log("❌ Disconnected from server")
    })

    this.socket.on("new_question", (data) => {
      console.log("📝 New question received:", data)
      this.handleNewQuestion(data)
    })

    this.socket.on("question_audio", (data) => {
      console.log("🔊 Question audio received")
      this.playQuestionAudio(data.audio_url)
    })

    this.socket.on("question_text_only", (data) => {
      console.log("📄 Question text only")
      this.hideAISpeaking()
    })

    this.socket.on("response_evaluated", (data) => {
      console.log("📊 Response evaluated:", data)
      this.handleResponseEvaluation(data)
    })

    this.socket.on("interview_completed", (data) => {
      console.log("🏁 Interview completed:", data)
      this.handleInterviewCompletion(data)
    })

    this.socket.on("transcription_result", (data) => {
      console.log("🎤 Transcription result:", data)
      this.handleTranscriptionResult(data)
    })

    this.socket.on("transcription_error", (data) => {
      console.error("❌ Transcription error:", data.error)
      this.handleError("Transcription failed: " + data.error)
    })

    this.socket.on("error", (data) => {
      console.error("❌ Server error:", data.message)
      this.handleError(data.message)
    })

    console.log("✅ Socket listeners initialized")
  }

  selectDifficulty(level) {
    console.log("🎯 Difficulty selected:", level)

    // Update UI
    document.querySelectorAll(".difficulty-btn").forEach((btn) => {
      btn.classList.remove("selected")
    })
    event.target.classList.add("selected")

    // Hide difficulty selection and show loading
    setTimeout(() => {
      const difficultySection = document.getElementById("difficulty-selection")
      if (difficultySection) {
        difficultySection.style.display = "none"
      }

      this.showLoading("Starting your interview...")

      // Start interview
      console.log("🚀 Starting interview...")
      this.socket.emit("start_interview", {
        session_id: this.sessionId,
        domain: this.domain,
        difficulty: level,
      })

      this.startTime = new Date()
      this.startTimer()
    }, 500)
  }

  handleNewQuestion(data) {
    console.log("📝 Handling new question:", data.question.text)
    this.hideLoading()
    this.currentQuestion = data.question_number

    // Update question display
    const questionText = document.getElementById("current-question-text")
    const currentQuestionNum = document.getElementById("current-question")

    if (questionText) {
      questionText.textContent = data.question.text
    }

    if (currentQuestionNum) {
      currentQuestionNum.textContent = this.currentQuestion
    }

    // Update progress
    const progress = (this.currentQuestion / this.totalQuestions) * 100
    const progressBar = document.getElementById("interview-progress")
    const progressText = document.getElementById("progress-text")

    if (progressBar) {
      progressBar.style.width = `${progress}%`
    }

    if (progressText) {
      progressText.textContent = `Question ${this.currentQuestion} of ${this.totalQuestions}`
    }

    // Show response section
    const responseSection = document.getElementById("response-section")
    const feedbackSection = document.getElementById("feedback-section")
    const endBtn = document.getElementById("end-interview-btn")

    if (responseSection) {
      responseSection.style.display = "block"
    }

    if (feedbackSection) {
      feedbackSection.style.display = "none"
    }

    if (endBtn) {
      endBtn.style.display = "block"
    }

    // Reset response area
    this.resetResponseArea()

    // Show AI speaking indicator
    this.showAISpeaking()
  }

  playQuestionAudio(audioUrl) {
    console.log("🔊 Playing question audio:", audioUrl)
    const audio = document.getElementById("question-audio")

    if (audio) {
      audio.src = audioUrl
      audio
        .play()
        .then(() => {
          console.log("✅ Audio playing")
        })
        .catch((error) => {
          console.log("⚠️ Audio autoplay prevented:", error)
        })

      audio.onended = () => {
        this.hideAISpeaking()
      }
    }
  }

  showAISpeaking() {
    const indicator = document.getElementById("ai-speaking")
    if (indicator) {
      indicator.classList.add("active")
    }
  }

  hideAISpeaking() {
    const indicator = document.getElementById("ai-speaking")
    if (indicator) {
      indicator.classList.remove("active")
    }
  }

  async startRecording() {
    console.log("🎤 Starting recording...")

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 44100,
        },
      })

      this.mediaRecorder = new MediaRecorder(stream, {
        mimeType: "audio/webm;codecs=opus",
      })

      this.audioChunks = []
      this.recordingStartTime = Date.now()

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data)
        }
      }

      this.mediaRecorder.onstop = () => {
        this.processRecording()
      }

      this.mediaRecorder.start(100)
      this.isRecording = true

      // Update UI
      const startBtn = document.getElementById("start-recording")
      const stopBtn = document.getElementById("stop-recording")
      const indicator = document.getElementById("recording-indicator")

      if (startBtn) startBtn.style.display = "none"
      if (stopBtn) stopBtn.style.display = "inline-flex"
      if (indicator) indicator.classList.add("active")

      // Start real-time transcription
      this.startWebSpeechRecognition()
    } catch (error) {
      console.error("❌ Recording error:", error)
      this.handleError("Failed to access microphone. Please check permissions.")
    }
  }

  startWebSpeechRecognition() {
    if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
      const recognition = new SpeechRecognition()

      recognition.continuous = true
      recognition.interimResults = true
      recognition.lang = "en-US"

      let finalTranscript = ""

      recognition.onresult = (event) => {
        let interimTranscript = ""

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript
          if (event.results[i].isFinal) {
            finalTranscript += transcript + " "
          } else {
            interimTranscript += transcript
          }
        }

        const transcriptionElement = document.getElementById("transcription-text")
        if (transcriptionElement) {
          transcriptionElement.innerHTML =
            finalTranscript + '<span style="color: #999;">' + interimTranscript + "</span>"
          transcriptionElement.classList.add("active")
        }

        const submitBtn = document.getElementById("submit-response")
        if (finalTranscript.trim().length > 0 && submitBtn) {
          submitBtn.disabled = false
        }
      }

      recognition.onerror = (event) => {
        console.error("🎤 Speech recognition error:", event.error)
      }

      recognition.start()
      this.speechRecognition = recognition
    }
  }

  stopRecording() {
    console.log("⏹️ Stopping recording...")

    if (this.mediaRecorder && this.isRecording) {
      this.mediaRecorder.stop()
      this.isRecording = false

      // Stop all tracks
      this.mediaRecorder.stream.getTracks().forEach((track) => track.stop())

      // Update UI
      const startBtn = document.getElementById("start-recording")
      const stopBtn = document.getElementById("stop-recording")
      const indicator = document.getElementById("recording-indicator")

      if (startBtn) startBtn.style.display = "inline-flex"
      if (stopBtn) stopBtn.style.display = "none"
      if (indicator) indicator.classList.remove("active")
    }

    // Stop speech recognition
    if (this.speechRecognition) {
      this.speechRecognition.stop()
    }
  }

  processRecording() {
    console.log("🔄 Processing recording...")

    const audioBlob = new Blob(this.audioChunks, { type: "audio/webm" })
    const audioDuration = (Date.now() - this.recordingStartTime) / 1000

    // Store for submission
    this.currentAudioBlob = audioBlob
    this.currentAudioDuration = audioDuration

    // Send to backend for transcription
    this.sendAudioForTranscription(audioBlob)
  }

  sendAudioForTranscription(audioBlob) {
    console.log("📤 Sending audio for transcription...")

    const reader = new FileReader()
    reader.onload = () => {
      this.socket.emit("transcribe_audio", {
        audio_data: reader.result,
        format: "webm",
        session_id: this.sessionId,
      })
    }
    reader.readAsDataURL(audioBlob)
  }

  submitResponse() {
    console.log("📤 Submitting response...")

    const transcriptionElement = document.getElementById("transcription-text")
    const transcriptionText = transcriptionElement ? transcriptionElement.textContent.trim() : ""

    if (!transcriptionText || transcriptionText === "Your response will appear here as you speak...") {
      this.handleError("Please record your response first.")
      return
    }

    // Get emotion data if available
    const emotionData = window.emotionDetector ? window.emotionDetector.getCurrentEmotions() : {}

    // Show loading
    this.showLoading("Evaluating your response...")

    // Submit to server
    this.socket.emit("submit_response", {
      session_id: this.sessionId,
      response_text: transcriptionText,
      emotion_data: emotionData,
      audio_duration: this.currentAudioDuration || 0,
    })

    // Hide response section
    const responseSection = document.getElementById("response-section")
    if (responseSection) {
      responseSection.style.display = "none"
    }
  }

  handleResponseEvaluation(data) {
    console.log("📊 Handling response evaluation:", data)
    this.hideLoading()

    // Update score
    this.currentScore = data.cumulative_score
    const scoreElement = document.getElementById("current-score")
    if (scoreElement) {
      scoreElement.textContent = this.currentScore.toFixed(1)
    }

    // Show feedback
    this.displayFeedback(data.evaluation)

    // Show feedback section
    const feedbackSection = document.getElementById("feedback-section")
    if (feedbackSection) {
      feedbackSection.style.display = "block"
    }
  }

  displayFeedback(evaluation) {
    console.log("📋 Displaying feedback:", evaluation)

    // Update score display
    const scoreElement = document.getElementById("response-score")
    if (scoreElement) {
      scoreElement.textContent = evaluation.overall_score
    }

    // Display strengths
    const strengthsList = document.getElementById("strengths-list")
    if (strengthsList && evaluation.strengths) {
      strengthsList.innerHTML = ""
      evaluation.strengths.forEach((strength) => {
        const li = document.createElement("li")
        li.textContent = strength
        strengthsList.appendChild(li)
      })
    }

    // Display improvements
    const improvementsList = document.getElementById("improvements-list")
    if (improvementsList && evaluation.improvements) {
      improvementsList.innerHTML = ""
      evaluation.improvements.forEach((improvement) => {
        const li = document.createElement("li")
        li.textContent = improvement
        improvementsList.appendChild(li)
      })
    }

    // Display detailed feedback
    const detailedFeedback = document.getElementById("detailed-feedback")
    if (detailedFeedback && evaluation.detailed_feedback) {
      detailedFeedback.textContent = evaluation.detailed_feedback
    }
  }

  nextQuestion() {
    console.log("➡️ Moving to next question...")

    const feedbackSection = document.getElementById("feedback-section")
    if (feedbackSection) {
      feedbackSection.style.display = "none"
    }

    this.showLoading("Generating next question...")
  }

  retryResponse() {
    console.log("🔄 Retrying response...")

    this.resetResponseArea()

    const responseSection = document.getElementById("response-section")
    const feedbackSection = document.getElementById("feedback-section")

    if (responseSection) {
      responseSection.style.display = "block"
    }

    if (feedbackSection) {
      feedbackSection.style.display = "none"
    }
  }

  resetResponseArea() {
    const transcriptionElement = document.getElementById("transcription-text")
    const submitBtn = document.getElementById("submit-response")

    if (transcriptionElement) {
      transcriptionElement.textContent = "Your response will appear here as you speak..."
      transcriptionElement.classList.remove("active")
    }

    if (submitBtn) {
      submitBtn.disabled = true
    }

    // Reset recording state
    if (this.isRecording) {
      this.stopRecording()
    }
  }

  handleInterviewCompletion(data) {
    console.log("🏁 Interview completed:", data)
    this.hideLoading()

    // Show completion message and redirect
    this.showLoading(`Interview Complete! Final Score: ${data.final_score.toFixed(1)}/10`)

    setTimeout(() => {
      window.location.href = `/results/${data.session_id}`
    }, 3000)
  }

  endInterview() {
    if (confirm("Are you sure you want to end the interview? Your progress will be saved.")) {
      console.log("🛑 Ending interview...")
      this.socket.emit("end_interview", {
        session_id: this.sessionId,
      })
    }
  }

  startTimer() {
    setInterval(() => {
      if (this.startTime) {
        const elapsed = new Date() - this.startTime
        const minutes = Math.floor(elapsed / 60000)
        const seconds = Math.floor((elapsed % 60000) / 1000)

        const timerElement = document.getElementById("interview-timer")
        if (timerElement) {
          timerElement.textContent = `${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`
        }
      }
    }, 1000)
  }

  showLoading(message) {
    const loadingText = document.getElementById("loading-text")
    const loadingOverlay = document.getElementById("loading-overlay")

    if (loadingText) {
      loadingText.textContent = message
    }

    if (loadingOverlay) {
      loadingOverlay.classList.remove("hidden")
      loadingOverlay.style.display = "flex"
    }
  }

  hideLoading() {
    const loadingOverlay = document.getElementById("loading-overlay")
    if (loadingOverlay) {
      loadingOverlay.classList.add("hidden")
      loadingOverlay.style.display = "none"
    }
  }

  handleError(message) {
    console.error("❌ Error:", message)
    this.hideLoading()
    alert(`Error: ${message}`)
  }

  handleTranscriptionResult(data) {
    console.log("🎤 Server transcription result:", data)

    const transcriptionElement = document.getElementById("transcription-text")
    if (transcriptionElement && data.transcript) {
      const currentText = transcriptionElement.textContent.replace(/\s+/g, " ").trim()

      if (data.transcript.trim().length > currentText.length) {
        transcriptionElement.textContent = data.transcript
        transcriptionElement.classList.add("active")

        const submitBtn = document.getElementById("submit-response")
        if (submitBtn) {
          submitBtn.disabled = false
        }
      }
    }
  }
}

// Initialize interview when DOM is loaded
function initializeInterview() {
  console.log("🚀 Initializing interview system...")

  // Check if required variables are available
  if (!window.SESSION_ID || !window.DOMAIN) {
    console.error("❌ Missing session variables")
    console.log("SESSION_ID:", window.SESSION_ID)
    console.log("DOMAIN:", window.DOMAIN)
    alert("Session initialization failed. Please refresh the page.")
    return
  }

  // Create global interview manager
  try {
    window.interviewManager = new InterviewManager()
    console.log("✅ Interview system initialized successfully")
  } catch (error) {
    console.error("❌ Failed to initialize interview manager:", error)
    alert("Failed to initialize interview system. Please refresh the page.")
  }
}

// Export for global access
window.initializeInterview = initializeInterview

// Auto-initialize if DOM is already loaded
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initializeInterview)
} else {
  initializeInterview()
}
