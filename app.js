    const socket = io("http://localhost:8000", {
      transports: ["websocket"]
    });

    const video = document.getElementById("video");
    const emotionSpan = document.getElementById("emotion");
    const postureSpan = document.getElementById("posture");
    const adviceList = document.getElementById("advice-list");
    const statusIndicator = document.getElementById("statusIndicator");

    let analysisActive = false;
    let frameInterval;

    navigator.mediaDevices.getUserMedia({ video: true }).then(stream => {
      video.srcObject = stream;
    }).catch(err => {
      console.error("Error accessing webcam:", err);
      adviceList.innerHTML = "<li>❌ Unable to access webcam. Please check permissions.</li>";
    });

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
      }, 500);
    }

    function stopFrameCapture() {
      if (frameInterval) {
        clearInterval(frameInterval);
        frameInterval = null;
      }
    }

    function getEmojiForEmotion(emotion) {
      const emojis = {
        happy: "😊", sad: "😢", angry: "😠", surprise: "😲",
        neutral: "😐", fear: "😨", disgust: "🤢", unknown: "❓"
      };
      return emojis[emotion.toLowerCase()] || "❓";
    }

    function getEmojiForPosture(posture) {
      const emojis = {
        Good: "✅", Slouching: "⚠️", Leaning: "↩️", Unknown: "❓"
      };
      return emojis[posture] || "❓";
    }

    const emotionData = {
      labels: [],
      datasets: [{
        label: 'Emotion Index (1-7)',
        data: [],
        borderColor: 'rgba(78, 115, 223, 1)',
        backgroundColor: 'rgba(78, 115, 223, 0.1)',
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
        scales: {
          y: {
            min: 1,
            max: 7,
            ticks: {
              callback: function (value) {
                const emotions = ["", "Angry", "Disgust", "Fear", "Happy", "Sad", "Surprise", "Neutral"];
                return emotions[value];
              }
            },
            title: {
              display: true,
              text: 'Emotion Type'
            }
          },
          x: {
            title: {
              display: true,
              text: 'Time'
            }
          }
        }
      }
    });

    const emotionToIndex = {
      angry: 1, disgust: 2, fear: 3,
      happy: 4, sad: 5, surprise: 6, neutral: 7
    };

    let lastEmotion = "neutral";

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

    setInterval(() => {
      if (!analysisActive) return;
      
      const now = new Date();
      const timeLabel = now.toLocaleTimeString();

      emotionData.labels.push(timeLabel);
      emotionData.datasets[0].data.push(emotionToIndex[lastEmotion] || 0);

      if (emotionData.labels.length > 12) {
        emotionData.labels.shift();
        emotionData.datasets[0].data.shift();
      }

      emotionChart.update();
    }, 5000);

    socket.on("connect", () => {
      console.log("Connected to backend");
    });

    document.getElementById('fullscreenBtn').addEventListener('click', () => {
      const videoElement = document.getElementById('video');
      if (!document.fullscreenElement) {
        videoElement.requestFullscreen().catch(err => {
          console.error("Error attempting to enable full-screen mode:", err);
        });
      } else {
        document.exitFullscreen();
      }
    });

    // Session Control
    const startSessionBtn = document.getElementById("startSessionBtn");
    const endSessionBtn = document.getElementById("endSessionBtn");
    const summaryDiv = document.getElementById("summary");
    const emotionSummaryDiv = document.getElementById("emotionSummary");
    const postureSummaryDiv = document.getElementById("postureSummary");

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
