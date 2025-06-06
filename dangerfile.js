import { danger, warn, message } from 'danger'
import fetch from 'node-fetch'
import * as dotenv from 'dotenv'

dotenv.config()

const prTitle = danger.github.pr.title
const files = [...danger.git.created_files, ...danger.git.modified_files].join(', ')
const diffStats = danger.github.pr.additions + danger.github.pr.deletions

let summary = `🧠 PR Intel
- Title: ${prTitle}
- Files Touched: ${files}
- Line Changes: ${diffStats}
`

// Add local risk heuristics
const flagged = files.match(/exploit|payload|loader|shell|network|binary|c2/i)
if (flagged) {
  warn(`🚨 High-risk keywords found in files: ${flagged[0]}`)
  summary += '\n🚩 Possible Operational Risk: HIGH\n'
}

// Optional: GPT commentary
async function gptOpsIntel() {
  try {
    const res = await fetch("https://api.openai.com/v1/chat/completions", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${process.env.OPENAI_API_KEY}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        model: "gpt-4",
        messages: [
          { role: "system", content: "You are an infosec analyst reviewing a pull request for a threatware platform." },
          { role: "user", content: `Files changed: ${files}\nPR Title: ${prTitle}` }
        ]
      })
    })

    const json = await res.json()
    const gptMsg = json.choices[0].message.content
    message("🧠 GPT-4 Intel:\n" + gptMsg)
  } catch (err) {
    message("⚠️ GPT-4 analysis failed.")
  }
}

await gptOpsIntel()
message(summary)

const fs = require("fs");
const { execSync } = require("child_process");

try {
  execSync("python3 scripts/threat_attributor.py");
  const report = JSON.parse(fs.readFileSync("threat_report.json", "utf8"));

  markdown("## 🕵️ Threat Attribution Report");

  Object.entries(report.domains).forEach(([domain, info]) => {
    markdown(`- 🔗 Domain: \`${domain}\` - ${JSON.stringify(info)}`);
  });

  Object.entries(report.ips).forEach(([ip, info]) => {
    markdown(`- 🧠 IP: \`${ip}\`\n\n\`\`\`\nWHOIS:\n${info.whois?.slice(0, 300) || 'N/A'}\n\nShodan:\n${JSON.stringify(info.shodan, null, 2)}\n\`\`\``);
  });
} catch (error) {
  markdown(`❌ Threat attribution failed: ${error.message}`);
}
