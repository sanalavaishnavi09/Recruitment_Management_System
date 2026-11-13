
import pandas as pd

detected = pd.read_csv("data/detected_anomalies.csv")
truth = pd.read_csv("ground_truth/ground_truth.csv")

# Create unique comparison keys
detected["match_key"] = (
    detected["issue_type"].astype(str) + "|" +
    detected["record_id"].astype(str)
)

truth["match_key"] = (
    truth["issue_type"].astype(str) + "|" +
    truth["record_id"].astype(str)
)

truth_keys = set(truth["match_key"])
detected_keys = set(detected["match_key"])

matched = detected[detected["match_key"].isin(truth_keys)]
unmatched = detected[~detected["match_key"].isin(truth_keys)]

duplicates = detected[
    detected.duplicated("match_key", keep=False)
]

print("\n1. DETECTION SUMMARY")
print("Detection rows:", len(detected))
print("Unique detections:", len(detected_keys))
print("Ground truth labels:", len(truth_keys))
print("Matched anomalies:", len(detected_keys & truth_keys))
print("Unmatched detections:", len(detected_keys - truth_keys))
print("Missed anomalies:", len(truth_keys - detected_keys))

print("\n2. DETECTIONS BY TYPE")
print(detected.groupby("issue_type").size())

print("\n3. GROUND TRUTH BY TYPE")
print(truth.groupby("issue_type").size())

print("\n4. UNMATCHED DETECTIONS BY TYPE")
print(unmatched.groupby("issue_type").size())

print("\n5. DUPLICATE DETECTION RECORDS")
print("Duplicate rows:", len(duplicates))

print("\n6. SAMPLE UNMATCHED RECORDS")
print(
    unmatched[
        ["record_id", "issue_type", "details"]
    ].head(15).to_string(index=False)
)

print("\nAnalysis completed!")
