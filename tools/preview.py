#!/usr/bin/env python3
import http.server
import socketserver
import sys
from pathlib import Path

# Datei aus Argument lesen (Standard: README.md)
TARGET_FILE = sys.argv[1] if len(sys.argv) > 1 else "README.md"
PORT = 6419

HTML_SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>KaTeX Preview</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.10/dist/katex.min.css">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/github-markdown-css/5.5.1/github-markdown.min.css">
  <script src="https://cdn.jsdelivr.net/npm/marked@12.0.1/marked.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/katex@0.16.10/dist/katex.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/katex@0.16.10/dist/contrib/auto-render.min.js"></script>
  <style>
    body { background-color: #0d1117; color: #c9d1d9; padding: 30px; }
    .markdown-body { max-width: 900px; margin: 0 auto; background-color: transparent !important; color: inherit; }
  </style>
</head>
<body class="markdown-body">
  <div id="content"></div>
  <script>
    async function update() {
      const res = await fetch('/raw');
      const text = await res.text();
      document.getElementById('content').innerHTML = marked.parse(text);
      renderMathInElement(document.getElementById('content'), {
        delimiters: [
          {left: '$$', right: '$$', display: true},
          {left: '$', right: '$', display: false}
        ],
        throwOnError: false
      });
    }
    update();
    // Automatischer Live-Reload alle 1.5 Sekunden
    setInterval(update, 1500);
  </script>
</body>
</html>"""

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/raw":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            p = Path(TARGET_FILE)
            content = p.read_bytes() if p.exists() else f"File '{TARGET_FILE}' not found.".encode()
            self.wfile.write(content)
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_SHELL.encode())

    def log_message(self, format, *args):
        pass # Stummschalten der Request-Logs für sauberes Terminal

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"[*] KaTeX Live-Preview für '{TARGET_FILE}' aktiv: http://localhost:{PORT}")
    print("[*] Beenden mit Ctrl+C")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
