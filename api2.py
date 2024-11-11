import spacy
import PyPDF2
from typing import List, Set, Dict
from spacy.matcher import PhraseMatcher
from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from enum import Enum

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

# Enum for predefined job roles
class JobRole(str, Enum):
    business_analyst = "business analyst"
    php_developer = "php developer"
    android_app_developer = "android app developer"
    digital_marketing_specialist = "digital marketing specialist"

# Appointment Scheduler class for scheduling
class AppointmentScheduler:
    def __init__(self):
        self.available_slots = self._generate_slots()

    def _generate_slots(self) -> List[Dict]:
        slots = [{'day': 'Monday-Saturday', 'time': '10:00 AM - 12:30 PM', 'available': True}]
        return slots

    def get_available_slots(self) -> List[Dict]:
        return [slot for slot in self.available_slots if slot['available']]

    def schedule_appointment(self, day: str, time: str) -> Dict:
        for slot in self.available_slots:
            if slot['day'] == day and slot['time'] == time and slot['available']:
                slot['available'] = False
                return {'status': 'confirmed', 'day': day, 'time': time}
        return {'status': 'error', 'message': 'Slot not available'}

# Extract text from PDF
def extract_text_from_pdf(file: UploadFile) -> str:
    text = ""
    try:
        pdf_reader = PyPDF2.PdfReader(file.file)
        for page in pdf_reader.pages:
            text += page.extract_text() or ""  # Ensure None doesn't raise an error
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return ""
    return text

# Extract keywords using spaCy and PhraseMatcher
def extract_keywords(text: str) -> Set[str]:
    doc = nlp(text)
    keywords = set()

    technical_terms = [
        "Excel", "SQL", "Power BI", "Tableau", "business process modeling", "data analysis",
        "project management", "agile methodologies", "PHP", "MySQL", "PostgreSQL", "Laravel",
        "CodeIgniter", "Symfony", "HTML", "CSS", "JavaScript", "AJAX", "Git", "RESTful APIs",
        "Kotlin", "Android SDK", "Android Studio", "MVVM", "Firebase", "SQLite", "Google Play Store",
        "SEO", "Google Ads", "Meta Ads", "Google Analytics", "Google Tag Manager", "A/B testing",
        "SEM", "Moz", "Ahrefs", "Facebook Ads", "Instagram Ads", "CPC", "CTR", "ROAS", "CPA",
        "audience segmentation", "campaign optimization", "object-oriented programming",
        "MVC design patterns", "stakeholder communication", "process improvement",
        "requirements gathering", "unit testing", "Material Design", "version control"
    ]

    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
    patterns = [nlp(term) for term in technical_terms]
    matcher.add("TECH_TERMS", patterns)

    matches = matcher(doc)
    for match_id, start, end in matches:
        span = doc[start:end]
        keywords.add(span.text.lower())

    return keywords

# Job roles and their required skills
class JobRoles:
    ROLES = {
        "business analyst": {
            "required_skills": [
                "SQL", "Excel", "Power BI", "Tableau", "requirements gathering",
                "business process modeling", "data analysis", "project management",
                "agile methodologies", "stakeholder communication", "process improvement"
            ],
        },
        "php developer": {
            "required_skills": [
                "PHP", "MySQL", "PostgreSQL", "Laravel", "CodeIgniter", "Symfony",
                "HTML", "CSS", "JavaScript", "AJAX", "Git", "RESTful APIs",
                "object-oriented programming", "MVC design patterns", "version control"
            ],
        },
        "android app developer": {
            "required_skills": [
                "Kotlin", "Java", "Android SDK", "Android Studio", "RESTful APIs",
                "MVVM", "Firebase", "SQLite", "Google Play Store", "unit testing",
                "Material Design", "Git", "version control"
            ],
        },
        "digital marketing specialist": {
            "required_skills": [
                "Google Ads", "Meta Ads", "SEO", "Google Analytics", "Google Tag Manager",
                "A/B testing", "SEM", "Moz", "Ahrefs", "Facebook Ads", "Instagram Ads",
                "CPC", "CTR", "ROAS", "CPA", "audience segmentation", "campaign optimization"
            ],
        }
    }

# Career Guidance class to get role requirements
class CareerGuidance:
    def __init__(self):
        self.job_roles = JobRoles.ROLES

    def get_role_requirements(self, role: str) -> Dict:
        return self.job_roles.get(role.lower(), {})

# Analyze resume and provide guidance
async def analyze_resume_and_provide_guidance(
    file: UploadFile,
    selected_role: str,
    threshold: float = 0.7
) -> Dict:
    scheduler = AppointmentScheduler()
    career_guide = CareerGuidance()

    role_data = career_guide.get_role_requirements(selected_role)
    if not role_data:
        return {"status": "Error", "message": "Job role not found"}

    required_keywords = role_data['required_skills']
    resume_text = extract_text_from_pdf(file)
    if not resume_text:
        return {"status": "Error", "message": "Could not extract text from PDF"}

    resume_keywords = extract_keywords(resume_text.lower())
    matched_keywords = [k for k in required_keywords if k.lower() in resume_keywords]
    missing_keywords = [k for k in required_keywords if k.lower() not in resume_keywords]
    match_percentage = len(matched_keywords) / len(required_keywords)

    if len(matched_keywords) == 0:
        matched_keywords = 0  # Set matched keywords to 0 if none are found

    if match_percentage >= threshold:
        return {
            "status": "Match",
            "role": selected_role,
            "match_percentage": round(match_percentage * 100, 2),
            "matched_keywords": matched_keywords,
            "available_slots": scheduler.get_available_slots()
        }
    else:
        return {
            "status": "Not Match",
            "role": selected_role,
            "match_percentage": round(match_percentage * 100, 2),
            "matched_keywords": matched_keywords,
            "guidance": f"To strengthen your profile for the role of {selected_role}, consider focusing on "
                        "areas where you can build hands-on experience and enhance your skills."
        }

# Endpoint to analyze resume with predefined roles
@app.post("/analyze_resume/")
async def analyze_resume(file: UploadFile, job_role: JobRole = Form(...)):
    # Check if the uploaded file is a PDF
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    result = await analyze_resume_and_provide_guidance(file, job_role.value)
    if result['status'] == "Error":
        raise HTTPException(status_code=400, detail=result["message"])
    return JSONResponse(content=result)
