const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const progress = document.querySelector(".scroll-progress");
const updateProgress = () => {
  if (!progress) return;
  const scrollTop = window.scrollY || document.documentElement.scrollTop;
  const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
  const ratio = maxScroll > 0 ? Math.min(scrollTop / maxScroll, 1) : 0;
  progress.style.width = `${ratio * 100}%`;
};
window.addEventListener("scroll", updateProgress, { passive: true });
window.addEventListener("resize", updateProgress);
updateProgress();

const revealItems = document.querySelectorAll(".reveal");
if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.14 }
  );
  revealItems.forEach((item) => observer.observe(item));
} else {
  revealItems.forEach((item) => item.classList.add("is-visible"));
}

const rotatingWord = document.querySelector("[data-rotate]");
if (rotatingWord && !reduceMotion) {
  const words = ["Strom", "Daten", "Betrug", "Jobs", "Macht"];
  let index = 0;
  window.setInterval(() => {
    index = (index + 1) % words.length;
    rotatingWord.textContent = words[index];
  }, 1500);
}

const canvas = document.getElementById("network");
if (canvas && !reduceMotion) {
  const context = canvas.getContext("2d");
  let width = 0;
  let height = 0;
  let points = [];
  let animationFrame = 0;

  const createPoints = () => {
    const count = Math.min(Math.max(Math.floor(window.innerWidth / 22), 42), 88);
    points = Array.from({ length: count }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.34,
      vy: (Math.random() - 0.5) * 0.34,
      radius: Math.random() * 1.9 + 0.9
    }));
  };

  const resizeCanvas = () => {
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    width = window.innerWidth;
    height = window.innerHeight;
    canvas.width = Math.floor(width * ratio);
    canvas.height = Math.floor(height * ratio);
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    createPoints();
  };

  const draw = () => {
    context.clearRect(0, 0, width, height);

    points.forEach((point, index) => {
      point.x += point.vx;
      point.y += point.vy;

      if (point.x < 0 || point.x > width) point.vx *= -1;
      if (point.y < 0 || point.y > height) point.vy *= -1;

      context.beginPath();
      context.arc(point.x, point.y, point.radius, 0, Math.PI * 2);
      context.fillStyle = "rgba(255, 191, 85, 0.62)";
      context.fill();

      for (let nextIndex = index + 1; nextIndex < points.length; nextIndex += 1) {
        const other = points[nextIndex];
        const distance = Math.hypot(point.x - other.x, point.y - other.y);
        if (distance < 132) {
          context.beginPath();
          context.moveTo(point.x, point.y);
          context.lineTo(other.x, other.y);
          context.strokeStyle = `rgba(113, 231, 255, ${0.16 * (1 - distance / 132)})`;
          context.lineWidth = 1;
          context.stroke();
        }
      }
    });

    animationFrame = window.requestAnimationFrame(draw);
  };

  window.addEventListener("resize", resizeCanvas);
  resizeCanvas();
  draw();

  window.addEventListener("pagehide", () => {
    window.cancelAnimationFrame(animationFrame);
  });
}
