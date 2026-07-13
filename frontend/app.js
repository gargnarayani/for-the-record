
// FOR THE RECORD - FRONTEND INTERFACE
// File: frontend/app.js

let currentMode = "mp3"; // default baseline mode state

const modeMp3Btn = document.getElementById("modeMp3");
const modeYoutubeBtn = document.getElementById("modeYoutube");
const appDescription = document.getElementById("appDescription");
const syncButton = document.getElementById("syncButton");
const consoleOutput = document.getElementById("consoleOutput");

// Flip UI view over to MP3 mode
modeMp3Btn.addEventListener("click", () => {
    currentMode = "mp3";
    modeMp3Btn.className = "border-b-2 border-slate-700 font-bold pb-1 transition-all";
    modeYoutubeBtn.className = "text-slate-400 hover:text-slate-600 pb-1 transition-all";
    appDescription.innerText = "Turn your Spotify playlist into MP3 files";
    syncButton.innerText = "Get My Music";
    consoleOutput.innerHTML = `<div class="text-slate-400">Ready to go. Paste a link above to begin!</div>`;
});

// Flip UI view over to YouTube Playlist mode
modeYoutubeBtn.addEventListener("click", () => {
    currentMode = "youtube";
    modeYoutubeBtn.className = "border-b-2 border-slate-700 font-bold pb-1 transition-all";
    modeMp3Btn.className = "text-slate-400 hover:text-slate-600 pb-1 transition-all";
    appDescription.innerText = "Turn your Spotify playlist into a YouTube playlist";
    syncButton.innerText = "Make Playlist";
    consoleOutput.innerHTML = `<div class="text-slate-400">Ready to build your mix. Paste a link above to begin!</div>`;
});

// Primary Button Action Event Listener
document.getElementById("syncButton").addEventListener("click", async () => {
    const urlInput = document.getElementById("spotifyUrlInput");
    const statusIndicator = document.getElementById("statusIndicator");
    const playlistUrl = urlInput.value.trim();

    // Start UI processing states
    syncButton.disabled = true;
    statusIndicator.innerHTML = `
        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-300 opacity-75"></span>
        <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-400"></span>
    `;

    if (currentMode === "mp3") {
        syncButton.innerText = "Getting your music...";
        consoleOutput.innerHTML = `<div class="text-teal-400">Starting up the pipeline...</div>`;
        consoleOutput.innerHTML += `<div class="text-slate-400">Reading your playlist link...</div>`;

        try {
            const response = await fetch('http://127.0.0.1:5000/api/sync', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: playlistUrl })
            });
            const data = await response.json();

            if (response.ok && data.status === "success") {
                consoleOutput.innerHTML += `<div class="text-indigo-400">Finding your songs on YouTube...</div>`;
                consoleOutput.innerHTML += `<div class="text-slate-500">Found: ${data.playlist_name} (${data.track_count} tracks).</div>`;
                consoleOutput.innerHTML += `<div class="text-slate-400">Downloading tracks into folder: ${data.playlist_name}...</div>`;
                consoleOutput.innerHTML += `<div class="text-slate-400">Shrinking audio files down for your iPod storage...</div>`;
                consoleOutput.innerHTML += `<div class="text-slate-400">Adding track titles and artwork tags...</div>`;
                consoleOutput.innerHTML += `<div class="text-emerald-400 font-bold">All done! Your folder is ready.</div>`;
            } else {
                consoleOutput.innerHTML += `<div class="text-rose-400 font-bold">Something went wrong: ${data.message}</div>`;
            }
        } catch (error) {
            consoleOutput.innerHTML += `<div class="text-rose-500 font-bold">Could not connect to the backend server.</div>`;
        } finally {
            syncButton.disabled = false;
            syncButton.innerText = "Get My Music";
            // FIXED: Resets status light inside the MP3 mode finally block
            statusIndicator.innerHTML = `
                <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-slate-300 opacity-75"></span>
                <span class="relative inline-flex rounded-full h-2 w-2 bg-slate-400"></span>
            `;
        }

    } else {
        // YOUTUBE PLAYLIST CONNECTION
        syncButton.innerText = "Creating playlist...";
        consoleOutput.innerHTML = `<div class="text-teal-400">Connecting to YouTube...</div>`;
        consoleOutput.innerHTML += `<div class="text-slate-400">Reading your playlist link...</div>`;

        try {
            const response = await fetch('http://127.0.0.1:5000/api/youtube-playlist', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: playlistUrl })
            });
            const data = await response.json();

            if (response.ok && data.status === "success") {
                consoleOutput.innerHTML += `<div class="text-indigo-400 font-bold">Creating new target playlist on YouTube...</div>`;
                consoleOutput.innerHTML += `<div class="text-slate-400">Finding matching videos and adding them over...</div>`;
                consoleOutput.innerHTML += `<div class="text-emerald-400 font-bold">All done! Check your YouTube account dashboard.</div>`;
            } else {
                consoleOutput.innerHTML += `<div class="text-rose-400 font-bold">Something went wrong: ${data.message}</div>`;
            }
        } catch (error) {
            consoleOutput.innerHTML += `<div class="text-rose-500 font-bold">Could not connect to the backend server.</div>`;
        } finally {
            syncButton.disabled = false;
            syncButton.innerText = "Make Playlist";
            statusIndicator.innerHTML = `
                <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-slate-300 opacity-75"></span>
                <span class="relative inline-flex rounded-full h-2 w-2 bg-slate-400"></span>
            `;
        }
    }
});