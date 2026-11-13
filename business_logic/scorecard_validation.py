
import sqlite3

DB_PATH = "database/recruitment.db"

# Criteria applicable to each job role
ROLE_CRITERIA = {
    "Python Developer": [
        "python_knowledge",
        "problem_solving",
        "communication",
        "technical_fundamentals"
    ],

    "Data Analyst": [
        "sql_knowledge",
        "data_analysis",
        "communication",
        "problem_solving"
    ],

    "AI Engineer": [
        "machine_learning",
        "python_knowledge",
        "problem_solving",
        "communication"
    ],

    "Java Developer": [
        "java_knowledge",
        "oops_concepts",
        "problem_solving",
        "communication"
    ],

    "Cloud Engineer": [
        "cloud_knowledge",
        "networking",
        "problem_solving",
        "communication"
    ]
}


# -----------------------------------------
# 1. VALIDATE SCORECARD
# -----------------------------------------

def validate_scorecard(job_role, scores):

    required = ROLE_CRITERIA.get(job_role)

    if required is None:
        return False, ["Unknown job role"], None

    errors = []

    # Check missing criteria
    for criterion in required:
        if criterion not in scores:
            errors.append(
                f"Missing criterion: {criterion}"
            )

    # Check irrelevant criteria
    for criterion in scores:
        if criterion not in required:
            errors.append(
                f"Irrelevant criterion: {criterion}"
            )

    # Check score range
    valid_scores = []

    for criterion in required:

        if criterion not in scores:
            continue

        score = scores[criterion]

        if (
            not isinstance(score, (int, float))
            or isinstance(score, bool)
            or not 1 <= score <= 5
        ):
            errors.append(
                f"Invalid score for {criterion}: {score}"
            )
        else:
            valid_scores.append(score)

    # Calculate average only for complete valid scorecards
    average = None

    if not errors and len(valid_scores) == len(required):
        average = round(
            sum(valid_scores) / len(valid_scores), 2
        )

    return len(errors) == 0, errors, average


# -----------------------------------------
# 2. CHECK EXISTING DATABASE SCORECARDS
# -----------------------------------------

def validate_existing_scorecards():

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scorecard_issues (
            issue_id INTEGER PRIMARY KEY AUTOINCREMENT,
            scorecard_id TEXT,
            issue_type TEXT,
            expected_value REAL,
            actual_value REAL,
            status TEXT
        )
    """)

    cursor.execute("DELETE FROM scorecard_issues")

    records = cursor.execute("""
        SELECT
            scorecard_id,
            technical_score,
            problem_solving_score,
            communication_score,
            overall_score
        FROM scorecards
    """).fetchall()

    issue_count = 0

    for record in records:

        scorecard_id, technical, problem, communication, overall = record

        scores = [technical, problem, communication]

        # Check completeness
        if any(score is None for score in scores):
            cursor.execute("""
                INSERT INTO scorecard_issues
                (scorecard_id, issue_type, status)
                VALUES (?, ?, ?)
            """, (
                scorecard_id,
                "INCOMPLETE_SCORECARD",
                "DETECTED"
            ))

            issue_count += 1
            continue

        # Check valid score range
        if any(
            not isinstance(score, (int, float))
            or not 1 <= score <= 5
            for score in scores
        ):
            cursor.execute("""
                INSERT INTO scorecard_issues
                (scorecard_id, issue_type, status)
                VALUES (?, ?, ?)
            """, (
                scorecard_id,
                "INVALID_SCORE_RANGE",
                "DETECTED"
            ))

            issue_count += 1
            continue

        # Recalculate average from stored criteria
        calculated = round(sum(scores) / len(scores), 2)

        # Compare stored and calculated averages
        if abs(calculated - overall) > 0.01:

            cursor.execute("""
                INSERT INTO scorecard_issues
                (scorecard_id, issue_type,
                 expected_value, actual_value, status)
                VALUES (?, ?, ?, ?, ?)
            """, (
                scorecard_id,
                "SCORE_TOTAL_MISMATCH",
                calculated,
                overall,
                "DETECTED"
            ))

            issue_count += 1

    conn.commit()
    conn.close()

    print("\nSCORECARD DATABASE VALIDATION")
    print("Total scorecards:", len(records))
    print("Detected issues:", issue_count)


# -----------------------------------------
# 3. TEST CASES
# -----------------------------------------

if __name__ == "__main__":

    print("\nTEST 1: Valid scorecard")

    valid_scores = {
        "python_knowledge": 4,
        "problem_solving": 5,
        "communication": 3,
        "technical_fundamentals": 4
    }

    print(
        validate_scorecard(
            "Python Developer", valid_scores
        )
    )

    print("\nTEST 2: Incomplete scorecard")

    incomplete_scores = {
        "python_knowledge": 4,
        "problem_solving": 5
    }

    print(
        validate_scorecard(
            "Python Developer", incomplete_scores
        )
    )

    print("\nTEST 3: Invalid score")

    invalid_scores = {
        "python_knowledge": 6,
        "problem_solving": 4,
        "communication": 3,
        "technical_fundamentals": 4
    }

    print(
        validate_scorecard(
            "Python Developer", invalid_scores
        )
    )

    print("\nTEST 4: Irrelevant evaluation criterion")

    irrelevant_scores = {
        "python_knowledge": 4,
        "problem_solving": 5,
        "communication": 3,
        "technical_fundamentals": 4,
        "cooking_skills": 5
    }

    print(
        validate_scorecard(
            "Python Developer", irrelevant_scores
        )
    )

    # Validate generated database records
    validate_existing_scorecards()
