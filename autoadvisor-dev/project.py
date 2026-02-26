from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.edge.options import Options
from selenium.common.exceptions import NoSuchElementException, SessionNotCreatedException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import os
import re
import json
import time
from datetime import datetime
import argparse
import getpass
import sys

import preprocess

class student_credentials():
    """
    Minimal CLI-compatible credentials wrapper used by the rest of project.py.
    Keeps method names expected by existing code.
    """
    def __init__(self):
        parser = argparse.ArgumentParser(add_help=False)
        parser.add_argument("--config", "-c", dest="config", default="", help="Path to config .xlsx file")
        parser.add_argument("--user", "-u", dest="user", default="", help="Email local-part or full email")
        parser.add_argument("--pass", "-p", dest="passwd", default="", help="Password (avoid on CLI)")
        parser.add_argument("--verify", dest="verify_method", default="Okta Push Notification", help="Verify method")
        parser.add_argument("--current-sem", dest="current_sem", action="store_true", help="Toggle current semester flag")
        args, _ = parser.parse_known_args()

        self.filename = args.config or ""
        self.username = args.user.strip() or ""
        if self.username and "@" not in self.username:
            self.username = self.username + "@students.vsu.edu"
        self.password = args.passwd or ""
        if not self.username:
            local = input("Email local-part (jdoe) or full email: ").strip()
            if local:
                if "@" in local:
                    self.username = local
                else:
                    self.username = local + "@students.vsu.edu"
        if not self.password:
            try:
                self.password = getpass.getpass(prompt="Enter your password: ")
            except Exception:
                self.password = input("Enter your password: ")

        try:
            self.student_id = re.search(r"^([^@]+)", self.username).group(1)
        except Exception:
            self.student_id = ""
        self.pin = ""
        self.login_count = 0
        self.current_sem = bool(args.current_sem)
        self.verify_method = args.verify_method or "Okta Push Notification"

    def set_config(self):
        cfg = input("Enter path to configuration .xlsx file: ").strip()
        if cfg:
            self.filename = cfg

    def get_config(self):
        return self.filename

    def set_credentials(self, uid, pwd=None):
        if hasattr(uid, "get"):
            user_val = uid.get()
        else:
            user_val = uid
        if hasattr(pwd, "get"):
            pwd_val = pwd.get()
        else:
            pwd_val = pwd or ""
        user_val = (user_val or "").strip()
        if user_val and "@" not in user_val:
            user_val = user_val + "@students.vsu.edu"
        self.username = user_val
        if pwd_val:
            self.password = pwd_val
        try:
            self.student_id = re.search(r"^([^@]+)", self.username).group(1)
        except Exception:
            self.student_id = ""

    def get_credentials(self):
        return self.username, self.password

    def get_student_id(self):
        return self.student_id

    def get_sem_flag(self):
        return self.current_sem

    def toggle_sem(self, flag):
        self.current_sem = bool(flag)

    def set_pin(self, pin):
        if hasattr(pin, "get"):
            self.pin = pin.get()
        else:
            self.pin = pin

    def return_pin(self):
        return self.pin

    def set_verify_method(self, method):
        self.verify_method = method

    def get_verify_method(self):
        return self.verify_method

#Get Rid of Tkinter so it can be ran from the terminal

version = "2.4.4-Student"

#method to return appropriate value for term dropdown
def get_timecode():
    #get current month and year
    month = datetime.now().month
    year = str(datetime.now().year)
    #change month to string
    if month >= 1:
        #set month to "01" if month is between 1 and 4
        if month >= 5:
            #set month to "05" if month is between 5 and 7
            if month >= 8:
                #set month to "08" if month is between 8 and 11
                if month == 12:
                    #change month to string if month is 12
                    month = "12"
                else:
                    month = "08"
            else:
                month = "05"
        else:
            month = "01"
    #return year and month to use as value for dropdown selector
    return year + month

def build_path(path, fullname):
    #create folder using student name
    #check if name has been established
    if bool(fullname):
        #search to see if student folder already exists
        if not os.path.exists(path):
            os.makedirs(path)
            if os.path.exists(path):
                print("Path successfully created!")
            else:
                print("Failed to create path!")
        else:
            print("Path already exists!")
    else:
        sys.exit("An unexpected error has occurred: Unable to locate student's name!")

