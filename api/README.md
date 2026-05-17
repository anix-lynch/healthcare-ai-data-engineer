# Healthcare API 🏥

> **Free REST API serving 55,500 synthetic patient encounters. No authentication required.**

Like **FakeStore API** but for healthcare data - perfect for demos, learning, prototyping, and AI agents!

---

## 🚀 Quick Start

### Install & Run

```bash
cd api
pip install -r requirements.txt
python app/main.py
```

API runs at: **http://localhost:8000**

Interactive docs: **http://localhost:8000/docs**

---

## 📡 API Endpoints

### Base URL
```
http://localhost:8000
```

### Get All Encounters
```bash
GET /api/encounters?limit=10&offset=0

# Filter by condition
GET /api/encounters?condition=Diabetes&limit=20

# Filter by age
GET /api/encounters?min_age=50&max_age=70

# Filter by admission type
GET /api/encounters?admission_type=Emergency

# Combine filters
GET /api/encounters?condition=Diabetes&min_age=50&admission_type=Urgent&limit=50
```

### Get Single Encounter
```bash
GET /api/encounters/42
```

### Get Patients
```bash
GET /api/patients?limit=10

# Filter by age group
GET /api/patients?age_group=51-70
```

### Get Doctors
```bash
GET /api/doctors?limit=10

# Filter by specialty
GET /api/doctors?specialty=Diabetes
```

### Get Hospitals
```bash
GET /api/hospitals?limit=10
```

### Get Medical Conditions
```bash
GET /api/conditions
```

### Get Medications
```bash
GET /api/medications
```

### Get Insurance Providers
```bash
GET /api/insurance
```

### Get Statistics
```bash
GET /api/stats
```

### Search
```bash
GET /api/search?q=diabetes&limit=20
```

---

## 📊 Example Response

### GET /api/encounters?limit=2

```json
{
  "total": 55500,
  "limit": 2,
  "offset": 0,
  "count": 2,
  "data": [
    {
      "Name": "Bobby JacksOn",
      "Age": 30,
      "Gender": "Male",
      "Blood Type": "B-",
      "Medical Condition": "Cancer",
      "Date of Admission": "2024-01-31",
      "Doctor": "Matthew Smith",
      "Hospital": "Sons and Miller",
      "Insurance Provider": "Blue Cross",
      "Billing Amount": 18856.28,
      "Room Number": 328,
      "Admission Type": "Urgent",
      "Discharge Date": "2024-02-02",
      "Medication": "Paracetamol",
      "Test Results": "Normal",
      "Length of Stay": 2
    },
    {
      "Name": "LesLie TErRy",
      "Age": 62,
      "Gender": "Male",
      "Blood Type": "A+",
      "Medical Condition": "Obesity",
      "Date of Admission": "2019-08-20",
      "Doctor": "Samantha Davies",
      "Hospital": "Kim Inc",
      "Insurance Provider": "Medicare",
      "Billing Amount": 33643.33,
      "Room Number": 265,
      "Admission Type": "Emergency",
      "Discharge Date": "2019-08-26",
      "Medication": "Ibuprofen",
      "Test Results": "Inconclusive",
      "Length of Stay": 6
    }
  ]
}
```

---

## 🎯 Use Cases

### 1. Data Analysis & Visualization
```python
import requests
import pandas as pd

# Fetch data
response = requests.get('http://localhost:8000/api/encounters?limit=1000')
data = response.json()['data']

# Convert to DataFrame
df = pd.DataFrame(data)

# Analyze
print(df['Medical Condition'].value_counts())
```

### 2. Machine Learning Training
```python
# Get all diabetic patients for ML model
response = requests.get('http://localhost:8000/api/encounters?condition=Diabetes&limit=10000')
diabetes_data = response.json()['data']

# Train model
from sklearn.model_selection import train_test_split
# ... model training code
```

### 3. dbt Data Warehouse
```sql
-- models/staging/stg_healthcare_api.sql
WITH api_data AS (
    SELECT * FROM EXTERNAL_TABLE(
        'http://localhost:8000/api/encounters?limit=55500'
    )
)
SELECT * FROM api_data
```

### 4. Power BI / Tableau
- Data Source: Web
- URL: `http://localhost:8000/api/encounters?limit=55500`
- Format: JSON

### 5. AI Agent / LLM
```python
from langchain.tools import Tool

healthcare_api = Tool(
    name="HealthcareAPI",
    description="Get patient encounter data from healthcare API",
    func=lambda query: requests.get(f'http://localhost:8000/api/search?q={query}').json()
)

# Agent can now query healthcare data!
```

---

## 🔥 Features

- ✅ **No Authentication Required** - Just call the endpoint!
- ✅ **55,500 Patient Encounters** - Realistic synthetic data
- ✅ **RESTful JSON** - Standard format, easy to consume
- ✅ **CORS Enabled** - Works from browsers
- ✅ **Pagination** - Handle large datasets
- ✅ **Filtering** - By condition, age, gender, insurance, etc.
- ✅ **Sorting** - By any field, asc/desc
- ✅ **Search** - Full-text search across all fields
- ✅ **Statistics** - Pre-computed aggregations
- ✅ **OpenAPI Docs** - Interactive documentation at `/docs`
- ✅ **Fast** - Powered by FastAPI + Pandas

---

## 📈 Dataset Info

- **Total Encounters:** 55,500
- **Unique Patients:** 49,992
- **Unique Doctors:** 40,341
- **Unique Hospitals:** 39,876
- **Date Range:** 2019-05-08 to 2024-05-07 (5 years)
- **Medical Conditions:** Diabetes, Hypertension, Cancer, Arthritis, Asthma, Obesity
- **Medications:** Aspirin, Ibuprofen, Paracetamol, Penicillin, Lipitor
- **Insurance Providers:** Blue Cross, Medicare, Medicaid, Aetna, UnitedHealthcare

---

## 🐳 Docker Deployment (Optional)

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY ../data/raw/healthcare_dataset.csv ./data/raw/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash
docker build -t healthcare-api .
docker run -p 8000:8000 healthcare-api
```

---

## 🌐 Deploy to Cloud (Free Tier)

### Option 1: Render.com
1. Push to GitHub
2. Connect Render to repo
3. Deploy (free tier available)

### Option 2: Railway.app
1. Push to GitHub
2. Connect Railway to repo
3. Deploy (free $5/month credit)

### Option 3: Fly.io
```bash
flyctl launch
flyctl deploy
```

---

## 🎓 Learning Resources

This API demonstrates:
- RESTful API design
- FastAPI framework
- Pandas data manipulation
- OpenAPI/Swagger documentation
- CORS configuration
- Pagination patterns
- Query parameter filtering
- Error handling

---

## 🤝 Contributing

Want to add features?
- [ ] Authentication (optional API keys)
- [ ] Rate limiting
- [ ] Caching (Redis)
- [ ] WebSocket streaming
- [ ] GraphQL endpoint
- [ ] Data export (CSV/Excel)
- [ ] Bulk operations

---

## 📝 License

Dataset: CC0-1.0 (Public Domain)
API Code: MIT License

---

## 🔗 Links

- **GitHub:** https://github.com/anix-lynch/healthcare-analytics
- **Documentation:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

**Built with ❤️ by Anix Lynch**

*Making healthcare data accessible for learning, prototyping, and AI!*

