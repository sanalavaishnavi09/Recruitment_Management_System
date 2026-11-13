# Recruitment Management System
## 1. Project Overview

The Recruitment Management System is a Python and SQLite-based application designed to manage the recruitment lifecycle, from job requisition creation to candidate selection and offer approval.

The system handles candidate applications, recruitment stages, interviewer scheduling, structured interview evaluations, and offer approvals.

It also includes an anomaly detection module to identify recruitment process violations, scheduling conflicts, and evaluation inconsistencies.

## 2. Objectives

- Manage job requisitions and candidate applications.
- Track candidates through different recruitment stages.
- Validate mandatory reviews before stage progression.
- Schedule interviews while preventing interviewer conflicts.
- Evaluate candidates using structured scorecards.
- Validate salary offers against approved salary bands.
- Maintain audit history and ground-truth labels.
- Detect recruitment anomalies and evaluate detection performance.

## 3. Technologies Used

- **Programming Language:** Python
- **Database:** SQLite
- **Data Processing:** Pandas, NumPy
- **Synthetic Data Generation:** Faker
- **Data Formats:** CSV, JSON
- **Development Environment:** Visual Studio Code

## 4. Project Structure

```text
Recruitment_Management_System/
│
├── anomaly_detection/
│   ├── inject_anomalies.py
│   ├── detect_anomalies.py
│   ├── analyze_detection_results.py
│   ├── backfill_stage_event.py
│   ├── audit_interviewer_conflicts.py
│   └── debug_anomalies.py
│
├── business_logic/
│   ├── stage_validation.py
│   ├── scheduling.py
│   ├── scorecard_validation.py
│   └── offer_approval.py
│
├── database/
│   └── recruitment.db
│
├── data/
│   ├── applications.csv
│   ├── candidates.csv
│   ├── requisitions.csv
│   ├── interviews.csv
│   ├── scorecards.csv
│   ├── offers.csv
│   ├── detected_anomalies.csv
│   └── detection_metrics.csv
│
├── ground_truth/
│   └── ground_truth.csv
│
├── generator/
|   └──generate_data.py
├── create_database.py
├── requirements.txt
└── README.md
```

## 5. Dataset Summary

The project uses synthetically generated recruitment data with a fixed random seed of `20261022`.

| Dataset | Actual records |
|---|---:|
| Hiring Managers | 50 |
| Requisitions | 200 |
| Candidates | 5,000 |
| Applications | 7,966 |
| Interview Panels | 100 |
| Panel Members | 300 |
| Interviews | 2,002 |
| Skill Requirements | 600 |

Application and interview counts represent the actual final dataset.

Data is exported in CSV and JSON formats.

## 6. Business Logic Implementation

### Candidate Stage Validation

The system validates candidate stage transitions and prevents invalid progression.

Supported stages:

- APPLIED
- SCREENING
- TECHNICAL
- MANAGERIAL
- SELECTED
- REJECTED
- WITHDRAWN

Mandatory review checks are applied before candidates advance to subsequent interview stages.

### Interview Scheduling

The scheduling module:

- Checks interviewer availability.
- Validates interview panel assignments.
- Prevents interviewer double-booking.
- Checks candidate scheduling eligibility.
- Rejects conflicting interview bookings.

### Scorecard Validation

The scorecard module validates evaluation criteria, score ranges, and missing or irrelevant criteria.

### Offer Approval

The offer approval module:

- Checks offered salary against the approved salary band.
- Records approval decisions.
- Prevents release of offers without approval.

## 7. Anomaly Detection

Five anomalies are injected into the recruitment data and evaluated against a separate ground-truth dataset.

| ID | Anomaly | Expected action |
|---|---|---|
| 1 | Invalid candidate stage transition | Reject transition |
| 2 | Interviewer double-booking | Flag scheduling conflict |
| 3 | Offer above approved salary band | Escalate offer |
| 4 | Withdrawn candidate remains scheduled | Cancel interview |
| 5 | Irrelevant scorecard evaluation criterion | Reject scorecard |

The detection module identifies these anomalies and exports the results to `data/detected_anomalies.csv`.

## 8. Detection Evaluation

The detected anomalies are compared against the ground-truth labels.

| Evaluation Metric | Result |
|---|---:|
| True Positives | 5 |
| False Positives | 0 |
| False Negatives | 0 |
| Precision | 1.00 |
| Recall | 1.00 |
| F1 Score | 1.00 |

The evaluation results are exported to `data/detection_metrics.csv`.

## 9. Database Validation

The SQLite database was checked using:

- `PRAGMA integrity_check`
- `PRAGMA foreign_key_check`

The final checks returned:

- Database integrity: OK
- Foreign key errors: None

## 10. Installation and Execution

### Step 1: Clone or open the project

Open the project folder in Visual Studio Code.

### Step 2: Create a virtual environment

```bash
python -m venv venv
```

Activate it on Windows:

```bash
.\venv\Scripts\Activate.ps1
```

### Step 3: Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Generate data (fresh setup only)

```bash
python generator/generate_data.py
```

### Step 5: Create the database (fresh setup only)

```bash
python create_database.py
```

### Step 6: Run business logic tests

```bash
python business_logic/stage_validation.py
python test_scheduling.py
python test_offer_approval.py
```

### Step 7: Run anomaly detection

For a fresh setup, first run the anomaly injection and required event preparation scripts once.

```bash
python anomaly_detection/inject_anomalies.py
python anomaly_detection/backfill_stage_event.py
```

Then execute:

```bash
python anomaly_detection/detect_anomalies.py
python anomaly_detection/analyze_detection_results.py
```

**Important:** The data generation, database creation, and anomaly injection steps are for a fresh setup. Do not rerun them on the current finalized database because they may overwrite or duplicate existing project data.

## 11. Conclusion

The Recruitment Management System demonstrates an end-to-end recruitment workflow with structured business rules, database management, audit traceability, and anomaly detection.

The system successfully detected all five injected anomalies in the final evaluation, achieving a precision of 1.00, recall of 1.00, and F1 score of 1.00.