def build_files(path, driver, fullname):
    #scrape transcript for courses and semesters
    try:
        wait.until(EC.visibility_of_all_elements_located((By.XPATH, "//table")))
        data = driver.find_elements(By.XPATH, "//table")

        courses = []
        semesters = []
        #boolean flags to distinguish semesters
        sem_start = sem_end = False
        #used to determine if we reached current/future semesters
        is_curr = False
        #used to hold course as we build it from data
        proto = ""
        course_marker = False
        
        output = []

        for i in data:
            output += i.text.split('\n')

        for line in output:
            #Find each semester as we iterate through scraped data
            #signifies the start of courses in progress
            if re.search("Course\(s\) in progress", line) and not is_curr:
                is_curr = True
            if re.search("Subject Course Level Title Grade Credit Hours Quality Points Start and End Dates R|Subject Course Title Grade Credit hours Quality points R|Subject Course Level Title Credit Hours Start and End Dates|Subject Course Campus Level Title Credit Hours Start and End Dates", line):
                if sem_start:
                    #lets us know that we've reached the end of a previous semester
                    sem_end = True
                #signifies the start of a new semester
                sem_start = True
            #if we are in a semester, find the courses
            elif sem_start:
                #add marker to course array to signify semesters
                if sem_end:
                    courses.append("-")
                    sem_end = False
                #append credits to course
                if course_marker:
                    if re.search("[0-9]+.[0-9]{3}", line):
                        course_marker = False
                        for i in line.replace("\n", " ").split(" "):
                            proto.append(i)
                        course = proto.copy()
                        #pop empty indices at beginning of course
                        while not bool(course[0]):
                            course.pop(0)
                        #remove 'U' from courses
                        if course[2] == 'U':
                            course.pop(2)
                        #remove unnecessary indices at end of course
                        try:
                            while re.search("[0-9]+.[0-9]{3}" ,course[-2]):
                                course.pop()
                        except IndexError as e:
                            print(e)
                            print(course)
                            print(line)
                            sys.exit()
                        #append course to array and reset proto
                        courses.append(course)
                        proto.clear()
                    #check if we reached current/future semesters
                    else:
                        for i in line.replace("\n", " ").split(" "):
                            proto.append(i)
                #find a course and store it to the holder array
                elif re.search("[A-Z]{4}", line):
                    proto = line.replace("\n", " ").split(" ")
                    #Extra code to catch transfer courses and current semester courses, since their contents are stored in one line
                    if re.search("0.000$", line) or is_curr:
                        course = proto.copy()
                        #Add 'inprog' to current semester courses as they have no letter grade
                        if is_curr:
                            course.insert(-1, "inprog")
                        #remove unnecessary indices at end of course
                        else:
                            course.pop()
                        courses.append(course)
                        proto.clear()
                    else:
                        course_marker = True

        #Append separator for final course structure
        courses.append("-")
        
        data = driver.find_elements(By.CSS_SELECTOR, ".sub-heading.period-padding.ng-binding")
        
        output = []

        for i in data:
            output += i.text.split('\n')
            
        for line in output:
            semesters.append(line)
            semesters.append('-')

        #print courses to file
        create_file_path(fullname , path, "/courses.txt", "courses", courses)
        #print semesters to file
        create_file_path(fullname , path, "/semesters.txt", "semesters", semesters)
        
        return True
    except TimeoutException:
        return False
        
#method to create file to store data
def create_file_path(fullname ,path, filename, file_type, array):
    #check if file directory exists
    if os.path.exists(path):
        #if folder exists, check if file already exists
        file_path = path + filename
        #if file exists, overwrite it
        if os.path.exists(file_path):
            #remove old file, then create new file
            print("Overwriting " + file_type + " file for " + fullname + "...")
            os.remove(file_path)
            with open(file_path, 'w') as target_file:
                if file_type == "courses":
                    for line in array:
                        for index in line:
                            target_file.write(index + " ")
                        target_file.write("\n")
                else:
                    for line in array:
                        target_file.write(line + "\n")
        else:
            #create new file
            print("Creating " + file_type + " file for " + fullname + "...")
            with open(file_path, 'w') as target_file:
                if file_type == "courses":
                    for line in array:
                        for index in line:
                            target_file.write(index + " ")
                        target_file.write("\n")
                else:
                    for line in array:
                        target_file.write(line + "\n")
    else:
        print("Error! Folder path for " + fullname + " does not exist!")


