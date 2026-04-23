<!DOCTYPE html>

<title>Flutter Code Reviewer Agent - README</title>
<style>
body{
  margin:0;
  font-family: Arial, sans-serif;
  background:#0b0f1a;
  color:#e6e6e6;
  line-height:1.6;
}
.container{
  max-width:1000px;
  margin:auto;
  padding:40px;
}
h1,h2,h3{
  color:#00d4ff;
}
code, pre{
  background:#111827;
  padding:10px;
  border-radius:8px;
  display:block;
  overflow-x:auto;
}
.section{
  margin-bottom:50px;
  padding-bottom:20px;
  border-bottom:1px solid #1f2937;
}
img{
  width:100%;
  border-radius:10px;
  margin-top:10px;
  border:1px solid #1f2937;
}
.badge{
  display:inline-block;
  padding:5px 10px;
  margin:5px;
  background:#1f2937;
  border-radius:6px;
  font-size:12px;
}
</style>
</head>
<body>
<div class="container">

<h1>🔍 Flutter Code Reviewer Agent</h1>
<p>An AI-powered terminal agent that automatically reviews Flutter/Dart code, detects vulnerabilities, and applies fixes using Groq LLaMA 3.3 70B.</p>

<div class="section">
<h2>✨ Features</h2>
<span class="badge">Security Checks</span>
<span class="badge">Bug Detection</span>
<span class="badge">Performance Optimization</span>
<span class="badge">Architecture Review</span>
<span class="badge">Auto Fix</span>
<span class="badge">AI Powered</span>
</div>

<div class="section">
<h2>📸 Before & After Results</h2>

<h3>❌ Before</h3>
<p>Vulnerable and bad structured code</p>
<img src="test_screenshots/before.PNG" />
<img src="test_screenshots/before 2.PNG" />

<h3>✅ After</h3>
<p>Clean, secure and optimized code</p>
<img src="test_screenshots/after1.PNG" />
<img src="test_screenshots/after2.PNG" />
<img src="test_screenshots/after3.PNG" />

<img src="test_screenshots/after4.PNG" />

</div>

<div class="section">
<h2>🖥️ Terminal Output</h2>
<img src="test_screenshots/terminal.PNG" />
<img src="test_screenshots/terminal2.PNG" />
<img src="test_screenshots/terminal3.PNG" />
<img src="test_screenshots/terminal4.PNG" />
</div>

<div class="section">
<h2>⚙️ How It Works</h2>
<ul>
<li>Detect Flutter project automatically</li>
<li>Scan Dart files</li>
<li>Send code to Groq LLaMA 3.3 70B</li>
<li>Analyze security, bugs, performance</li>
<li>Suggest and apply fixes</li>
<li>Run dart analyze</li>
</ul>
</div>

<div class="section">
<h2>🚀 Run Project</h2>
<pre>
pip install groq python-dotenv
</pre>

<h3>Create .env</h3>
<pre>
GROQ_API_KEY=your_key_here
</pre>

<h3>Run Agent</h3>
<pre>
python reviewer_agent.py
</pre>
</div>

<div class="section">
<h2>💬 Commands</h2>
<pre>
all        → scan full project
filename   → scan file
list       → show files
exit       → close agent
</pre>
</div>

<div class="section">
<h2>🎯 Goal</h2>
<p>Make Flutter code production-ready automatically with AI-powered review and fixes.</p>
</div>

</div>
</body>
</html>
