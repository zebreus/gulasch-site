(function () {
  var notes = [
    "lorem ipsum slop lorem ipsum.",
    "ipsum slop lorem ipsum slop.",
    "slop lorem ipsum slop lorem.",
    "lorem slop ipsum lorem slop.",
    "ipsum lorem slop ipsum lorem."
  ];

  var note = document.getElementById("field-note");
  if (note) {
    note.textContent = notes[Math.floor(Math.random() * notes.length)];
  }

  var counter = document.getElementById("visitor-count");
  if (counter) {
    counter.textContent = "static";
    counter.title = "Static Nix-hosted copy. No server-side counter is running here.";
  }

  var guestbookForm = document.getElementById("guestbook-form");
  var guestbookText = document.getElementById("guestbook-text");
  var guestbookStatus = document.getElementById("guestbook-status");

  if (guestbookForm && guestbookText && guestbookStatus) {
    guestbookForm.addEventListener("submit", function (event) {
      event.preventDefault();

      var text = guestbookText.value.trim();
      if (!text) {
        guestbookStatus.textContent = "empty slop refused";
        return;
      }

      guestbookStatus.textContent = "static slopbook: read /guestbook.txt";
    });
  }
}());
