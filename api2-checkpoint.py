import spacy
import PyPDF2
import re
from typing import List, Set, Dict
from datetime import datetime, timedelta
from spacy.matcher import PhraseMatcher
import json
from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

# Adding CORS Middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load spaCy model
nlp = spacy.load('en_core_web_sm')

class AppointmentScheduler:
    def __init__(self):
        self.available_slots = self._generate_slots()

    def _generate_slots(self) -> List[Dict]:
        slots = [
            {'date': '2024-11-10', 'time': '09:00', 'available': True},
            {'date': '2024-11-10', 'time': '10:00', 'available': True},
            {'date': '2024-11-11', 'time': '09:00', 'available': True},
            {'date': '2024-11-11', 'time': '10:00', 'available': True},
            {'date': '2024-11-12', 'time': '14:00', 'available': True},
            {'date': '2024-11-12', 'time': '15:00', 'available': True}
        ]
        return slots

    def get_available_slots(self) -> List[Dict]:
        return [slot for slot in self.available_slots if slot['available']]

    def schedule_appointment(self, date: str, time: str) -> Dict:
        for slot in self.available_slots:
            if slot['date'] == date and slot['time'] == time and slot['available']:
                slot['available'] = False
                return {
                    'status': 'confirmed',
                    'date': date,
                    'time': time,
                    'message': 'Please arrive 10 minutes before your scheduled interview.'
                }
        return {'status': 'error', 'message': 'Slot not available'}

def extract_text_from_pdf(file: UploadFile) -> str:
    text = ""
    try:
        pdf_reader = PyPDF2.PdfReader(file.file)
        for page in pdf_reader.pages:
            text += page.extract_text()
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""
    return text

def extract_keywords(text: str) -> Set[str]:
    doc = nlp(text)
    keywords = set()

    technical_terms = [
        "python", "Java", "TensorFlow", "Keras", "Langchain", "Huggingface",
        "HTML", "CSS"
    ]
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    patterns = [nlp(term) for term in technical_terms]
    matcher.add("TECH_TERMS", patterns)

    matches = matcher(doc)
    for match_id, start, end in matches:
        span = doc[start:end]
        keywords.add(span.text.lower())

    return keywords

class JobRoles:
    ROLES = {
        "python developer": {
            "required_skills": [
                "python", "Java", "TensorFlow", "Keras", "Langchain", "Huggingface",
                "HTML", "CSS"
            ],
            "courses": {
                "python": [
                    {"name": "Complete Python Bootcamp", "platform": "Udemy", "url": "https://www.udemy.com/course/complete-python-bootcamp/"},
                    {"name": "Python for Everybody", "platform": "Coursera", "url": "https://www.coursera.org/specializations/python"}
                ]
            }
        },
        "business analyst": {
            "required_skills": [
                "sql", "excel", "tableau", "power bi", "requirements gathering",
                "business process modeling", "data analysis", "project management", "agile methodologies"
            ],
            "courses": {
                "sql": [
                    {"name": "Complete SQL Bootcamp", "platform": "Udemy", "url": "https://www.udemy.com/course/the-complete-sql-bootcamp/"},
                    {"name": "SQL for Data Science", "platform": "Coursera", "url": "https://www.coursera.org/learn/sql-for-data-science"}
                ]
            }
        }
    }

class CareerGuidance:
    def __init__(self):
        self.job_roles = JobRoles.ROLES

    def get_role_requirements(self, role: str) -> Dict:
        return self.job_roles.get(role.lower(), {})

    def get_recommendations(self, role: str, missing_skills: List[str]) -> Dict:
        role_data = self.get_role_requirements(role)
        if not role_data:
            return {}

        recommendations = {}
        for skill in missing_skills:
            if skill in role_data['courses']:
                recommendations[skill] = role_data['courses'][skill]

        return recommendations

def analyze_resume_and_provide_guidance(
    file: UploadFile,
    selected_role: str,
    threshold: float = 0.6
) -> Dict:
    scheduler = AppointmentScheduler()
    career_guide = CareerGuidance()

    role_data = career_guide.get_role_requirements(selected_role)
    if not role_data:
        return {"status": "Error", "message": "Invalid job role selected"}

    required_keywords = role_data['required_skills']
    resume_text = extract_text_from_pdf(file)
    if not resume_text:
        return {"status": "Error", "message": "Could not extract text from PDF"}

    resume_keywords = extract_keywords(resume_text.lower())
    matched_keywords = [k for k in required_keywords if k.lower() in resume_keywords]
    missing_keywords = [k for k in required_keywords if k.lower() not in resume_keywords]
    match_percentage = len(matched_keywords) / len(required_keywords)

    if match_percentage >= threshold:
        return {
            "status": "Match",
            "role": selected_role,
            "match_percentage": round(match_percentage * 100, 2),
            "matched_keywords": matched_keywords,
            "available_slots": scheduler.get_available_slots()
        }
    else:
        recommendations = career_guide.get_recommendations(selected_role, missing_keywords)
        return {
            "status": "Not Match",
            "role": selected_role,
            "match_percentage": round(match_percentage * 100, 2),
            "matched_keywords": matched_keywords,
            "missing_keywords": missing_keywords,
            "guidance": {
                "message": f"Consider enhancing skills in these areas:",
                "skill_recommendations": recommendations
            }
        }

@app.post("/analyze_resume/")
async def analyze_resume(file: UploadFile, job_role: str = Form(...)):
    # Check if the uploaded file is a PDF
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    result = analyze_resume_and_provide_guidance(file, job_role)
    if result['status'] == "Error":
        raise HTTPException(status_code=400, detail=result["message"])
    return JSONResponse(content=result)
