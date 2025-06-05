# ------------------------------------------------------------------------------
# Copyright (c) 2025 Mahfujar Rahman
# Author: Mahfujar Rahman Noyon <mrnoyon.cse@gmail.com>
# Created: 2025-06-05
# Description: This script extracts all 9-digit roll numbers from a list of 
# ntrca viva schedule PDF files and stores them in a JSON file.
# ------------------------------------------------------------------------------



import PyPDF2
import re
import json

viva_schedule_pdf_files = [
    '27_10_to_13_11.pdf',
    '14_11_to_04_12.pdf',
    '5_12_to_2_01.pdf',
    '5_01_to_23_01.pdf',
    '26_01_to_13_02.pdf',
    '16_02_to_6_03.pdf',
    '9_03_to_20_03_n_6_04_to_30_04.pdf',
    '23_03.pdf',
    '4_05_to_29_05.pdf',
    '31_05.pdf'
]

all_rolls = set()

for pdf in viva_schedule_pdf_files:
    print('Procesing: ', pdf)
    with open(f'schedules/{pdf}', "rb") as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text

    rolls = re.findall(r'\b\d{9}\b', text)
    all_rolls.update(rolls)
print('total rolls found: ', len(all_rolls))
with open("all_rolls.json", "w") as f:
    json.dump(sorted(all_rolls), f)