def create_note_files(path, name, vnumber, advisor):
    """
    Read courses.txt / semesters.txt in path, build structured JSON
    (courses as objects) and note.txt.  No special transfer‑credit bucket;
    every course stays in its original semester group.
    Returns the JSON dict.
    """
    courses_path = os.path.join(path, "courses.txt")
    semesters_path = os.path.join(path, "semesters.txt")
    note_json_path = os.path.join(path, "note.json")
    note_txt_path = os.path.join(path, "note.txt")

    # read semester descriptions
    semesters = []
    if os.path.exists(semesters_path):
        with open(semesters_path, "r", encoding="utf-8") as f:
            curr = []
            for ln in f:
                ln = ln.strip()
                if ln == "-" or ln == "":
                    if curr:
                        semesters.append(" ".join(curr).strip())
                        curr = []
                else:
                    curr.append(ln)
            if curr:
                semesters.append(" ".join(curr).strip())

    # read course lines and group by ‘-’ separators
    sem_courses = []
    if os.path.exists(courses_path):
        with open(courses_path, "r", encoding="utf-8") as f:
            current = []
            for ln in f:
                ln = ln.strip()
                if ln == "-" or ln == "":
                    if current:
                        sem_courses.append(current.copy())
                        current = []
                else:
                    current.append(ln)
            if current:
                sem_courses.append(current.copy())

    semcode_re = re.compile(r"\b(?:FA|SP|SU|WI)\s?\d{2,4}\b", re.IGNORECASE)

    def parse_course_line(raw):
        parsed = {
            "course_code": "",
            "name": "",
            "grade": "",
            "credits": "",
            "semester": "",
            "notes": ""
        }
        if not raw or not raw.strip():
            return parsed

        parsed["notes"] = raw

        if " - " in raw:
            parts = [p.strip() for p in raw.split(" - ")]
            if len(parts) >= 1:
                parsed["course_code"] = parts[0]
            if len(parts) >= 2:
                parsed["name"] = parts[1]
            if len(parts) >= 3:
                parsed["grade"] = parts[2]
            if len(parts) >= 4:
                parsed["credits"] = parts[3]
            if len(parts) >= 5:
                parsed["semester"] = parts[4]
            if len(parts) >= 6:
                parsed["notes"] = parsed["notes"] + " | " + " - ".join(parts[5:]).strip()
            m = semcode_re.search(parsed.get("semester", "") or raw)
            if m:
                parsed["_sem_code"] = m.group(0).upper().replace(" ", "")
            return parsed

        parts = raw.split()
        credits_idx = None
        for i, p in enumerate(parts[::-1]):
            if re.match(r"^\d+\.\d{3}$", p):
                credits_idx = len(parts) - 1 - i
                break
        if credits_idx is not None:
            parsed["credits"] = parts[credits_idx]
            if credits_idx - 1 >= 0:
                parsed["grade"] = parts[credits_idx - 1]
            if len(parts) >= 2:
                parsed["course_code"] = f"{parts[0]} {parts[1]}"
                parsed["name"] = " ".join(parts[2: max(2, credits_idx - 1)]).strip()
            else:
                parsed["name"] = " ".join(parts[:credits_idx - 1]).strip()

        m = semcode_re.search(raw)
        if m:
            parsed["_sem_code"] = m.group(0).upper().replace(" ", "")

        return parsed

    # build labels (Freshman 1, etc.)
    label_names = ["Freshman", "Sophomore", "Junior", "Senior"]
    bucket_count = max(len(sem_courses), len(semesters), 1)
    labels = []
    for i in range(bucket_count):
        year = i // 2
        part = (i % 2) + 1
        base = label_names[year] if year < len(label_names) else f"Year{year+1}"
        labels.append(f"{base} {part}")

    sem_buckets = []
    for i in range(len(labels)):
        sem_buckets.append({
            "label": labels[i],
            "description": semesters[i] if i < len(semesters) else "",
            "courses": []
        })

    def sem_code_to_index(code):
        if not code:
            return None
        code = code.upper()
        season_map = {"FA": "FALL", "SP": "SPRING", "SU": "SUMMER", "WI": "WINTER"}
        m = re.match(r"^(FA|SP|SU|WI)(\d{2,4})$", code)
        if not m:
            return None
        season = season_map.get(m.group(1))
        year = m.group(2)
        year4 = "20" + year if len(year) == 2 else year
        for idx, sem in enumerate(sem_buckets):
            desc = (sem.get("description") or "").upper()
            label = (sem.get("label") or "").upper()
            if code in desc or code in label:
                return idx
            if season and season in desc:
                if year and (year in desc or year4 in desc):
                    return idx
                if not year:
                    return idx
        return None

    block_count = len(sem_courses)
    next_seq_bucket = 0
    block_to_bucket = {}
    for b_idx, block in enumerate(sem_courses):
        mapped = None
        for raw in block:
            m = semcode_re.search(raw)
            if m:
                idx = sem_code_to_index(m.group(0).upper().replace(" ", ""))
                if idx is not None:
                    mapped = idx
                    break
        if mapped is None:
            block_text = " ".join(block).upper()
            for idx, sem in enumerate(sem_buckets):
                desc = (sem.get("description") or "").upper()
                if desc and desc in block_text:
                    mapped = idx
                    break
            if mapped is None and block_count == len(sem_buckets):
                mapped = b_idx
        if mapped is None:
            for idx in range(len(sem_buckets)):
                if len(sem_buckets[idx]["courses"]) == 0:
                    mapped = idx
                    break
            if mapped is None:
                mapped = min(next_seq_bucket, len(sem_buckets) - 1)
        block_to_bucket[b_idx] = mapped
        next_seq_bucket = min(mapped + 1, len(sem_buckets) - 1)

    for b_idx, block in enumerate(sem_courses):
        target_idx = block_to_bucket.get(b_idx, 0)
        for raw in block:
            p = parse_course_line(raw)
            if p.get("_sem_code"):
                override_idx = sem_code_to_index(p.get("_sem_code"))
                if override_idx is not None:
                    target_idx = override_idx
            if target_idx >= len(sem_buckets):
                target_idx = len(sem_buckets) - 1
            if not p.get("semester"):
                p["semester"] = sem_buckets[target_idx].get("label", "")
            p.pop("_sem_code", None)
            sem_buckets[target_idx]["courses"].append(p)

    for sem in sem_buckets:
        for c in sem["courses"]:
            if "notes" not in c:
                c["notes"] = ""
            if not c.get("semester"):
                c["semester"] = sem.get("label", "")

    data = {
        "name": name,
        "v_number": vnumber,
        "advisor": advisor,
        "semesters": sem_buckets
    }

    # write JSON
    try:
        with open(note_json_path, "w", encoding="utf-8") as jf:
            json.dump(data, jf, indent=2, ensure_ascii=False)
        print(f"Wrote JSON note to {note_json_path}")
    except Exception as e:
        print(f"Failed to write JSON note: {e}")

    # write plain text note
    try:
        with open(note_txt_path, "w", encoding="utf-8") as tf:
            tf.write(f"Name: {name}\nV-Number: {vnumber}\nAdvisor: {advisor}\n\n")
            tf.write('Transcripts / Semesters:\n')
            for sem in data['semesters']:
                tf.write(f"{sem.get('label','')}: {sem.get('description','')}\n")
                for c in sem.get('courses', []):
                    tf.write(f"  - {c.get('course_code','')} {c.get('name','')}\n")
                    tf.write(f"      grade: {c.get('grade','')}, credits: {c.get('credits','')}, notes: {c.get('notes','')}\n")
                tf.write('\n')
        print(f"Wrote text note to {note_txt_path}")
    except Exception as e:
        print(f"Failed to write text note: {e}")

    return data
