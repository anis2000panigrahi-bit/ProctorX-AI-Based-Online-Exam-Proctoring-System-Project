
(() => {

    const $ = (id) => document.getElementById(id);

    const sections = [
        'dashboard-view',
        'upcoming-panel',
        'history-panel',
        'results-panel',
        'profile-panel',
        'instructions-view',
        'exam-view',
        'result-view'
    ];

    const links = [
        ...document.querySelectorAll('.side-link')
    ];

    function activate(section) {

        sections.forEach(id => {
            $(id)?.classList.add('hidden');
        });

        $(section)?.classList.remove('hidden');

        links.forEach(button => {
            button.classList.toggle(
                'active',
                button.dataset.section === section
            );
        });

        if (
            section === 'history-panel' ||
            section === 'results-panel'
        ) {
            loadHistory();
        }

        if (section === 'profile-panel') {
            loadProfile();
        }

        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    }

    // -----------------------------------------
    // EXAMINATION NAVIGATION
    // -----------------------------------------

    links.forEach(button => {

        button.addEventListener('click', () => {

            const section = button.dataset.section;

            if (examActive && section !== 'exam-view') {

                reportViolation(
                    'Attempted to navigate away from the examination.'
                );

                return;
            }

            activate(section);
        });

    });

    // -----------------------------------------
    // EXAMINATION HISTORY
    // -----------------------------------------

    async function loadHistory() {

        try {

            const response = await fetch('/api/history', {
                credentials: 'same-origin'
            });

            if (!response.ok) {
                throw new Error('Unable to load examination history.');
            }

            const data = await response.json();

            const rows = Array.isArray(data.history)
                ? data.history
                : [];

            const historyHTML = renderHistoryRows(rows);

            const resultRows = rows.filter(
                record => record.result && typeof record.result === 'object'
            );

            const resultsHTML = renderHistoryRows(resultRows);

            if ($('history-list')) {
                $('history-list').innerHTML = historyHTML;
            }

            if ($('results-list')) {
                $('results-list').innerHTML = resultsHTML;
            }

        } catch (error) {

            console.error(
                'History loading error:',
                error
            );

        }
    }

    // -----------------------------------------
    // RENDER HISTORY AND RESULTS
    // -----------------------------------------

    function renderHistoryRows(rows) {

        if (!rows.length) {

            return `
                <p class="feature-muted">
                    No completed exams yet. Your submitted attempts will appear here.
                </p>
            `;
        }

        return rows.map((r) => {

            const date = r.submitted_at
                ? new Date(r.submitted_at).toLocaleString()
                : 'Date unavailable';

            let score;

            if (r.exam_status === 'Cancelled') {

                score = `${r.violation_count || 10}/10 violations`;

            } else if (r.result?.pattern === 'short') {

                score =
                    `${r.result.correct}/${r.result.total} (${r.result.percentage}%)`;

            } else {

                score =
                    `${r.result?.submitted || 0}/${r.result?.total || 0} responses`;
            }

            const status =
                r.result?.status ||
                r.exam_status ||
                'Submitted';

            return `
                <article class="history-item">

                    <div>

                        <b>
                            ${r.pattern === 'short'
                                ? 'Short Answer Exam'
                                : 'Long Answer Exam'}
                        </b>

                        <small>${escapeText(date)}</small>

                    </div>

                    <span>${escapeText(score)}</span>

                    <em>${escapeText(status)}</em>

                </article>
            `;

        }).join('');
    }

    // -----------------------------------------
    // CLEAR EXAM HISTORY AND RESULT HISTORY
    // -----------------------------------------

    async function clearRecords(type) {

        const button = type === 'history'
            ? $('clear-history-btn')
            : $('clear-results-btn');

        if (!button) return;

        const message = type === 'history'
            ? 'Are you sure you want to clear your entire exam history?'
            : 'Are you sure you want to clear your result history?';

        if (!confirm(message + '\n\nThe action cannot be undone.')) {
            return;
        }

        const originalText = button.innerHTML;

        button.disabled = true;

        button.innerHTML =
            '<i class="fa-solid fa-spinner fa-spin"></i> Clearing...';

        try {

            const response = await fetch('/api/clear-history', {

                method: 'POST',

                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },

                credentials: 'same-origin',

                body: JSON.stringify({
                    type: type
                })

            });

            const contentType =
                response.headers.get('content-type') || '';

            if (!contentType.includes('application/json')) {

                const responseText = await response.text();

                console.error(
                    'Unexpected server response:',
                    response.status,
                    responseText.substring(0, 500)
                );

                if (response.redirected) {

                    throw new Error(
                        'Your session may have expired. Please log in again.'
                    );
                }

                throw new Error(
                    'The server returned HTML instead of JSON. Check the /api/clear-history route in server.py.'
                );
            }

            const data = await response.json();

            if (!response.ok || !data.success) {

                throw new Error(
                    data.message || 'Unable to clear records.'
                );
            }

            alert(
                data.message || 'Records cleared successfully.'
            );

            await loadHistory();

        } catch (error) {

            console.error(
                'Clear history error:',
                error
            );

            alert(
                error.message || 'Unable to clear records. Please try again.'
            );

        } finally {

            button.disabled = false;

            button.innerHTML = originalText;

        }
    }

    // -----------------------------------------
    // CLEAR HISTORY BUTTONS
    // -----------------------------------------

    $('clear-history-btn')?.addEventListener(
        'click',
        () => clearRecords('history')
    );

    $('clear-results-btn')?.addEventListener(
        'click',
        () => clearRecords('results')
    );

    // -----------------------------------------
    // STUDENT PROFILE
    // -----------------------------------------

    async function loadProfile() {

        const profileContainer = $('profile-details');

        if (!profileContainer) return;

        profileContainer.innerHTML = 'Loading profile...';

        try {

            const response = await fetch('/api/profile', {
                credentials: 'same-origin'
            });

            const data = await response.json();

            if (!response.ok || !data.success) {

                profileContainer.innerHTML = `
                    <p class="feature-muted">
                        ${escapeText(data.message || 'Unable to load profile.')}
                    </p>
                `;

                return;
            }

            renderProfile(data);

        } catch (error) {

            console.error('Profile loading error:', error);

            profileContainer.innerHTML = `
                <p class="feature-muted">
                    Unable to load profile. Please try again.
                </p>
            `;
        }
    }

    // -----------------------------------------
    // DISPLAY PROFILE
    // -----------------------------------------

    function renderProfile(data) {

        const profileContainer = $('profile-details');

        if (!profileContainer) return;

        profileContainer.innerHTML = `

            <div class="profile-avatar">
                ${escapeText(
                    String(data.name || 'S').charAt(0).toUpperCase()
                )}
            </div>

            <div class="profile-info">

                <b>${escapeText(data.name)}</b>

                <p>${escapeText(data.email)}</p>

                <small>Student account · ProctorX</small>

                <br><br>

                <button
                    type="button"
                    id="edit-profile-btn"
                    class="profile-action-btn"
                >
                    <i class="fa-solid fa-pen"></i>
                    Edit Profile
                </button>

            </div>

            <div id="edit-profile-form" class="hidden">

                <h3>Edit Profile</h3>

                <label for="edit-username">
                    Username
                </label>

                <input
                    type="text"
                    id="edit-username"
                    value="${escapeText(data.name)}"
                    maxlength="50"
                    required
                >

                <br><br>

                <button
                    type="button"
                    id="save-profile-btn"
                    class="profile-action-btn"
                >
                    Save Changes
                </button>

                <button
                    type="button"
                    id="cancel-profile-btn"
                    class="profile-cancel-btn"
                >
                    Cancel
                </button>

                <p id="profile-message"></p>

                <hr>

                <h3>Account Security</h3>

                <button
                    type="button"
                    id="show-password-form-btn"
                    class="profile-action-btn"
                >
                    <i class="fa-solid fa-lock"></i>
                    Change Password
                </button>

                <div
                    id="change-password-form"
                    class="password-section hidden"
                >

                    <h3>Change Password</h3>

                    <label for="current-password">
                        Current Password
                    </label>

                    <input
                        type="password"
                        id="current-password"
                        placeholder="Enter current password"
                        autocomplete="current-password"
                        required
                    >

                    <label for="new-password">
                        New Password
                    </label>

                    <input
                        type="password"
                        id="new-password"
                        placeholder="Enter new password"
                        autocomplete="new-password"
                        minlength="8"
                        required
                    >

                    <label for="confirm-password">
                        Confirm New Password
                    </label>

                    <input
                        type="password"
                        id="confirm-password"
                        placeholder="Confirm new password"
                        autocomplete="new-password"
                        required
                    >

                    <div class="password-actions">

                        <button
                            type="button"
                            id="update-password-btn"
                            class="password-submit-btn"
                        >
                            Update Password
                        </button>

                        <button
                            type="button"
                            id="cancel-password-btn"
                            class="profile-cancel-btn"
                        >
                            Cancel
                        </button>

                    </div>

                    <p id="password-message"></p>

                </div>

            </div>
        `;

        // OPEN EDIT PROFILE

        $('edit-profile-btn')?.addEventListener('click', () => {

            $('edit-profile-form')?.classList.remove('hidden');

            $('edit-username')?.focus();

        });

        // CANCEL EDIT PROFILE

        $('cancel-profile-btn')?.addEventListener(
            'click',
            cancelProfile
        );

        function cancelProfile() {

            $('edit-profile-form')?.classList.add('hidden');

            if ($('edit-username')) {
                $('edit-username').value = data.name || '';
            }

            if ($('profile-message')) {
                $('profile-message').textContent = '';
            }

            $('change-password-form')?.classList.add('hidden');

            clearPasswordFields();
        }

        // SAVE PROFILE

        $('save-profile-btn')?.addEventListener(
            'click',
            saveProfile
        );

        // SHOW PASSWORD FORM

        $('show-password-form-btn')?.addEventListener('click', () => {

            $('change-password-form')?.classList.remove('hidden');

            $('current-password')?.focus();

        });

        // CANCEL PASSWORD FORM

        $('cancel-password-btn')?.addEventListener(
            'click',
            cancelPasswordForm
        );

        function cancelPasswordForm() {

            $('change-password-form')?.classList.add('hidden');

            if ($('password-message')) {
                $('password-message').textContent = '';
            }

            clearPasswordFields();
        }

        // UPDATE PASSWORD

        $('update-password-btn')?.addEventListener(
            'click',
            changePassword
        );

    }

    // -----------------------------------------
    // CLEAR PASSWORD FIELDS
    // -----------------------------------------

    function clearPasswordFields() {

        if ($('current-password')) {
            $('current-password').value = '';
        }

        if ($('new-password')) {
            $('new-password').value = '';
        }

        if ($('confirm-password')) {
            $('confirm-password').value = '';
        }

    }

    // -----------------------------------------
    // SAVE PROFILE TO DATABASE
    // -----------------------------------------

    async function saveProfile() {

        const usernameInput = $('edit-username');

        const message = $('profile-message');

        const saveButton = $('save-profile-btn');

        if (!usernameInput || !message || !saveButton) return;

        const username = usernameInput.value.trim();

        if (!username) {

            message.textContent = 'Username cannot be empty.';

            return;
        }

        if (username.length > 50) {

            message.textContent =
                'Username must be 50 characters or fewer.';

            return;
        }

        saveButton.disabled = true;

        saveButton.textContent = 'Saving...';

        try {

            const response = await fetch('/api/profile', {

                method: 'POST',

                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },

                credentials: 'same-origin',

                body: JSON.stringify({
                    username: username
                })

            });

            const data = await response.json();

            if (!response.ok || !data.success) {

                message.textContent =
                    data.message || 'Profile update failed.';

                return;
            }

            alert('Profile updated successfully!');

            await loadProfile();

        } catch (error) {

            console.error('Profile update error:', error);

            message.textContent =
                'Unable to update profile. Please try again.';

        } finally {

            if ($('save-profile-btn')) {

                $('save-profile-btn').disabled = false;

                $('save-profile-btn').textContent = 'Save Changes';
            }
        }
    }

    // -----------------------------------------
    // CHANGE ACCOUNT PASSWORD
    // -----------------------------------------

    async function changePassword() {

        const currentPassword = $('current-password')?.value || '';

        const newPassword = $('new-password')?.value || '';

        const confirmPassword = $('confirm-password')?.value || '';

        const message = $('password-message');

        const button = $('update-password-btn');

        if (!message || !button) return;

        if (!currentPassword || !newPassword || !confirmPassword) {

            message.textContent = 'Please complete all password fields.';

            return;
        }

        if (newPassword.length < 8) {

            message.textContent =
                'New password must contain at least 8 characters.';

            return;
        }

        if (newPassword !== confirmPassword) {

            message.textContent =
                'New password and confirm password do not match.';

            return;
        }

        button.disabled = true;

        button.textContent = 'Updating...';

        message.textContent = '';

        try {

            const response = await fetch('/api/change-password', {

                method: 'POST',

                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },

                credentials: 'same-origin',

                body: JSON.stringify({

                    current_password: currentPassword,

                    new_password: newPassword,

                    confirm_password: confirmPassword

                })

            });

            const data = await response.json();

            if (!response.ok || !data.success) {

                message.textContent =
                    data.message || 'Password update failed.';

                return;
            }

            alert('Password changed successfully!');

            clearPasswordFields();

            $('change-password-form')?.classList.add('hidden');

            message.textContent = '';

        } catch (error) {

            console.error('Password change error:', error);

            message.textContent =
                'Unable to change password. Please try again.';

        } finally {

            button.disabled = false;

            button.textContent = 'Update Password';

        }

    }

    // -----------------------------------------
    // ESCAPE HTML
    // -----------------------------------------

    function escapeText(value) {

        return String(value || '').replace(
            /[&<>"']/g,
            character => ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#39;'
            }[character])
        );
    }

    // -----------------------------------------
    // VOICE ASSISTANCE
    // -----------------------------------------

    const SpeechRecognition =
        window.SpeechRecognition ||
        window.webkitSpeechRecognition;

    let recognition = null;

    function speak(text) {

        if ('speechSynthesis' in window) {

            speechSynthesis.cancel();

            speechSynthesis.speak(
                new SpeechSynthesisUtterance(text)
            );
        }
    }

    const voice = document.createElement('button');

    voice.className = 'voice-assist-btn';

    voice.innerHTML =
        '<i class="fa-solid fa-microphone"></i> Voice help';

    voice.type = 'button';

    voice.title =
        'Read the current question and listen for commands';

    document.querySelector('.topbar-right')?.prepend(voice);

    voice.addEventListener('click', () => {

        const question = document.querySelector(
            '#question-container .question-title'
        )?.textContent;

        if (question) {

            speak(
                question +
                '. Say next question, previous question, or repeat question.'
            );
        }

        if (!SpeechRecognition) {

            speak(
                'Voice commands are not supported in this browser.'
            );

            return;
        }

        recognition = new SpeechRecognition();

        recognition.lang = 'en-IN';

        recognition.interimResults = false;

        recognition.onresult = event => {

            const command =
                event.results[0][0].transcript.toLowerCase();

            if (command.includes('next')) {

                $('next-question')?.click();

            } else if (
                command.includes('previous') ||
                command.includes('back')
            ) {

                $('previous-question')?.click();

            } else if (command.includes('repeat')) {

                const current = document.querySelector(
                    '#question-container .question-title'
                )?.textContent;

                if (current) speak(current);

            } else {

                speak(
                    'Command not recognized. Say next question, previous question, or repeat question.'
                );
            }
        };

        recognition.onerror = () => {

            speak(
                'I could not hear that. Please try again.'
            );

        };

        recognition.start();

    });

    // -----------------------------------------
    // PROCTORING SYSTEM
    // -----------------------------------------

    let examActive = false;

    let violationCount = 0;

    let lastDisplayedViolationCount = 0;

    let lastReportedEvent = {};

    const MAX_VIOLATIONS = 10;

    const BROWSER_EVENT_COOLDOWN = 20000;

    let resizeTimer = null;

    let lastWindowWidth = window.innerWidth;

    let lastWindowHeight = window.innerHeight;

    let lastFullscreenChangeAt = 0;

    const warning = $('proctor-warning');

    const warningMessage = $('warning-message');

    const warningCount = $('warning-count');

    const warningButton = $('warning-ok');

    // -----------------------------------------
    // DISPLAY WARNING
    // -----------------------------------------

    function displayWarning(reason) {

        if (!warning) return;

        if (warningMessage) {

            warningMessage.textContent = reason;
        }

        if (warningCount) {

            warningCount.textContent =
                `Warning ${violationCount} of ${MAX_VIOLATIONS}`;
        }

        if (warningButton) {

            warningButton.textContent =
                violationCount >= MAX_VIOLATIONS
                    ? 'Exam cancelled'
                    : 'I understand';
        }

        warning.classList.remove('hidden');
    }

    // -----------------------------------------
    // REPORT VIOLATION
    // -----------------------------------------

    async function reportViolation(reason) {

        if (!examActive) return;

        const now = Date.now();

        const previous =
            lastReportedEvent[reason] || 0;

        if (
            now - previous <
            BROWSER_EVENT_COOLDOWN
        ) {
            return;
        }

        lastReportedEvent[reason] = now;

        try {

            const response = await fetch(
                '/api/report_violation',
                {
                    method: 'POST',

                    headers: {
                        'Content-Type': 'application/json'
                    },

                    credentials: 'same-origin',

                    body: JSON.stringify({
                        reason: reason
                    })
                }
            );

            const data = await response.json();

            if (!response.ok || !data.success) {

                console.error(
                    'Violation report failed:',
                    data.message
                );

                return;
            }

            updateViolationStatus(data);

        } catch (error) {

            console.error(
                'Could not report violation:',
                error
            );
        }
    }

    // -----------------------------------------
    // UPDATE VIOLATION COUNTER
    // -----------------------------------------

    function updateViolationStatus(data) {

        violationCount =
            Number(data.violation_count || 0);

        if (
            violationCount >
            lastDisplayedViolationCount
        ) {

            lastDisplayedViolationCount =
                violationCount;

            const reason =
                data.reason ||
                'Suspicious activity detected during your examination.';

            displayWarning(reason);
        }

        if (
            data.cancelled ||
            violationCount >= MAX_VIOLATIONS
        ) {

            displayWarning(
                'You have reached 10 proctoring violations. Your examination is being cancelled.'
            );

            examActive = false;
        }
    }

    // -----------------------------------------
    // RECEIVE STATUS FROM SCRIPT.JS
    // -----------------------------------------

    document.addEventListener(
        'proctoring:status',
        event => {

            const data = event.detail;

            if (!data) return;

            updateViolationStatus(data);
        }
    );

    // -----------------------------------------
    // WARNING BUTTON
    // -----------------------------------------

    warningButton?.addEventListener('click', async () => {

        warning?.classList.add('hidden');

        if (
            examActive &&
            !document.fullscreenElement
        ) {

            try {

                await document.documentElement.requestFullscreen();

            } catch (error) {

                console.warn(
                    'Fullscreen request was blocked:',
                    error
                );
            }
        }

    });

    // -----------------------------------------
    // EXAMINATION START
    // -----------------------------------------

    document.addEventListener(
        'proctoring:started',
        () => {

            examActive = true;

            violationCount = 0;

            lastDisplayedViolationCount = 0;

            lastReportedEvent = {};

            lastWindowWidth = window.innerWidth;

            lastWindowHeight = window.innerHeight;

            warning?.classList.add('hidden');

        }
    );

    // -----------------------------------------
    // PAGE VISIBILITY DETECTION
    // -----------------------------------------

    document.addEventListener(
        'visibilitychange',
        () => {

            if (
                examActive &&
                document.hidden
            ) {

                reportViolation(
                    'You left or minimized the examination page.'
                );
            }
        }
    );

    // -----------------------------------------
    // FULLSCREEN DETECTION
    // -----------------------------------------

    document.addEventListener('fullscreenchange', () => {

        lastFullscreenChangeAt = Date.now();

        lastWindowWidth = window.innerWidth;

        lastWindowHeight = window.innerHeight;

        if (
            examActive &&
            !document.hidden &&
            !document.fullscreenElement
        ) {

            reportViolation(
                'You exited fullscreen mode.'
            );
        }

    });

    // -----------------------------------------
    // BROWSER RESIZE DETECTION
    // -----------------------------------------

    window.addEventListener('resize', () => {

        if (!examActive) return;

        clearTimeout(resizeTimer);

        resizeTimer = setTimeout(() => {

            if (!examActive) return;

            if (Date.now() - lastFullscreenChangeAt < 1500) {

                lastWindowWidth = window.innerWidth;

                lastWindowHeight = window.innerHeight;

                return;
            }

            const widthDifference = Math.abs(
                window.innerWidth - lastWindowWidth
            );

            const heightDifference = Math.abs(
                window.innerHeight - lastWindowHeight
            );

            if (
                widthDifference >= 100 ||
                heightDifference >= 100
            ) {

                reportViolation(
                    'Suspicious browser window resizing detected.'
                );
            }

            lastWindowWidth = window.innerWidth;

            lastWindowHeight = window.innerHeight;

        }, 800);

    });

    // -----------------------------------------
    // KEYBOARD SHORTCUT DETECTION
    // -----------------------------------------

    document.addEventListener('keydown', event => {

        if (!examActive) return;

        const key = event.key.toLowerCase();

        const ctrlOrMeta = event.ctrlKey || event.metaKey;

        if (ctrlOrMeta && key === 'c') {

            reportViolation(
                'Copy shortcut detected during the examination.'
            );

        }

        else if (ctrlOrMeta && key === 'v') {

            reportViolation(
                'Paste shortcut detected during the examination.'
            );

        }

        else if (key === 'printscreen') {

            reportViolation(
                'Print Screen key activity detected.'
            );

        }

        else if (key === 'f12') {

            reportViolation(
                'Developer tools shortcut detected.'
            );

        }

        else if (
            ctrlOrMeta &&
            event.shiftKey &&
            ['i', 'j', 'c'].includes(key)
        ) {

            reportViolation(
                'Developer tools keyboard shortcut detected.'
            );

        }

    });

    // -----------------------------------------
    // COPY EVENT DETECTION
    // -----------------------------------------

    document.addEventListener('copy', () => {

        if (!examActive) return;

        reportViolation(
            'Copy activity detected during the examination.'
        );

    });

    // -----------------------------------------
    // PASTE EVENT DETECTION
    // -----------------------------------------

    document.addEventListener('paste', () => {

        if (!examActive) return;

        reportViolation(
            'Paste activity detected during the examination.'
        );

    });

    // -----------------------------------------
    // EXAMINATION END
    // -----------------------------------------

    document.addEventListener(
        'proctoring:ended',
        () => {

            examActive = false;

            clearTimeout(resizeTimer);

            warning?.classList.add('hidden');

        }
    );

    // -----------------------------------------
    // SUBMIT EXAMINATION
    // -----------------------------------------

    $('confirm-submit')?.addEventListener(
        'click',
        () => {

            examActive = false;

            if (document.fullscreenElement) {

                document.exitFullscreen().catch(() => {});
            }
        }
    );

    // -----------------------------------------
    // RETURN TO DASHBOARD
    // -----------------------------------------

    $('return-dashboard')?.addEventListener(
        'click',
        () => {

            examActive = false;

            activate('dashboard-view');
        }
    );

    console.log(
        'Portal features, history management, profile editing, password management, voice assistance and Phase 1 browser monitoring loaded.'
    );

})();
