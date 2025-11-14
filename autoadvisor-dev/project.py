from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
from selenium.webdriver.edge.options import Options
from selenium.common.exceptions import NoSuchElementException, SessionNotCreatedException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
import tkinter #GUI
from tkinter import *
from tkinter.ttk import *
from tkinter import messagebox
from tkinter.filedialog import askopenfilename
from datetime import datetime

import os
import re
import json
import time

import preprocess

version = "2.4.4-Student"

#Get Rid of Tkinter so it can be ran from the terminal


#Class to hold student login info for session
class student_credentials():
    #Opens a window and prompts user to select config file and to log in
    def greeting_window (self, greeting, filename):
        portal = Tk()
        portal.title("Student Auto Advisor: Home")
        is_current_sem = BooleanVar(portal, value = self.current_sem)
        welcome = Label(portal, text = greeting)
        portal.after(1, lambda: portal.focus_force())
        
        #if no configuration file is selected, prompt user for config file
        if len(filename) == 0 or not re.search('.xlsx$', filename):
            config = Button(portal, text="Set Configuration File", command = lambda:[portal.destroy(), self.set_config()])
            portal.bind('<Return>', lambda x:[portal.destroy(), self.set_config()])
            welcome.pack(side = TOP)
            config.pack(side = BOTTOM)
        #if a config file has be selected, prompt user to log in
        else:
            login = Button(portal, text="Log In", command = lambda:[portal.destroy(), self.click_login()])
            config = Button(portal, text="Change Configuration File", command = lambda:[portal.destroy(), self.set_config()])
            sem_btn = Checkbutton(portal, text="Toggle on if planning for Current Semester", variable = is_current_sem, command = lambda:[self.toggle_sem(is_current_sem.get())])
            portal.bind('<Return>', lambda x:[portal.destroy(), self.click_login()])
            config.pack(side = BOTTOM)
            welcome.pack(side = TOP)
            login.pack(side = BOTTOM)
            sem_btn.pack(side = TOP, expand = True)
        
        portal.mainloop()

    def toggle_sem (self, is_current_sem):
        if is_current_sem:
            self.current_sem = True
        else:
            self.current_sem = False

    def get_sem_flag(self):
        return self.current_sem

    #function that grabs file path of config file
    def set_config(self):
        file_name = askopenfilename(title = 'Select Config File', filetypes = [('Excel Files','*.xlsx')])
        self.filename = file_name
        self.greeting_window(self.greeting, self.filename)               

    #function that returns config file path
    def get_config(self):
        return self.filename

    #method to grab student login info
    def click_login(self):
        def on_option_value_change(*args):
            self.set_verify_method(option.get())
        #opens a window to grab student login info
        login = Tk()
        login.title("Student Auto Advisor: Login")
        auth_options = ["Google Authenticator", "Okta 2FA Code", "Okta Push Notification"]
        welcome = Label(login, text = "Enter your E-Mail and Password:")
        login.after(1, lambda: login.focus_force())
        Label(login, text='E-mail').grid(row=1)
        Label(login, text='Password').grid(row=2)
        Label(login, text="@students.vsu.edu").grid(row=1, column = 2)
        Label(login, text="Auth Method:").grid(row = 3)
        uid = Entry(login, width = 15)
        pwd = Entry(login, show ="*", width = 25)
        option = StringVar(value=self.get_verify_method())
        option.trace_add("write", on_option_value_change)
        auth_menu = OptionMenu(login, option, self.get_verify_method(), *auth_options)
        #when submit button is clicked, it sends credentials to Banner Portal
        submit = Button(login, text='Submit', command = lambda:[self.set_credentials(uid, pwd), self.set_verify_method(option.get()), login.destroy()])
        back = Button(login, text='Return', command = lambda:[login.destroy(), self.greeting_window(self.greeting, self.filename)])
        login.bind('<Return>', lambda x:[self.set_credentials(uid, pwd), login.destroy()])
        welcome.grid(row = 0, columnspan = 3)
        uid.grid(row = 1, column = 1)
        pwd.grid(row = 2, column = 1, columnspan = 2)
        auth_menu.grid(row = 3, column = 1, columnspan = 2)
        submit.grid(row = 4, column = 1)
        back.grid(row = 4, column = 2)
        
    #sets student's login info
    def set_credentials(self, uid, pwd):
        self.username = uid.get() + "@students.vsu.edu"
        self.password = pwd.get()
        self.student_id = uid.get()  # Store the V-number for later use
        
    #returns login info
    def get_credentials(self):
        return self.username, self.password

    def get_student_id(self):
        return self.student_id

    #warns the user about login failures
    def login_warning(self):
        warn = Tk()
        warn.title("Warning!")
        warning = Label(text = "Warning! You have failed to login 3 times now. Please ensure that you enter your information correctly.")
        warn.after(1, lambda: warn.focus_force())
        back = Button(warn, text='Return', command = lambda:[warn.destroy(), self.greeting_window(self.greeting, self.filename)])
        warn.bind('<Return>', lambda x:[warn.destroy(), self.greeting_window(self.greeting, self.filename)])
        warning.pack(side = TOP)
        back.pack(side = TOP)
        warn.mainloop()

    #terminates the program if user fails to log in 4 times
    def login_timeout(self):
        terminate = Tk()
        terminate.title("Too Many Login Attempts")
        terminate.after(1, lambda: terminate.focus_force())
        message = Label(text = "You have attempted too many failed login attempts. To prevent account lockout, please try again later.")
        end = Button(terminate, text='Exit', command = lambda:[terminate.destroy(), driver.quit(), sys.exit("Program Terminated: Too Many Login Attempts!")])
        terminate.bind('<Return>', lambda x:[terminate.destroy(), driver.quit(), sys.exit("Program Terminated: Too Many Login Attempts!")])
        message.pack(side = TOP)
        end.pack(side = TOP)
        terminate.mainloop()

    #method that prompts user to correct invalid login info
    def invalid_creds(self):
        self.greeting = 'Invalid login credentials!'
        self.login_count += 1
        if self.login_count < 3:
            self.greeting_window(self.greeting, self.filename)
        elif self.login_count == 3:
            self.login_warning()
        else:
            self.login_timeout()

    #UPDATED: Method for students to access their own transcript
    def access_student_services(self):
        """Navigate to student services instead of faculty services"""
        return True

    #UPDATED: Warns the user if Edge webdriver is not installed or up to date
    def update_webdriver(self):
        update = Tk()
        update.title('Update Edge Webdriver')
        update.after(1, lambda: update.focus_force())
        msg = Label(update, text="Please update Edge webdriver!")
        ok_btn = Button(update, text="OK", command = lambda:[update.destroy(), sys.exit('Program Terminated')])
        update.bind('<Return>', update.destroy)
        msg.pack(side = TOP)
        ok_btn.pack(side = BOTTOM)
        update.mainloop()
    
    #Gets 2FA input from user    
    def get_pin(self):
        pinget = Tk()
        auth_method = self.get_verify_method()
        match auth_method:
            case "Google Authenticator":
                pinget.title('Google Auth 2FA Code')
                pinget.after(1, lambda: pinget.focus_force())
                msg = Label(pinget, text='Enter 2FA Code:')
                code = Entry(pinget)
                submit = Button(pinget, text='Submit', command = lambda:[self.set_pin(code), pinget.destroy()])
                pinget.bind('<Return>', lambda x:[self.set_pin(code), pinget.destroy()])
                msg.pack(side = TOP)
                code.pack()
                submit.pack(side = BOTTOM)
                pinget.mainloop()
            case "Okta 2FA Code":
                pinget.title('Okta 2FA Code')
                pinget.after(1, lambda: pinget.focus_force())
                msg = Label(pinget, text='Enter 2FA Code:')
                code = Entry(pinget)
                submit = Button(pinget, text='Submit', command = lambda:[self.set_pin(code), pinget.destroy()])
                pinget.bind('<Return>', lambda x:[self.set_pin(code), pinget.destroy()])
                msg.pack(side = TOP)
                code.pack()
                submit.pack(side = BOTTOM)
                pinget.mainloop()
            case "Okta Push Notification":
                pinget.destroy()
       
    #Sets 2FA code for retrieval    
    def set_pin(self, pin):
        self.pin = pin.get()
    
    #Fetches stored 2FA code
    def return_pin(self):
        return self.pin
    
    def set_verify_method(self, method):
        self.verify_method = method
        
    def get_verify_method(self):
        return self.verify_method

    #instantiates class
    def __init__(self):
        self.username = ""
        self.password = ""
        self.student_id = ""
        self.filename = ""
        self.pin = ""
        self.greeting = 'Welcome to Student Auto-Advisor!'
        self.login_count = 0
        self.current_sem = False
        self.verify_method = "Okta Push Notification"
        self.greeting_window(self.greeting, self.filename)

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
    """Read courses.txt / semesters.txt in path, build structured JSON (courses as objects) and note.txt.
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

    # read course raw lines and group into semester buckets (preserve original grouping)
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

    # regex for compact semester codes like FA23, SP2024, etc.
    semcode_re = re.compile(r"\b(?:FA|SP|SU|WI)\s?\d{2,4}\b", re.IGNORECASE)

    def parse_course_line(raw):
        """Return a course object. Store original raw line in notes."""
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

        parsed["notes"] = raw  # keep raw line in notes

        # prefer dash-separated format: CODE - NAME - GRADE - CREDITS - SEM - NOTES
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
                # preserve any trailing pieces in notes as well
                parsed["notes"] = parsed["notes"] + " | " + " - ".join(parts[5:]).strip()
            # detect compact code inside semester field or raw
            m = semcode_re.search(parsed.get("semester", "") or raw)
            if m:
                parsed["_sem_code"] = m.group(0).upper().replace(" ", "")
            return parsed

        # fallback: token heuristic (look for credits like 3.000)
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

        # detect compact semester code anywhere in raw (FA23, SP24, etc.)
        m = semcode_re.search(raw)
        if m:
            parsed["_sem_code"] = m.group(0).upper().replace(" ", "")

        return parsed

    # Build semester labels (two per academic year)
    label_names = ["Freshman", "Sophomore", "Junior", "Senior"]
    bucket_count = max(len(sem_courses), len(semesters), 1)
    labels = []
    for i in range(bucket_count):
        year = i // 2
        part = (i % 2) + 1
        base = label_names[year] if year < len(label_names) else f"Year{year+1}"
        labels.append(f"{base} {part}")

    # Prepare buckets initialized with descriptions if available
    sem_buckets = []
    for i in range(len(labels)):
        sem_buckets.append({
            "label": labels[i],
            "description": semesters[i] if i < len(semesters) else "",
            "courses": []
        })

    # Helper: try to map compact code (e.g., FA23) to bucket index using descriptions/labels
    def sem_code_to_index(code):
        if not code:
            return None
        code = code.upper()
        # normalize season/year tokens
        season_map = {"FA": "FALL", "SP": "SPRING", "SU": "SUMMER", "WI": "WINTER"}
        season = None
        year = None
        m = re.match(r"^(FA|SP|SU|WI)(\d{2,4})$", code)
        if m:
            season = season_map.get(m.group(1), None)
            year = m.group(2)
            if len(year) == 2:
                year4 = "20" + year
            else:
                year4 = year
        else:
            year4 = None

        for idx, sem in enumerate(sem_buckets):
            desc = (sem.get("description") or "").upper()
            label = (sem.get("label") or "").upper()
            # direct match of code in desc/label
            if code in desc or code in label:
                return idx
            if season:
                if season in desc:
                    # check year variants
                    if year and (year in desc or (year4 and year4 in desc)):
                        return idx
                    # if no year present, match season only
                    if not year:
                        return idx
        return None

    # Assign blocks to buckets using block-level heuristics:
    # If number of blocks equals number of buckets -> map by index.
    # Else, for each block try sem_code in any course -> sem_code_to_index.
    # Else try to match season/year words from semester descriptions.
    # Else assign to next available bucket sequentially.
    block_to_bucket = {}
    num_blocks = len(sem_courses)
    next_seq_bucket = 0

    for b_idx, block in enumerate(sem_courses):
        mapped = None
        # 1) If any course in block contains sem_code that maps -> use it
        for raw in block:
            m = semcode_re.search(raw)
            if m:
                idx = sem_code_to_index(m.group(0).upper().replace(" ", ""))
                if idx is not None:
                    mapped = idx
                    break
        if mapped is None:
            # 2) try to detect season/year words in block text that match a semester description
            block_text = " ".join(block).upper()
            for idx, sem in enumerate(sem_buckets):
                desc = (sem.get("description") or "").upper()
                if desc and desc in block_text:
                    mapped = idx
                    break
            # 3) if counts align, map by index
            if mapped is None and num_blocks == len(sem_buckets):
                mapped = b_idx
        if mapped is None:
            # 4) fallback sequential next available (first bucket with no courses yet or next_seq_bucket)
            # prefer bucket with same label if possible; otherwise use next_seq_bucket
            for idx in range(len(sem_buckets)):
                if len(sem_buckets[idx]["courses"]) == 0:
                    mapped = idx
                    break
            if mapped is None:
                mapped = min(next_seq_bucket, len(sem_buckets) - 1)
        block_to_bucket[b_idx] = mapped
        # advance next_seq_bucket just after mapped to reduce bunching
        next_seq_bucket = min(mapped + 1, len(sem_buckets) - 1)

    # Now parse and assign each course in each block; allow item-level sem_code to override block mapping
    for b_idx, block in enumerate(sem_courses):
        target_idx = block_to_bucket.get(b_idx, 0)
        for raw in block:
            p = parse_course_line(raw)
            # item-level override
            if p.get("_sem_code"):
                override_idx = sem_code_to_index(p.get("_sem_code"))
                if override_idx is not None:
                    target_idx = override_idx
            # ensure target_idx valid
            if target_idx >= len(sem_buckets):
                target_idx = len(sem_buckets) - 1
            # ensure semester label field present
            if not p.get("semester"):
                p["semester"] = sem_buckets[target_idx].get("label", "")
            p.pop("_sem_code", None)
            sem_buckets[target_idx]["courses"].append(p)

    # If there were no grouped blocks but sem_courses empty, still check for semesters list to create empties
    if not sem_courses and semesters:
        # ensure sem_buckets already created above
        pass

    # Build final data
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



# UPDATED: Navigate to Student Services instead of Faculty Services
wait.until(EC.element_to_be_clickable((By.XPATH, "//img[@alt='Banner Student Self Service logo']")))
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
    print("✅ Raw Header Text:", vnum_text)

    # Example: "Student Profile – Jordan A. Broomfield (V00679148)"
    match = re.search(r"Student Profile\s*[–-]\s*(.+)\s+\((V\d+)\)", vnum_text)
    if match:
        student_name = match.group(1).strip()
        vnumber = match.group(2).strip()
        print(f"✅ Name: {student_name}")
        print(f"✅ V-Number: {vnumber}")
    else:
        print("⚠️ Could not parse name and V-number from:", vnum_text)

except TimeoutException:
    print("❌ Could not locate the Student Profile title element quickly.")
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


