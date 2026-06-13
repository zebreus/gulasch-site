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

const rotatingText = document.querySelector("[data-rotate]");
if (rotatingText && !reduceMotion) {
  const phrases = [
    "„Kannst du mir das einfacher erklären?“",
    "„Mach daraus bitte eine kurze Liste.“",
    "„Welche Frage sollte ich noch stellen?“",
    "„Schreib es höflich, aber nicht steif.“",
    "„Fass es auf eine halbe Seite zusammen.“"
  ];
  let index = 0;
  window.setInterval(() => {
    index = (index + 1) % phrases.length;
    rotatingText.textContent = phrases[index];
  }, 1800);
}

const countNumbers = () => {
  const counters = document.querySelectorAll("[data-count]");
  counters.forEach((counter) => {
    const target = Number(counter.getAttribute("data-count"));
    if (!Number.isFinite(target)) return;

    const duration = 900;
    const startTime = performance.now();
    const tick = (time) => {
      const progressValue = Math.min((time - startTime) / duration, 1);
      counter.textContent = Math.round(target * progressValue).toString();
      if (progressValue < 1) window.requestAnimationFrame(tick);
    };
    window.requestAnimationFrame(tick);
  });
};

let counted = false;
const proofSection = document.querySelector(".proof");
if (proofSection && "IntersectionObserver" in window && !reduceMotion) {
  const counterObserver = new IntersectionObserver(
    (entries) => {
      if (!counted && entries.some((entry) => entry.isIntersecting)) {
        counted = true;
        countNumbers();
        counterObserver.disconnect();
      }
    },
    { threshold: 0.25 }
  );
  counterObserver.observe(proofSection);
} else {
  countNumbers();
}

const demos = {
  letter: {
    title: "Einladung etwas lockerer",
    text: "Liebe Nachbarinnen und Nachbarn, am Samstag stellen wir ein paar Tische in den Hof. Wer Lust hat, kommt einfach dazu. Eine Kleinigkeit zu essen ist willkommen, aber kein Muss."
  },
  explain: {
    title: "Amtssprache übersetzt",
    text: "Das Amt braucht noch einen Nachweis. Sie haben zwei Wochen Zeit. Wenn Sie unsicher sind, rufen Sie dort an und fragen nach, welches Dokument genau gemeint ist."
  },
  travel: {
    title: "Reise nicht zu voll packen",
    text: "Nehmen Sie pro Tag lieber nur ein bis zwei feste Programmpunkte. Dazwischen Pausen lassen. Adresse vom Hotel und Rückweg einmal auf Papier notieren."
  }
};

const demoTitle = document.getElementById("demo-title");
const demoText = document.getElementById("demo-text");
const demoButtons = document.querySelectorAll("[data-demo]");
demoButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const demo = demos[button.getAttribute("data-demo")];
    if (!demo || !demoTitle || !demoText) return;

    demoButtons.forEach((item) => item.classList.remove("is-active"));
    button.classList.add("is-active");
    demoTitle.textContent = demo.title;
    demoText.textContent = demo.text;
  });
});
if (demoButtons[0]) demoButtons[0].classList.add("is-active");

const canvas = document.getElementById("spark-canvas");
if (canvas && !reduceMotion) {
  const context = canvas.getContext("2d");
  let width = 0;
  let height = 0;
  let sparks = [];
  let animationFrame = 0;

  const createSparks = () => {
    const count = Math.min(Math.max(Math.floor(window.innerWidth / 40), 18), 42);
    sparks = Array.from({ length: count }, () => ({
      x: Math.random() * width,
      y: Math.random() * height,
      vx: (Math.random() - 0.5) * 0.18,
      vy: (Math.random() - 0.5) * 0.18,
      radius: Math.random() * 1.6 + 0.7,
      hue: 38 + Math.random() * 175
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
    createSparks();
  };

  const draw = () => {
    context.clearRect(0, 0, width, height);
    sparks.forEach((spark, index) => {
      spark.x += spark.vx;
      spark.y += spark.vy;

      if (spark.x < 0 || spark.x > width) spark.vx *= -1;
      if (spark.y < 0 || spark.y > height) spark.vy *= -1;

      context.beginPath();
      context.arc(spark.x, spark.y, spark.radius, 0, Math.PI * 2);
      context.fillStyle = `hsla(${spark.hue}, 70%, 45%, 0.24)`;
      context.fill();

      for (let nextIndex = index + 1; nextIndex < sparks.length; nextIndex += 1) {
        const other = sparks[nextIndex];
        const distance = Math.hypot(spark.x - other.x, spark.y - other.y);
        if (distance < 95) {
          context.beginPath();
          context.moveTo(spark.x, spark.y);
          context.lineTo(other.x, other.y);
          context.strokeStyle = `rgba(68, 83, 56, ${0.06 * (1 - distance / 95)})`;
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
