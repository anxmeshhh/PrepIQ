// Enhanced Speech Recognition with Google Speech-to-Text integration
class SpeechRecognitionManager {
  constructor() {
    this.isSupported = this.checkSupport()
    this.recognition = null
    this.isListening = false
    this.finalTranscript = ""
    this.interimTranscript = ""
    this.onTranscriptUpdate = null
    this.onFinalTranscript = null

    if (this.isSupported) {
      this.initializeRecognition()
    }
  }

  checkSupport() {
    return "webkitSpeechRecognition" in window || "SpeechRecognition" in window
  }

  initializeRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    this.recognition = new SpeechRecognition()

    // Configure recognition settings
    this.recognition.continuous = true
    this.recognition.interimResults = true
    this.recognition.lang = "en-US"
    this.recognition.maxAlternatives = 3

    // Event handlers
    this.recognition.onstart = () => {
      this.isListening = true
      console.log("Speech recognition started")
    }

    this.recognition.onresult = (event) => {
      this.handleResults(event)
    }

    this.recognition.onerror = (event) => {
      this.handleError(event)
    }

    this.recognition.onend = () => {
      this.isListening = false
      console.log("Speech recognition ended")
    }
  }

  handleResults(event) {
    let interimTranscript = ""
    let finalTranscript = this.finalTranscript

    for (let i = event.resultIndex; i < event.results.length; i++) {
      const result = event.results[i]
      const transcript = result[0].transcript

      if (result.isFinal) {
        finalTranscript += transcript + " "
      } else {
        interimTranscript += transcript
      }
    }

    this.finalTranscript = finalTranscript
    this.interimTranscript = interimTranscript

    // Trigger callbacks
    if (this.onTranscriptUpdate) {
      this.onTranscriptUpdate(finalTranscript, interimTranscript)
    }

    if (event.results[event.results.length - 1].isFinal && this.onFinalTranscript) {
      this.onFinalTranscript(finalTranscript)
    }
  }

  handleError(event) {
    console.error("Speech recognition error:", event.error)

    const errorMessages = {
      "no-speech": "No speech detected. Please try speaking again.",
      "audio-capture": "Audio capture failed. Please check your microphone.",
      "not-allowed": "Microphone access denied. Please allow microphone access.",
      network: "Network error occurred. Please check your connection.",
      aborted: "Speech recognition was aborted.",
      "bad-grammar": "Grammar error in speech recognition.",
    }

    const message = errorMessages[event.error] || `Speech recognition error: ${event.error}`

    if (window.interviewManager) {
      window.interviewManager.handleError(message)
    }
  }

  start() {
    if (!this.isSupported) {
      throw new Error("Speech recognition is not supported in this browser")
    }

    if (!this.isListening) {
      this.finalTranscript = ""
      this.interimTranscript = ""
      this.recognition.start()
    }
  }

  stop() {
    if (this.isListening) {
      this.recognition.stop()
    }
  }

  setTranscriptUpdateCallback(callback) {
    this.onTranscriptUpdate = callback
  }

  setFinalTranscriptCallback(callback) {
    this.onFinalTranscript = callback
  }

  getFinalTranscript() {
    return this.finalTranscript.trim()
  }

  getInterimTranscript() {
    return this.interimTranscript.trim()
  }

  isCurrentlyListening() {
    return this.isListening
  }
}

// Google Speech-to-Text API integration (server-side processing)
class GoogleSpeechToText {
  constructor(apiKey) {
    this.apiKey = apiKey
    this.apiUrl = "https://speech.googleapis.com/v1/speech:recognize"
  }

  async transcribeAudio(audioBlob, options = {}) {
    try {
      // Convert audio blob to base64
      const audioBase64 = await this.blobToBase64(audioBlob)

      const requestBody = {
        config: {
          encoding: "WEBM_OPUS",
          sampleRateHertz: 48000,
          languageCode: options.languageCode || "en-US",
          enableAutomaticPunctuation: true,
          enableWordTimeOffsets: true,
          model: "latest_long",
          useEnhanced: true,
          ...options.config,
        },
        audio: {
          content: audioBase64.split(",")[1], // Remove data:audio/webm;base64, prefix
        },
      }

      const response = await fetch(`${this.apiUrl}?key=${this.apiKey}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      return this.processTranscriptionResult(result)
    } catch (error) {
      console.error("Google Speech-to-Text error:", error)
      throw error
    }
  }

  processTranscriptionResult(result) {
    if (!result.results || result.results.length === 0) {
      return {
        transcript: "",
        confidence: 0,
        words: [],
      }
    }

    const bestResult = result.results[0]
    const alternative = bestResult.alternatives[0]

    return {
      transcript: alternative.transcript || "",
      confidence: alternative.confidence || 0,
      words: alternative.words || [],
      alternatives: bestResult.alternatives.slice(1),
    }
  }

  async blobToBase64(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result)
      reader.onerror = reject
      reader.readAsDataURL(blob)
    })
  }
}

// Text-to-Speech for AI responses
class TextToSpeechManager {
  constructor() {
    this.synth = window.speechSynthesis
    this.voices = []
    this.selectedVoice = null
    this.isSupported = "speechSynthesis" in window

    if (this.isSupported) {
      this.loadVoices()
    }
  }

  loadVoices() {
    this.voices = this.synth.getVoices()

    // Select a professional female voice for the interviewer
    this.selectedVoice =
      this.voices.find(
        (voice) =>
          voice.name.includes("Female") ||
          voice.name.includes("Samantha") ||
          voice.name.includes("Karen") ||
          voice.gender === "female",
      ) || this.voices[0]

    // If voices aren't loaded yet, wait for the event
    if (this.voices.length === 0) {
      this.synth.addEventListener("voiceschanged", () => {
        this.loadVoices()
      })
    }
  }

  speak(text, options = {}) {
    if (!this.isSupported) {
      console.warn("Text-to-speech is not supported in this browser")
      return Promise.resolve()
    }

    return new Promise((resolve, reject) => {
      const utterance = new SpeechSynthesisUtterance(text)

      // Configure utterance
      utterance.voice = this.selectedVoice
      utterance.rate = options.rate || 0.9
      utterance.pitch = options.pitch || 1.0
      utterance.volume = options.volume || 0.8

      // Event handlers
      utterance.onend = () => resolve()
      utterance.onerror = (event) => reject(event.error)

      // Speak
      this.synth.speak(utterance)
    })
  }

  stop() {
    if (this.isSupported) {
      this.synth.cancel()
    }
  }

  pause() {
    if (this.isSupported) {
      this.synth.pause()
    }
  }

  resume() {
    if (this.isSupported) {
      this.synth.resume()
    }
  }

  getAvailableVoices() {
    return this.voices
  }

  setVoice(voiceName) {
    const voice = this.voices.find((v) => v.name === voiceName)
    if (voice) {
      this.selectedVoice = voice
    }
  }
}

// Export classes for global use
window.SpeechRecognitionManager = SpeechRecognitionManager
window.GoogleSpeechToText = GoogleSpeechToText
window.TextToSpeechManager = TextToSpeechManager
