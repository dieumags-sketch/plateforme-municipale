// frontend/js/modules/face-auth.js

let faceVideo = null;
let faceStream = null;
let faceDetectionInterval = null;
let currentFaceImage = null;

async function initFaceAPI() {
    // Charger les modèles face-api.js
    const MODEL_URL = 'https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.12/model/';
    
    await faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL);
    await faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL);
    await faceapi.nets.faceRecognitionNet.loadFromUri(MODEL_URL);
    
    console.log('Face API initialisé');
}

async function startFaceCamera() {
    const video = document.getElementById('face-video');
    const cameraBtn = document.getElementById('start-camera');
    const overlay = document.querySelector('.face-overlay');
    
    if (!video) return;
    
    try {
        faceStream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = faceStream;
        
        // Attendre que la vidéo soit prête
        video.onloadedmetadata = () => {
            video.play();
            if (overlay) overlay.style.display = 'none';
            if (cameraBtn) cameraBtn.textContent = 'Caméra active';
            startFaceDetection();
        };
    } catch (error) {
        console.error('Erreur caméra:', error);
        showToast('Impossible d\'accéder à la caméra', 'error');
    }
}

function stopFaceCamera() {
    if (faceStream) {
        faceStream.getTracks().forEach(track => track.stop());
        faceStream = null;
    }
    
    if (faceDetectionInterval) {
        clearInterval(faceDetectionInterval);
        faceDetectionInterval = null;
    }
    
    const video = document.getElementById('face-video');
    if (video) {
        video.srcObject = null;
    }
}

async function startFaceDetection() {
    const video = document.getElementById('face-video');
    const canvas = document.getElementById('face-canvas');
    const submitBtn = document.getElementById('face-submit');
    
    if (!video) return;
    
    faceDetectionInterval = setInterval(async () => {
        if (!video.videoWidth || !video.videoHeight) return;
        
        // Détecter le visage
        const detections = await faceapi.detectSingleFace(
            video,
            new faceapi.TinyFaceDetectorOptions()
        ).withFaceLandmarks();
        
        if (detections) {
            // Dessiner les contours du visage
            const displaySize = { width: video.videoWidth, height: video.videoHeight };
            faceapi.matchDimensions(canvas, displaySize);
            
            const resizedDetections = faceapi.resizeResults(detections, displaySize);
            canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
            faceapi.draw.drawDetections(canvas, resizedDetections);
            faceapi.draw.drawFaceLandmarks(canvas, resizedDetections);
            
            // Capturer l'image du visage
            captureFaceImage(video, detections);
            
            if (submitBtn) submitBtn.disabled = false;
        } else {
            if (submitBtn) submitBtn.disabled = true;
        }
    }, 100);
}

function captureFaceImage(video, detection) {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    
    const box = detection.detection.box;
    const margin = 20;
    
    canvas.width = box.width + margin * 2;
    canvas.height = box.height + margin * 2;
    
    ctx.drawImage(
        video,
        box.x - margin,
        box.y - margin,
        box.width + margin * 2,
        box.height + margin * 2,
        0,
        0,
        canvas.width,
        canvas.height
    );
    
    currentFaceImage = canvas.toDataURL('image/jpeg');
}

function dataURLtoFile(dataurl, filename) {
    const arr = dataurl.split(',');
    const mime = arr[0].match(/:(.*?);/)[1];
    const bstr = atob(arr[1]);
    let n = bstr.length;
    const u8arr = new Uint8Array(n);
    while (n--) {
        u8arr[n] = bstr.charCodeAt(n);
    }
    return new File([u8arr], filename, { type: mime });
}

async function enableFaceRecognition() {
    if (!currentFaceImage) {
        showToast('Veuillez positionner votre visage', 'error');
        return false;
    }
    
    const faceFile = dataURLtoFile(currentFaceImage, 'face.jpg');
    const formData = new FormData();
    formData.append('face_image', faceFile);
    
    try {
        const response = await fetch(`${API_BASE}/face/enable/`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            },
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast('Reconnaissance faciale activée', 'success');
            stopFaceCamera();
            return true;
        } else {
            showToast(data.error || 'Erreur', 'error');
            return false;
        }
    } catch (error) {
        console.error('Erreur:', error);
        showToast('Erreur de connexion', 'error');
        return false;
    }
}

async function faceLogin() {
    const email = document.getElementById('face-email')?.value;
    
    if (!email) {
        showToast('Email requis', 'error');
        return;
    }
    
    if (!currentFaceImage) {
        showToast('Veuillez positionner votre visage', 'error');
        return;
    }
    
    const faceFile = dataURLtoFile(currentFaceImage, 'face.jpg');
    const formData = new FormData();
    formData.append('email', email);
    formData.append('face_image', faceFile);
    
    try {
        const response = await fetch(`${API_BASE}/face/login/`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok) {
            setAuthToken(data.token);
            localStorage.setItem('user', JSON.stringify(data.user));
            showToast('Connexion réussie', 'success');
            window.location.href = '/dashboard.html';
        } else {
            showToast(data.error || 'Visage non reconnu', 'error');
        }
    } catch (error) {
        console.error('Erreur:', error);
        showToast('Erreur de connexion', 'error');
    }
}

// Initialisation
document.addEventListener('DOMContentLoaded', async () => {
    // Charger Face API
    await initFaceAPI();
    
    // Bouton démarrer caméra
    const startCameraBtn = document.getElementById('start-camera');
    if (startCameraBtn) {
        startCameraBtn.addEventListener('click', startFaceCamera);
    }
    
    // Formulaire connexion faciale
    const faceLoginForm = document.getElementById('face-login');
    if (faceLoginForm) {
        faceLoginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await faceLogin();
        });
    }
    
    // Activation reconnaissance faciale (page profil)
    const enableFaceBtn = document.getElementById('enable-face');
    if (enableFaceBtn) {
        enableFaceBtn.addEventListener('click', async () => {
            await startFaceCamera();
            // Attendre 3 secondes puis capturer et activer
            setTimeout(async () => {
                await enableFaceRecognition();
                stopFaceCamera();
            }, 3000);
        });
    }
});