import os
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont


def create_sample_documents():
    out_dir = Path("./sample_documents").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Normal Digital Question Paper (01_digital_exam.pdf)
    doc1 = fitz.open()
    page1 = doc1.new_page()
    text1 = """HIGH SCHOOL SCIENCE EXAMINATION - 2026

Q1. What is the primary function of mitochondria in eukaryotic cells?
A. Photosynthesis
B. ATP energy production
C. Protein packaging
D. Lipid synthesis
Answer: B

Q2. Which element has the chemical symbol 'Fe'?
(a) Fluorine
(b) Iron
(c) Francium
(d) Fermium
Answer: (b)

Q3. The speed of light in a vacuum is approximately 300,000 km/s. (True/False)
Answer: True
"""
    page1.insert_text((50, 72), text1, fontsize=12)
    doc1.save(str(out_dir / "01_digital_exam.pdf"))
    doc1.close()

    # 2. Scanned Question Paper (02_scanned_exam.png)
    img2 = Image.new("RGB", (800, 1000), color=(255, 255, 255))
    draw2 = ImageDraw.Draw(img2)
    text2 = """MATHEMATICS ENTRANCE TEST

1. What is the derivative of sin(x)?
A. cos(x)
B. -cos(x)
C. tan(x)
D. sec(x)
Ans: A

2. If 2x + 5 = 15, what is the value of x?
A. 3
B. 5
C. 7
D. 10
Ans: B
"""
    draw2.multiline_text((50, 60), text2, fill=(20, 20, 20), spacing=8)
    img2.save(str(out_dir / "02_scanned_exam.png"))

    # 3. Low-quality / Rotated Example (03_rotated_exam.png)
    img3 = Image.new("RGB", (800, 900), color=(245, 245, 240))
    draw3 = ImageDraw.Draw(img3)
    text3 = """PHYSICS SHORT TEST

1. Newton's First Law is also known as:
A. Law of Inertia
B. Law of Acceleration
C. Law of Reaction
D. Law of Gravitation
Answer: A
"""
    draw3.multiline_text((60, 80), text3, fill=(30, 30, 30), spacing=8)
    # Rotate slightly to simulate skew
    rotated3 = img3.rotate(3.5, expand=True, fillcolor=(255, 255, 255))
    rotated3.save(str(out_dir / "03_rotated_exam.png"))

    # 4. Multi-page Question Document (04_multipage_exam.pdf)
    doc4 = fitz.open()
    p4_1 = doc4.new_page()
    text4_1 = """ADVANCED BIOLOGY EXAM

17. Which of the following organelles is directly involved in cellular autophagy and cellular waste recycling?
A. Peroxisome
B. Ribosome
"""
    p4_1.insert_text((50, 72), text4_1, fontsize=12)

    p4_2 = doc4.new_page()
    text4_2 = """C. Lysosome
D. Endoplasmic Reticulum
Answer: C

18. What is the basic structural and functional unit of the nervous system?
A. Nephron
B. Neuron
C. Axon
D. Glial cell
Answer: B
"""
    p4_2.insert_text((50, 72), text4_2, fontsize=12)
    doc4.save(str(out_dir / "04_multipage_exam.pdf"))
    doc4.close()

    # 5. Question Paper + Separate Answer Key (05_question_paper.pdf & 05_answer_key.pdf)
    doc5_q = fitz.open()
    p5_q = doc5_q.new_page()
    text5_q = """GENERAL KNOWLEDGE QUIZ

1. What is the capital city of Australia?
A. Sydney
B. Melbourne
C. Canberra
D. Brisbane

2. Who proposed the general theory of relativity?
A. Isaac Newton
B. Albert Einstein
C. Niels Bohr
D. Max Planck

3. Which planet is known as the Red Planet?
A. Venus
B. Mars
C. Jupiter
D. Saturn
"""
    p5_q.insert_text((50, 72), text5_q, fontsize=12)
    doc5_q.save(str(out_dir / "05_question_paper.pdf"))
    doc5_q.close()

    doc5_a = fitz.open()
    p5_a = doc5_a.new_page()
    text5_a = """GENERAL KNOWLEDGE QUIZ - OFFICIAL ANSWER KEY

1. C
2. B
3. B
"""
    p5_a.insert_text((50, 72), text5_a, fontsize=12)
    doc5_a.save(str(out_dir / "05_answer_key.pdf"))
    doc5_a.close()

    # 6. Intentionally Ambiguous Question (06_ambiguous_exam.pdf)
    doc6 = fitz.open()
    p6 = doc6.new_page()
    text6 = """DIAGNOSTIC TEST (AMBIGUOUS SAMPLE)

Which of the following compounds exhibits ionic bonding?
A. Sodium chloride

Explain why water has a high specific heat capacity.
"""
    p6.insert_text((50, 72), text6, fontsize=12)
    doc6.save(str(out_dir / "06_ambiguous_exam.pdf"))
    doc6.close()

    # 7. Invalid/Corrupted File (07_corrupted.pdf)
    with open(out_dir / "07_corrupted.pdf", "wb") as f:
        f.write(b"NOT_A_VALID_PDF_HEADER_CORRUPTED_BYTES_1234567890")

    print(f"Generated 7 test sample documents in: {out_dir}")


if __name__ == "__main__":
    create_sample_documents()
