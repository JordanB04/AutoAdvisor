import advise
import re
import os

def find_advisor(name, config_file, timestamp):
    advisor_path = "advisors/" + timestamp
    advisors = [f for f in os.listdir(advisor_path)]
    for advisor in advisors:
        #print(advisor)
        fpath = "advisors/" + timestamp + "/" + advisor + "/" + name + "/" + config_file.split('/')[-1].split('.')[0] + "/courses.txt"
        if os.path.exists(fpath):
            return advisor

def main(fullname, config_file, vnums, names, sem_flag, timestamp):
    counter = 0
    for name in fullname:
        advisor = find_advisor(name, config_file, timestamp)
        name = name.strip()
        f1 = open("advisors/" + timestamp + "/" + advisor + "/" + name + "/" + config_file.split('/')[-1].split('.')[0] + "/courses.txt", "r")
        f2 = open("advisors/" + timestamp + "/" + advisor + "/" + name + "/" + config_file.split('/')[-1].split('.')[0] + "/semesters.txt", "r")

        print("Formatting Transcript for " + name + "...")
        print(vnums[counter])

        #Read semesters from file and insert it into list semesters
        semesters = []
        for line in f2:
            if len(line) > 2:
                line=line.strip()
                sem = ''
                #print(line)
                if re.search('Term : Spring', line):
                    sem = 'SP' + line[-2:]
                elif re.search('Term : Summer', line):
                    sem = 'SU' + line[-2:]
                elif re.search('Term : Fall', line):
                    sem = 'FA' + line[-2:]
                elif re.search('Term : Winter', line):
                    sem = 'WI' + line[-2:]
                else:
                    sem = 'N/A'
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
        advise.main(courses, name, config_file, names[counter], vnums[counter], advisor, sem_flag, timestamp)
        counter += 1
