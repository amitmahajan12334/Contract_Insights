from io import BytesIO
from pdfminer.high_level import extract_text
import pdfplumber
import requests
import re

def extract_text_from_pdf(pdf_data):
    text = ""
    with pdfplumber.open(pdf_data) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

def format_to_structure(text):
    section_pattern = re.compile(r"^\d+\.\s+([A-Z\s]+)")
    subsection_pattern = re.compile(r"^\d+\.\d+\s+")
    bullet_pattern = re.compile(r"^\s*\(?([a-z])\)\s+(.+?)(?=\n\s*\(?[a-z]\)|\n\d+\.\d|\Z)", re.DOTALL | re.MULTILINE)
    
    # Pattern to match unwanted text patterns to be removed from lines
    removal_pattern = re.compile(
        r"\b\d{7,}\.\d{2}\b"                         # Matches '24336663.35'
        r"|\b\d{5,}-\d{5,}\b"                        # Matches '230849-10007'
        r"|\b\d+\s+Master Services Agreement\b"      # Matches '123 Master Services Agreement'
        r"|Customer and Vendor Confidential Execution Version"  # Matches 'Customer and Vendor Confidential Execution Version'
    )

    formatted_text = ""
    for line in text.splitlines():
        # Remove unwanted patterns from the line
        clean_line = removal_pattern.sub("", line).strip()
        
        if section_pattern.match(clean_line):
            formatted_text += f"\n{clean_line}\n"
        elif subsection_pattern.match(clean_line):
            formatted_text += f"{clean_line}\n"
        elif bullet_pattern.match(clean_line):
            formatted_text += f"    {clean_line}\n"
        else:
            formatted_text += f"        {clean_line}\n"

    return formatted_text

def parse_content_to_json(text):
    content = {}
    current_section = None
    current_subsection = None
    current_section_number = None
    current_subsection_number = None
    accumulated_text = ""

    section_pattern = re.compile(r"^(\d+\.)\s+(.*)", re.MULTILINE)
    subsection_pattern = re.compile(r"^(\d+\.\d+)\s+(.*)", re.MULTILINE)
    bullet_pattern = re.compile(r"^\(([a-z])\)\s+(.*)", re.MULTILINE)

    lines = text.splitlines()

    for line in lines:
        line = line.strip()

        section_match = section_pattern.match(line)
        if section_match:
            if accumulated_text:
                if current_subsection:
                    content[f"{current_section_number} {current_section}"][f"{current_subsection_number} {current_subsection}"].append(accumulated_text)
                else:
                    if "No Subsection" not in content[f"{current_section_number} {current_section}"]:
                        content[f"{current_section_number} {current_section}"]["No Subsection"] = []
                    content[f"{current_section_number} {current_section}"]["No Subsection"].append(accumulated_text)
                accumulated_text = ""
            current_section_number = section_match.group(1)
            current_section = section_match.group(2).strip()
            content[f"{current_section_number} {current_section}"] = {}
            current_subsection = None
            current_subsection_number = None
            continue

        subsection_match = subsection_pattern.match(line)
        if subsection_match and current_section:
            if accumulated_text:
                if current_subsection:
                    content[f"{current_section_number} {current_section}"][f"{current_subsection_number} {current_subsection}"].append(accumulated_text)
                else:
                    if "No Subsection" not in content[f"{current_section_number} {current_section}"]:
                        content[f"{current_section_number} {current_section}"]["No Subsection"] = []
                    content[f"{current_section_number} {current_section}"]["No Subsection"].append(accumulated_text)
                accumulated_text = ""
            current_subsection_number = subsection_match.group(1)
            current_subsection = subsection_match.group(2).strip()
            content[f"{current_section_number} {current_section}"][f"{current_subsection_number} {current_subsection}"] = []
            continue

        bullet_match = bullet_pattern.match(line)
        if bullet_match:
            if accumulated_text:
                if current_subsection:
                    content[f"{current_section_number} {current_section}"][f"{current_subsection_number} {current_subsection}"].append(accumulated_text)
                else:
                    if "No Subsection" not in content[f"{current_section_number} {current_section}"]:
                        content[f"{current_section_number} {current_section}"]["No Subsection"] = []
                    content[f"{current_section_number} {current_section}"]["No Subsection"].append(accumulated_text)
                accumulated_text = ""
            bullet_content = bullet_match.group(2).strip()
            accumulated_text = f"({bullet_match.group(1)}) {bullet_content}"
        elif current_section:
            accumulated_text += " " + line

    if accumulated_text:
        if current_subsection:
            content[f"{current_section_number} {current_section}"][f"{current_subsection_number} {current_subsection}"].append(accumulated_text)
        else:
            if "No Subsection" not in content[f"{current_section_number} {current_section}"]:
                content[f"{current_section_number} {current_section}"]["No Subsection"] = []
            content[f"{current_section_number} {current_section}"]["No Subsection"].append(accumulated_text)

    return content

def remove_outside_braces(content):

    # Read the file content

   
 
    # Use a regular expression to extract everything inside braces

    extracted_text = re.findall(r'\{[^{}]*\}', content)
 
    # Join the extracted parts into one string

    cleaned_content = '\n'.join(extracted_text)
 
    # Write the cleaned content to a new file

    return cleaned_content