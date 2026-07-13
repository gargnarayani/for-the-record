
// FOR THE RECORD - FRONTEND INTERFACE
// File: frontend/app.js

document.getElementById("syncButton").addEventListener("click", async () => {
    const urlInput = document.getElementById("spotifyUrlInput");
    const syncButton = document.getElementById("syncButton");
    const consoleOutput = document.getElementById("consoleOutput");
    const statusIndicator = document.getElementById("statusIndicator");

    const playlistUrl = urlInput.value.trim();

    // Simplified initial status updates
    consoleOutput.innerHTML = `<div class="text-teal-400">Starting up the pipeline...</div>`;
    consoleOutput.innerHTML += `<div class="text-slate-400">Reading your playlist link...</div>`;
    
    // Status visual triggers
    syncButton.disabled = true;
    syncButton.innerText = "Getting your music...";
    statusIndicator.innerHTML = `
        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-300 opacity-75"></span>
        <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-400"></span>
    `;

    try {
        // Post track links out to backend endpoints
        const response = await fetch('http://127.0.0.1:5000/api/sync', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: playlistUrl })
        });

        const data = await response.json();

        if (response.ok && data.status === "success") {
            // Conversational, plain-English update streams
            consoleOutput.innerHTML += `<div class="text-indigo-400">Finding your songs on YouTube...</div>`;
            consoleOutput.innerHTML += `<div class="text-slate-500">Found: ${data.playlist_name} (${data.track_count} tracks).</div>`;
            consoleOutput.innerHTML += `<div class="text-slate-400">Downloading tracks into your folder...</div>`;
            consoleOutput.innerHTML += `<div class="text-slate-400">Shrinking audio files down for your iPod storage...</div>`;
            consoleOutput.innerHTML += `<div class="text-slate-400">Adding track titles and artwork tags...</div>`;
            consoleOutput.innerHTML += `<div class="text-emerald-400 font-bold">All done! Your music is ready.</div>`;
        } else {
            consoleOutput.innerHTML += `<div class="text-rose-400 font-bold">Something went wrong: ${data.message}</div>`;
        }

    } catch (error) {
        consoleOutput.innerHTML += `<div class="text-rose-500 font-bold">Could not connect to the backend server.</div>`;
    } finally {
        // Reset operational flags back to default baseline states
        syncButton.disabled = false;
        syncButton.innerText = "Get My Music";
        statusIndicator.innerHTML = `
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-slate-300 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-2 w-2 bg-slate-400"></span>
        `;
    }
});