// script.js

const socket = io("http://localhost:8000", {
  transports: ["websocket"]
});

const video = document.getElementById("video");
const emotionSpan = document.getElementById("emotion");
const postureSpan = document.getElementById("posture");
const adviceList = document.getElementById("advice-list");
const statusIndicator = document.getElementById("statusIndicator");
const startSessionBtn = document.getElementById("startSessionBtn");
const endSessionBtn = document.getElementById("endSessionBtn");
const summaryDiv = document.getElementById("summary");
const emotionSummaryDiv = document.getElementById("emotionSummary");
const postureSummaryDiv = document.getElementById("postureSummary");
const fullscreenBtn = document.getElementById('fullscreenBtn');

let analysisActive = false;
let frameInterval;

// Request webcam access
navigator.mediaDevices.getUserMedia({ video: true }).then(stream => {
  video.srcObject = stream;
}).catch(err => {
  console.error("Error accessing webcam:", err);
  adviceList.innerHTML = "<li>❌ Unable to access webcam. Please check permissions.</li>";
});

// Function to start capturing and sending video frames
function startFrameCapture() {
  const canvas = document.createElement("canvas");
  const context = canvas.getContext("2d");

  frameInterval = setInterval(() => {
    if (!analysisActive) return;

    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    const base64 = canvas.toDataURL("image/jpeg");
    socket.emit("frame", { image: base64 });
  }, 500); // Send frame every 500ms
}

// Function to stop capturing video frames
function stopFrameCapture() {
  if (frameInterval) {
    clearInterval(frameInterval);
    frameInterval = null;
  }
}

// Helper to get emoji for emotion
function getEmojiForEmotion(emotion) {
  const emojis = {
    happy: "😊", sad: "😢", angry: "😠", surprise: "😲",
    neutral: "😐", fear: "😨", disgust: "🤢", unknown: "❓"
  };
  return emojis[emotion.toLowerCase()] || "❓";
}

// Helper to get emoji for posture
function getEmojiForPosture(posture) {
  const emojis = {
    Good: "✅", Slouching: "⚠️", Leaning: "↩️", Unknown: "❓"
  };
  return emojis[posture] || "❓";
}

// Chart.js setup for emotion trend
const emotionData = {
  labels: [],
  datasets: [{
    label: 'Emotion Index (1-7)',
    data: [],
    borderColor: 'var(--primary-blue)',
    backgroundColor: 'rgba(0, 123, 255, 0.1)',
    fill: true,
    tension: 0.3
  }]
};

const emotionChart = new Chart(document.getElementById('emotionChart').getContext('2d'), {
  type: 'line',
  data: emotionData,
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        labels: {
          font: {
            family: 'Inter',
            size: 14,
            weight: 500,
            color: 'var(--light-text)'
          }
        }
      },
      tooltip: {
        backgroundColor: 'rgba(0,0,0,0.7)',
        bodyFont: {
          family: 'Inter',
          size: 14
        },
        titleFont: {
          family: 'Inter',
          size: 14,
          weight: 'bold'
        },
        padding: 10,
        cornerRadius: 6,
        displayColors: false
      }
    },
    scales: {
      y: {
        min: 1,
        max: 7,
        ticks: {
          callback: function (value) {
            const emotions = ["", "Angry", "Disgust", "Fear", "Happy", "Sad", "Surprise", "Neutral"];
            return emotions[value];
          },
          font: {
            family: 'Inter',
            size: 12,
            color: 'var(--light-text)'
          }
        },
        grid: {
          color: 'rgba(0,0,0,0.05)',
          borderColor: 'rgba(0,0,0,0.1)'
        },
        title: {
          display: true,
          text: 'Emotion Type',
          font: {
            family: 'Inter',
            size: 14,
            weight: 'bold',
            color: 'var(--dark-text)'
          }
        }
      },
      x: {
        ticks: {
          font: {
            family: 'Inter',
            size: 12,
            color: 'var(--light-text)'
          }
        },
        grid: {
          display: false,
          borderColor: 'rgba(0,0,0,0.1)'
        },
        title: {
          display: true,
          text: 'Time',
          font: {
            family: 'Inter',
            size: 14,
            weight: 'bold',
            color: 'var(--dark-text)'
          }
        }
      }
    }
  }
});

