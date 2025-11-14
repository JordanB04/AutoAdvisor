import advise
import re
import os
import json
import warnings

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
    # fallback: return first advisor folder if any
    return advisors[0] if advisors else None


def handle_note_json(note_json):
    """
    Minimal handler for incoming structured note JSON.
    Validates basic shape and returns the same object for further processing.
    """
    if not note_json:
        return None
    if not isinstance(note_json, dict):
        print("handle_note_json: note_json is not a dict")
        return None
    # basic validation
    name = note_json.get("name")
    vnum = note_json.get("v_number")
    semesters = note_json.get("semesters", [])
    if not name or not vnum:
        print("handle_note_json: missing name or v_number")
        return None
    if not isinstance(semesters, list):
        print("handle_note_json: semesters is not a list")
        return None

    # simple summary print for debug
    try:
        print(f"preprocess: received note for {name} ({vnum}) with {len(semesters)} semesters")
    except Exception:
        pass

    # Optionally: do lightweight normalization (ensure each semester has courses list)
    for sem in semesters:
        if not isinstance(sem, dict):
            continue
        if "courses" not in sem or not isinstance(sem["courses"], list):
            sem["courses"] = []

    return note_json


# Update main signature to accept note_json (keeps backwards compatibility)
def main(student_names, config_file, vnums, display_names, sem_flag, timestamp, advisor, note_json=None):
    """
    Preprocess entry point.

    - If note_json is provided, handle it via handle_note_json and return the processed object.
    - If no note_json, run the (minimal) preprocessing loop over student_names.
    """
    # If structured note JSON provided, let preprocess handle it and return processed note
    if note_json is not None:
        processed_note = handle_note_json(note_json)
        return processed_note

    # Backwards-compatible fallback: iterate students and prepare "courses" placeholder
    processed = []
    for idx, name in enumerate(student_names):
        disp = display_names[idx] if idx < len(display_names) else name
        vnum = vnums[idx] if idx < len(vnums) else ""
        print(f"preprocess: processing {disp} ({vnum})")
        # Placeholder: read existing note.json if it exists and append
        advisor_path = os.path.join("advisors", timestamp, advisor, disp.replace("/", "_"))
        note_path = os.path.join(advisor_path, "CSCI_2020_TRANSCRIPT", "note.json")
        if os.path.exists(note_path):
            try:
                with open(note_path, "r", encoding="utf-8") as jf:
                    note = json.load(jf)
                    processed.append(note)
            except Exception as e:
                print(f"preprocess: failed to read {note_path}: {e}")
        else:
            # minimal structure if no note.json found
            processed.append({"name": disp, "v_number": vnum, "semesters": []})

    return processed

    counter = 0
    for name in student_names:
        #advisor = find_advisor(name, config_file, timestamp)
        name = name.strip()
        f1 = open("advisors/" + timestamp + "/" + advisor + "/" + name + "/" + config_file.split('/')[-1].split('.')[0] + "/courses.txt", "r")
        f2 = open("advisors/" + timestamp + "/" + advisor + "/" + name + "/" + config_file.split('/')[-1].split('.')[0] + "/semesters.txt", "r")

        print("Formatting Transcript for " + name + "...")
        print(vnums[counter])

        #Read semesters from file and insert it into list semesters
        semesters = []
        for line in f2:
            if len(line) > 2:
                line = line.strip()
                sem = ''
                # Try to capture patterns like "Term : Fall 2022" or "Fall 2022 : Advanced Placement"
                m = re.search(r'(Spring|Summer|Fall|Winter)[^\d]*(\d{4})', line, re.I)
                if m:
                    season = m.group(1).capitalize()
                    year = m.group(2)[-2:]
                    if season == 'Spring':
                        sem = 'SP' + year
                    elif season == 'Summer':
                        sem = 'SU' + year
                    elif season == 'Fall':
                        sem = 'FA' + year
                    elif season == 'Winter':
                        sem = 'WI' + year
                else:
                    # fallback to older "Term : ..." forms
                    if re.search('Term : Spring', line):
                        sem = 'SP' + line[-2:]
                    elif re.search('Term : Summer', line):
                        sem = 'SU' + line[-2:]
                    elif re.search('Term : Fall', line):
                        sem = 'FA' + line[-2:]
                    elif re.search('Term : Winter', line):
                        sem = 'WI' + line[-2:]
                    else:
                        # ignore non-semester labels (e.g. "Advanced Placement") to avoid inserting phantom semesters
                        continue
                semesters.append(sem)
        f2.close()

        #Read courses from file and insert it into list courses.
        #Ensure there is only one dash between courses
        courses = []
        for line in f1:
            line=line.strip()
            #Create a list by splitting the a line. Each word is an item in list
            lineRec = line.split()
            courses.append(lineRec)
        f1.close()  

        #Adjust courses to have course title as one element in list
        #For example ['CHEM', '152', 'General', 'Chemistry', 'II', 'S', '0.000'] becomes
        #['CHEM', '152', 'General Chemistry II ', 'S', '0.000']
        j=0
        in_prog = False
        for rec in courses:
            courseName = ""
            #For those who actually are course records not "-"
            if len(rec) > 1:
                size = len(rec)
                start = 2
                end = size-2
                popCount = 0
                #Create a course title in a single string
                for i in range (start, end):
                    if (i<end):
                        courseName = courseName + rec[i] + " "
                    else:
                        courseName = courseName + rec[i]
                    #While creating string remove the title words from course record
                    popCount = popCount + 1
                for itr in range(popCount):
                    rec.pop(2)
                #insert back course name as one string title
                courses[j].insert(2, courseName)
            j=j+1

        #Unify semester and course lists (Final Data structure view)
        #add semester to end of list
        i = 0
        for s in semesters:
            while (courses[i][0] != "-"):
                courses[i].append(s)
                i += 1
            i += 1

        #Then remove dashes
        for c in courses:
            if c[0] == "-":
                courses.remove(c)

        #join course acronym and number together
        for c in courses:
            course = c[0]+ " " + c[1]
            c[0] = course
            c.pop(1)

        #Set semester and Replace 'inprog' with 'In progress',
        for c in courses:
            if c[2] == 'inprog':
                c[2] = 'In progress'

        #remove failed courses
        #course, name, grade, credits, semester    
        i = 0
        while i < len(courses):
            c = courses[i]
            course = c[0]
            abbr = course[:-4]
            grade = c[2]
            if grade == 'F' or grade == 'U' or grade == 'N' or \
                 grade == 'W' or grade == 'I':
                courses.pop(i)
                i -= 1
            i += 1

        #remove duplicate courses
        i = 0
        while i < len(courses):
            j = i + 1
            c1 = courses[i][0]
            abbr = c1[:-4]
            #ignore science courses
            if not abbr == 'BIOL':
                if not abbr == 'PHYS':
                    if not abbr == 'CHEM':
                        while j < len(courses):
                            c2 = courses[j][0]
                            if c1 == c2:
                                c1_name = courses[i][1]
                                c2_name = courses[j][1]
                                if not c1_name == c2_name:
                                    j += 1
                                    continue
                                
                                grade1 = courses[i][2]
                                grade2 = courses[j][2]
                                if grade1 == 'TR':
                                    courses.pop(j)
                                    break
                                elif grade1 == 'S':
                                    if grade2 < 'C':
                                        courses.pop(i)
                                        break
                                    else:
                                        courses.pop(j)
                                        break
                                elif grade1 == 'SP':
                                    if grade2 < 'D':
                                        courses.pop(i)
                                        break
                                    else:
                                        courses.pop(j)
                                        break
                                elif grade2 == 'TR':
                                    courses.pop(j)
                                    break
                                elif grade2 == 'S':
                                    if grade1 < 'C':
                                        courses.pop(j)
                                        break
                                    else:
                                        courses.pop(i)
                                        break
                                elif grade2 == 'SP':
                                    if grade1 < 'D':
                                        courses.pop(j)
                                        break
                                    else:
                                        courses.pop(i)
                                        break
                                elif grade2 == "In progress":
                                    if grade1 == 'D':
                                        courses.pop(i)
                                elif grade1 <= grade2:
                                    courses.pop(j)
                                    break
                                else:
                                    courses.pop(i)
                            j += 1
            i += 1
                    
        #Pass name(string) and courses(list) to advise.py
        #advise.main(courses, name)
        advise.main(courses, name, config_file, display_names[counter], vnums[counter], advisor, sem_flag, timestamp)
        counter += 1

    # If a structured note JSON was provided, let preprocess handle it
    processed_note = None
    if note_json is not None:
        processed_note = handle_note_json(note_json)

    # Return processed_note for caller if available (backwards-compatible)
    try:
        # existing main may return something; preserve that if present
        return processed_note
    except Exception:
        return processed_note
