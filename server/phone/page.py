"""The one page a phone sees before it is paired: enter the code shown on the PC. Self-contained -
no script or style from anywhere else - because nothing else is served until it is paired."""

PAIR_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pair with Jarvis</title>
<style>
  :root { color-scheme: light dark; --bg:#F8F9FB; --ink:#16181D; --muted:#5B6270; --accent:#2F5BEA; }
  @media (prefers-color-scheme: dark) { :root { --bg:#0E1014; --ink:#ECEEF2; --muted:#9AA1AD; --accent:#7C9CFF; } }
  body { margin:0; min-height:100vh; display:grid; place-items:center; background:var(--bg); color:var(--ink);
         font:16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
  main { width:min(360px, 100vw - 32px); }
  h1 { font-size:28px; margin:0 0 4px; }
  p { color:var(--muted); margin:0 0 20px; }
  input { box-sizing:border-box; width:100%; padding:14px 16px; border-radius:16px; border:1px solid #8884;
          background:transparent; color:var(--ink); font-size:18px; margin-bottom:10px; }
  #code { letter-spacing:.4em; text-align:center; font-size:28px; }
  button { width:100%; padding:14px; border:0; border-radius:999px; background:var(--ink); color:var(--bg);
           font-size:16px; font-weight:600; }
  #msg { color:#D64545; min-height:24px; margin-top:12px; }
</style></head>
<body><main>
  <h1>Pair with Jarvis</h1>
  <p>Enter the six-digit code shown on your PC, in Settings &rsaquo; Phone.</p>
  <input id="code" inputmode="numeric" autocomplete="one-time-code" maxlength="6" placeholder="000000">
  <input id="name" placeholder="Name this phone" value="Phone">
  <button id="go">Pair</button>
  <div id="msg"></div>
</main>
<script>
  const code = document.getElementById("code");
  code.value = new URLSearchParams(location.search).get("code") || "";
  document.getElementById("go").onclick = async () => {
    const name = document.getElementById("name").value;
    const r = await fetch("/api/phone/pair", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: code.value, name }) });
    if (r.ok) { location.replace("/"); return; }
    const body = await r.json().catch(() => ({}));
    document.getElementById("msg").textContent = body.message || "That did not work.";
  };
</script>
</body></html>"""  # noqa: E501 - a page, laid out as one