#Above can stay Global
# MAIN EXECUTION STARTS HERE
#Gets student login credentials
#Everything from here on down in the main function
student = student_credentials()

try:
    username, password = student.get_credentials()
    student_id = student.get_student_id()
    #Exception Handling that closes program if tkinter box is closed prematurely
    if not bool(username) or not bool(password):
        sys.exit("Program Terminated!")
except AttributeError:
    sys.exit('Program Terminated!')

config_file = student.get_config()

#Initialize webdriver
try:
    driver = webdriver.Edge()
    driver.get('https://login.vsu.edu')
except SessionNotCreatedException:
    student.update_webdriver()

wait = WebDriverWait(driver, 10)

#attempt to log in

wait.until(EC.visibility_of_element_located((By.ID, "input28")))
uid = driver.find_element(By.ID, "input28")
uid.send_keys(username)
driver.find_element(By.CSS_SELECTOR, ".button").click()
 
wait = WebDriverWait(driver, 5)
 
try:
    wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Verify with something else")))
    driver.find_element(By.LINK_TEXT, "Verify with something else").click()
except TimeoutException:
    pass
 
wait = WebDriverWait(driver, 600)
 
# Get authentication method from user
auth_type = student.get_verify_method()
test = driver.find_elements(By.XPATH, "//div[@class = 'authenticator-row clearfix']")
for t in test:
    button = t.find_element(By.CSS_SELECTOR, "a[data-se='button']")
    target = button.get_attribute("aria-label")
    match auth_type:
        case "Google Authenticator":
            if(target == "Select Google Authenticator."):
                button.click()
                break
        case "Okta 2FA Code":
            if(target == "Select to enter a code from the Okta Verify app."):
                button.click()
                break
        case "Okta Push Notification":
            if(target == "Select to get a push notification to the Okta Verify app."):
                button.click()
                break
 
