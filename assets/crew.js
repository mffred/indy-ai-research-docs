// Progressive enhancement for /crew. Without JavaScript the form posts normally to /api/crew and
// the server redirects to /crew/?sent=1. With JavaScript, the answers are sent with fetch, errors
// appear next to their fields, and the entered data stays put if something goes wrong.
(function () {
  var form = document.getElementById("crew-form");
  if (!form) return;
  var status = document.getElementById("crew-status");
  var thanks = document.getElementById("crew-thanks");
  var submit = form.querySelector("button[type=submit]");

  function showThanks() {
    form.hidden = true;
    thanks.hidden = false;
    thanks.focus();
  }

  // Arriving from a no-JS submission.
  try {
    if (new URLSearchParams(location.search).get("sent") === "1") showThanks();
  } catch (e) { /* URLSearchParams unavailable: the form simply stays visible */ }

  function clearErrors() {
    form.querySelectorAll(".cf-err").forEach(function (p) { p.hidden = true; p.textContent = ""; });
    form.querySelectorAll(".is-invalid").forEach(function (el) { el.classList.remove("is-invalid"); });
    form.querySelectorAll("[aria-invalid]").forEach(function (el) { el.removeAttribute("aria-invalid"); });
    status.hidden = true;
    status.textContent = "";
  }

  function showFieldError(id, message) {
    var err = document.getElementById("err-" + id);
    var wrap = document.getElementById("field-" + id);
    if (err) { err.textContent = message; err.hidden = false; }
    if (wrap) {
      wrap.classList.add("is-invalid");
      var input = wrap.querySelector("input[type=text],input[type=email]");
      if (input) input.setAttribute("aria-invalid", "true");
    }
  }

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    clearErrors();

    var idleLabel = submit.textContent;
    submit.disabled = true;
    submit.textContent = "Sending...";

    // Same body shape a plain form post sends, so the server handles both paths identically.
    var body = new URLSearchParams(new FormData(form));

    fetch(form.getAttribute("action"), {
      method: "POST",
      credentials: "same-origin",
      headers: { "Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8" },
      body: body.toString()
    })
      .then(function (res) {
        return res.json().catch(function () { return { ok: false }; }).then(function (data) {
          return { httpOk: res.ok, data: data };
        });
      })
      .then(function (result) {
        if (result.httpOk && result.data && result.data.ok) {
          showThanks();
          return; // leave the button disabled: the form is gone
        }
        var fields = (result.data && result.data.fields) || {};
        Object.keys(fields).forEach(function (id) { showFieldError(id, fields[id]); });
        status.textContent = (result.data && result.data.error) || "Something went wrong. Your answers are still filled in, so please try again.";
        status.hidden = false;
        status.focus();
        submit.disabled = false;
        submit.textContent = idleLabel;
      })
      .catch(function () {
        status.textContent = "We could not reach the server. Your answers are still filled in, so please try again.";
        status.hidden = false;
        status.focus();
        submit.disabled = false;
        submit.textContent = idleLabel;
      });
  });
})();