const emotionToIndex = {
  angry: 1, disgust: 2, fear: 3,
  happy: 4, sad: 5, surprise: 6, neutral: 7
};

let lastEmotion = "neutral"; // Track the last detected emotion

// Socket.IO event listeners
socket.on("feedback", (data) => {
  if (!analysisActive) return;

  const { emotion, posture, feedback } = data;

  emotionSpan.textContent = `${emotion} ${getEmojiForEmotion(emotion)}`;
  postureSpan.textContent = `${posture} ${getEmojiForPosture(posture)}`;
  adviceList.innerHTML = "";

  if (feedback.length === 0) {
    adviceList.innerHTML = "<li>You're doing great! 👍</li>";
  } else {
    feedback.forEach(f => {
      const li = document.createElement("li");
      li.textContent = f;
      adviceList.appendChild(li);
    });
  }

  lastEmotion = emotion.toLowerCase();
});

// Update emotion chart every 5 seconds
setInterval(() => {
  if (!analysisActive) return;

  const now = new Date();
  const timeLabel = now.toLocaleTimeString();

  emotionData.labels.push(timeLabel);
  emotionData.datasets[0].data.push(emotionToIndex[lastEmotion] || 0);

  // Keep only the last 12 data points (for 60 seconds of history)
  if (emotionData.labels.length > 12) {
    emotionData.labels.shift();
    emotionData.datasets[0].data.shift();
  }

  emotionChart.update();
}, 5000);

socket.on("connect", () => {
  console.log("Connected to backend");
});

// Fullscreen toggle for video
fullscreenBtn.addEventListener('click', () => {
  if (!document.fullscreenElement) {
    video.requestFullscreen().catch(err => {
      console.error("Error attempting to enable full-screen mode:", err);
    });
  } else {
    document.exitFullscreen();
  }
});

// Session Control
startSessionBtn.addEventListener("click", () => {
  analysisActive = true;
  socket.emit("start_session");
  startFrameCapture();

  startSessionBtn.disabled = true;
  endSessionBtn.disabled = false;
  summaryDiv.style.display = "none";

  statusIndicator.className = "status-indicator status-active";
  emotionSpan.textContent = "Initializing...";
  postureSpan.textContent = "Starting analysis...";
  adviceList.innerHTML = "<li>🔄 Analysis started! Sit up straight and look at the camera.</li>";
});

endSessionBtn.addEventListener("click", () => {
  analysisActive = false;
  socket.emit("end_session");
  stopFrameCapture();

  startSessionBtn.disabled = false;
  endSessionBtn.disabled = true;

  statusIndicator.className = "status-indicator status-inactive";
  emotionSpan.textContent = "Session ended";
  postureSpan.textContent = "Session ended";
  adviceList.innerHTML = "<li>✅ Analysis completed! Check your session summary below.</li>";
});

socket.on("session_summary", (summary) => {
  summaryDiv.style.display = "block";

  emotionSummaryDiv.innerHTML = "<h4>🎭 Emotion Summary</h4>" +
    Object.entries(summary.emotion_summary || {}).map(([emotion, percent]) =>
      `<p>${emotion.charAt(0).toUpperCase() + emotion.slice(1)}: ${percent}%</p>`
    ).join("");

  postureSummaryDiv.innerHTML = "<h4>🧍 Posture Summary</h4>" +
    Object.entries(summary.posture_summary || {}).map(([posture, percent]) =>
      `<p>${posture}: ${percent}%</p>`
    ).join("");
});