wait = WebDriverWait(driver, 10)
 
try:
    wait.until(EC.visibility_of_element_located((By.XPATH, "//input[@type = 'password']")))    
    pwd = driver.find_element(By.XPATH, "//input[@type = 'password']")
    pwd.send_keys(password)
    driver.find_element(By.CSS_SELECTOR, ".button").click()
except TimeoutException:
    pass

# DEBUG: Check current page after Okta auth
print("Current URL after Okta:", driver.current_url)
print("Current page title:", driver.title)

# UPDATED: Navigate to Student Services instead of Faculty Services
print("Waiting for Banner Student Self Service logo...")
wait = WebDriverWait(driver, 30)
wait.until(EC.element_to_be_clickable((By.XPATH, "//img[@alt='Banner Student Self Service logo']")))
print("Banner logo found! Clicking...")
driver.find_element(By.XPATH, "//img[@alt='Banner Student Self Service logo']").click()

wait = WebDriverWait(driver, 10)

original_window = driver.current_window_handle

for window_handle in driver.window_handles:
    if window_handle != original_window:
        driver.switch_to.window(window_handle)
        
second_window = driver.current_window_handle

# UPDATED: Navigate to student's own transcript
wait.until(EC.title_is("Student Services Dashboard"))
driver.find_element(By.LINK_TEXT, "Student Profile").click()
import re
from selenium.common.exceptions import TimeoutException

try:
    print("Waiting for Student Profile title...")

    # Use the correct locator type: By.XPATH
    vnum_element = WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.XPATH, "//div[@id='title-panel']/h1"))
    )

    # Grab the header text
    vnum_text = vnum_element.text.strip()
    print("[OK] Raw Header Text:", vnum_text)

    # Example: "Student Profile – Jordan A. Broomfield (V00679148)"
    match = re.search(r"Student Profile\s*[–-]\s*(.+)\s+\((V\d+)\)", vnum_text)
    if match:
        student_name = match.group(1).strip()
        vnumber = match.group(2).strip()
        print(f"[OK] Name: {student_name}")
        print(f"[OK] V-Number: {vnumber}")
    else:
        print("[WARNING] Could not parse name and V-number from:", vnum_text)

except TimeoutException:
    print("[ERROR] Could not locate the Student Profile title element quickly.")
