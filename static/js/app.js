function bootIcons() {
  if (window.lucide) {
    window.lucide.createIcons();
  }
}

function bootShare() {
  document.querySelectorAll("[data-share]").forEach((button) => {
    button.addEventListener("click", async () => {
      const shareData = { title: document.title, url: window.location.href };
      if (navigator.share) {
        await navigator.share(shareData);
      } else {
        await navigator.clipboard.writeText(window.location.href);
        button.textContent = "Copied";
        setTimeout(() => window.location.reload(), 800);
      }
    });
  });
}

function bootPlayers() {
  document.querySelectorAll(".video-player").forEach((video) => {
    const src = video.dataset.hls;
    let hls = null;
    if (src && window.Hls && Hls.isSupported()) {
      hls = new Hls({ capLevelToPlayerSize: true });
      hls.loadSource(src);
      hls.attachMedia(video);
    } else if (src && video.canPlayType("application/vnd.apple.mpegurl")) {
      video.src = src;
    }

    video.addEventListener("ended", () => {
      if (video.dataset.nextUrl) {
        window.location.href = video.dataset.nextUrl;
      }
    });

    const shell = video.closest(".player-shell");
    if (!shell || !hls) return;

    shell.querySelectorAll("[data-quality]").forEach((button) => {
      button.addEventListener("click", () => {
        shell.querySelectorAll("[data-quality]").forEach((item) => item.classList.remove("active"));
        button.classList.add("active");
        const quality = button.dataset.quality;
        if (quality === "auto") {
          hls.currentLevel = -1;
          return;
        }
        const target = Number(quality);
        const levelIndex = hls.levels.findIndex((level) => Math.abs(level.height - target) <= 24);
        hls.currentLevel = levelIndex >= 0 ? levelIndex : -1;
      });
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  bootIcons();
  bootShare();
  bootPlayers();
});
