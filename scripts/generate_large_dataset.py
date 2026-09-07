"""
Large Synthetic Dataset Generator for Candidate Transformation System
Generates 10,000+ realistic candidate records across multi-source JSON and CSV formats with controlled duplicates, field aliases, and noise.
"""

import argparse
import json
import csv
import os
import random
import uuid

FIRST_NAMES = ["Rahul", "Priya", "Amit", "Neha", "Rohan", "Ananya", "Siddharth", "Kavya", "Vikram", "Sneha", "Arjun", "Meera", "Aarav", "Ishani", "Karan"]
LAST_NAMES = ["Kumar", "Sharma", "Singh", "Verma", "Patel", "Gupta", "Rao", "Nair", "Joshi", "Chawla", "Deshmukh", "Reddy", "Mehta", "Bhat"]
DOMAINS = ["gmail.com", "yahoo.com", "techcorp.io", "innovate.org", "outlook.com", "domain.de", "enterprise.com"]
SKILLS_POOL = ["Java", "Python", "React", "SQL", "Docker", "AWS", "Node.js", "Kubernetes", "TypeScript", "C++", "Go", "Machine Learning", "GraphQL"]
LOCATIONS = ["San Francisco, CA", "Bangalore, India", "New York, NY", "London, UK", "Austin, TX", "Berlin, Germany", "Toronto, ON", "Seattle, WA"]
TITLES = ["Senior Software Engineer", "Data Scientist", "Full Stack Developer", "DevOps Engineer", "Frontend Developer", "Product Manager"]


def generate_base_profile(cid: int):
    fname = random.choice(FIRST_NAMES)
    lname = random.choice(LAST_NAMES)
    name = f"{fname} {lname}"
    email = f"{fname.lower()}.{lname.lower()}{cid % 300}@{(random.choice(DOMAINS))}"
    phone = f"+1 (555) {random.randint(100, 999):03d}-{random.randint(1000, 9999):04d}"
    skills = random.sample(SKILLS_POOL, k=random.randint(2, 6))
    exp_years = round(random.uniform(0.5, 15.0), 1)
    location = random.choice(LOCATIONS)
    title = random.choice(TITLES)
    return {
        "id": f"CAN-{cid:06d}",
        "name": name,
        "email": email,
        "phone": phone,
        "skills": skills,
        "experience": exp_years,
        "location": location,
        "title": title
    }


def generate_datasets(total_count: int = 10000, output_dir: str = "data/large_scale"):
    os.makedirs(output_dir, exist_ok=True)
    random.seed(42)  # Deterministic generation for reproducible benchmarking

    json_records = []
    csv_records = []

    base_profiles = []
    # Create ~8,000 unique base profiles to generate ~10,000 records with 20% duplicate rate
    unique_base_count = int(total_count * 0.8)
    for i in range(1, unique_base_count + 1):
        base_profiles.append(generate_base_profile(i))

    for idx in range(total_count):
        # 80% unique profile selection, 20% duplicate variant selection
        if idx < unique_base_count:
            profile = base_profiles[idx]
        else:
            profile = random.choice(base_profiles)

        is_json = (idx % 2 == 0)

        if is_json:
            # Vary field names for JSON source
            rec = {
                "candidate_id": profile["id"] if random.random() > 0.3 else f"JSON-{idx:06d}",
                "full_name": profile["name"] if random.random() > 0.1 else profile["name"].upper(),
                "email_address": profile["email"] if random.random() > 0.05 else f"mailto:{profile['email']}",
                "contact_number": profile["phone"],
                "technologies": profile["skills"],
                "years_experience": f"{profile['experience']} years",
                "current_location": profile["location"],
                "job_title": profile["title"]
            }
            json_records.append(rec)
        else:
            # Vary field names for CSV source
            rec = {
                "id": profile["id"] if random.random() > 0.3 else f"CSV-{idx:06d}",
                "applicant_name": profile["name"],
                "email": profile["email"],
                "mobile_phone": profile["phone"],
                "skills_list": ", ".join(profile["skills"]),
                "experience_years": f"{int(profile['experience'] * 12)} months" if random.random() > 0.5 else str(profile["experience"]),
                "city_state": profile["location"],
                "role_title": profile["title"]
            }
            csv_records.append(rec)

    json_file = os.path.join(output_dir, f"candidates_{len(json_records)}.json")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_records, f, indent=2)

    csv_file = os.path.join(output_dir, f"candidates_{len(csv_records)}.csv")
    if csv_records:
        headers = list(csv_records[0].keys())
        with open(csv_file, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(csv_records)

    print(f"[+] Successfully generated {len(json_records)} JSON records in: {json_file}")
    print(f"[+] Successfully generated {len(csv_records)} CSV records in: {csv_file}")
    print(f"[+] Total dataset size: {total_count} records")
    return [json_file, csv_file]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic large dataset for scaling benchmark.")
    parser.add_argument("--count", type=int, default=10000, help="Total candidate records to generate (default: 10000)")
    parser.add_argument("--output-dir", default="data/large_scale", help="Target output directory")
    args = parser.parse_args()
    generate_datasets(total_count=args.count, output_dir=args.output_dir)
