import base64
import json
from datetime import datetime

from Crypto.Cipher import AES
from fpdf import FPDF


def decrypt_entry(line, key):
    raw = base64.b64decode(line)
    nonce, tag, ciphertext = raw[:16], raw[16:32], raw[32:]
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    return json.loads(cipher.decrypt_and_verify(ciphertext, tag).decode())


def generate_pdf_report(log_file, key_file, output="mission_report.pdf"):
    key = open(key_file, "rb").read()
    entries = []

    with open(log_file, "r") as f:
        for line in f:
            try:
                entries.append(decrypt_entry(line.strip(), key))
            except BaseException:
                continue

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="SessionExfil OMEGA: Mission Report", ln=1, align="C")
    pdf.cell(200, 10, txt="Generated: " + datetime.utcnow().isoformat(), ln=2)

    for entry in entries:
        line = f"[{entry['time']}] ({entry['type']}) - {entry['data']}"
        pdf.multi_cell(0, 10, line)

    pdf.output(output)
    print(f"[+] Report generated: {output}")


if __name__ == "__main__":
    generate_pdf_report("session_memory.json", "session_key.bin")
