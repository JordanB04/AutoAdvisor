import os
import json
import warnings
import re

# suppress openpyxl user warnings (optional)
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl.*")


def find_advisor(name, config_file, timestamp):
    """Return advisor folder name if found under advisors/<timestamp>/"""
    advisor_path = os.path.join("advisors", timestamp)
    try:
        advisors = [f for f in os.listdir(advisor_path)]
    except Exception:
        return None
    for adv in advisors:
        if adv and adv in name:
            return adv
    return advisors[0] if advisors else None


def handle_note_json(note_json):
    """
    Validate and normalize structured note JSON.
    Ensures each semester has a courses list and normalizes inprog labels.
    """
    if not note_json or not isinstance(note_json, dict):
        return None

    # basic validation
    name = note_json.get("name")
    vnum = note_json.get("v_number")
    semesters = note_json.get("semesters", [])
    if not name or not vnum or not isinstance(semesters, list):
        return None

    # basic normalization: ensure courses list and notes field
    for sem in semesters:
        if not isinstance(sem, dict):
            continue
        sem.setdefault("courses", [])
        for c in sem["courses"]:
            if "notes" not in c:
                c["notes"] = ""
            # normalize grade token 'inprog' -> placeholder handled below
            if isinstance(c.get("grade"), str) and c.get("grade").lower() == "inprog":
                c["grade"] = "inprog"

    # Convert 'inprog' semantics: if course semester equals current semester -> "In progress", else "Next Sem"
    try:
        import advise
        curr = getattr(advise, "get_curr_sem", lambda: None)()
    except Exception:
        curr = None

    for sem in semesters:
        label_or_desc = (sem.get("description") or sem.get("label") or "").upper()
        for c in sem.get("courses", []):
            if c.get("grade") == "inprog":
                term_field = (c.get("semester") or "").upper()
                # decide status
                if curr and curr.upper() in term_field:
                    c["grade"] = "In progress"
                else:
                    c["grade"] = "Next Sem"

    return note_json


def main(student_names, config_file, vnums, display_names, sem_flag, timestamp, advisor, note_json=None):
    # If structured note JSON provided, let preprocess handle it and return processed object
    if note_json is not None:
        processed = handle_note_json(note_json)
        return processed

    # Backwards-compatible fallback: read existing note.json files if present
    processed = []
    for idx, name in enumerate(student_names):
        disp = display_names[idx] if idx < len(display_names) else name
        vnum = vnums[idx] if idx < len(vnums) else ""
        advisor_path = os.path.join("advisors", timestamp, advisor, disp.replace("/", "_"))
        note_path = os.path.join(advisor_path, "CSCI_2020_TRANSCRIPT", "note.json")
        if os.path.exists(note_path):
            try:
                with open(note_path, "r", encoding="utf-8") as jf:
                    note = json.load(jf)
                    processed.append(handle_note_json(note))
            except Exception as e:
                print(f"preprocess: failed to read {note_path}: {e}")
                processed.append({"name": disp, "v_number": vnum, "semesters": []})
        else:
            processed.append({"name": disp, "v_number": vnum, "semesters": []})

    return processed
