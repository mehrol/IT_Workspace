function bootIcons() {
  if (window.lucide) {
    window.lucide.createIcons();
  }
}

function bootShare() {
  document.querySelectorAll("[data-share]").forEach((button) => {
    button.addEventListener("click", async () => {
      const shareUrl = button.dataset.shareUrl || window.location.href;
      const shareData = { title: button.dataset.shareTitle || document.title, url: shareUrl };
      if (navigator.share) {
        await navigator.share(shareData);
      } else {
        await navigator.clipboard.writeText(shareUrl);
        button.textContent = "Copied";
        setTimeout(() => window.location.reload(), 800);
      }
    });
  });
}

/* ────────────────────────────────────────────────────────────────
   HELPER: format seconds → "m:ss" or "h:mm:ss"
   ──────────────────────────────────────────────────────────────── */
function fmtTime(sec) {
  if (!Number.isFinite(sec) || sec < 0) return "0:00";
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = Math.floor(sec % 60);
  const ss = String(s).padStart(2, "0");
  return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${ss}` : `${m}:${ss}`;
}

/* ────────────────────────────────────────────────────────────────
   SHORTS – Instagram Reels style
   • Tap centre = play / pause (overlay icon fades)
   • No seek, no volume, no quality – pure full-screen reel feel
   ──────────────────────────────────────────────────────────────── */
function bootShortPlayer() {
  const overlay = document.getElementById("short-overlay");
  if (!overlay) return;

  const video = document.getElementById("main-video");
  if (!video) return;

  const toggle = () => {
    if (video.paused) {
      video.play().catch(() => {});
    } else {
      video.pause();
    }
  };

  overlay.addEventListener("click", toggle);

  const maybeSkipForward = (event) => {
    if (!video.dataset.nextUrl) return false;
    const rect = video.getBoundingClientRect();
    return event.clientX > rect.left + rect.width * 0.65;
  };

  const handleShortClick = (event) => {
    if (maybeSkipForward(event)) {
      window.location.href = video.dataset.nextUrl;
      return;
    }
    toggle();
  };

  const nextBtn = document.getElementById("short-next");
  if (nextBtn) {
    nextBtn.addEventListener("click", () => {
      if (video.dataset.nextUrl) window.location.href = video.dataset.nextUrl;
    });
  }

  video.addEventListener("click", handleShortClick);

  const sync = () => {
    overlay.classList.toggle("is-hidden", !video.paused);
  };
  video.addEventListener("play", sync);
  video.addEventListener("pause", sync);
  sync();

  // autoplay-next on end (like Reels auto-scroll)
  video.addEventListener("ended", () => {
    if (video.dataset.nextUrl) {
      window.location.href = video.dataset.nextUrl;
    }
  });
}

/* ────────────────────────────────────────────────────────────────
   LONG VIDEOS – YouTube style
   ──────────────────────────────────────────────────────────────── */
function bootYouTubePlayer() {
  const controls = document.getElementById("yt-controls");
  const video = document.getElementById("main-video");
  const frame = document.getElementById("player-frame");
  const shell = document.getElementById("player-shell");

  console.log("bootYouTubePlayer called");
  console.log("yt-controls:", controls);
  console.log("main-video:", video);
  console.log("player-frame:", frame);
  console.log("player-shell:", shell);

  if (!controls || !video || !frame || !shell) {
    console.log("Missing required elements for YouTube player");
    return;
  }

  console.log("Video type:", video.dataset.videoType);
  console.log("Video element classes:", video.className);

  /* ── HLS setup ──────────────────────────────────────────────── */
  const hlsSrc = video.dataset.hls;
  let hls = null;
  if (hlsSrc && window.Hls && Hls.isSupported()) {
    hls = new Hls({ capLevelToPlayerSize: true });
    hls.loadSource(hlsSrc);
    hls.attachMedia(video);
  } else if (hlsSrc && video.canPlayType("application/vnd.apple.mpegurl")) {
    video.src = hlsSrc;
  }

  /* ── DOM refs ────────────────────────────────────────────────── */
  const bigPlay     = document.getElementById("yt-big-play");
  const btnPlay     = document.getElementById("yt-play");
  const iconPlay    = document.getElementById("yt-icon-play");
  const iconPause   = document.getElementById("yt-icon-pause");
  const btnRew      = document.getElementById("yt-rew");
  const btnFwd      = document.getElementById("yt-fwd");
  const btnMute     = document.getElementById("yt-mute");
  const iconVolOn   = document.getElementById("yt-icon-vol-on");
  const iconVolOff  = document.getElementById("yt-icon-vol-off");
  const volSlider   = document.getElementById("yt-vol");
  const timeLabel   = document.getElementById("yt-time");
  const progressArea= document.getElementById("yt-progress-area");
  const fillBar     = document.getElementById("yt-fill-bar");
  const bufBar      = document.getElementById("yt-buf-bar");
  const scrubThumb  = document.getElementById("yt-scrub-thumb");
  const speedSelect = document.getElementById("yt-speed");
  const qualSelect  = document.getElementById("yt-quality");
  const btnCC       = document.getElementById("yt-cc");
  const btnPip      = document.getElementById("yt-pip");
  const btnFS       = document.getElementById("yt-fs");
  const iconFSon    = document.getElementById("yt-icon-fs-on");
  const iconFSoff   = document.getElementById("yt-icon-fs-off");

  /* ── Play / Pause ────────────────────────────────────────────── */
  const togglePlay = () => {
    if (video.paused) video.play().catch(() => {});
    else video.pause();
  };
  const syncPlayIcons = () => {
    const playing = !video.paused;
    if (iconPlay)  iconPlay.style.display  = playing ? "none" : "";
    if (iconPause) iconPause.style.display = playing ? "" : "none";
    if (bigPlay)   bigPlay.classList.toggle("is-hidden", playing);
  };

  if (bigPlay)  bigPlay.addEventListener("click", togglePlay);
  if (btnPlay)  btnPlay.addEventListener("click", togglePlay);
  video.addEventListener("click", togglePlay);
  video.addEventListener("play",  syncPlayIcons);
  video.addEventListener("pause", syncPlayIcons);
  syncPlayIcons();

  /* ── Rewind / Forward ────────────────────────────────────────── */
  if (btnRew) btnRew.addEventListener("click", () => { video.currentTime = Math.max(0, video.currentTime - 10); });
  if (btnFwd) btnFwd.addEventListener("click", () => { video.currentTime = Math.min(video.duration || 0, video.currentTime + 10); });

  /* ── Volume / Mute ───────────────────────────────────────────── */
  const syncVolIcons = () => {
    const muted = video.muted || video.volume === 0;
    if (iconVolOn)  iconVolOn.style.display  = muted ? "none" : "";
    if (iconVolOff) iconVolOff.style.display = muted ? "" : "none";
    if (volSlider)  volSlider.value = muted ? "0" : String(video.volume);
  };
  if (btnMute) {
    btnMute.addEventListener("click", () => {
      video.muted = !video.muted;
      if (!video.muted && video.volume === 0) { video.volume = 0.5; }
      syncVolIcons();
    });
  }
  if (volSlider) {
    volSlider.addEventListener("input", () => {
      video.volume = Number(volSlider.value);
      video.muted = video.volume === 0;
      syncVolIcons();
    });
  }
  video.addEventListener("volumechange", syncVolIcons);
  syncVolIcons();

  /* ── Progress / Seek bar ─────────────────────────────────────── */
  const updateProgress = () => {
    const dur = video.duration;
    if (!Number.isFinite(dur) || dur <= 0) return;
    const pct = (video.currentTime / dur) * 100;
    if (fillBar)    fillBar.style.width = pct + "%";
    if (scrubThumb) scrubThumb.style.left = pct + "%";
    if (timeLabel)  timeLabel.textContent = fmtTime(video.currentTime) + " / " + fmtTime(dur);
  };
  video.addEventListener("timeupdate", updateProgress);
  video.addEventListener("loadedmetadata", updateProgress);

  // buffer bar
  const updateBuffer = () => {
    if (!bufBar) return;
    const dur = video.duration;
    if (!Number.isFinite(dur) || dur <= 0) return;
    if (video.buffered.length > 0) {
      const end = video.buffered.end(video.buffered.length - 1);
      bufBar.style.width = (end / dur * 100) + "%";
    }
  };
  video.addEventListener("progress", updateBuffer);
  video.addEventListener("loadedmetadata", updateBuffer);

  // click-to-seek
  if (progressArea) {
    let dragging = false;

    const seekTo = (e) => {
      const rect = progressArea.getBoundingClientRect();
      const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
      const dur = video.duration;
      if (Number.isFinite(dur) && dur > 0) {
        video.currentTime = pct * dur;
        updateProgress();
      }
    };

    progressArea.addEventListener("mousedown", (e) => {
      dragging = true;
      seekTo(e);
    });
    document.addEventListener("mousemove", (e) => { if (dragging) seekTo(e); });
    document.addEventListener("mouseup", () => { dragging = false; });
    progressArea.addEventListener("click", seekTo);
  }

  /* ── Speed ───────────────────────────────────────────────────── */
  if (speedSelect) {
    speedSelect.addEventListener("change", () => {
      video.playbackRate = Number(speedSelect.value);
    });
  }

  /* ── Quality (HLS) ───────────────────────────────────────────── */
  if (qualSelect && !hlsSrc) qualSelect.disabled = true;
  if (qualSelect && hls) {
    qualSelect.addEventListener("change", () => {
      if (qualSelect.value === "auto") { hls.currentLevel = -1; return; }
      const target = Number(qualSelect.value);
      const idx = hls.levels.findIndex((l) => Math.abs(l.height - target) <= 24);
      hls.currentLevel = idx >= 0 ? idx : -1;
    });
  }

  /* ── CC / Subtitles ──────────────────────────────────────────── */
  if (btnCC) {
    btnCC.addEventListener("click", () => {
      const track = video.textTracks && video.textTracks[0];
      if (!track) return;
      track.mode = track.mode === "showing" ? "hidden" : "showing";
      btnCC.classList.toggle("active", track.mode === "showing");
    });
  }

  /* ── Picture-in-Picture ──────────────────────────────────────── */
  if (btnPip) {
    btnPip.addEventListener("click", async () => {
      try {
        if (document.pictureInPictureElement) {
          await document.exitPictureInPicture();
        } else {
          await video.requestPictureInPicture();
        }
      } catch (_) { /* not supported */ }
    });
  }

  /* ── Fullscreen ──────────────────────────────────────────────── */
  const syncFSIcons = () => {
    const isFS = !!document.fullscreenElement || shell.classList.contains("is-fullscreen");
    if (document.fullscreenElement) {
      shell.classList.add("is-fullscreen");
    } else {
      shell.classList.remove("is-fullscreen");
    }
    if (iconFSon)  iconFSon.style.display  = isFS ? "none" : "";
    if (iconFSoff) iconFSoff.style.display = isFS ? "" : "none";
  };

  if (btnFS) {
    btnFS.addEventListener("click", async () => {
      try {
        if (document.fullscreenElement) {
          await document.exitFullscreen();
        } else if (shell.requestFullscreen) {
          await shell.requestFullscreen();
        } else {
          shell.classList.toggle("is-fullscreen");
          syncFSIcons();
        }
      } catch (_) {
        shell.classList.toggle("is-fullscreen");
        syncFSIcons();
      }
    });
  }
  document.addEventListener("fullscreenchange", syncFSIcons);

  /* ── Auto-next on end ────────────────────────────────────────── */
  video.addEventListener("ended", () => {
    if (video.dataset.nextUrl) window.location.href = video.dataset.nextUrl;
  });

  /* ── Auto-hide controls ──────────────────────────────────────── */
  // For long videos, keep controls visible
  const showControls = () => {
    frame.classList.add("controls-visible");
  };
  // show controls initially and keep them visible
  showControls();

  /* ── Keyboard shortcuts (YouTube-standard) ───────────────────── */
  document.addEventListener("keydown", (e) => {
    // ignore when typing in inputs
    if (e.target.matches("input, textarea, select")) return;
    switch (e.key.toLowerCase()) {
      case " ":
      case "k":
        e.preventDefault();
        togglePlay();
        break;
      case "j":
        e.preventDefault();
        video.currentTime = Math.max(0, video.currentTime - 10);
        break;
      case "l":
        e.preventDefault();
        video.currentTime = Math.min(video.duration || 0, video.currentTime + 10);
        break;
      case "arrowleft":
        e.preventDefault();
        video.currentTime = Math.max(0, video.currentTime - 5);
        break;
      case "arrowright":
        e.preventDefault();
        video.currentTime = Math.min(video.duration || 0, video.currentTime + 5);
        break;
      case "arrowup":
        e.preventDefault();
        video.volume = Math.min(1, video.volume + 0.05);
        video.muted = false;
        syncVolIcons();
        break;
      case "arrowdown":
        e.preventDefault();
        video.volume = Math.max(0, video.volume - 0.05);
        syncVolIcons();
        break;
      case "m":
        e.preventDefault();
        video.muted = !video.muted;
        syncVolIcons();
        break;
      case "f":
        e.preventDefault();
        if (btnFS) btnFS.click();
        break;
      case "i":
        e.preventDefault();
        if (btnPip) btnPip.click();
        break;
      case "c":
        e.preventDefault();
        if (btnCC) btnCC.click();
        break;
      case "escape":
        if (document.fullscreenElement) {
          document.exitFullscreen();
        } else if (shell.classList.contains("is-fullscreen")) {
          shell.classList.remove("is-fullscreen");
          syncFSIcons();
        }
        break;
    }
  });

  /* ── Double-click to fullscreen (YouTube behavior) ────────────── */
  video.addEventListener("dblclick", (e) => {
    e.preventDefault();
    if (btnFS) btnFS.click();
  });
}

/* ────────────────────────────────────────────────────────────────
   EXTERNAL EMBEDS (YouTube iframes) – keep existing behavior
   ──────────────────────────────────────────────────────────────── */
function loadYouTubeApi() {
  if (window.YT && window.YT.Player) {
    return Promise.resolve();
  }

  return new Promise((resolve) => {
    const previous = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => {
      if (typeof previous === "function") previous();
      resolve();
    };

    if (!document.querySelector("script[src='https://www.youtube.com/iframe_api']")) {
      const script = document.createElement("script");
      script.src = "https://www.youtube.com/iframe_api";
      document.head.appendChild(script);
    }
  });
}

function bootExternalPlayers() {
  const players = [...document.querySelectorAll(".embed-player[data-platform='youtube']")];
  if (!players.length) return;

  loadYouTubeApi().then(() => {
    players.forEach((iframe) => {
      if (!iframe.id) return;

      const player = new YT.Player(iframe.id, {
        events: {
          onStateChange: (event) => {
            if (event.data === YT.PlayerState.ENDED && iframe.dataset.nextUrl) {
              window.location.href = iframe.dataset.nextUrl;
            }
          },
        },
      });
    });
  });
}

/* ────────────────────────────────────────────────────────────────
   POSTER PREVIEWS (unchanged)
   ──────────────────────────────────────────────────────────────── */
function withQueryParams(src, params) {
  const url = new URL(src, window.location.href);
  Object.entries(params).forEach(([key, value]) => url.searchParams.set(key, value));
  return url.toString();
}

function stopPosterPreview(poster) {
  const preview = poster.querySelector(".poster-preview");
  if (preview) {
    const hls = preview._hlsPreview;
    if (hls) hls.destroy();
    preview.remove();
  }
  poster.classList.remove("previewing");
}

function startPosterPreview(poster, trigger) {
  if (poster.querySelector(".poster-preview")) return;

  const platform = trigger.dataset.previewPlatform;
  const src = trigger.dataset.previewSrc;
  if (!src) return;

  let preview = null;
  if (platform === "youtube") {
    preview = document.createElement("iframe");
    preview.src = withQueryParams(src, {
      autoplay: "1",
      mute: "1",
      controls: "0",
      playsinline: "1",
      modestbranding: "1",
    });
    preview.allow = "autoplay; encrypted-media; picture-in-picture";
    preview.setAttribute("title", "Video preview");
  } else {
    preview = document.createElement("video");
    preview.muted = true;
    preview.autoplay = true;
    preview.loop = true;
    preview.playsInline = true;
    preview.preload = "metadata";
    if (src.toLowerCase().endsWith(".m3u8") && window.Hls && Hls.isSupported()) {
      const hls = new Hls({ capLevelToPlayerSize: true });
      hls.loadSource(src);
      hls.attachMedia(preview);
      preview._hlsPreview = hls;
    } else {
      preview.src = src;
    }
  }

  preview.className = "poster-preview";
  preview.setAttribute("aria-hidden", "true");
  poster.appendChild(preview);
  poster.classList.add("previewing");

  if (preview.play) {
    preview.play().catch(() => stopPosterPreview(poster));
  }
}

function bootPosterPreviews() {
  document.querySelectorAll("[data-hover-preview]").forEach((trigger) => {
    const poster = trigger.closest(".poster");
    if (!poster) return;

    poster.addEventListener("mouseenter", () => startPosterPreview(poster, trigger));
    poster.addEventListener("mouseleave", () => stopPosterPreview(poster));
    poster.addEventListener("focus", () => startPosterPreview(poster, trigger));
    poster.addEventListener("blur", () => stopPosterPreview(poster));
  });
}

/* ────────────────────────────────────────────────────────────────
   OTHER BOOTS (unchanged)
   ──────────────────────────────────────────────────────────────── */
function bootProfileTabs() {
  const buttons = document.querySelectorAll("[data-profile-tab]");
  const cards = document.querySelectorAll("[data-profile-domain]");
  if (!buttons.length || !cards.length) return;

  buttons.forEach((button) => {
    button.addEventListener("click", () => {
      const selected = button.dataset.profileTab;
      buttons.forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      cards.forEach((card) => {
        const domain = (card.dataset.profileDomain || "").toLowerCase();
        card.hidden = selected !== "all" && domain !== selected;
      });
    });
  });
}

function bootSearchPanel() {
  document.querySelectorAll("[data-search-panel]").forEach((form) => {
    const toggle = form.querySelector("[data-search-toggle]");
    const input = form.querySelector("input[name='q']");
    if (!toggle || !input) return;
    if (input.value.trim()) {
      form.classList.remove("collapsed");
    }

    toggle.addEventListener("click", () => {
      form.classList.toggle("collapsed");
      if (!form.classList.contains("collapsed")) {
        input.focus();
      }
    });
  });
}

function bootAdminForms() {
  const select = document.querySelector("[data-admin-form-select]");
  const forms = document.querySelectorAll("[data-admin-form]");
  if (!select || !forms.length) return;

  const showSelected = () => {
    forms.forEach((form) => {
      form.hidden = form.dataset.adminForm !== select.value;
    });
  };

  select.addEventListener("change", showSelected);
  showSelected();
}

/* ────────────────────────────────────────────────────────────────
   BOOT
   ──────────────────────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", () => {
  bootIcons();
  bootShare();

  // Player – pick the right mode
  // Delay player initialization slightly to ensure DOM is ready
  setTimeout(() => {
    bootShortPlayer();      // Insta-Reels for shorts
    bootYouTubePlayer();    // YouTube for long videos
    bootExternalPlayers();  // embedded YouTube iframes
  }, 100);

  bootPosterPreviews();
  bootProfileTabs();
  bootSearchPanel();
  bootAdminForms();
});
