document.addEventListener('DOMContentLoaded', () => {
    // --- AUTHENTICATION LOGIC ---
    let authToken = localStorage.getItem('nexus_token');
    let currentUser = localStorage.getItem('nexus_user_name');
    
    const loginOverlay = document.getElementById('login-overlay');
    const mainApp = document.getElementById('main-app');
    const userNameDisplay = document.getElementById('user-name-display');
    const userAvatar = document.getElementById('user-avatar');
    
    const onboardingOverlay = document.getElementById('onboarding-overlay');
    
    function loadProfileToSidebar() {
        if(localStorage.getItem('nexus_profile_set') === 'true') {
            document.getElementById('p-name').value = localStorage.getItem('nexus_profile_name');
            document.getElementById('p-age').value = localStorage.getItem('nexus_profile_age');
            document.getElementById('p-weight').value = localStorage.getItem('nexus_profile_weight');
            document.getElementById('p-gender').value = localStorage.getItem('nexus_profile_gender');
            document.getElementById('p-conditions').value = localStorage.getItem('nexus_profile_conditions');
        } else {
            document.getElementById('p-name').value = currentUser || 'Pasien';
        }
    }

    if (authToken) {
        loginOverlay.style.display = 'none';
        userNameDisplay.textContent = currentUser || 'Pasien';
        userAvatar.src = `https://ui-avatars.com/api/?name=${currentUser}&background=4F46E5&color=fff`;
        
        if (localStorage.getItem('nexus_profile_set') === 'true') {
            loadProfileToSidebar();
            mainApp.style.display = 'flex';
        } else {
            document.getElementById('ob-name').value = currentUser || '';
            onboardingOverlay.style.display = 'flex';
        }
    }

    document.getElementById('btn-save-onboarding').addEventListener('click', () => {
        const name = document.getElementById('ob-name').value;
        const age = document.getElementById('ob-age').value;
        const weight = document.getElementById('ob-weight').value;
        const gender = document.getElementById('ob-gender').value;
        const conditions = document.getElementById('ob-conditions').value;
        
        if (!name || !age || !weight) {
            showToast("Harap isi nama, umur, dan berat badan!");
            return;
        }
        
        localStorage.setItem('nexus_profile_set', 'true');
        localStorage.setItem('nexus_profile_name', name);
        localStorage.setItem('nexus_profile_age', age);
        localStorage.setItem('nexus_profile_weight', weight);
        localStorage.setItem('nexus_profile_gender', gender);
        localStorage.setItem('nexus_profile_conditions', conditions || 'Tidak ada');
        
        loadProfileToSidebar();
        onboardingOverlay.style.display = 'none';
        mainApp.style.display = 'flex';
        showToast("Profil berhasil disimpan!");
    });

    window.toggleAuthMode = function() {
        const loginForm = document.getElementById('login-form');
        const regForm = document.getElementById('register-form');
        if (loginForm.style.display === 'none') {
            loginForm.style.display = 'block';
            regForm.style.display = 'none';
        } else {
            loginForm.style.display = 'none';
            regForm.style.display = 'block';
        }
    };

    document.getElementById('user-profile-btn').addEventListener('click', () => {
        if(confirm("Apakah Anda yakin ingin logout dari Nexus Health?")) {
            localStorage.removeItem('nexus_token');
            localStorage.removeItem('nexus_user_name');
            localStorage.removeItem('nexus_user_id');
            window.location.reload();
        }
    });

    document.getElementById('btn-login').addEventListener('click', async () => {
        const email = document.getElementById('auth-email').value;
        const password = document.getElementById('auth-password').value;
        if(!email || !password) return showToast("Isi email dan password!");
        
        const btn = document.getElementById('btn-login');
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Loading...';
        
        const formData = new URLSearchParams();
        formData.append('username', email);
        formData.append('password', password);
        
        try {
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: formData
            });
            const data = await res.json();
            if(res.ok) {
                localStorage.setItem('nexus_token', data.access_token);
                localStorage.setItem('nexus_user_name', data.name);
                localStorage.setItem('nexus_user_id', data.user_id);
                window.location.reload();
            } else {
                showToast(data.detail || "Login gagal");
                btn.innerHTML = '<i class="fa-solid fa-right-to-bracket"></i> Login Keamanan';
            }
        } catch(e) { 
            showToast("Error koneksi server."); 
            btn.innerHTML = '<i class="fa-solid fa-right-to-bracket"></i> Login Keamanan';
        }
    });

    document.getElementById('btn-register').addEventListener('click', async () => {
        const name = document.getElementById('reg-name').value;
        const email = document.getElementById('reg-email').value;
        const password = document.getElementById('reg-password').value;
        if(!name || !email || !password) return showToast("Isi semua data!");
        
        const btn = document.getElementById('btn-register');
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Mendaftar...';
        
        try {
            const res = await fetch('/api/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, email, password })
            });
            const data = await res.json();
            if(res.ok) {
                showToast("Registrasi berhasil! Silakan Login.");
                toggleAuthMode();
            } else {
                showToast(data.detail || "Registrasi gagal");
            }
            btn.innerHTML = '<i class="fa-solid fa-user-plus"></i> Buat Akun Baru';
        } catch(e) { 
            showToast("Error koneksi server."); 
            btn.innerHTML = '<i class="fa-solid fa-user-plus"></i> Buat Akun Baru';
        }
    });

    // --- GOOGLE AUTH LOGIC ---
    fetch('/api/config').then(r => r.json()).then(config => {
        if (config.google_client_id && config.google_client_id !== "null") {
            document.getElementById('google-auth-section').style.display = 'block';
            
            // Tunggu script google terload
            const checkGoogle = setInterval(() => {
                if (typeof google !== 'undefined' && google.accounts && google.accounts.id) {
                    clearInterval(checkGoogle);
                    google.accounts.id.initialize({
                        client_id: config.google_client_id,
                        callback: async (response) => {
                            try {
                                const res = await fetch('/api/auth/google', {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({ credential: response.credential })
                                });
                                const data = await res.json();
                                if(res.ok) {
                                    localStorage.setItem('nexus_token', data.access_token);
                                    localStorage.setItem('nexus_user_name', data.name);
                                    localStorage.setItem('nexus_user_id', data.user_id);
                                    window.location.reload();
                                } else {
                                    showToast(data.detail || "Google Login gagal");
                                }
                            } catch(e) {
                                showToast("Error koneksi server.");
                            }
                        }
                    });
                    google.accounts.id.renderButton(
                        document.getElementById("google-btn-wrapper"),
                        { theme: document.body.classList.contains("dark-theme") ? "filled_black" : "outline", size: "large", shape: "pill" }
                    );
                }
            }, 500);
        }
    }).catch(e => console.log("Google Config Error", e));

    function getAuthHeaders() {
        return {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('nexus_token')}`
        };
    }
    
    function checkAuthError(res) {
        if(res.status === 401) {
            localStorage.removeItem('nexus_token');
            window.location.reload();
            return true;
        }
        return false;
    }

    // --- TAB & UI LOGIC ---
    const tabs = document.querySelectorAll('.tab-btn');
    const contents = document.querySelectorAll('.tab-content');
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            tabs.forEach(t => t.classList.remove('active'));
            contents.forEach(c => c.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById(`tab-${tab.dataset.tab}`).classList.add('active');
        });
    });

    const chatInput = document.getElementById('chat-input');
    const btnSend = document.getElementById('btn-send');
    const chatBox = document.getElementById('chat-box');

    chatInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
        if(this.value === '') this.style.height = 'auto';
    });

    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const isDark = document.body.classList.contains('dark-theme');
            if (isDark) {
                document.body.classList.remove('dark-theme');
                themeToggle.innerHTML = '<i class="fa-solid fa-moon"></i>';
            } else {
                document.body.classList.add('dark-theme');
                themeToggle.innerHTML = '<i class="fa-solid fa-sun"></i>';
            }
        });
    }

    // --- STT & TTS LOGIC ---
    const btnVoice = document.getElementById('btn-voice');
    const btnTts = document.getElementById('btn-tts');
    let ttsEnabled = true;

    if (btnTts) {
        btnTts.addEventListener('click', () => {
            ttsEnabled = !ttsEnabled;
            if (ttsEnabled) {
                btnTts.innerHTML = '<i class="fa-solid fa-volume-high"></i> AI Bicara: ON';
                btnTts.style.color = 'var(--accent)';
            } else {
                btnTts.innerHTML = '<i class="fa-solid fa-volume-xmark"></i> AI Bicara: OFF';
                btnTts.style.color = 'var(--text-muted)';
                window.speechSynthesis.cancel();
            }
        });
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recognition;
    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.lang = 'id-ID';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        recognition.onstart = () => {
            btnVoice.innerHTML = '<i class="fa-solid fa-microphone-lines fa-fade"></i> Mendengarkan...';
            btnVoice.style.color = 'var(--danger)';
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            chatInput.value = transcript;
            chatInput.style.height = 'auto';
            chatInput.style.height = (chatInput.scrollHeight) + 'px';
            sendMessage();
        };

        recognition.onspeechend = () => {
            recognition.stop();
            btnVoice.innerHTML = '<i class="fa-solid fa-microphone"></i> Suara';
            btnVoice.style.color = 'var(--text-muted)';
        };

        recognition.onerror = (event) => {
            showToast("Error mikrofon: " + event.error);
            btnVoice.innerHTML = '<i class="fa-solid fa-microphone"></i> Suara';
            btnVoice.style.color = 'var(--text-muted)';
        };

        if (btnVoice) {
            btnVoice.addEventListener('click', () => {
                recognition.start();
            });
        }
    } else {
        if (btnVoice) {
            btnVoice.style.display = 'none';
        }
    }

    function speakText(text) {
        if (!ttsEnabled || !window.speechSynthesis) return;
        window.speechSynthesis.cancel(); // Stop current speech
        
        // Bersihkan markdown dari text untuk dibaca
        const cleanText = text.replace(/[*_#`]/g, '').replace(/\[.*?\]\(.*?\)/g, '');
        const utterance = new SpeechSynthesisUtterance(cleanText);
        utterance.lang = 'id-ID';
        utterance.rate = 1.0;
        
        // Set voice Indonesia jika tersedia
        const voices = window.speechSynthesis.getVoices();
        const idVoice = voices.find(voice => voice.lang.includes('id'));
        if (idVoice) utterance.voice = idVoice;

        window.speechSynthesis.speak(utterance);
    }
    
    // Pastikan suara termuat
    if (window.speechSynthesis) {
        window.speechSynthesis.onvoiceschanged = () => { window.speechSynthesis.getVoices(); };
    }

    // --- CHAT LOGIC ---
    function getPatientData() {
        return {
            patient_id: parseInt(document.getElementById('patient-id').value) || 1,
            name: document.getElementById('p-name').value || 'Unknown',
            age: parseInt(document.getElementById('p-age').value) || 30,
            gender: document.getElementById('p-gender').value || 'Pria',
            weight: parseFloat(document.getElementById('p-weight').value) || 70,
            conditions: document.getElementById('p-conditions').value || 'None',
            message: chatInput.value.trim()
        };
    }

    function addMessage(content, role, isEmergency = false) {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${role === 'user' ? 'user-msg' : 'ai-msg'}`;
        const avatarIcon = role === 'user' ? '<i class="fa-solid fa-user"></i>' : '<i class="fa-solid fa-robot"></i>';
        let bodyClass = isEmergency ? 'msg-body glass-bubble emergency-alert' : 'msg-body glass-bubble';
        let formatted = role === 'user' ? content.replace(/\n/g, '<br>') : DOMPurify.sanitize(marked.parse(content));
        
        const timeStr = new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        const senderName = role === 'user' ? (document.getElementById('p-name').value || 'Anda') : 'Nexus Health AI';
        msgDiv.innerHTML = `<div class="avatar">${avatarIcon}</div><div class="${bodyClass}">${formatted}<div class="msg-meta">${senderName} • ${timeStr}</div></div>`;
        chatBox.appendChild(msgDiv);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function addTyping() {
        const div = document.createElement('div');
        div.className = 'message ai-msg typing-indicator';
        div.id = 'typing';
        div.innerHTML = `<div class="avatar"><i class="fa-solid fa-robot"></i></div><div class="msg-body glass-bubble typing-bubble"><div class="dot"></div><div class="dot"></div><div class="dot"></div></div>`;
        chatBox.appendChild(div);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function removeTyping() { const el = document.getElementById('typing'); if(el) el.remove(); }

    async function sendMessage() {
        if (!chatInput.value.trim() || !authToken) return;
        const data = getPatientData();
        addMessage(data.message, 'user');
        
        chatInput.value = ''; chatInput.style.height = 'auto';
        btnSend.disabled = true; chatInput.disabled = true;
        addTyping();

        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify(data)
            });
            if(checkAuthError(res)) return;
            const result = await res.json();
            removeTyping();
            if(res.ok) {
                addMessage(result.response, 'ai', result.emergency);
                speakText(result.response);
            } else addMessage("Error: " + JSON.stringify(result), 'ai');
        } catch(e) {
            removeTyping(); addMessage("Koneksi API terputus.", 'ai');
        } finally {
            btnSend.disabled = false; chatInput.disabled = false; chatInput.focus();
        }
    }

    btnSend.addEventListener('click', sendMessage);
    chatInput.addEventListener('keydown', (e) => {
        if(e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
    });

    document.getElementById('btn-load-history').addEventListener('click', async () => {
        if(!authToken) return;
        const id = document.getElementById('patient-id').value;
        const res = await fetch(`/api/history/${id}`, { headers: getAuthHeaders() });
        if(checkAuthError(res)) return;
        if(res.ok) {
            const data = await res.json();
            chatBox.innerHTML = '';
            data.history.forEach(m => addMessage(m.content, m.role));
            showToast("Riwayat dimuat!");
        }
    });

    document.getElementById('btn-clear-history').addEventListener('click', async () => {
        if(!authToken) return;
        if(!confirm("Anda yakin ingin menghapus seluruh riwayat obrolan?")) return;
        const id = document.getElementById('patient-id').value;
        const res = await fetch(`/api/history/${id}`, { method: 'DELETE', headers: getAuthHeaders() });
        if(checkAuthError(res)) return;
        if(res.ok) {
            chatBox.innerHTML = `<div class="message ai-msg"><div class="avatar"><i class="fa-solid fa-robot"></i></div><div class="msg-body glass-bubble">Riwayat dihapus. Ada keluhan baru yang bisa saya bantu?</div></div>`;
            showToast("Sesi baru dimulai!");
        }
    });

    document.getElementById('btn-download-pdf').addEventListener('click', () => {
        if(!authToken) return;
        const id = document.getElementById('patient-id').value;
        window.open(`/api/pdf/${id}?token=${authToken}`, '_blank');
        showToast("Mempersiapkan PDF...");
    });

    // --- VISION LOGIC ---
    const uploadBox = document.getElementById('upload-box');
    const fileInput = document.getElementById('file-upload');
    const previewSection = document.getElementById('preview-section');
    const imgPreview = document.getElementById('image-preview');
    const btnReset = document.getElementById('btn-reset-img');
    const btnAnalyze = document.getElementById('btn-analyze-img');
    const visionResult = document.getElementById('vision-result');
    const resultContent = document.getElementById('result-content');
    let currentFile = null;

    uploadBox.addEventListener('click', () => fileInput.click());
    
    uploadBox.addEventListener('dragover', (e) => { e.preventDefault(); uploadBox.style.borderColor = 'var(--primary)'; });
    uploadBox.addEventListener('dragleave', () => { uploadBox.style.borderColor = 'rgba(79, 70, 229, 0.3)'; });
    uploadBox.addEventListener('drop', (e) => {
        e.preventDefault(); uploadBox.style.borderColor = 'rgba(79, 70, 229, 0.3)';
        if(e.dataTransfer.files && e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
    });

    fileInput.addEventListener('change', (e) => {
        if(e.target.files && e.target.files[0]) handleFile(e.target.files[0]);
    });

    function handleFile(file) {
        const validTypes = ['image/jpeg', 'image/png', 'image/jpg', 'application/pdf'];
        if(!validTypes.includes(file.type)) { showToast("Format tidak didukung!"); return; }
        
        currentFile = file;
        const oldPdfIcon = document.getElementById('pdf-icon-preview');
        if(oldPdfIcon) oldPdfIcon.remove();
        
        if(file.type === 'application/pdf') {
            imgPreview.style.display = 'none';
            const pdfIcon = document.createElement('div');
            pdfIcon.id = 'pdf-icon-preview';
            pdfIcon.innerHTML = `<i class="fa-solid fa-file-pdf" style="font-size: 60px; color: #ef4444; margin-bottom: 15px;"></i><br><span>${file.name}</span>`;
            document.getElementById('preview-wrapper').appendChild(pdfIcon);
        } else {
            imgPreview.src = URL.createObjectURL(file);
            imgPreview.style.display = 'block';
        }

        uploadBox.style.display = 'none';
        previewSection.style.display = 'block';
        visionResult.style.display = 'none';
        btnAnalyze.innerHTML = '<i class="fa-solid fa-microchip"></i> Pindai Sekarang';
        btnAnalyze.disabled = false;
    }

    btnReset.addEventListener('click', () => {
        currentFile = null; fileInput.value = '';
        previewSection.style.display = 'none';
        uploadBox.style.display = 'block';
        visionResult.style.display = 'none';
    });

    btnAnalyze.addEventListener('click', async () => {
        if(!currentFile || !authToken) return;
        btnAnalyze.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Memindai...';
        btnAnalyze.disabled = true;
        
        const formData = new FormData();
        formData.append('file', currentFile);
        formData.append('patient_id', document.getElementById('patient-id').value || 1);
        
        try {
            const res = await fetch('/api/vision', { 
                method: 'POST', 
                headers: { 'Authorization': `Bearer ${authToken}` },
                body: formData 
            });
            if(checkAuthError(res)) return;
            const data = await res.json();
            visionResult.style.display = 'block';
            
            if (data.error) {
                resultContent.innerHTML = `<div style="color:red;">Error: ${data.error}</div>`;
                btnAnalyze.innerHTML = '<i class="fa-solid fa-rotate-right"></i> Coba Lagi';
                btnAnalyze.disabled = false;
                return;
            }
            
            resultContent.innerHTML = DOMPurify.sanitize(marked.parse(data.result));
            btnAnalyze.innerHTML = '<i class="fa-solid fa-check-double"></i> Selesai';
            showToast("Analisis berhasil!");
            
            const discussBtn = document.createElement('button');
            discussBtn.className = 'btn-primary mt-4';
            discussBtn.innerHTML = '<i class="fa-regular fa-comments"></i> Diskusikan dengan AI';
            discussBtn.onclick = () => {
                document.querySelector('[data-tab="chat"]').click();
                document.getElementById('btn-load-history').click();
            };
            resultContent.appendChild(discussBtn);
        } catch(e) {
            resultContent.innerHTML = 'Gagal memproses gambar.';
            btnAnalyze.innerHTML = '<i class="fa-solid fa-rotate-right"></i> Coba Lagi';
            btnAnalyze.disabled = false;
        }
    });

    function showToast(msg) {
        const toast = document.getElementById('toast');
        toast.textContent = msg; toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 3000);
    }
});