print(vnumber)

#Navigate to Student Profile. Code Below will handle the rest.
sem_flag = student.get_sem_flag()
dt = datetime.now()
timestamp = dt.strftime("%b") + "-" + str(dt.day) + "-" + str(dt.year) + "-" + str(dt.hour) + "-" + str(dt.minute) + "-" + str(dt.second)

wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Academic Transcript")))
#Pulls Advisor Names
try:
        advisor_listing = driver.find_element(By.CSS_SELECTOR, ".facultyLinkClass:nth-child(2)").text.split(" ")
        advisor = advisor_listing[-1]
except NoSuchElementException:
        pass
driver.find_element(By.LINK_TEXT, "Academic Transcript").click()
for window_handle in driver.window_handles:
        if window_handle != original_window and window_handle != second_window:
            driver.switch_to.window(window_handle)
wait.until(EC.visibility_of_element_located((By.ID, "transcriptLevelSelection")))
driver.find_element(By.ID, "transcriptLevelSelection").click()
wait.until(EC.visibility_of_element_located((By.XPATH, "//li[@id='ui-select-choices-row-1-']/div/div")))
driver.find_element(By.XPATH, "//li[@id='ui-select-choices-row-1-']/div/div").click()
wait.until(EC.visibility_of_element_located((By.ID, "transcriptTypeSelection")))
driver.find_element(By.ID, "transcriptTypeSelection").click()
wait.until(EC.visibility_of_element_located((By.XPATH, "//li[@id='ui-select-choices-row-2-']/div/div")))
driver.find_element(By.XPATH, "//li[@id='ui-select-choices-row-2-']/div/div").click()
wait.until(EC.visibility_of_element_located((By.XPATH, "//button[contains(.,'Submit')]")))
driver.find_element(By.XPATH, "//button[contains(.,'Submit')]").click()


path = "advisors/" + timestamp + "/" + advisor + "/" + student_name.strip() + '/' + config_file.split('/')[-1].split('.')[0]


build_path(path, student_name.strip())
success = build_files(path, driver, student_name.strip())

note_data = None
try:
    note_data = create_note_files(path, student_name.strip(), vnumber, advisor)
except Exception as e:
    print(f"create_note_files failed: {e}")

try:
    driver.quit()
except Exception:
    pass

try:
    processed_note = preprocess.main(
        [student_name],
        config_file,
        [vnumber],
        [student_name],
        sem_flag,
        timestamp,
        advisor,
        note_json=note_data
    )
    print(f"preprocess returned: {'present' if processed_note else 'none'}")
except Exception as e:
    print(f"Error calling preprocess.main: {e}")
    processed_note = None

# ALWAYS print the final transcript
print("\n" + "="*100)
print("FINAL STUDENT TRANSCRIPT DATA - note.json")
print("="*100)

try:
    advisors_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "advisors"))
    
    if os.path.exists(advisors_dir):
        timestamps = sorted([d for d in os.listdir(advisors_dir) 
                           if os.path.isdir(os.path.join(advisors_dir, d))])
        
        if timestamps:
            latest_timestamp = timestamps[-1]
            timestamp_dir = os.path.join(advisors_dir, latest_timestamp)
            
            note_files = []
            for root, dirs, files in os.walk(timestamp_dir):
                if "note.json" in files:
                    note_path = os.path.join(root, "note.json")
                    mtime = os.path.getmtime(note_path)
                    note_files.append((mtime, note_path))
            
            if note_files:
                note_files.sort(reverse=True)
                latest_note_path = note_files[0][1]
                
                print(f"File: {latest_note_path}\n")
                
                with open(latest_note_path, "r", encoding="utf-8") as f:
                    transcript_data = json.load(f)
                
                # Print the JSON
                print(json.dumps(transcript_data, indent=2, ensure_ascii=False))
            else:
                print("ERROR: No note.json found in advisors directory")
        else:
            print("ERROR: No timestamp folders found in advisors directory")
    else:
        print(f"ERROR: Advisors directory not found at {advisors_dir}")

except Exception as e:
    print(f"ERROR: Could not print final transcript data: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*100 + "\n")


