
document.addEventListener("DOMContentLoaded", () => {

    const dashboardView = document.getElementById("dashboard-view");
    const instructionsView = document.getElementById("instructions-view");
    const examView = document.getElementById("exam-view");
    const resultView = document.getElementById("result-view");

    const getElement = (id) => document.getElementById(id);

    let selectedPattern = null;
    let examQuestions = [];
    let currentQuestion = 0;
    let answers = {};

    let violationTimer = null;
    let heartbeatTimer = null;
    let examActive = false;

    let lastClipboardViolation = 0;

    // EXAMINATION TIMER VARIABLES

    let examTimerInterval = null;
    let remainingSeconds = 0;
    let examSubmissionInProgress = false;


    // PAGE NAVIGATION

    function showView(view) {

        if (!view) {
            console.error("Page section not found.");
            return;
        }

        [
            dashboardView,
            instructionsView,
            examView,
            resultView
        ].forEach(section => {

            if (section) {
                section.classList.add("hidden");
            }

        });

        view.classList.remove("hidden");

        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });

    }


    // HTML SECURITY

    function escapeHtml(value) {

        return String(value).replace(/[&<>"']/g, char => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#039;"
        }[char]));

    }


    function showError(message) {

        alert(message);
        console.error(message);

    }


    // ANSWER COUNTER

    function updateAnsweredCount() {

        const count = getElement("answered-count");

        if (count) {

            count.textContent =
                `${Object.values(answers).filter(value => String(value).trim()).length} answered`;

        }

    }


    // REPORT VIOLATIONS

    function reportViolation(reason) {

        if (!examActive) return;

        const now = Date.now();

        if (now - lastClipboardViolation < 700) {
            return;
        }

        lastClipboardViolation = now;

        fetch("/api/report_violation", {

            method: "POST",

            headers: {
                "Content-Type": "application/json"
            },

            body: JSON.stringify({
                reason: reason
            })

        })

        .then(response => {

            if (!response.ok) {
                throw new Error("Violation reporting failed.");
            }

            return response.json();

        })

        .then(data => {

            console.log("Violation reported:", reason, data);

        })

        .catch(error => {

            console.error("Violation reporting failed:", error);

        });

    }


    // EXAMINATION TIMER

    function updateExamTimer() {

        const timerElement = getElement("exam-timer");

        const minutes = Math.floor(remainingSeconds / 60);
        const seconds = remainingSeconds % 60;

        if (timerElement) {

            timerElement.textContent =
                `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;

        }

        if (timerElement) {

            timerElement.classList.toggle(
                "timer-warning",
                remainingSeconds <= 60
            );

        }

    }


    function startExamTimer() {

        stopExamTimer();

        remainingSeconds = selectedPattern === "short"
            ? 15 * 60
            : 30 * 60;

        updateExamTimer();

        console.log(
            `Examination timer started: ${remainingSeconds / 60} minutes`
        );

        examTimerInterval = setInterval(() => {

            if (!examActive) {

                stopExamTimer();
                return;

            }

            remainingSeconds--;

            updateExamTimer();

            if (remainingSeconds <= 0) {

                stopExamTimer();

                console.log("Examination time expired.");

                alert(
                    "Time is over! Your examination will be submitted automatically."
                );

                // Directly submit through the existing submission handler.

                submitExamination(true);

            }

        }, 1000);

    }


    function stopExamTimer() {

        if (examTimerInterval !== null) {

            clearInterval(examTimerInterval);
            examTimerInterval = null;

        }

    }


    // COPY, CUT, PASTE AND KEYBOARD SHORTCUT PREVENTION

    document.addEventListener("keydown", event => {

        if (!examActive) return;

        const key = event.key.toLowerCase();

        if (
            (event.ctrlKey || event.metaKey) &&
            ["c", "v", "x"].includes(key)
        ) {

            event.preventDefault();
            event.stopPropagation();

            const actions = {

                c: "Copy attempt detected (Ctrl+C)",
                v: "Paste attempt detected (Ctrl+V)",
                x: "Cut attempt detected (Ctrl+X)"

            };

            reportViolation(actions[key]);

        }

    }, true);


    document.addEventListener("copy", event => {

        if (!examActive) return;

        event.preventDefault();

        reportViolation("Copy attempt detected");

    });


    document.addEventListener("cut", event => {

        if (!examActive) return;

        event.preventDefault();

        reportViolation("Cut attempt detected");

    });


    document.addEventListener("paste", event => {

        if (!examActive) return;

        event.preventDefault();

        reportViolation("Paste attempt detected");

    });


    document.addEventListener("contextmenu", event => {

        if (!examActive) return;

        event.preventDefault();

        reportViolation("Right-click context menu attempt detected");

    });


    // STOP VIOLATION MONITORING

    function stopViolationMonitoring() {

        if (violationTimer !== null) {

            clearInterval(violationTimer);
            violationTimer = null;

        }

    }


    // STOP CAMERA FEED

    function stopCameraFeed() {

        const feed = getElement("proctor-feed");
        const cameraError = getElement("camera-error");

        if (feed) {

            feed.removeAttribute("src");
            feed.src = "";

        }

        if (cameraError) {

            cameraError.classList.remove("hidden");

        }

    }


    function requestProctoringEnded() {

        document.dispatchEvent(
            new Event("proctoring:ended")
        );

    }


    // EXAM HEARTBEAT

    function startExamHeartbeat() {

        stopExamHeartbeat();

        heartbeatTimer = setInterval(() => {

            if (!examActive) {
                return;
            }

            fetch("/api/exam_heartbeat", {

                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({})

            }).catch(error => {

                console.error("Exam heartbeat failed:", error);

            });

        }, 3000);

    }


    function stopExamHeartbeat() {

        if (heartbeatTimer !== null) {

            clearInterval(heartbeatTimer);
            heartbeatTimer = null;

        }

    }


    // CAMERA AND MICROPHONE PERMISSIONS

    async function requestMediaPermissions() {

        if (
            !navigator.mediaDevices ||
            !navigator.mediaDevices.getUserMedia
        ) {

            throw new Error(
                "Camera and microphone access are not supported. Please use an updated Chrome or Edge browser on localhost."
            );

        }

        let permissionStream = null;

        try {

            permissionStream =
                await navigator.mediaDevices.getUserMedia({

                    video: true,
                    audio: true

                });

            console.log("Camera permission granted.");
            console.log("Microphone permission granted.");

        } catch (error) {

            if (error.name === "NotAllowedError") {

                throw new Error(
                    "Camera and microphone permissions are required. Please allow both permissions in your browser settings."
                );

            }

            if (error.name === "NotFoundError") {

                throw new Error(
                    "A webcam or microphone could not be found. Connect both devices and try again."
                );

            }

            if (error.name === "NotReadableError") {

                throw new Error(
                    "Your camera or microphone is being used by another application. Close other applications and try again."
                );

            }

            throw new Error(
                "Unable to access your camera and microphone: " + error.message
            );

        } finally {

            if (permissionStream) {

                permissionStream.getTracks().forEach(track => {
                    track.stop();
                });

            }

        }

        await new Promise(resolve => setTimeout(resolve, 500));

    }


    // QUESTION NAVIGATION

    function renderQuestionNav() {

        const nav = getElement("question-nav");

        if (!nav) return;

        nav.innerHTML = examQuestions.map((q, index) => {

            const answered =
                String(answers[q.id] || "").trim().length > 0;

            return `
                <button
                    class="nav-number ${answered ? "answered" : ""} ${index === currentQuestion ? "current" : ""}"
                    data-index="${index}"
                    aria-label="Question ${index + 1}">
                    ${index + 1}
                </button>
            `;

        }).join("");

        nav.querySelectorAll("button").forEach(button => {

            button.addEventListener("click", () => {

                currentQuestion = Number(button.dataset.index);

                renderQuestion();

            });

        });

    }


    // RENDER QUESTION

    function renderQuestion() {

        const q = examQuestions[currentQuestion];

        if (!q) {

            showError("Question could not be loaded.");
            return;

        }

        const isShort = selectedPattern === "short";

        const questionNumber = getElement("question-number");
        const progress = getElement("question-progress");
        const container = getElement("question-container");

        const previousButton = getElement("previous-question");
        const nextButton = getElement("next-question");

        if (!container) {

            showError("Question container was not found in quiz.html.");
            return;

        }

        if (questionNumber) {

            questionNumber.textContent =
                `QUESTION ${String(currentQuestion + 1).padStart(2, "0")} / ${String(examQuestions.length).padStart(2, "0")}`;

        }

        if (progress) {

            progress.style.width =
                `${((currentQuestion + 1) / examQuestions.length) * 100}%`;

        }

        updateAnsweredCount();

        let content =
            `<h2 class="question-title">${escapeHtml(q.question)}</h2>`;

        if (isShort) {

            if (!Array.isArray(q.options)) {

                showError("MCQ options are missing for this question.");
                return;

            }

            content += `
                <div class="answer-options">

                    ${q.options.map((option, index) => `

                        <label class="answer-option ${answers[q.id] === option ? "selected" : ""}">

                            <input
                                type="radio"
                                name="answer"
                                value="${escapeHtml(option)}"
                                ${answers[q.id] === option ? "checked" : ""}>

                            <span class="option-letter">
                                ${String.fromCharCode(65 + index)}
                            </span>

                            <span>${escapeHtml(option)}</span>

                        </label>

                    `).join("")}

                </div>
            `;

        } else {

            content += `

                <textarea
                    id="long-answer"
                    class="long-answer"
                    rows="9"
                    placeholder="Write your answer here...">${escapeHtml(answers[q.id] || "")}</textarea>

                <div class="answer-hint">
                    Tip: Structure your response with key points and examples where appropriate.
                </div>

            `;

        }

        container.innerHTML = content;

        if (isShort) {

            container.querySelectorAll('input[name="answer"]').forEach(input => {

                input.addEventListener("change", () => {

                    answers[q.id] = input.value;

                    renderQuestionNav();

                    updateAnsweredCount();

                    container.querySelectorAll(".answer-option").forEach(label => {

                        label.classList.toggle(
                            "selected",
                            label.querySelector("input").checked
                        );

                    });

                });

            });

        } else {

            const textarea = getElement("long-answer");

            if (textarea) {

                textarea.addEventListener("input", event => {

                    answers[q.id] = event.target.value;

                    renderQuestionNav();

                    updateAnsweredCount();

                });

            }

        }

        if (previousButton) {

            previousButton.disabled = currentQuestion === 0;

        }

        if (nextButton) {

            nextButton.innerHTML =
                currentQuestion === examQuestions.length - 1
                    ? "Review answers <span>→</span>"
                    : "Next question <span>→</span>";

        }

        renderQuestionNav();

    }


    // EXAM INSTRUCTIONS

    function openInstructions(pattern) {

        selectedPattern = pattern;

        const isShort = pattern === "short";

        const title = getElement("instruction-title");
        const description = getElement("instruction-description");
        const facts = getElement("instruction-facts");
        const checkbox = getElement("agree-rules");

        if (!title || !description || !facts || !checkbox) {

            showError("Instructions page elements are missing. Check templates/quiz.html.");
            return;

        }

        title.textContent = isShort
            ? "Short answer assessment"
            : "Long answer assessment";

        description.textContent = isShort
            ? "This assessment contains 10 randomized multiple-choice questions. Each correct answer earns one mark. Time limit: 15 minutes."
            : "This assessment contains 5 randomized descriptive questions. Write clear, detailed answers. Your responses will be submitted for evaluation. Time limit: 30 minutes.";

        facts.innerHTML = isShort

            ? `
                <div><strong>10</strong><span>Questions</span></div>
                <div><strong>10</strong><span>Total marks</span></div>
                <div><strong>15 min</strong><span>Duration</span></div>
            `

            : `
                <div><strong>5</strong><span>Questions</span></div>
                <div><strong>30 min</strong><span>Duration</span></div>
                <div><strong>Manual</strong><span>Evaluation</span></div>
            `;

        checkbox.checked = false;

        showView(instructionsView);

    }


    // SELECT EXAM PATTERN

    document.querySelectorAll(".pattern-btn").forEach(button => {

        button.addEventListener("click", () => {

            const pattern = button.dataset.pattern;

            if (pattern !== "short" && pattern !== "long") {

                showError("Invalid examination pattern.");
                return;

            }

            openInstructions(pattern);

        });

    });


    // BACK TO DASHBOARD

    const backDashboard = getElement("back-dashboard");

    if (backDashboard) {

        backDashboard.addEventListener("click", () => {

            showView(dashboardView);

        });

    }


    // START EXAMINATION

    const startButton = getElement("start-exam");

    if (startButton) {

        startButton.addEventListener("click", async () => {

            const checkbox = getElement("agree-rules");

            if (!selectedPattern) {

                showError("Please select an examination pattern first.");
                return;

            }

            if (!checkbox || !checkbox.checked) {

                alert("Please confirm that you have read the exam guidelines.");
                return;

            }

            startButton.disabled = true;

            try {

                startButton.textContent = "Checking permissions...";

                await requestMediaPermissions();

                startButton.textContent = "Starting examination...";

                const response = await fetch("/api/start_exam", {

                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({
                        pattern: selectedPattern
                    })

                });

                const data = await response.json();

                if (!response.ok || !data.success) {

                    throw new Error(
                        data.message || "Could not start the examination."
                    );

                }

                if (
                    !Array.isArray(data.questions) ||
                    data.questions.length === 0
                ) {

                    throw new Error(
                        "No examination questions were received from the server."
                    );

                }

                examQuestions = data.questions;

                currentQuestion = 0;

                answers = {};

                examActive = true;

                examSubmissionInProgress = false;

                // START HEARTBEAT AND TIMER

                startExamHeartbeat();

                startExamTimer();

                document.dispatchEvent(
                    new Event("proctoring:started")
                );

                const examTitle = getElement("exam-title");
                const examLabel = getElement("exam-label");

                if (examTitle) {

                    examTitle.textContent =
                        selectedPattern === "short"
                            ? "Short Answer Assessment"
                            : "Long Answer Assessment";

                }

                if (examLabel) {

                    examLabel.textContent =
                        selectedPattern === "short"
                            ? "OBJECTIVE EXAM"
                            : "DESCRIPTIVE EXAM";

                }

                showView(examView);

                const feed = getElement("proctor-feed");
                const cameraError = getElement("camera-error");

                if (feed) {

                    const source = feed.dataset.src || "/video_feed";

                    feed.onload = () => {

                        cameraError?.classList.add("hidden");

                        console.log("AI proctoring camera feed connected.");

                    };

                    feed.onerror = () => {

                        cameraError?.classList.remove("hidden");

                        console.error(
                            "Unable to load the AI proctoring camera feed."
                        );

                    };

                    feed.src = source + "?t=" + Date.now();

                }

                renderQuestion();

                startViolationMonitoring();

                console.log("Examination started successfully.");

            } catch (error) {

                stopExamTimer();

                stopExamHeartbeat();

                examActive = false;

                showError(error.message);

            } finally {

                startButton.disabled = false;

                startButton.textContent = "Start examination";

            }

        });

    }


    // VIOLATION MONITORING

    function startViolationMonitoring() {

        stopViolationMonitoring();

        violationTimer = setInterval(async () => {

            if (!examActive) {
                return;
            }

            try {

                const response = await fetch("/api/proctor_status", {

                    method: "GET",

                    cache: "no-store"

                });

                if (!response.ok) {
                    return;
                }

                const data = await response.json();

                if (!data.success) {
                    return;
                }

                document.dispatchEvent(

                    new CustomEvent("proctoring:status", {

                        detail: data

                    })

                );

                console.log(
                    `Proctoring violations: ${data.violation_count}/${data.max_violations}`
                );

            } catch (error) {

                console.error("Proctoring monitoring error:", error);

            }

        }, 2000);

    }


    // MANUAL EXAMINATION CANCELLATION

    const cancelExamButton = getElement("cancel-exam-btn");

    if (cancelExamButton) {

        cancelExamButton.addEventListener("click", async () => {

            if (!examActive) {
                return;
            }

            const confirmed = window.confirm(
                "Are you sure you want to cancel this examination? Your answers will not be submitted."
            );

            if (!confirmed) {
                return;
            }

            cancelExamButton.disabled = true;

            cancelExamButton.textContent = "Cancelling...";

            try {

                const response = await fetch("/api/cancel_exam", {

                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({
                        manual: true
                    })

                });

                const data = await response.json();

                if (!response.ok || !data.success) {

                    throw new Error(
                        data.message || "Unable to cancel the examination."
                    );

                }

                examActive = false;

                stopExamTimer();

                stopViolationMonitoring();

                stopExamHeartbeat();

                stopCameraFeed();

                requestProctoringEnded();

                selectedPattern = null;

                examQuestions = [];

                currentQuestion = 0;

                answers = {};

                const modal = getElement("confirm-modal");

                if (modal) {

                    modal.classList.add("hidden");

                }

                const dashboardLink = document.querySelector(
                    '.side-link[data-section="dashboard-view"]'
                );

                if (dashboardLink) {

                    dashboardLink.click();

                } else {

                    showView(dashboardView);

                }

                alert("Your examination has been cancelled successfully.");

                console.log("Examination cancelled successfully.");

            } catch (error) {

                console.error("Cancel examination error:", error);

                alert(error.message);

            } finally {

                cancelExamButton.disabled = false;

                cancelExamButton.innerHTML =
                    '<i class="fa-solid fa-xmark"></i> Cancel Examination';

            }

        });

    }


    // PREVIOUS QUESTION

    const previousButton = getElement("previous-question");

    if (previousButton) {

        previousButton.addEventListener("click", () => {

            if (currentQuestion > 0) {

                currentQuestion--;

                renderQuestion();

            }

        });

    }


    // SUBMISSION CONFIRMATION

    const nextButton = getElement("next-question");

    function openSubmitConfirmation() {

        const unanswered = examQuestions.filter(q =>

            !String(answers[q.id] || "").trim()

        ).length;

        const confirmText = getElement("confirm-text");

        const modal = getElement("confirm-modal");

        if (!modal) {

            showError("Submission confirmation window was not found.");

            return;

        }

        if (confirmText) {

            confirmText.textContent = unanswered

                ? `You have ${unanswered} unanswered question(s). You can still submit, but unanswered questions may affect your result.`

                : "All questions have an answer. You won't be able to change them after submission.";

        }

        modal.classList.remove("hidden");

    }


    if (nextButton) {

        nextButton.addEventListener("click", () => {

            if (currentQuestion < examQuestions.length - 1) {

                currentQuestion++;

                renderQuestion();

            } else {

                openSubmitConfirmation();

            }

        });

    }


    const submitButton = getElement("submit-exam");

    if (submitButton) {

        submitButton.addEventListener("click", openSubmitConfirmation);

    }


    const cancelButton = getElement("cancel-submit");

    if (cancelButton) {

        cancelButton.addEventListener("click", () => {

            const modal = getElement("confirm-modal");

            if (modal) {

                modal.classList.add("hidden");

            }

        });

    }


    // DISPLAY RESULT

    function renderResult(data) {

        const metrics = getElement("result-metrics");

        const title = getElement("result-title");

        const description = getElement("result-description");

        const note = getElement("result-note");

        if (!metrics) return;

        if (
            data.status === "Cancelled due to 10 proctoring violations" ||
            data.status === "Cancelled"
        ) {

            if (title) {

                title.textContent = "Examination Cancelled";

            }

            if (description) {

                description.textContent =
                    "Your examination was cancelled.";

            }

            metrics.innerHTML = `

                <div>
                    <strong>${data.violation_count ?? 0}/${data.max_violations ?? 10}</strong>
                    <span>Violations</span>
                </div>

                <div>
                    <strong>Cancelled</strong>
                    <span>Exam status</span>
                </div>

            `;

            if (note) {

                note.textContent =
                    "Your examination cancellation has been recorded in your history.";

            }

            return;

        }


        if (data.pattern === "short") {

            if (title) {

                title.textContent = data.status || "Examination completed";

            }

            if (description) {

                description.textContent =
                    "Your short answer assessment has been evaluated.";

            }

            metrics.innerHTML = `

                <div>
                    <strong>${data.correct ?? 0}/${data.total ?? 0}</strong>
                    <span>Correct answers</span>
                </div>

                <div>
                    <strong>${data.percentage ?? 0}%</strong>
                    <span>Score</span>
                </div>

                <div>
                    <strong>${data.incorrect ?? 0}</strong>
                    <span>Incorrect</span>
                </div>

                <div>
                    <strong>${data.unanswered ?? 0}</strong>
                    <span>Unanswered</span>
                </div>

            `;

            if (note) {

                note.textContent =
                    "Your result is based on the answers submitted. You can return to the dashboard to begin another randomized attempt.";

            }

        } else {

            if (title) {

                title.textContent = "Submission received";

            }

            if (description) {

                description.textContent =
                    "Your descriptive answers have been saved successfully.";

            }

            metrics.innerHTML = `

                <div>
                    <strong>${data.submitted ?? 0}/${data.total ?? 0}</strong>
                    <span>Answers submitted</span>
                </div>

                <div>
                    <strong>${data.unanswered ?? 0}</strong>
                    <span>Unanswered</span>
                </div>

            `;

            if (note) {

                note.textContent =
                    "Your responses have been submitted. Descriptive answers require instructor evaluation, so a final score is not calculated automatically.";

            }

        }

    }


    // SUBMIT EXAMINATION

    async function submitExamination(autoSubmit = false) {

        if (!examActive || examSubmissionInProgress) {
            return;
        }

        examSubmissionInProgress = true;

        const confirmSubmit = getElement("confirm-submit");

        if (confirmSubmit) {

            confirmSubmit.disabled = true;

            confirmSubmit.textContent = "Submitting...";

        }

        const modal = getElement("confirm-modal");

        if (autoSubmit && modal) {

            modal.classList.add("hidden");

        }

        try {

            const response = await fetch("/api/submit_exam", {

                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({

                    answers: answers

                })

            });

            const data = await response.json();

            if (!response.ok || !data.success) {

                throw new Error(
                    data.message || "Could not submit your examination."
                );

            }

            examActive = false;

            stopExamTimer();

            stopViolationMonitoring();

            stopExamHeartbeat();

            stopCameraFeed();

            requestProctoringEnded();

            if (modal) {

                modal.classList.add("hidden");

            }

            renderResult(data);

            showView(resultView);

            console.log(
                autoSubmit
                    ? "Examination automatically submitted."
                    : "Examination submitted successfully."
            );

        } catch (error) {

            examSubmissionInProgress = false;

            showError(error.message);

        } finally {

            if (confirmSubmit) {

                confirmSubmit.disabled = false;

                confirmSubmit.textContent = "Yes, submit";

            }

        }

    }


    // CONFIRM SUBMISSION

    const confirmSubmit = getElement("confirm-submit");

    if (confirmSubmit) {

        confirmSubmit.addEventListener("click", () => {

            submitExamination(false);

        });

    }


    // RETURN TO DASHBOARD

    const returnDashboard = getElement("return-dashboard");

    if (returnDashboard) {

        returnDashboard.addEventListener("click", () => {

            stopExamTimer();

            stopViolationMonitoring();

            stopExamHeartbeat();

            stopCameraFeed();

            examActive = false;

            examSubmissionInProgress = false;

            requestProctoringEnded();

            selectedPattern = null;

            examQuestions = [];

            currentQuestion = 0;

            answers = {};

            remainingSeconds = 0;

            showView(dashboardView);

        });

    }


    // HANDLE EXAMINATION PAGE CLOSING

    window.addEventListener("beforeunload", () => {

        stopExamTimer();

    });


    window.addEventListener("pagehide", () => {

        stopExamTimer();

        if (!examActive) {
            return;
        }

        const data = new Blob(

            [JSON.stringify({})],

            {
                type: "application/json"
            }

        );

        navigator.sendBeacon(
            "/api/end_exam",
            data
        );

    });


    // INITIAL PAGE CHECK

    if (
        !dashboardView ||
        !instructionsView ||
        !examView ||
        !resultView
    ) {

        console.error(
            "One or more examination page sections are missing in quiz.html."
        );

    }

    console.log("Examination JavaScript loaded successfully.");

});
