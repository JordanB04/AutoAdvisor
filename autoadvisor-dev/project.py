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
import os #used for read/write to files
import re #used for regular expressions
import sys #used to stop execution under certain circumstances
import preprocess

version = "2.4.4-Student"

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

# MAIN EXECUTION STARTS HERE
#Gets student login credentials
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

# Enter username
wait.until(EC.visibility_of_element_located((By.ID, "input28")))
uid = driver.find_element(By.ID, "input28")
uid.send_keys(username)

# Enter password
wait.until(EC.visibility_of_element_located((By.ID, "input62")))
pwd = driver.find_element(By.ID, "input62")
pwd.send_keys(password)

# Click login/submit button
driver.find_element(By.CSS_SELECTOR, ".button").click()

wait = WebDriverWait(driver, 2)

try:
    wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Verify with something else")))
    driver.find_element(By.LINK_TEXT, "Verify with something else").click()
except TimeoutException:
    pass

wait = WebDriverWait(driver, 600)

# Get authentication method from student
auth_type = student.get_verify_method()

# --- New authentication selection block ---
import time
wait.until(EC.visibility_of_all_elements_located((By.CSS_SELECTOR, ".authenticator-row:nth-child(2) .button")))
#auth_buttons = driver.find_elements(By.CSS_SELECTOR, ".authenticator-row .button")
auth_buttons = driver.find_elements(By.CSS_SELECTOR, ".authenticator-row:nth-child(2) .button")

print("Available authentication methods:")
for btn in auth_buttons:
    print(btn.text)  # Print the text of each button for debugging

# Select the correct button based on auth_type

# Map dropdown selection to correct authenticator button
selected = False
if auth_type == "Okta 2FA Code":
    try:
        btn = driver.find_element(By.CSS_SELECTOR, ".authenticator-row:nth-child(1) .button")
        btn.click()
        print("Selected Okta 2FA Code (nth-child(1))")
        selected = True
    except Exception as e:
        print(f"Error selecting Okta 2FA Code: {e}")
elif auth_type == "Okta Push Notification":
    try:
        btn = driver.find_element(By.CSS_SELECTOR, ".authenticator-row:nth-child(2) .button")
        btn.click()
        print("Selected Okta Push Notification (nth-child(2))")
        selected = True
    except Exception as e:
        print(f"Error selecting Okta Push Notification: {e}")

if not selected:
    print(f"Authentication method '{auth_type}' not found or not handled. Defaulting to first available.")
    auth_buttons[0].click()




# UPDATED: Navigate to Student Services instead of Faculty Services
wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@aria-label='launch app Banner Self Service Student 9']")))
driver.find_element(By.XPATH, "//a[@aria-label='launch app Banner Self Service Student 9']").click()

wait = WebDriverWait(driver, 10)

original_window = driver.current_window_handle

for window_handle in driver.window_handles:
    if window_handle != original_window:
        driver.switch_to.window(window_handle)
        
second_window = driver.current_window_handle

# UPDATED: Navigate to student's own transcript
wait.until(EC.title_is("Student Services Dashboard"))
driver.find_element(By.LINK_TEXT, "Academic Transcript").click()

# Process the student's own transcript
sem_flag = student.get_sem_flag()

dt = datetime.now()
timestamp = dt.strftime("%b") + "-" + str(dt.day) + "-" + str(dt.year) + "-" + str(dt.hour) + "-" + str(dt.minute) + "-" + str(dt.second)

# Create status window for single student processing

# --- Old authentication block commented out ---
# match auth_type:
#     ...

# UPDATED: Process the student's own data
try:
    preprocess.main([student_id], config_file, [student_id], [[student_id]], sem_flag, timestamp)
    print('Program complete! Check files for your advisory report.')
    messagebox.showinfo("Success", f"Your transcript analysis is complete!\nCheck the folder: my_transcript/{timestamp}/")
except Exception as e:
    print(f'Error in preprocessing: {e}')
    messagebox.showerror("Error", f"Error processing your data: {e}")